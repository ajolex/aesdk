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
    inferred_method = method or _infer_method(task_text or "", task.name)
    active_design_origin = design_origin or _infer_design_origin(task_text or "", task.name, inferred_method)
    pap = draft_pap(
        goal=title or _title_from_text(task_text, task.stem),
        method=inferred_method,
        data_path=data_path,
        outcome=outcome,
        treatment=treatment,
        unit=unit,
        time=time,
        design_origin=active_design_origin,
    )
    if inferred_method == "did" and active_design_origin == "experimental_rct":
        pap["identification"]["design_note"] = (
            "Treatment timing or assignment is randomized; apply DiD event-study guardrails with "
            "experimental-design provenance documented."
        )

    proposal = {
        "estimator": pap["identification"]["strategy"],
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

    pap_path = target_dir / "pap.yaml"
    proposal_path = target_dir / "proposal.json"
    pap_path.write_text(yaml.safe_dump(pap, sort_keys=False), encoding="utf-8")
    proposal_path.write_text(json.dumps(proposal, indent=2), encoding="utf-8")
    return IntakeResult(
        method=inferred_method,
        pap_path=pap_path,
        proposal_path=proposal_path,
        task_text_path=(target_dir / f"{task.stem}_extracted.txt") if task_text is not None else None,
    )


def _extract_task_text(task: Path, output_dir: Path) -> str | None:
    if task.suffix.lower() == ".pdf":
        target = output_dir / f"{task.stem}_extracted.txt"
        pdftotext = shutil.which("pdftotext")
        if pdftotext:
            subprocess.run([pdftotext, "-layout", str(task), str(target)], check=False, capture_output=True)
            if target.exists():
                return target.read_text(encoding="utf-8", errors="replace")
        return None
    if task.suffix.lower() in {".txt", ".md"}:
        text = task.read_text(encoding="utf-8", errors="replace")
        target = output_dir / f"{task.stem}_extracted.txt"
        target.write_text(text, encoding="utf-8")
        return text
    return None


def _infer_method(text: str, name: str) -> str:
    haystack = f"{name}\n{text}".lower()
    did_tokens = [
        "event-study",
        "event study",
        "difference-in-differences",
        "diff-in-diff",
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
        "randomized phase-in",
        "randomised phase-in",
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
    return None


def _title_from_text(text: str | None, fallback: str) -> str:
    if text:
        for line in text.splitlines():
            cleaned = re.sub(r"\s+", " ", line).strip()
            if len(cleaned) >= 5:
                return cleaned[:120]
    return fallback.replace("_", " ").title()
