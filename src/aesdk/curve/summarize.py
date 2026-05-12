"""Summarization of econometric results."""
from __future__ import annotations
from aesdk.curve.spec_engine import SpecResult

def summarize_result(result: SpecResult) -> str:
    """Creates a human-readable summary of the econometric result."""
    lines = [
        f"Estimator: {result.estimator_name}",
        f"Observations: {result.n_observations}",
        f"R-squared: {result.r_squared:.4f}",
        "\nCoefficients:"
    ]
    for var, val in result.coefficients.items():
        se = result.std_errors.get(var, 0)
        p = result.p_values.get(var, 1)
        lines.append(f"  {var}: {val:.4f} (SE: {se:.4f}, p: {p:.4f})")

    return "\n".join(lines)
