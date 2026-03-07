"""Governance rules engine and validation."""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from aesdk.core.errors import RuleEvaluationError

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


def _cluster_hierarchy_rank(level: str | None) -> int:
    order = ["individual", "firm", "school", "county", "state", "region", "country"]
    if level is None:
        return -1
    try:
        return order.index(level)
    except ValueError:
        return -1


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
        values = [bool(self.visit(v)) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
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
    except Exception:
        return False


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


class ValidationContext:
    def __init__(self, pap: dict[str, Any], proposal: dict[str, Any]):
        self._pap = pap
        self._proposal = proposal

    def as_dict(self) -> dict[str, Any]:
        data = self._pap.get("data", {})
        identification = self._pap.get("identification", {})
        did = self._pap.get("did_block", {})
        robustness = self._pap.get("robustness", {})
        covariates = identification.get("covariates", {})

        context: dict[str, Any] = {
            "data": data,
            "did_block": did,
            "robustness": robustness,
            "covariates": covariates,
            "data_structure": data.get("structure"),
            "N": data.get("N"),
            "T": data.get("T"),
            "G": data.get("G"),
            "time_invariant_vars": data.get("time_invariant_vars", []),
            "identification_strategy": identification.get("strategy"),
            "estimator": self._proposal.get("estimator", identification.get("strategy")),
            "standard_errors": self._proposal.get("standard_errors", identification.get("standard_errors")),
            "clustering_level": self._proposal.get("clustering", identification.get("clustering")),
            "treatment_assignment_level": self._proposal.get("treatment_level"),
            "parallel_trends_test": did.get("parallel_trends_test", False),
            "staggered_adoption": did.get("staggered_adoption", False),
            "event_study_leads_lags": did.get("event_study_leads_lags"),
            "control_group": did.get("control_group"),
            "control_group_justification": did.get("control_group_justification"),
            "placebo_test": did.get("placebo_test", False),
            "goodman_bacon_decomposition": did.get("goodman_bacon_decomposition", False),
            "hausman_test_documented": did.get("hausman_test_documented", False),
            "n_covariates": len(covariates.get("mandatory", [])) + len(covariates.get("optional", [])),
            "citation_report": self._proposal.get("citation_report"),
        }
        return context


class Validator:
    def __init__(self, registry: RuleRegistry | None = None):
        self.registry = registry or RuleRegistry()

    def validate(self, pap: dict[str, Any], proposal: dict[str, Any]) -> ValidationResult:
        context = ValidationContext(pap, proposal).as_dict()
        violations: list[RuleViolation] = []
        for rule in self.registry.all_rules:
            estimators = rule.get("estimators") or []
            structures = rule.get("data_structures") or []
            if estimators and context.get("estimator") not in estimators:
                continue
            if structures and context.get("data_structure") not in structures:
                continue
            if _evaluate_condition((rule.get("condition") or "").strip(), context):
                violations.append(
                    RuleViolation(
                        rule_id=rule.get("id", "UNKNOWN"),
                        rule_name=rule.get("name", "Unnamed Rule"),
                        severity=Severity(rule.get("severity", "warning")),
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
