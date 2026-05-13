"""Replay utilities for replication blobs."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from aesdk.sandbox.runner import SandboxRunner
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
    runner = sandbox_runner or SandboxRunner()
    results: list[ReplayExecutionResult] = []

    for idx, event in enumerate(blob.events):
        if event.event_type != "execute":
            continue
        code = str(event.payload.get("code", ""))
        language = str(event.payload.get("language", "python"))
        recorded_status = str(event.payload.get("status", "unknown"))
        recorded_hash = event.payload.get("code_sha256")
        replay_hash = hashlib.sha256(code.encode("utf-8")).hexdigest() if code else None
        code_hash_matches = bool(recorded_hash and replay_hash == recorded_hash)

        replay_result = runner.run(code, language=language)
        results.append(
            ReplayExecutionResult(
                event_index=idx,
                recorded_status=recorded_status,
                replay_status=replay_result.status,
                code_hash_matches=code_hash_matches,
            )
        )

    return results
