"""Audit and maintain AESDK econometrics knowledge packs.

This script is the repeatable "deep-work pass" entry point for local source
updates. It scans every PDF page-by-page for method-topic signals, compares the
results to bundled knowledge packs, and writes a compact report that contains
page locators and coverage gaps without copying textbook prose.

Typical use:

    python scripts/deep_knowledge_audit.py --tools-dir tools --write-report docs/deep_knowledge_audit_report.yaml
    python scripts/deep_knowledge_audit.py --tools-dir tools --update-packs

The script intentionally stores metadata, topic hits, and scaffolds only. Human
review is still required before raising a pack from starter to reviewed/audited.
"""

from __future__ import annotations

import argparse
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


KNOWLEDGE_DIR = Path("src/aesdk/knowledge")
PACKS_DIR = KNOWLEDGE_DIR / "packs"


@dataclass(frozen=True)
class MethodBlueprint:
    method_id: str
    name: str
    keywords: list[str]
    use_when: list[str]
    do_not_use_when: list[str]
    estimators: list[str]
    data_structures: list[str]
    required_inputs: list[str]
    diagnostics: list[str]
    failure_modes: list[str]
    source_ids: list[str]


BLUEPRINTS: dict[str, MethodBlueprint] = {
    "ols_cef": MethodBlueprint(
        method_id="ols_cef",
        name="OLS / Conditional Expectation Function",
        keywords=["ordinary least squares", "conditional expectation", "heteroskedasticity", "robust standard errors"],
        use_when=["Estimating conditional mean relationships or causal effects under a stated exogeneity design."],
        do_not_use_when=["Causal interpretation is requested without a documented identification assumption."],
        estimators=["OLS"],
        data_structures=["cross-section", "pooled", "panel"],
        required_inputs=["outcome_variable", "treatment_or_regressor", "covariates", "standard_errors"],
        diagnostics=["support", "robust_inference", "specification_curve"],
        failure_modes=["causal language without identification", "post-hoc covariate selection"],
        source_ids=["wooldridge_cross_section_panel", "angrist_pischke_mhe", "stock_watson_intro_econometrics"],
    ),
    "iv_2sls": MethodBlueprint(
        method_id="iv_2sls",
        name="Instrumental Variables / 2SLS",
        keywords=["instrumental variables", "two-stage least squares", "2sls", "weak instruments", "first stage"],
        use_when=["Treatment or exposure is endogenous and excluded instruments are available."],
        do_not_use_when=["No excluded instrument or no exclusion restriction argument is available."],
        estimators=["IV", "2SLS", "GMM"],
        data_structures=["cross-section", "pooled", "panel"],
        required_inputs=["endogenous_variable", "excluded_instruments", "first_stage_threshold", "exclusion_argument"],
        diagnostics=["first_stage_strength", "reduced_form", "overidentification"],
        failure_modes=["no excluded instrument", "weak first stage", "unsupported exclusion restriction"],
        source_ids=["wooldridge_cross_section_panel", "angrist_pischke_mhe", "stock_watson_intro_econometrics"],
    ),
    "panel_fe": MethodBlueprint(
        method_id="panel_fe",
        name="Panel Fixed Effects / Unobserved Effects",
        keywords=["fixed effects", "unobserved effects", "panel data", "clustered standard errors", "serial correlation"],
        use_when=["Repeated observations are available and time-invariant unobservables are a concern."],
        do_not_use_when=["The coefficient of interest is absorbed by the fixed effects."],
        estimators=["FE", "TWFE", "RE", "POLS"],
        data_structures=["panel"],
        required_inputs=["unit_id", "time_id", "fixed_effects", "clustering_level"],
        diagnostics=["within_variation", "cluster_structure", "serial_correlation"],
        failure_modes=["conventional standard errors in panel data", "no within variation"],
        source_ids=["wooldridge_cross_section_panel", "angrist_pischke_mhe", "stock_watson_intro_econometrics"],
    ),
    "did": MethodBlueprint(
        method_id="did",
        name="Differences-in-Differences",
        keywords=["difference-in-differences", "differences-in-differences", "parallel trends", "event study", "staggered"],
        use_when=["Treatment changes for a treated group and a credible comparison group is observed over time."],
        do_not_use_when=["No pre-period or no credible comparison group is available."],
        estimators=["DiD", "TWFE", "EventStudy"],
        data_structures=["panel", "pooled"],
        required_inputs=["outcome_variable", "treatment_variable", "unit_id", "time_id", "control_group", "clustering_level"],
        diagnostics=["pre_trend", "event_study", "comparison_group_audit", "cluster_audit"],
        failure_modes=["no comparison group", "plain TWFE under staggered adoption", "non-clustered panel inference"],
        source_ids=["angrist_pischke_mhe", "callaway_santanna_2021", "world_bank_impact_eval"],
    ),
    "rdd": MethodBlueprint(
        method_id="rdd",
        name="Regression Discontinuity Design",
        keywords=["regression discontinuity", "running variable", "cutoff", "bandwidth", "density test"],
        use_when=["Treatment assignment changes discontinuously at a known cutoff."],
        do_not_use_when=["No running variable or cutoff exists."],
        estimators=["RDD", "FuzzyRDD"],
        data_structures=["cross-section", "pooled", "panel"],
        required_inputs=["running_variable", "cutoff", "bandwidth_rule", "sharp_or_fuzzy"],
        diagnostics=["density", "covariate_continuity", "bandwidth_sensitivity"],
        failure_modes=["missing cutoff", "no manipulation check", "global polynomial default"],
        source_ids=["angrist_pischke_mhe", "world_bank_impact_eval"],
    ),
    "matching": MethodBlueprint(
        method_id="matching",
        name="Matching / Propensity Score Preprocessing",
        keywords=["matching", "propensity score", "nearest neighbor", "common support", "balance", "matched"],
        use_when=["The design compares treated and untreated units after improving covariate balance on pre-treatment variables."],
        do_not_use_when=["Important confounders are unobserved or post-treatment variables are used for matching."],
        estimators=["Matching", "PropensityScore", "Mahalanobis", "EntropyBalance"],
        data_structures=["cross-section", "pooled"],
        required_inputs=["treatment_variable", "outcome_variable", "pre_treatment_covariates", "estimand", "matching_method"],
        diagnostics=["balance_before_after", "common_support", "effective_sample_size"],
        failure_modes=["post-treatment covariates", "poor balance after matching", "discarding changes estimand"],
        source_ids=["world_bank_impact_eval", "angrist_pischke_mhe", "stock_watson_intro_econometrics"],
    ),
    "synthetic_control": MethodBlueprint(
        method_id="synthetic_control",
        name="Synthetic Control",
        keywords=["synthetic control", "donor pool", "treated unit", "placebo", "pre-treatment fit", "comparative case"],
        use_when=["One or a small number of aggregate units receive treatment and a donor pool can approximate pre-treatment outcomes."],
        do_not_use_when=["There is no credible donor pool or no pre-treatment outcome history."],
        estimators=["SyntheticControl", "AugmentedSyntheticControl", "SyntheticDiD"],
        data_structures=["panel"],
        required_inputs=["treated_unit", "donor_pool", "time_id", "intervention_time", "outcome_variable", "predictors"],
        diagnostics=["pre_treatment_fit", "donor_weights", "placebo_tests", "sensitivity_to_donor_pool"],
        failure_modes=["poor pre-treatment fit", "contaminated donor pool", "single post-period overclaim"],
        source_ids=["world_bank_impact_eval", "stock_watson_intro_econometrics"],
    ),
    "nonlinear_did": MethodBlueprint(
        method_id="nonlinear_did",
        name="Nonlinear Difference-in-Differences",
        keywords=["nonlinear difference-in-differences", "nonlinear did", "binary outcome", "count outcome", "poisson", "logit"],
        use_when=["The outcome or estimand is nonlinear and a linear DiD coefficient is not the target effect."],
        do_not_use_when=["The agent silently uses a linear TWFE coefficient for a nonlinear target without interpretation."],
        estimators=["NonlinearDiD", "PoissonDiD", "LogitDiD", "DRDID"],
        data_structures=["panel", "pooled"],
        required_inputs=["outcome_variable", "treatment_variable", "unit_id", "time_id", "outcome_family", "target_scale"],
        diagnostics=["scale_interpretation", "parallel_trends_on_target_scale", "event_study_or_placebo"],
        failure_modes=["wrong target scale", "incidental parameter overclaim", "unqualified nonlinear FE interpretation"],
        source_ids=["wooldridge_nonlinear_did_2023", "wooldridge_recent_did_notes", "callaway_santanna_2021"],
    ),
    "gmm": MethodBlueprint(
        method_id="gmm",
        name="Generalized Method of Moments",
        keywords=["generalized method of moments", "gmm", "moment conditions", "weighting matrix", "overidentifying restrictions"],
        use_when=["A model is defined by moment restrictions rather than a full likelihood."],
        do_not_use_when=["Moment conditions are not derived from theory or design."],
        estimators=["GMM", "IVGMM", "DynamicPanelGMM"],
        data_structures=["cross-section", "time-series", "panel"],
        required_inputs=["moment_conditions", "parameters", "instruments", "weighting_matrix", "identification_rank"],
        diagnostics=["moment_condition_audit", "overidentification", "weighting_matrix_sensitivity"],
        failure_modes=["too few valid moments", "many weak instruments", "unreported weighting matrix"],
        source_ids=["greene_econometric_analysis", "wooldridge_cross_section_panel", "stock_watson_intro_econometrics"],
    ),
    "limited_dependent": MethodBlueprint(
        method_id="limited_dependent",
        name="Limited Dependent Variable Models",
        keywords=["limited dependent", "binary response", "logit", "probit", "tobit", "poisson", "negative binomial"],
        use_when=["The outcome is binary, censored, truncated, ordered, multinomial, or a count."],
        do_not_use_when=["The agent reports nonlinear coefficients as marginal effects without transformation."],
        estimators=["Logit", "Probit", "Tobit", "Poisson", "NegativeBinomial", "OrderedLogit", "MultinomialLogit"],
        data_structures=["cross-section", "pooled", "panel"],
        required_inputs=["outcome_type", "link_or_family", "covariates", "target_effect", "marginal_effect_plan"],
        diagnostics=["marginal_effects", "fit_convergence", "separation_or_sparse_cells", "overdispersion_for_counts"],
        failure_modes=["coefficient interpreted as probability effect", "complete separation", "wrong count family"],
        source_ids=["greene_econometric_analysis", "wooldridge_cross_section_panel", "stock_watson_intro_econometrics"],
    ),
    "time_series": MethodBlueprint(
        method_id="time_series",
        name="Time-Series Econometrics",
        keywords=["time series", "stationary", "unit root", "arima", "serial correlation", "cointegration", "forecast"],
        use_when=["Observations are ordered over time and dependence over time is central to estimation or inference."],
        do_not_use_when=["The data are treated as iid despite serial dependence or trending behavior."],
        estimators=["ARIMA", "ARMAX", "VAR", "VECM", "ARDL", "HACRegression"],
        data_structures=["time-series"],
        required_inputs=["time_index", "frequency", "stationarity_plan", "lag_order_plan", "forecast_or_causal_target"],
        diagnostics=["unit_root", "autocorrelation", "lag_selection", "residual_diagnostics", "structural_breaks"],
        failure_modes=["spurious regression", "look-ahead bias", "unmodeled autocorrelation", "overfit forecast"],
        source_ids=["stock_watson_intro_econometrics", "greene_econometric_analysis", "wooldridge_cross_section_panel"],
    ),
}


def read_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    return loaded if isinstance(loaded, dict) else {}


def write_yaml(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, width=100), encoding="utf-8")


def extract_pdf_pages(path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - maintenance script
        raise SystemExit("Install pypdf before running the deep knowledge audit.") from exc
    pages: list[str] = []
    reader = PdfReader(str(path))
    for page in reader.pages:
        try:
            pages.append(page.extract_text() or "")
        except Exception:
            pages.append("")
    return pages


def scan_pdf(path: Path, max_pages_per_method: int) -> dict[str, dict[str, Any]]:
    pages = extract_pdf_pages(path)
    report: dict[str, dict[str, Any]] = {}
    for method_id, blueprint in BLUEPRINTS.items():
        hits: list[int] = []
        term_counts: Counter[str] = Counter()
        patterns = [(term, re.compile(re.escape(term), re.IGNORECASE)) for term in blueprint.keywords]
        for page_index, text in enumerate(pages, start=1):
            page_hit = False
            for term, pattern in patterns:
                count = len(pattern.findall(text))
                if count:
                    term_counts[term] += count
                    page_hit = True
            if page_hit and len(hits) < max_pages_per_method:
                hits.append(page_index)
        if hits:
            report[method_id] = {
                "candidate_pages": hits,
                "keyword_hits": dict(term_counts),
            }
    return report


def scan_sources(tools_dir: Path, max_pages_per_method: int) -> list[dict[str, Any]]:
    scanned: list[dict[str, Any]] = []
    for pdf in sorted(tools_dir.glob("*.pdf")):
        scanned.append(
            {
                "file_name": pdf.name,
                "local_path": str(pdf).replace("\\", "/"),
                "topics": scan_pdf(pdf, max_pages_per_method=max_pages_per_method),
            }
        )
    return scanned


def pack_path(method_id: str) -> Path:
    return PACKS_DIR / f"{method_id}.yaml"


def load_pack(method_id: str) -> dict[str, Any]:
    return read_yaml(pack_path(method_id))


def duplicate_ids(pack: dict[str, Any]) -> dict[str, list[str]]:
    duplicates: dict[str, list[str]] = {}
    for section in ["decision_tree", "assumptions", "required_inputs", "diagnostics", "failure_modes", "code_recipes"]:
        ids = [item.get("id") for item in pack.get(section, []) if isinstance(item, dict)]
        repeated = sorted(item for item, count in Counter(ids).items() if item and count > 1)
        if repeated:
            duplicates[section] = repeated
    return duplicates


def long_text_warnings(pack: dict[str, Any], max_words: int) -> list[str]:
    warnings: list[str] = []

    def walk(value: Any, path: str) -> None:
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
        elif isinstance(value, list):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
        elif isinstance(value, str):
            words = value.split()
            if len(words) > max_words:
                warnings.append(f"{path} has {len(words)} words")

    walk(pack, "")
    return warnings


def coverage_report(scanned_sources: list[dict[str, Any]]) -> dict[str, Any]:
    report: dict[str, Any] = {}
    for method_id in BLUEPRINTS:
        source_hits = []
        for source in scanned_sources:
            topic = source.get("topics", {}).get(method_id)
            if topic:
                source_hits.append(
                    {
                        "file_name": source["file_name"],
                        "candidate_pages": topic["candidate_pages"],
                        "keyword_hits": topic["keyword_hits"],
                    }
                )
        pack = load_pack(method_id)
        report[method_id] = {
            "pack_exists": bool(pack),
            "duplicate_ids": duplicate_ids(pack) if pack else {},
            "long_text_warnings": long_text_warnings(pack, max_words=120) if pack else [],
            "source_hits": source_hits,
            "suggested_next_action": "human_audit_candidate_pages" if source_hits else "add_or_verify_source_material",
        }
    return report


def scaffold_pack(blueprint: MethodBlueprint, scanned_sources: list[dict[str, Any]]) -> dict[str, Any]:
    anchors = []
    for source in scanned_sources:
        topic = source.get("topics", {}).get(blueprint.method_id)
        if not topic:
            continue
        anchors.append(
            {
                "source_id": source_id_from_file(source["file_name"]),
                "topics": [f"candidate pages from keyword scan for {blueprint.name}"],
                "local_pdf_pages": topic["candidate_pages"],
            }
        )
    if not anchors:
        anchors = [{"source_id": source_id, "topics": ["human review required"]} for source_id in blueprint.source_ids]

    return {
        "version": "0.1.0",
        "method_id": blueprint.method_id,
        "name": blueprint.name,
        "maturity": {
            "status": "starter_scaffold",
            "source_review": "machine_locator_only",
            "estimator_choice": "low",
            "diagnostics": "low",
            "code_recipes": "starter",
        },
        "scope": {
            "use_when": blueprint.use_when,
            "do_not_use_when": blueprint.do_not_use_when,
        },
        "estimand": {
            "default": "Human review required before public use.",
            "agent_instruction": "Use this scaffold only as a checklist until a researcher audits the source anchors.",
        },
        "decision_tree": [
            {"id": f"{blueprint.method_id}-design-001", "if": "Method appears appropriate after PAP review.", "then": "Run the method-specific preflight checks before writing code."}
        ],
        "assumptions": [
            {"id": f"{blueprint.method_id}-assumption-001", "plain": item, "formal": "Human review required.", "evidence": "Source anchors and PAP."}
            for item in blueprint.use_when
        ],
        "required_inputs": [
            {"id": f"{blueprint.method_id}-input-{index:03d}", "name": item, "reason": "Required for method-specific preflight and reporting."}
            for index, item in enumerate(blueprint.required_inputs, start=1)
        ],
        "diagnostics": [
            {"id": f"{blueprint.method_id}-diagnostic-{index:03d}", "name": item, "instruction": "Run and report this diagnostic before causal interpretation."}
            for index, item in enumerate(blueprint.diagnostics, start=1)
        ],
        "failure_modes": [
            {"id": f"{blueprint.method_id}-failure-{index:03d}", "risk": item, "response": "Warn or block depending on conformance level."}
            for index, item in enumerate(blueprint.failure_modes, start=1)
        ],
        "code_recipes": [
            {"id": f"{blueprint.method_id}-recipe-placeholder", "language": "pending", "package": "pending", "source": "pending", "template": "# Add official package recipe after human review."}
        ],
        "reporting_checklist": [
            "State the estimand and identifying assumptions.",
            "Report required diagnostics and failure-mode checks.",
            "Name software package, version, estimator, and inference choices.",
        ],
        "source_anchors": anchors,
    }


def source_id_from_file(file_name: str) -> str:
    known = {
        "Wooldridge.pdf": "wooldridge_cross_section_panel",
        "MostlyHarmlessEconometrics.pdf": "angrist_pischke_mhe",
        "econometric_analysis_by_greence.pdf": "greene_econometric_analysis",
        "FlorianHeiss.pdf": "heiss_using_r_intro_econometrics",
        "JamesHStock.pdf": "stock_watson_intro_econometrics",
        "WorldBankImpactEval.pdf": "world_bank_impact_eval",
        "US25_Wooldridge.pdf": "wooldridge_recent_did_notes",
        "utad016.pdf": "wooldridge_nonlinear_did_2023",
        "wooldridgePackage.pdf": "wooldridge_r_package",
    }
    return known.get(file_name, Path(file_name).stem)


def update_missing_packs(scanned_sources: list[dict[str, Any]]) -> list[str]:
    written: list[str] = []
    for method_id, blueprint in BLUEPRINTS.items():
        path = pack_path(method_id)
        if path.exists():
            continue
        write_yaml(path, scaffold_pack(blueprint, scanned_sources))
        written.append(str(path))
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Run AESDK's deep knowledge-pack audit.")
    parser.add_argument("--tools-dir", default="tools", help="Directory containing local textbook/source PDFs.")
    parser.add_argument("--write-report", default="docs/deep_knowledge_audit_report.yaml")
    parser.add_argument("--max-pages-per-method", type=int, default=20)
    parser.add_argument("--update-packs", action="store_true", help="Create scaffold packs for blueprint methods that are missing.")
    args = parser.parse_args()

    scanned = scan_sources(Path(args.tools_dir), max_pages_per_method=args.max_pages_per_method)
    report = {
        "version": "0.1.0",
        "policy": {
            "stores_textbook_text": False,
            "stores_page_locators": True,
            "requires_human_review_for_maturity_upgrade": True,
        },
        "scanned_sources": scanned,
        "coverage": coverage_report(scanned),
    }
    if args.update_packs:
        report["written_pack_scaffolds"] = update_missing_packs(scanned)

    write_yaml(Path(args.write_report), report)
    print(f"wrote={args.write_report} sources={len(scanned)} methods={len(BLUEPRINTS)}")
    if args.update_packs:
        print(f"scaffolds={len(report.get('written_pack_scaffolds', []))}")


if __name__ == "__main__":
    main()
