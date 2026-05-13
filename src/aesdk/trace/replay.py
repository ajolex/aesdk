"""Replay utilities for replication blobs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from aesdk.sandbox.runner import SandboxRunner, normalize_language
from aesdk.trace.blob import ReplicationBlob


@dataclass
class ReplayExecutionResult:
    event_index: int
    recorded_status: str
    replay_status: str
    code_hash_matches: bool


def replay_execute_events(
    blob_path: str | Path,
    *,
    sandbox_runner: SandboxRunner | None = None,
) -> list[ReplayExecutionResult]:
    blob = ReplicationBlob.load(blob_path)
    results: list[ReplayExecutionResult] = []

    for idx, event in enumerate(blob.events):
        if event.event_type != "execute":
            continue
        code = str(event.payload.get("code", ""))
        language = normalize_language(str(event.payload.get("language", "python")))
        recorded_status = str(event.payload.get("status", "unknown"))
        recorded_hash = event.payload.get("code_sha256")
        timeout_seconds = event.payload.get("timeout_seconds")
        replay_hash = hashlib.sha256(code.encode("utf-8")).hexdigest() if code else None
        code_hash_matches = bool(recorded_hash and replay_hash == recorded_hash)

        runner = sandbox_runner or _runner_for_recorded_seed(language, event.payload.get("artifacts", {}))
        replay_result = runner.run(code, language=language, timeout_seconds=timeout_seconds)
        results.append(
            ReplayExecutionResult(
                event_index=idx,
                recorded_status=recorded_status,
                replay_status=replay_result.status,
                code_hash_matches=code_hash_matches,
            )
        )

    return results


def _runner_for_recorded_seed(language: str, artifacts: object) -> SandboxRunner:
    if not isinstance(artifacts, dict):
        return SandboxRunner()
    if language == "python" and artifacts.get("python_seed"):
        return SandboxRunner(python_seed=str(artifacts["python_seed"]))
    if language == "r" and artifacts.get("r_seed"):
        return SandboxRunner(r_seed=str(artifacts["r_seed"]))
    if language == "stata" and artifacts.get("stata_seed"):
        return SandboxRunner(stata_seed=str(artifacts["stata_seed"]))
    return SandboxRunner()
