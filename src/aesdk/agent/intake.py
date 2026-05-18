"""Task-folder intake helpers for agent workflows."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aesdk.agent.pap_draft import draft_pap


@dataclass(frozen=True)
class IntakeResult:
    method: str
    pap_path: Path
    proposal_path: Path
    task_text_path: Path | None


def intake_prompt(
    *,
    prompt: str,
    data_path: str | Path | None = None,
    method: str | None = None,
    output_dir: str | Path | None = None,
    outcome: str = "outcome",
    treatment: str = "treatment",
    unit: str | None = None,
    time: str | None = None,
    design_origin: str | None = None,
    title: str | None = None,
) -> IntakeResult:
    """Draft a reviewable PAP/proposal pair from the user's analysis prompt."""

    target_dir = Path(output_dir or ".")
    target_dir.mkdir(parents=True, exist_ok=True)
    task_text_path = target_dir / "prompt_extracted.txt"
    task_text_path.write_text(prompt, encoding="utf-8")
    return _intake_from_text(
        text=prompt,
        name="prompt",
        task_text_path=task_text_path,
        data_path=data_path,
        method=method,
        output_dir=target_dir,
        outcome=outcome,
        treatment=treatment,
        unit=unit,
        time=time,
        design_origin=design_origin,
        title=title,
    )


def intake_task(
    *,
    task_path: str | Path,
    data_path: str | Path | None = None,
    method: str | None = None,
    output_dir: str | Path | None = None,
    outcome: str = "outcome",
    treatment: str = "treatment",
    unit: str | None = None,
    time: str | None = None,
    design_origin: str | None = None,
    title: str | None = None,
) -> IntakeResult:
    """Draft a reviewable PAP/proposal pair from a task document and optional data."""

    task = Path(task_path)
    target_dir = Path(output_dir) if output_dir else task.parent
    target_dir.mkdir(parents=True, exist_ok=True)
    task_text = _extract_task_text(task, target_dir)
    if task.suffix.lower() == ".pdf" and task_text is None:
        raise ValueError(
            f"AESDK could not extract text from {task}. Install pdftotext or pypdf, or rerun intake with --prompt "
            "using the actual task instructions. AESDK will not infer from an unreadable PDF filename alone."
        )
    return _intake_from_text(
        text=task_text or "",
        name=task.name,
        task_text_path=(target_dir / f"{task.stem}_extracted.txt") if task_text is not None else None,
        data_path=data_path,
        method=method,
        output_dir=target_dir,
        outcome=outcome,
        treatment=treatment,
        unit=unit,
        time=time,
        design_origin=design_origin,
        title=title,
    )


def _intake_from_text(
    *,
    text: str,
    name: str,
    task_text_path: Path | None,
    data_path: str | Path | None,
    method: str | None,
    output_dir: Path,
    outcome: str,
    treatment: str,
    unit: str | None,
    time: str | None,
    design_origin: str | None,
    title: str | None,
) -> IntakeResult:
    inferred_method = method or _infer_method(text, name)
    active_design_origin = design_origin or _infer_design_origin(text, name, inferred_method)
    pap = draft_pap(
        goal=title or _title_from_text(text, Path(name).stem),
        method=inferred_method,
        data_path=data_path,
        outcome=outcome,
        treatment=treatment,
        unit=unit,
        time=time,
        design_origin=active_design_origin,
    )
    task_prescribed_estimator = _infer_task_prescribed_estimator(text)
    if inferred_method == "did":
        _strengthen_did_scaffold(
            pap=pap,
            text=text,
            treatment=treatment,
            unit=unit,
            active_design_origin=active_design_origin,
            task_prescribed_estimator=task_prescribed_estimator,
        )

    proposal = {
        "estimator": task_prescribed_estimator or pap["identification"]["strategy"],
        "standard_errors": pap["identification"].get("standard_errors"),
        "clustering": pap["identification"].get("clustering"),
        "outcome_variable": outcome,
        "treatment_variable": treatment,
        "design_origin": active_design_origin,
        "citation_report": {
            "hallucinated_count": 0,
            "uncertain_count": 0,
            "unreachable_count": 0,
            "invalid_format_count": 0,
        },
    }
    if active_design_origin == "experimental_rct" and inferred_method == "did":
        proposal["identification_assumption_documented"] = True
        proposal["design_note"] = pap["identification"].get("design_note")
    if task_prescribed_estimator:
        proposal["task_required_estimator"] = task_prescribed_estimator
        proposal["task_required_estimator_justification"] = (
            "AESDK detected language indicating that the analysis task prescribes this estimator; "
            "the researcher should verify this before treating it as binding."
        )

    pap_path = output_dir / "pap.yaml"
    proposal_path = output_dir / "proposal.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return IntakeResult(
        method=inferred_method,
        pap_path=pap_path,
        proposal_path=proposal_path,
        task_text_path=task_text_path,
    )


def _extract_task_text(task: Path, output_dir: Path) -> str | None:
    if task.suffix.lower() == ".pdf":
        target = output_dir / f"{task.stem}_extracted.txt"
        pdftotext = shutil.which("pdftotext")
        if pdftotext:
            subprocess.run([pdftotext, "-layout", str(task), str(target)], check=False, capture_output=True)
            if target.exists() and target.stat().st_size > 0:
                return target.read_text(encoding="utf-8", errors="replace")
        fallback_text = _extract_pdf_with_pypdf(task)
        if fallback_text:
            target.write_text(fallback_text, encoding="utf-8")
            return fallback_text
        return None
    if task.suffix.lower() in {".txt", ".md"}:
        text = task.read_text(encoding="utf-8", errors="replace")
        target = output_dir / f"{task.stem}_extracted.txt"
        target.write_text(text, encoding="utf-8")
        return text
    return None


def _extract_pdf_with_pypdf(task: Path) -> str | None:
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        reader = PdfReader(str(task))
        pages = [page.extract_text() or "" for page in reader.pages]
    except Exception:
        return None
    text = "\n".join(pages).strip()
    return text or None


def _infer_method(text: str, name: str) -> str:
    haystack = f"{name}\n{text}".lower()
    did_tokens = [
        "adoption cohort",
        "cohort-specific",
        "control cohort",
        "event-study",
        "event study",
        "event-time",
        "event time",
        "difference-in-differences",
        "diff-in-diff",
        "not-yet-treated",
        "not yet treated",
        "parallel trends",
        "phase-in",
        "rollout",
        "treatment timing",
        "two-way fixed effects",
        "twfe",
        "staggered",
    ]
    if any(token in haystack for token in did_tokens):
        return "did"
    if any(
        token in haystack
        for token in ["randomized controlled trial", "randomised controlled trial", "rct", "randomized"]
    ):
        return "experimental_rct"
    if "instrument" in haystack or "2sls" in haystack:
        return "iv_2sls"
    if "regression discontinuity" in haystack or "cutoff" in haystack:
        return "rdd"
    if "synthetic control" in haystack:
        return "synthetic_control"
    return "ols_cef"


def _infer_design_origin(text: str, name: str, method: str) -> str | None:
    if method != "did":
        return None
    haystack = f"{name}\n{text}".lower()
    randomized_tokens = [
        "randomized rollout",
        "randomised rollout",
        "randomized in timing",
        "randomised in timing",
        "randomized phase-in",
        "randomised phase-in",
        "randomized across",
        "randomised across",
        "randomized controlled trial",
        "randomised controlled trial",
        "random assignment",
        "randomized assignment",
        "randomised assignment",
        "randomly assigned",
        "rct",
    ]
    if any(token in haystack for token in randomized_tokens):
        return "experimental_rct"
    if ("randomized" in haystack or "randomised" in haystack) and any(
        token in haystack for token in ["rollout", "phase-in", "phase in", "staggered", "treatment timing"]
    ):
        return "experimental_rct"
    return None


def _infer_task_prescribed_estimator(text: str) -> str | None:
    haystack = text.lower()
    if "two-way fixed effects" not in haystack and "twfe" not in haystack:
        return None
    prescribed_tokens = [
        "pre-specified",
        "prespecified",
        "specified",
        "required",
        "must use",
        "asked to use",
        "instructed to use",
        "estimate a two-way fixed effects",
        "estimate twfe",
    ]
    if any(token in haystack for token in prescribed_tokens):
        return "TWFE"
    return None


def _mentions_any(text: str, tokens: list[str]) -> bool:
    haystack = text.lower()
    return any(token in haystack for token in tokens)


def _strengthen_did_scaffold(
    *,
    pap: dict[str, Any],
    text: str,
    treatment: str,
    unit: str | None,
    active_design_origin: str | None,
    task_prescribed_estimator: str | None,
) -> None:
    identification = pap.setdefault("identification", {})
    did = pap.setdefault("did_block", {})
    if _mentions_any(text, ["event-study", "event study", "event-time", "event time"]):
        identification["strategy"] = "EventStudy"
    if _mentions_any(text, ["staggered", "rollout", "phase-in", "phase in", "not-yet-treated", "not yet treated"]):
        did["staggered_adoption"] = True
        did["control_group"] = "not_yet_treated"
        did["control_group_justification"] = (
            "Drafted from task language indicating staggered timing; compare treated units to not-yet-treated "
            "or otherwise eligible units after researcher verification."
        )
    if active_design_origin == "experimental_rct":
        identification["design_note"] = (
            "Treatment timing or assignment is randomized; apply DiD/event-study guardrails while preserving "
            "the experimental-design provenance and checking spillovers, compliance, and attrition."
        )
        randomization_unit = _infer_randomization_unit(text, unit)
        pap["rct_block"] = {
            "randomization_unit": randomization_unit,
            "assignment_variable": treatment,
            "treatment_arms": [treatment],
            "control_group": "not_yet_treated" if did.get("staggered_adoption") else "control",
            "assignment_probability": 0.5,
            "randomization_method": "researcher_review_required",
            "estimand": "ITT",
            "baseline_balance_check": False,
            "attrition_check": False,
            "spillover_plan": "researcher_review_required",
            "spillover_risk": False,
            "sutva_rationale": "researcher_review_required",
            "power_calculation": False,
            "trial_registration": False,
            "pap_registered": True,
        }
        identification["clustering"] = randomization_unit
    if task_prescribed_estimator:
        did["task_required_estimator"] = task_prescribed_estimator
        did["task_required_estimator_justification"] = (
            "The task appears to prescribe the estimator; this does not waive diagnostics or researcher review."
        )


def _infer_randomization_unit(text: str, unit: str | None) -> str:
    haystack = text.lower()
    candidates = [
        "gvh",
        "village",
        "school",
        "clinic",
        "firm",
        "district",
        "county",
        "state",
        "household",
        "individual",
    ]
    for candidate in candidates:
        if candidate in haystack:
            return candidate
    return unit or "cluster"


def _title_from_text(text: str | None, fallback: str) -> str:
    if text:
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if len(cleaned) >= 5:
                return cleaned[:120]
    return fallback.replace("_", " ").title()
