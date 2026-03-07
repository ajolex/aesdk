"""Phase-4 specification curve summary scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from aesdk.curve.runner import SpecificationResult


@dataclass
class CurveSummary:
    n_specs: int
    n_estimated: int


def summarize(results: list[SpecificationResult]) -> CurveSummary:
    """Return aggregate counts for placeholder phase-4 output."""
    estimated = sum(1 for result in results if result.estimate is not None)
    return CurveSummary(n_specs=len(results), n_estimated=estimated)
