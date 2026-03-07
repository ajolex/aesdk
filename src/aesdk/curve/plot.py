"""Phase-4 specification curve plot scaffold."""

from __future__ import annotations

from pathlib import Path

from aesdk.curve.runner import SpecificationResult


def plot_curve(results: list[SpecificationResult], output_path: str | Path) -> Path:
    """Placeholder plotting function; writes a minimal marker file."""
    target = Path(output_path)
    target.write_text("Specification curve plotting not yet implemented.\n", encoding="utf-8")
    return target
