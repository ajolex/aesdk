"""Human-in-loop review evidence helpers."""

from __future__ import annotations

import difflib
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class ReviewDiffResult:
    path: Path
    changed: bool
    line_count: int


@dataclass(frozen=True)
class InteractionLogResult:
    path: Path
    sha256: str
    entry_count: int


def write_review_diff(
    *,
    ai_code_path: str | Path,
    final_code_path: str | Path,
    output_path: str | Path,
    label_ai: str = "ai_generated",
    label_final: str = "final_reviewed",
) -> ReviewDiffResult:
    """Write a unified diff between an AI code draft and the final code."""

    ai_path = Path(ai_code_path)
    final_path = Path(final_code_path)
    ai_lines = _read_text_with_fallback(ai_path).splitlines(keepends=True)
    final_lines = _read_text_with_fallback(final_path).splitlines(keepends=True)
    diff_lines = list(
        difflib.unified_diff(
            ai_lines,
            final_lines,
            fromfile=f"{label_ai}/{ai_path.name}",
            tofile=f"{label_final}/{final_path.name}",
            lineterm="",
        )
    )
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    if diff_lines:
        text = "\n".join(line.rstrip("\n") for line in diff_lines) + "\n"
    else:
        text = "AESDK-REVIEW-DIFF: no_textual_changes\nNo textual differences detected between AI draft and final code.\n"
    output.write_text(text, encoding="utf-8")
    return ReviewDiffResult(path=output, changed=bool(diff_lines), line_count=len(diff_lines))


def append_interaction_log(
    *,
    output_path: str | Path,
    speaker: Literal["human", "agent", "system", "other"],
    message: str,
    source: str | None = None,
    now: datetime | None = None,
) -> InteractionLogResult:
    """Append a timestamped human/agent interaction entry to a markdown log."""

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    active_time = now or datetime.now(timezone.utc)
    if not output.exists():
        output.write_text("# AESDK Human-In-Loop Interaction Log\n\n", encoding="utf-8")
    entry = [
        f"## {active_time.isoformat()} - {speaker}",
        "",
        f"Source: {source or 'unspecified'}",
        "",
        message.strip(),
        "",
    ]
    with output.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(entry))
        handle.write("\n")
    text = output.read_text(encoding="utf-8")
    entry_count = sum(1 for line in text.splitlines() if line.startswith("## "))
    return InteractionLogResult(path=output, sha256=hashlib.sha256(output.read_bytes()).hexdigest(), entry_count=entry_count)


def _read_text_with_fallback(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")
