"""Prepare an AESDK replication blob before analysis code is written."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from aesdk.core.project import Project
from aesdk.protocol.validator import ValidationResult


@dataclass(frozen=True)
class PrepareResult:
    blob_path: Path
    validation: ValidationResult
    project_id: str

    @property
    def status(self) -> str:
        return self.validation.status

    @property
    def blocked(self) -> bool:
        return self.validation.blocked


def prepare(
    *,
    pap_path: str | Path,
    proposal: dict[str, Any] | str | Path,
    blob_path: str | Path | None = None,
    context: str = "research",
    conformance: str = "strict",
    policy_version: str = "1.0.0",
) -> PrepareResult:
    """Create or refresh the `.aesdk.json` replication blob without executing code."""

    proposal_path = proposal if isinstance(proposal, (str, Path)) else None
    proposal_dict = _load_proposal(proposal)
    project = Project.create(
        pap_path=pap_path,
        proposal_path=proposal_path,
        blob_path=blob_path,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    project.propose_model(proposal_dict)
    validation = project.validate()
    return PrepareResult(blob_path=project.blob_path, validation=validation, project_id=project.blob.project_id)


def _load_proposal(proposal: dict[str, Any] | str | Path) -> dict[str, Any]:
    if isinstance(proposal, dict):
        return proposal
    with Path(proposal).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)
