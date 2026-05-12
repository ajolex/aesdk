"""Plotting utilities for econometric results."""
from __future__ import annotations
import matplotlib.pyplot as plt
from aesdk.curve.spec_engine import SpecResult

def plot_coefficients(result: SpecResult, title: str = "Coefficient Estimates", show: bool = True):
    """Plots coefficients with confidence intervals."""
    coeffs = list(result.coefficients.values())
    errs = list(result.std_errors.values())
    names = list(result.coefficients.keys())

    plt.figure(figsize=(10, 6))
    plt.errorbar(coeffs, range(len(coeffs)), xerr=errs, fmt='o', color='black', capsize=5)
    plt.yticks(range(len(coeffs)), names)
    plt.axvline(0, color='red', linestyle='--')
    plt.title(title)
    plt.xlabel("Estimate")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    if show:
        plt.show()
    return plt.gcf()
