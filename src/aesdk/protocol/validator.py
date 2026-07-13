"""Governance rules engine and validation."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from aesdk.core.errors import RuleEvaluationError
from aesdk.governance.policy import ConformanceLevel

DEFAULT_RULES_DIR = Path(__file__).resolve().parents[1] / "governance" / "rules"


class Severity(str, Enum):
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class RuleViolation:
    rule_id: str
    rule_name: str
    severity: Severity
    message: str
    guidance: str
    citation: str
    source_file: str


@dataclass
class ValidationResult:
    status: str
    violations: list[RuleViolation] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return self.status == "block"


class RuleRegistry:
    def __init__(self, rules_dir: Path = DEFAULT_RULES_DIR):
        self.rules_dir = rules_dir
        self._rules: list[dict[str, Any]] = []
        self._loaded_files: list[str] = []
        self._load_all()

    def _load_all(self) -> None:
        if not self.rules_dir.exists():
            return
        for rule_file in sorted(self.rules_dir.glob("*.rules.yaml")):
            self._load_file(rule_file)

    def _load_file(self, path: Path) -> None:
        with path.open("r", encoding="utf-8") as handle:
            doc = yaml.safe_load(handle) or {}
        for rule in doc.get("rules", []):
            rule["_source_file"] = path.name
            self._rules.append(rule)
        self._loaded_files.append(path.name)

    @property
    def all_rules(self) -> list[dict[str, Any]]:
        return list(self._rules)


class AttrDict(dict):
    def __getattr__(self, item: str) -> Any:
        value = self.get(item)
        if isinstance(value, dict):
            return AttrDict(value)
        if isinstance(value, list):
            return [AttrDict(v) if isinstance(v, dict) else v for v in value]
        return value


def _cluster_level_parts(level: Any) -> list[str]:
    if level is None:
        return []
    if isinstance(level, (list, tuple, set)):
        return [str(item).strip().lower() for item in level if str(item).strip()]
    text = str(level).strip().lower()
    if not text:
        return []
    for separator in [",", ";", "+", "&", "/"]:
        text = text.replace(separator, " ")
    if "-" in text:
        text = text.replace("-", " ")
    return [part for part in text.split() if part]


def _normalized_phrase(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).strip().lower()
    for separator in ["-", "/", "\\", ",", ";", ":"]:
        text = text.replace(separator, " ")
    return "_".join(part for part in text.split() if part)


def _normalized_standard_errors(value: Any) -> Any:
    if value is None:
        return None
    text = _normalized_phrase(value)
    if not text:
        return value
    cluster_negations = {
        "not_clustered",
        "not_cluster",
        "no_cluster",
        "no_clustering",
        "non_clustered",
        "unclustered",
        "without_cluster",
        "without_clustering",
    }
    if (
        text in cluster_negations
        or any(text.startswith(f"{item}_") for item in cluster_negations)
        or any(text.endswith(f"_{item}") for item in cluster_negations)
        or "not_cluster" in text
        or "no_cluster" in text
        or "unclustered" in text
        or "without_cluster" in text
    ):
        return value
    if "two_way" in text and "cluster" in text:
        return "two-way-cluster"
    if "wild" in text and "cluster" in text:
        return "wild-cluster-bootstrap"
    if "driscoll" in text or "kraay" in text:
        return "driscoll-kraay"
    if text in {"robust_cluster", "cluster_robust", "clustered_robust"}:
        return "robust-cluster"
    if "cluster" in text:
        return "cluster"
    aliases = {
        "hc1": "HC1",
        "hc2": "HC2",
        "hc3": "HC3",
        "heteroskedasticity_robust": "HC1",
        "heteroskedastic_robust": "HC1",
        "robust": "HC1",
        "iid": "conventional",
        "classical": "conventional",
    }
    return aliases.get(text, value)


def _text_missing(value: Any) -> bool:
    text = _normalized_phrase(value)
    return text in {
        "",
        "tbd",
        "todo",
        "to_be_determined",
        "unknown",
        "na",
        "n_a",
        "none",
        "not_applicable",
        "undisclosed",
        "not_disclosed",
        "unavailable",
        "researcher_review_required",
        "requires_researcher_review",
        "draft_requires_researcher_review",
    }


def _code_languages_from_files(values: Any) -> list[str]:
    languages: list[str] = []
    for value in _as_list(values):
        suffix = Path(str(value)).suffix.lower()
        if suffix == ".py":
            languages.append("python")
        elif suffix == ".r":
            languages.append("r")
        elif suffix == ".do":
            languages.append("stata")
    return sorted(set(languages))


def _normalized_languages(values: Any) -> list[str]:
    return sorted({str(value).strip().lower() for value in _as_list(values) if str(value).strip()})


def _ai_code_language_mismatch(declared_values: Any, code_file_values: Any) -> bool:
    declared = set(_normalized_languages(declared_values))
    recognized = set(_code_languages_from_files(code_file_values))
    if not declared or "none" in declared:
        return False
    if "mixed" in declared:
        return False
    if not recognized:
        return False
    return declared != recognized


def _looks_like_agent_tool_model(value: Any) -> bool:
    text = _normalized_phrase(value)
    if text in {
        "codex",
        "codex_cli",
        "openai_codex",
        "claude_code",
        "claude",
        "claude_cli",
        "vs_code",
        "vscode",
        "vs_code_copilot",
        "vscode_copilot",
        "github_copilot",
        "copilot",
        "open_code",
        "opencode",
        "cursor",
        "windsurf",
    }:
        return True
    return any(token in text.split("_") for token in {"codex", "copilot"})


def _cluster_level_missing(level: Any) -> bool:
    return not _cluster_level_parts(level)


def _cluster_level_count(level: Any) -> int:
    return len(_cluster_level_parts(level))


def _cluster_hierarchy_rank(level: Any) -> int:
    order = [
        "individual",
        "person",
        "student",
        "patient",
        "worker",
        "child",
        "household",
        "classroom",
        "clinic",
        "firm",
        "school",
        "village",
        "community",
        "market",
        "tract",
        "zip",
        "district",
        "county",
        "state",
        "region",
        "country",
    ]
    parts = _cluster_level_parts(level)
    if not parts:
        return -1
    return max((order.index(part) for part in parts if part in order), default=-1)


class _SafeEval(ast.NodeVisitor):
    def __init__(self, context: dict[str, Any]):
        self.context = context

    def visit_Expression(self, node: ast.Expression) -> Any:
        return self.visit(node.body)

    def visit_Name(self, node: ast.Name) -> Any:
        if node.id in {"true", "True"}:
            return True
        if node.id in {"false", "False"}:
            return False
        if node.id in {"null", "None"}:
            return None
        return self.context.get(node.id)

    def visit_Constant(self, node: ast.Constant) -> Any:
        return node.value

    def visit_List(self, node: ast.List) -> Any:
        return [self.visit(elt) for elt in node.elts]

    def visit_Tuple(self, node: ast.Tuple) -> Any:
        return tuple(self.visit(elt) for elt in node.elts)

    def visit_Attribute(self, node: ast.Attribute) -> Any:
        base = self.visit(node.value)
        if isinstance(base, dict):
            base = AttrDict(base)
        return getattr(base, node.attr)

    def visit_Subscript(self, node: ast.Subscript) -> Any:
        base = self.visit(node.value)
        index = self.visit(node.slice)
        return base[index]

    def visit_Index(self, node: ast.Index) -> Any:
        return self.visit(node.value)

    def visit_BoolOp(self, node: ast.BoolOp) -> Any:
        if isinstance(node.op, ast.And):
            for value in node.values:
                if not bool(self.visit(value)):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for value in node.values:
                if bool(self.visit(value)):
                    return True
            return False
        raise RuleEvaluationError("Unsupported bool operator")

    def visit_UnaryOp(self, node: ast.UnaryOp) -> Any:
        if isinstance(node.op, ast.Not):
            return not bool(self.visit(node.operand))
        raise RuleEvaluationError("Unsupported unary operator")

    def visit_BinOp(self, node: ast.BinOp) -> Any:
        left = self.visit(node.left)
        right = self.visit(node.right)
        if isinstance(node.op, ast.Add):
            return left + right
        raise RuleEvaluationError("Unsupported binary operator")

    def visit_Compare(self, node: ast.Compare) -> Any:
        left = self.visit(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self.visit(comparator)
            if isinstance(op, ast.Eq):
                ok = left == right
            elif isinstance(op, ast.NotEq):
                ok = left != right
            elif isinstance(op, ast.Gt):
                ok = left > right
            elif isinstance(op, ast.GtE):
                ok = left >= right
            elif isinstance(op, ast.Lt):
                ok = left < right
            elif isinstance(op, ast.LtE):
                ok = left <= right
            elif isinstance(op, ast.In):
                ok = left in right
            elif isinstance(op, ast.NotIn):
                ok = left not in right
            elif isinstance(op, ast.Is):
                ok = left is right
            elif isinstance(op, ast.IsNot):
                ok = left is not right
            else:
                raise RuleEvaluationError("Unsupported comparison operator")
            if not ok:
                return False
            left = right
        return True

    def visit_Call(self, node: ast.Call) -> Any:
        if not isinstance(node.func, ast.Name):
            raise RuleEvaluationError("Only named calls are allowed")
        fn_name = node.func.id
        args = [self.visit(arg) for arg in node.args]
        if fn_name == "len":
            return len(args[0])
        if fn_name == "any":
            return any(args[0])
        if fn_name == "all":
            return all(args[0])
        if fn_name == "cluster_hierarchy_rank":
            return _cluster_hierarchy_rank(args[0])
        if fn_name == "cluster_level_missing":
            return _cluster_level_missing(args[0])
        if fn_name == "cluster_level_count":
            return _cluster_level_count(args[0])
        if fn_name == "text_missing":
            return _text_missing(args[0])
        raise RuleEvaluationError(f"Function '{fn_name}' is not allowed")

    def visit_GeneratorExp(self, node: ast.GeneratorExp) -> Any:
        if len(node.generators) != 1:
            raise RuleEvaluationError("Only single-generator comprehensions are supported")
        comp = node.generators[0]
        if not isinstance(comp.target, ast.Name):
            raise RuleEvaluationError("Only name targets are supported")
        iterable = self.visit(comp.iter)
        results: list[Any] = []
        for item in iterable:
            scoped = dict(self.context)
            scoped[comp.target.id] = item
            evaluator = _SafeEval(scoped)
            if all(bool(evaluator.visit(condition)) for condition in comp.ifs):
                results.append(evaluator.visit(node.elt))
        return results

    def generic_visit(self, node: ast.AST) -> Any:
        raise RuleEvaluationError(f"Unsupported expression component: {type(node).__name__}")


def _evaluate_condition(condition: str, context: dict[str, Any]) -> bool:
    if not condition:
        return False
    try:
        tree = ast.parse(condition, mode="eval")
        return bool(_SafeEval(context).visit(tree))
    except Exception as exc:
        raise RuleEvaluationError(f"Rule condition failed to evaluate: {condition}") from exc


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, set):
        return list(value)
    if isinstance(value, str):
        return [value] if value.strip() else []
    return [value]


def _file_missing_count(values: Any, base_dirs: list[Path]) -> int:
    missing = 0
    for value in _as_list(values):
        path = Path(str(value))
        candidates = [path] if path.is_absolute() else [base / path for base in base_dirs]
        if not any(candidate.exists() and candidate.is_file() for candidate in candidates):
            missing += 1
    return missing


def _file_text_match_count(values: Any, base_dirs: list[Path], marker: str) -> int:
    matches = 0
    for value in _as_list(values):
        path = Path(str(value))
        candidates = [path] if path.is_absolute() else [base / path for base in base_dirs]
        for candidate in candidates:
            if candidate.exists() and candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8-sig")
                except UnicodeDecodeError:
                    text = candidate.read_text(encoding="cp1252")
                if marker in text:
                    matches += 1
                break
    return matches


def _file_trivial_text_count(values: Any, base_dirs: list[Path]) -> int:
    trivial = 0
    for value in _as_list(values):
        path = Path(str(value))
        candidates = [path] if path.is_absolute() else [base / path for base in base_dirs]
        resolved = next((candidate for candidate in candidates if candidate.exists() and candidate.is_file()), None)
        if resolved is None:
            continue
        try:
            text = resolved.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            text = resolved.read_text(encoding="cp1252")
        if not text.strip():
            trivial += 1
    return trivial


def _estimator_matches(active: Any, rule_estimators: list[Any]) -> bool:
    if not rule_estimators:
        return True
    aliases = {
        "SynthControl": "SyntheticControl",
    }
    active_values = _as_list(active)
    if not active_values:
        active_values = [""]
    candidates: set[str] = set()
    for value in active_values:
        active_text = str(value) if value is not None else ""
        candidates.add(active_text)
        candidates.add(aliases.get(active_text, active_text))
    return any(str(item) in candidates for item in rule_estimators)


def _normalized_citation_report(value: Any) -> Any:
    if value is None:
        return None
    if not isinstance(value, dict):
        return value
    report = dict(value)
    report.setdefault("hallucinated_count", 0)
    report.setdefault("uncertain_count", 0)
    report.setdefault("unreachable_count", 0)
    report.setdefault("invalid_format_count", 0)
    return report


def _first_present(*values: Any) -> Any:
    for value in values:
        if isinstance(value, str):
            if not _text_missing(value):
                return value
            continue
        if value is not None:
            return value
    return None


def _format_reference(ref: dict[str, Any] | str | None) -> str:
    if isinstance(ref, str):
        return ref
    if not ref:
        return "No citation provided"
    parts: list[str] = []
    for key in ["authors", "book", "journal", "year", "chapter", "section", "title"]:
        value = ref.get(key)
        if value is not None:
            parts.append(str(value))
    return ", ".join(parts) if parts else "No citation provided"


def _apply_conformance_to_severity(
    severity: Severity,
    conformance: ConformanceLevel,
    rule: dict[str, Any] | None = None,
) -> Severity:
    if conformance == ConformanceLevel.BASIC:
        return severity
    if (
        conformance == ConformanceLevel.STRICT
        and severity == Severity.WARNING
        and not (rule and rule.get("strict_escalates") is False)
    ):
        return Severity.ERROR
    if conformance == ConformanceLevel.REGULATED and severity in {Severity.WARNING, Severity.INFO}:
        return Severity.ERROR
    return severity


class ValidationContext:
    def __init__(
        self,
        pap: dict[str, Any],
        proposal: dict[str, Any],
        artifact_base_dirs: list[Path] | None = None,
        artifact_base_dirs_by_source: dict[str, Path] | None = None,
    ):
        self._pap = pap
        self._proposal = proposal
        self._artifact_base_dirs = artifact_base_dirs or [Path.cwd()]
        self._artifact_base_dirs_by_source = artifact_base_dirs_by_source or {}

    def as_dict(self) -> dict[str, Any]:
        data = self._pap.get("data", {})
        identification = self._pap.get("identification", {})
        did = self._pap.get("did_block", {})
        iv = self._pap.get("iv_block", {})
        rdd = self._merged_block("rdd_block")
        matching = self._merged_block("matching_block")
        rct = self._merged_block("rct_block")
        synthetic_control = self._merged_block("synthetic_control_block")
        nonlinear_did = self._merged_block("nonlinear_did_block")
        gmm = self._merged_block("gmm_block")
        limited = self._merged_block("limited_dependent_block")
        time_series = self._merged_block("time_series_block")
        mle = self._merged_block("mle_block")
        dml = self._merged_block("dml_block")
        structural = self._merged_block("structural_block")
        nonparametric = self._merged_block("nonparametric_block")
        bayesian = self._merged_block("bayesian_block")
        garch = self._merged_block("garch_block")
        ai_use, ai_use_provenance = self._merged_block_with_provenance("ai_use")
        robustness = self._pap.get("robustness", {})
        covariates = identification.get("covariates", {})
        outcome_variable = self._proposal.get("outcome_variable", identification.get("outcome_variable"))
        treatment_variable = self._proposal.get("treatment_variable", identification.get("treatment_variable"))
        standard_errors = _normalized_standard_errors(
            self._proposal.get("standard_errors", identification.get("standard_errors"))
        )
        clustering_level = self._proposal.get("clustering", identification.get("clustering"))
        fixed_effects = self._proposal.get("fixed_effects", identification.get("fixed_effects", []))
        estimator = self._proposal.get("estimator", identification.get("strategy"))
        design_origin = _first_present(self._proposal.get("design_origin"), identification.get("design_origin"))
        active_estimators = _as_list(estimator)
        if identification.get("strategy") not in active_estimators:
            active_estimators.extend(_as_list(identification.get("strategy")))
        if design_origin == "experimental_rct" or rct:
            active_estimators.append("RCT")
            if rct.get("estimand"):
                active_estimators.append(rct.get("estimand"))

        context: dict[str, Any] = {
            "data": data,
            "proposal": self._proposal,
            "did_block": did,
            "iv_block": iv,
            "rdd_block": rdd,
            "matching_block": matching,
            "rct_block": rct,
            "synthetic_control_block": synthetic_control,
            "nonlinear_did_block": nonlinear_did,
            "gmm_block": gmm,
            "limited_dependent_block": limited,
            "time_series_block": time_series,
            "ai_use": ai_use,
            "robustness": robustness,
            "covariates": covariates,
            "data_structure": data.get("structure"),
            "panel_unit": data.get("unit"),
            "panel_time": data.get("time", data.get("time_index")),
            "N": data.get("N"),
            "T": data.get("T"),
            "G": data.get("G"),
            "time_invariant_vars": data.get("time_invariant_vars", []),
            "identification_strategy": identification.get("strategy"),
            "design_origin": design_origin,
            "design_note": _first_present(self._proposal.get("design_note"), identification.get("design_note")),
            "estimator": estimator,
            "active_estimators": sorted({str(item) for item in active_estimators if item is not None and str(item)}),
            "task_required_estimator": _first_present(
                self._proposal.get("task_required_estimator"),
                did.get("task_required_estimator"),
            ),
            "task_required_estimator_justification": _first_present(
                self._proposal.get("task_required_estimator_justification"),
                did.get("task_required_estimator_justification"),
            ),
            "twfe_prescribed_by_task": _first_present(
                self._proposal.get("task_required_estimator"),
                did.get("task_required_estimator"),
            )
            == "TWFE"
            and not _text_missing(
                _first_present(
                    self._proposal.get("task_required_estimator_justification"),
                    did.get("task_required_estimator_justification"),
                )
            ),
            "outcome_variable": outcome_variable,
            "treatment_variable": treatment_variable,
            "fixed_effects": _as_list(fixed_effects),
            "within_variation_documented": self._proposal.get(
                "within_variation_documented",
                identification.get("within_variation_documented", False),
            ),
            "time_invariant_regressors": _as_list(self._proposal.get("time_invariant_regressors", [])),
            "time_invariant_interpreted": self._proposal.get("time_invariant_interpreted", False),
            "standard_errors": standard_errors,
            "clustering_level": clustering_level,
            "treatment_assignment_level": self._proposal.get("treatment_level"),
            "parallel_trends_test": did.get("parallel_trends_test", False),
            "staggered_adoption": did.get("staggered_adoption", False),
            "event_study_leads_lags": did.get("event_study_leads_lags"),
            "control_group": did.get("control_group"),
            "control_group_justification": did.get("control_group_justification"),
            "placebo_test": did.get("placebo_test", False),
            "goodman_bacon_decomposition": did.get("goodman_bacon_decomposition", False),
            "hausman_test_documented": did.get("hausman_test_documented", False),
            "no_anticipation": did.get("no_anticipation", False),
            "non_absorbing_treatment": did.get("non_absorbing_treatment", False),
            "parallel_trends_transformation": did.get("parallel_trends_transformation"),
            "sensitivity_analysis": did.get(
                "sensitivity_analysis", robustness.get("sensitivity_analysis", False)
            ),
            "covariate_adjustment": did.get("covariate_adjustment"),
            "iv_instruments": _as_list(iv.get("instruments", [])),
            "first_stage_f_threshold": iv.get("first_stage_f_threshold", 10),
            "first_stage_f_stat": self._proposal.get("first_stage_f_stat"),
            "exclusion_restriction_documented": self._proposal.get(
                "exclusion_restriction_documented",
                iv.get("exclusion_restriction_documented", False),
            ),
            "n_covariates": len(covariates.get("mandatory", [])) + len(covariates.get("optional", [])),
            "citation_report": _normalized_citation_report(self._proposal.get("citation_report")),
            "citation_uncertainty_acknowledged": self._proposal.get("citation_uncertainty_acknowledged", False),
            "rule_citation_verified": self._proposal.get("rule_citation_verified", True),
            "causal_claim": self._proposal.get("causal_claim", identification.get("causal_claim", False)),
            "identification_assumption_documented": self._proposal.get(
                "identification_assumption_documented",
                bool(identification.get("strategy")),
            ),
            "support_check": self._proposal.get("support_check", robustness.get("support_check")),
            "post_hoc_covariate_selection": self._proposal.get("post_hoc_covariate_selection", False),
            "conventional_se_justified": self._proposal.get("conventional_se_justified", False),
            "specification_curve": self._proposal.get("specification_curve", robustness.get("specification_curve")),
            "rdd_running_variable": rdd.get("running_variable"),
            "rdd_cutoff": rdd.get("cutoff"),
            "rdd_bandwidth_rule": rdd.get("bandwidth_rule"),
            "rdd_sharp_or_fuzzy": rdd.get("sharp_or_fuzzy"),
            "rdd_manipulation_check": rdd.get("manipulation_check"),
            "rdd_covariate_continuity": rdd.get("covariate_continuity"),
            "rdd_bandwidth_sensitivity": rdd.get("bandwidth_sensitivity"),
            "rdd_polynomial_order": rdd.get("polynomial_order"),
            "matching_method": matching.get("method"),
            "matching_pre_treatment_covariates": _as_list(matching.get("pre_treatment_covariates", [])),
            "matching_post_treatment_covariates": _as_list(matching.get("post_treatment_covariates", [])),
            "matching_estimand": matching.get("estimand"),
            "matching_balance_diagnostics": matching.get("balance_diagnostics"),
            "matching_common_support": matching.get("common_support"),
            "matching_effective_sample_size": matching.get("effective_sample_size"),
            "matching_balance_passed": matching.get("balance_passed"),
            "matching_discarded_units_reported": matching.get("discarded_units_reported"),
            "rct_randomization_unit": rct.get("randomization_unit"),
            "rct_assignment_variable": rct.get("assignment_variable"),
            "rct_treatment_arms": _as_list(rct.get("treatment_arms", [])),
            "rct_control_group": rct.get("control_group"),
            "rct_assignment_probability": rct.get("assignment_probability"),
            "rct_random_seed": rct.get("random_seed"),
            "rct_assignment_file": rct.get("assignment_file"),
            "rct_randomization_method": rct.get("randomization_method"),
            "rct_strata": _as_list(rct.get("strata", [])),
            "rct_stratification_used": rct.get("stratification_used", False),
            "rct_cluster_randomized": rct.get("cluster_randomized", False),
            "rct_compliance_type": _normalized_phrase(rct.get("compliance_type")),
            "rct_estimand": rct.get("estimand"),
            "rct_takeup_variable": rct.get("takeup_variable"),
            "rct_compliance_rate": rct.get("compliance_rate"),
            "rct_exclusion_for_late_documented": rct.get("exclusion_for_late_documented", False),
            "rct_monotonicity_documented": rct.get("monotonicity_documented", False),
            "rct_baseline_balance_check": rct.get("baseline_balance_check"),
            "rct_attrition_check": rct.get("attrition_check"),
            "rct_attrition_differential": rct.get("attrition_differential", False),
            "rct_attrition_sensitivity_plan": rct.get("attrition_sensitivity_plan"),
            "rct_spillover_plan": rct.get("spillover_plan"),
            "rct_spillover_risk": rct.get("spillover_risk", False),
            "rct_spillover_measurement_plan": rct.get("spillover_measurement_plan"),
            "rct_sutva_rationale": rct.get("sutva_rationale"),
            "rct_power_calculation": rct.get("power_calculation"),
            "rct_trial_registration": rct.get("trial_registration"),
            "rct_pap_registered": rct.get("pap_registered"),
            "rct_randomization_inference_plan": rct.get("randomization_inference_plan"),
            "synth_treated_unit": synthetic_control.get("treated_unit"),
            "synth_donor_pool": _as_list(synthetic_control.get("donor_pool", [])),
            "synth_intervention_time": synthetic_control.get("intervention_time"),
            "synth_predictors": _as_list(synthetic_control.get("predictors", [])),
            "synth_pre_treatment_fit": synthetic_control.get("pre_treatment_fit"),
            "synth_donor_weights": synthetic_control.get("donor_weights"),
            "synth_placebo_tests": synthetic_control.get("placebo_tests"),
            "synth_donor_pool_sensitivity": synthetic_control.get("donor_pool_sensitivity"),
            "synth_contaminated_donors": _as_list(synthetic_control.get("contaminated_donors", [])),
            "nonlinear_did_outcome_family": nonlinear_did.get("outcome_family"),
            "nonlinear_did_target_scale": nonlinear_did.get("target_scale"),
            "nonlinear_did_effect_transformation": nonlinear_did.get("effect_transformation"),
            "nonlinear_did_functional_form_sensitivity": nonlinear_did.get("functional_form_sensitivity"),
            "gmm_moment_conditions": _as_list(gmm.get("moment_conditions", [])),
            "gmm_parameters": _as_list(gmm.get("parameters", [])),
            "gmm_instruments": _as_list(gmm.get("instruments", [])),
            "gmm_weighting_matrix": gmm.get("weighting_matrix"),
            "gmm_identification_rank": gmm.get("identification_rank"),
            "gmm_overidentification_diagnostic": gmm.get("overidentification_diagnostic"),
            "gmm_weighting_sensitivity": gmm.get("weighting_sensitivity"),
            "gmm_many_instruments": gmm.get("many_instruments", False),
            "limited_outcome_type": limited.get("outcome_type"),
            "limited_link_or_family": limited.get("link_or_family"),
            "limited_target_effect": limited.get("target_effect"),
            "limited_marginal_effect_plan": limited.get("marginal_effect_plan"),
            "limited_reporting_raw_coefficient": limited.get("reporting_raw_coefficient", False),
            "limited_convergence_check": limited.get("convergence_check"),
            "limited_separation_check": limited.get("separation_check"),
            "limited_overdispersion_check": limited.get("overdispersion_check"),
            "time_index": time_series.get("time_index", data.get("time_index")),
            "time_frequency": time_series.get("frequency", data.get("frequency")),
            "stationarity_plan": time_series.get("stationarity_plan"),
            "lag_order_plan": time_series.get("lag_order_plan"),
            "forecast_or_causal_target": time_series.get("forecast_or_causal_target"),
            "autocorrelation_diagnostic": time_series.get("autocorrelation_diagnostic"),
            "forecast_backtest": time_series.get("forecast_backtest"),
            "lookahead_bias": time_series.get("lookahead_bias", False),
            "mle_distribution": _first_present(mle.get("distribution"), mle.get("likelihood")),
            "mle_convergence_confirmed": mle.get("convergence_confirmed", False),
            "mle_standard_error_type": _normalized_phrase(mle.get("standard_error_type")) or None,
            "dml_cross_fitting": bool(dml.get("cross_fitting"))
            or bool(dml.get("cross_fitting_folds")),
            "dml_orthogonal_score": bool(dml.get("orthogonal_score")),
            "structural_model": structural.get("model"),
            "structural_identification_argument": structural.get("identification_argument"),
            "structural_prices_endogenous": structural.get("prices_endogenous", False),
            "structural_instruments": _as_list(structural.get("instruments", [])),
            "structural_counterfactual": structural.get("counterfactual", False),
            "structural_support_note": bool(structural.get("support_note")),
            "nonparametric_bandwidth_rule": nonparametric.get("bandwidth_rule"),
            "nonparametric_continuous_regressor_count": nonparametric.get(
                "continuous_regressor_count",
                len(_as_list(nonparametric.get("continuous_regressors", []))),
            ),
            "nonparametric_semiparametric_restriction": bool(
                nonparametric.get("semiparametric_restriction", False)
            ),
            "bayesian_priors": bayesian.get("priors"),
            "bayesian_convergence_checked": bayesian.get("convergence_checked", False),
            "bayesian_prior_sensitivity_checked": bayesian.get("prior_sensitivity_checked", False),
            "garch_arch_test_planned": bool(garch.get("arch_test_planned"))
            or not _text_missing(garch.get("arch_test_plan")),
            "garch_mean_model": garch.get("mean_model"),
            "garch_innovation_distribution": garch.get("innovation_distribution"),
            "ai_used": ai_use.get("used", False),
            "ai_role": ai_use.get("role"),
            "ai_roles": _as_list(ai_use.get("role", [])),
            "ai_languages": _normalized_languages(ai_use.get("languages", [])),
            "ai_code_file_languages": _code_languages_from_files(ai_use.get("code_files", [])),
            "ai_code_language_has_none": "none" in _normalized_languages(ai_use.get("languages", [])),
            "ai_code_language_mismatch": _ai_code_language_mismatch(ai_use.get("languages", []), ai_use.get("code_files", [])),
            "ai_provider": ai_use.get("provider"),
            "ai_model": ai_use.get("model"),
            "ai_model_looks_like_agent_tool": _looks_like_agent_tool_model(ai_use.get("model")),
            "ai_agent_tool": ai_use.get("agent_tool"),
            "ai_model_metadata_source": ai_use.get("model_metadata_source"),
            "ai_model_metadata_unavailable_reason": ai_use.get("model_metadata_unavailable_reason"),
            "ai_prompts_archived": ai_use.get("prompts_archived", False),
            "ai_raw_outputs_archived": ai_use.get("raw_outputs_archived", False),
            "ai_human_in_loop": ai_use.get("human_in_loop", False),
            "ai_human_interaction_file_count": len(_as_list(ai_use.get("human_interaction_files", []))),
            "ai_human_interaction_file_missing_count": _file_missing_count(
                ai_use.get("human_interaction_files", []),
                self._field_base_dirs("human_interaction_files", ai_use_provenance),
            ),
            "ai_human_interaction_file_trivial_count": _file_trivial_text_count(
                ai_use.get("human_interaction_files", []),
                self._field_base_dirs("human_interaction_files", ai_use_provenance),
            ),
            "ai_human_modified_code": ai_use.get("human_modified_code", False),
            "ai_human_intervention_file_count": len(_as_list(ai_use.get("human_intervention_files", []))),
            "ai_human_intervention_file_missing_count": _file_missing_count(
                ai_use.get("human_intervention_files", []),
                self._field_base_dirs("human_intervention_files", ai_use_provenance),
            ),
            "ai_human_intervention_file_trivial_count": _file_trivial_text_count(
                ai_use.get("human_intervention_files", []),
                self._field_base_dirs("human_intervention_files", ai_use_provenance),
            ),
            "ai_human_intervention_no_change_file_count": _file_text_match_count(
                ai_use.get("human_intervention_files", []),
                self._field_base_dirs("human_intervention_files", ai_use_provenance),
                "AESDK-REVIEW-DIFF: no_textual_changes",
            ),
            "ai_code_draft_file_count": len(_as_list(ai_use.get("ai_code_draft_files", []))),
            "ai_code_draft_file_missing_count": _file_missing_count(
                ai_use.get("ai_code_draft_files", []),
                self._field_base_dirs("ai_code_draft_files", ai_use_provenance),
            ),
            "ai_human_reviewed": ai_use.get("human_reviewed", False),
            "ai_review_status": ai_use.get("review_status"),
            "ai_review_file_count": len(_as_list(ai_use.get("review_files", []))),
            "ai_review_file_missing_count": _file_missing_count(
                ai_use.get("review_files", []),
                self._field_base_dirs("review_files", ai_use_provenance),
            ),
            "ai_review_file_trivial_count": _file_trivial_text_count(
                ai_use.get("review_files", []),
                self._field_base_dirs("review_files", ai_use_provenance),
            ),
            "ai_runtime_metadata_file_count": len(_as_list(ai_use.get("runtime_metadata_files", []))),
            "ai_runtime_metadata_file_missing_count": _file_missing_count(
                ai_use.get("runtime_metadata_files", []),
                self._field_base_dirs("runtime_metadata_files", ai_use_provenance),
            ),
            "ai_reviewer_role": ai_use.get("reviewer_role"),
            "ai_reproducible_without_ai": ai_use.get("reproducible_without_ai"),
            "ai_live_model_required": ai_use.get("live_model_required", False),
            "ai_output_used_as_data": ai_use.get("ai_output_used_as_data", False),
            "ai_derived_variables": _as_list(ai_use.get("ai_derived_variables", [])),
            "ai_prompt_file_count": len(_as_list(ai_use.get("prompt_files", []))),
            "ai_prompt_file_missing_count": _file_missing_count(
                ai_use.get("prompt_files", []),
                self._field_base_dirs("prompt_files", ai_use_provenance),
            ),
            "ai_output_file_count": len(_as_list(ai_use.get("output_files", []))),
            "ai_output_file_missing_count": _file_missing_count(
                ai_use.get("output_files", []),
                self._field_base_dirs("output_files", ai_use_provenance),
            ),
            "ai_input_file_count": len(_as_list(ai_use.get("input_files", []))),
            "ai_input_file_missing_count": _file_missing_count(
                ai_use.get("input_files", []),
                self._field_base_dirs("input_files", ai_use_provenance),
            ),
            "ai_code_file_count": len(_as_list(ai_use.get("code_files", []))),
            "ai_code_file_missing_count": _file_missing_count(
                ai_use.get("code_files", []),
                self._field_base_dirs("code_files", ai_use_provenance),
            ),
            "ai_qa_sample_plan": ai_use.get("qa_sample_plan"),
            "ai_sensitivity_plan": ai_use.get("sensitivity_plan"),
        }
        return context

    def _merged_block(self, name: str) -> dict[str, Any]:
        block: dict[str, Any] = {}
        pap_block = self._pap.get(name, {})
        proposal_block = self._proposal.get(name, {})
        if isinstance(pap_block, dict):
            block.update(pap_block)
        if isinstance(proposal_block, dict):
            block.update(proposal_block)
        return block

    def _merged_block_with_provenance(self, name: str) -> tuple[dict[str, Any], dict[str, str]]:
        block: dict[str, Any] = {}
        provenance: dict[str, str] = {}
        pap_block = self._pap.get(name, {})
        proposal_block = self._proposal.get(name, {})
        if isinstance(pap_block, dict):
            for key, value in pap_block.items():
                block[key] = value
                provenance[key] = "pap"
        if isinstance(proposal_block, dict):
            for key, value in proposal_block.items():
                if value is not None:
                    block[key] = value
                    provenance[key] = "proposal"
        return block, provenance

    def _field_base_dirs(self, field: str, provenance: dict[str, str]) -> list[Path]:
        source = provenance.get(field)
        if source and source in self._artifact_base_dirs_by_source:
            return [self._artifact_base_dirs_by_source[source]]
        return self._artifact_base_dirs


class Validator:
    def __init__(
        self,
        registry: RuleRegistry | None = None,
        artifact_base_dirs: list[str | Path] | None = None,
        artifact_base_dirs_by_source: dict[str, str | Path] | None = None,
    ):
        self.registry = registry or RuleRegistry()
        self.artifact_base_dirs = [Path(path) for path in (artifact_base_dirs or [Path.cwd()])]
        self.artifact_base_dirs_by_source = {
            source: Path(path) for source, path in (artifact_base_dirs_by_source or {}).items()
        }

    def validate(
        self,
        pap: dict[str, Any],
        proposal: dict[str, Any],
        conformance: ConformanceLevel = ConformanceLevel.BASIC,
    ) -> ValidationResult:
        context = ValidationContext(
            pap,
            proposal,
            artifact_base_dirs=self.artifact_base_dirs,
            artifact_base_dirs_by_source=self.artifact_base_dirs_by_source,
        ).as_dict()
        violations: list[RuleViolation] = []
        for rule in self.registry.all_rules:
            estimators = rule.get("estimators") or []
            structures = rule.get("data_structures") or []
            if not _estimator_matches(context.get("active_estimators", context.get("estimator")), estimators):
                continue
            if structures and context.get("data_structure") not in structures:
                continue
            try:
                triggered = _evaluate_condition((rule.get("condition") or "").strip(), context)
            except RuleEvaluationError as exc:
                violations.append(
                    RuleViolation(
                        rule_id=f"{rule.get('id', 'UNKNOWN')}-EVAL",
                        rule_name=f"Rule Evaluation Failed: {rule.get('name', 'Unnamed Rule')}",
                        severity=Severity.ERROR,
                        message=str(exc),
                        guidance="Fix the governance rule condition or normalize the PAP/proposal field it depends on.",
                        citation=_format_reference(rule.get("reference")),
                        source_file=rule.get("_source_file", ""),
                    )
                )
                continue
            if triggered:
                raw_severity = Severity(rule.get("severity", "warning"))
                severity = _apply_conformance_to_severity(raw_severity, conformance, rule)
                violations.append(
                    RuleViolation(
                        rule_id=rule.get("id", "UNKNOWN"),
                        rule_name=rule.get("name", "Unnamed Rule"),
                        severity=severity,
                        message=rule.get("requirement", "Requirement violated."),
                        guidance=rule.get("guidance", ""),
                        citation=_format_reference(rule.get("reference")),
                        source_file=rule.get("_source_file", ""),
                    )
                )
        if any(v.severity == Severity.ERROR for v in violations):
            status = "block"
        elif any(v.severity == Severity.WARNING for v in violations):
            status = "warn"
        else:
            status = "pass"
        return ValidationResult(status=status, violations=violations)

