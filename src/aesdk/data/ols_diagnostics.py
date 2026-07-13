"""Wooldridge-grounded OLS assumption diagnostics.

AESDK's OLS rules check what the researcher *declares*. This module goes
further: it fits the declared linear model on the dataset and runs the
classical assumption diagnostics, mapping each to the assumption labels in
Wooldridge, *Introductory Econometrics: A Modern Approach* (MLR.1-MLR.6 plus
the practical extensions in Chapters 8, 9, and 12).

The checklist has ten items. Some assumptions are testable from the fitted
model (collinearity, homoskedasticity, functional form, normality of
residuals, serial correlation, influential observations, degrees of freedom,
inference choice). Two are *not* testable from data alone -- random sampling
(MLR.2) and the zero-conditional-mean/exogeneity assumption (MLR.4) -- so they
are reported as declaration-only items rather than given a false "pass".

All math is done with numpy and scipy so the module works wherever scipy is
available (it ships with statsmodels, a declared dependency). Every test is
wrapped so that a single numerical failure degrades to a skipped item rather
than aborting the whole report.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np

# Rules of thumb, each tied to a documented source.
VIF_WARN_THRESHOLD = 10.0  # Wooldridge Ch. 3 discussion of multicollinearity.
HET_TEST_ALPHA = 0.05  # Breusch-Pagan / White (Wooldridge Ch. 8).
RESET_ALPHA = 0.05  # Ramsey RESET functional-form test (Wooldridge Ch. 9).
NORMALITY_ALPHA = 0.05  # Jarque-Bera (Wooldridge Ch. 5); softened by the CLT.
LARGE_SAMPLE_N = 100  # Above this, non-normal errors are an asymptotic non-issue.
SERIAL_ALPHA = 0.05  # Breusch-Godfrey (Wooldridge Ch. 12).
COOKS_MULTIPLIER = 4.0  # Cook's distance > 4/n flags an influential observation.


@dataclass
class AssumptionCheck:
    key: str
    wooldridge: str
    name: str
    status: str  # pass | warn | fail | declaration | skipped
    detail: str
    statistic: float | None = None
    p_value: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "key": self.key,
            "wooldridge": self.wooldridge,
            "name": self.name,
            "status": self.status,
            "detail": self.detail,
            "statistic": None if self.statistic is None else round(float(self.statistic), 5),
            "p_value": None if self.p_value is None else round(float(self.p_value), 5),
        }


@dataclass
class OLSDiagnosticsReport:
    fitted: bool = False
    reason_unfitted: str | None = None
    n_obs: int | None = None
    n_params: int | None = None
    r_squared: float | None = None
    checks: list[AssumptionCheck] = field(default_factory=list)
    dropped_non_numeric: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "fitted": self.fitted,
            "reason_unfitted": self.reason_unfitted,
            "n_obs": self.n_obs,
            "n_params": self.n_params,
            "r_squared": None if self.r_squared is None else round(float(self.r_squared), 5),
            "dropped_non_numeric": self.dropped_non_numeric,
            "checks": [c.to_dict() for c in self.checks],
        }


def _scipy_stats():
    try:
        from scipy import stats  # type: ignore

        return stats
    except Exception:  # pragma: no cover - scipy ships with statsmodels
        return None


def _ols_fit(X: np.ndarray, y: np.ndarray):
    """Return (beta, resid, fitted, xtx_inv, leverage) via least squares."""
    xtx = X.T @ X
    xtx_inv = np.linalg.pinv(xtx)
    beta = xtx_inv @ (X.T @ y)
    fitted = X @ beta
    resid = y - fitted
    leverage = np.einsum("ij,jk,ik->i", X, xtx_inv, X)
    return beta, resid, fitted, xtx_inv, leverage


def _aux_r_squared(target: np.ndarray, design: np.ndarray) -> float:
    beta, resid, _, _, _ = _ols_fit(design, target)
    ss_res = float(resid @ resid)
    ss_tot = float(((target - target.mean()) ** 2).sum())
    if ss_tot <= 0:
        return 0.0
    return 1.0 - ss_res / ss_tot


def ols_assumption_report(
    frame,
    *,
    outcome: str,
    regressors: list[str],
    structure: str | None = None,
    standard_errors: str | None = None,
) -> OLSDiagnosticsReport:
    """Fit ``outcome ~ regressors`` and run the ten-item OLS assumption checklist."""

    report = OLSDiagnosticsReport()
    stats = _scipy_stats()

    present = [r for r in regressors if r in frame.columns]
    if outcome not in frame.columns or not present:
        report.reason_unfitted = "outcome or regressors are not columns in the dataset"
        return report

    # Keep numeric regressors only; note any dropped categorical columns.
    numeric_regressors: list[str] = []
    for r in present:
        col = frame[r]
        try:
            import pandas as pd  # local import; pandas is a hard dependency

            if pd.api.types.is_numeric_dtype(col) or pd.api.types.is_bool_dtype(col):
                numeric_regressors.append(r)
            else:
                report.dropped_non_numeric.append(r)
        except Exception:
            numeric_regressors.append(r)

    cols = [outcome, *numeric_regressors]
    data = frame[cols].apply(lambda s: s.astype("float64", errors="ignore"))
    data = data.select_dtypes(include=[np.number]).dropna()
    if outcome not in data.columns or data.shape[0] == 0:
        report.reason_unfitted = "no numeric, non-missing rows for the declared model"
        return report

    numeric_regressors = [r for r in numeric_regressors if r in data.columns]
    if not numeric_regressors:
        report.reason_unfitted = "no numeric regressors remain after dropping missing/categorical data"
        return report

    y = data[outcome].to_numpy(dtype=float)
    X_raw = data[numeric_regressors].to_numpy(dtype=float)
    n = X_raw.shape[0]
    X = np.column_stack([np.ones(n), X_raw])
    k = X.shape[1]
    report.n_obs = int(n)
    report.n_params = int(k)

    checks: list[AssumptionCheck] = []

    # -- Item 9 (report first): degrees of freedom / estimability ------------
    if n <= k:
        checks.append(
            AssumptionCheck(
                "degrees_of_freedom",
                "df",
                "Sufficient observations for the parameters (n > k)",
                "fail",
                f"Only {n} usable rows for {k} parameters; OLS is not estimable.",
            )
        )
        report.checks = checks
        return report

    beta, resid, fitted, xtx_inv, leverage = _ols_fit(X, y)
    ss_res = float(resid @ resid)
    ss_tot = float(((y - y.mean()) ** 2).sum())
    r_squared = 1.0 - ss_res / ss_tot if ss_tot > 0 else 0.0
    report.r_squared = r_squared
    report.fitted = True
    df_resid = n - k
    sigma2 = ss_res / df_resid if df_resid > 0 else float("nan")

    # -- Item 1: MLR.1 linear in parameters (functional form via RESET) ------
    checks.append(_reset_check(X, y, fitted, n, k, stats))

    # -- Item 2: MLR.2 random sampling (declaration-only) --------------------
    dup_note = ""
    try:
        n_dup = int(data.duplicated().sum())
        if n_dup > 0:
            dup_note = f" Note: {n_dup} duplicate rows detected."
    except Exception:
        pass
    checks.append(
        AssumptionCheck(
            "random_sampling",
            "MLR.2",
            "Random sampling / independent observations",
            "declaration",
            "Not testable from data alone. Confirm the sampling scheme; if observations are "
            "grouped or repeated, cluster the standard errors accordingly." + dup_note,
        )
    )

    # -- Item 3: MLR.3 no perfect collinearity (rank + VIF) ------------------
    checks.append(_collinearity_check(X, numeric_regressors))

    # -- Item 4: MLR.4 zero conditional mean / exogeneity (declaration) ------
    checks.append(
        AssumptionCheck(
            "zero_conditional_mean",
            "MLR.4",
            "Zero conditional mean of errors (exogeneity)",
            "declaration",
            "Fundamentally untestable without an identification argument. State the exogeneity "
            "or design assumption; omitted-variable or simultaneity bias cannot be ruled out by "
            "a diagnostic.",
        )
    )

    # -- Item 5: MLR.5 homoskedasticity (Breusch-Pagan + White) --------------
    checks.append(_homoskedasticity_check(X, resid, fitted, n, k, standard_errors, stats))

    # -- Item 6: no serial correlation (Breusch-Godfrey; time-ordered only) --
    checks.append(_serial_correlation_check(X, resid, n, k, structure, stats))

    # -- Item 7: MLR.6 normality of errors (Jarque-Bera) ---------------------
    checks.append(_normality_check(resid, n, stats))

    # -- Item 8: influential observations (Cook's distance / leverage) -------
    checks.append(_influence_check(resid, leverage, sigma2, n, k))

    # -- Item 10: inference matches error structure --------------------------
    checks.append(_inference_check(structure, standard_errors))

    report.checks = checks
    return report


def _reset_check(X, y, fitted, n, k, stats) -> AssumptionCheck:
    try:
        yhat2 = fitted ** 2
        yhat3 = fitted ** 3
        X_aug = np.column_stack([X, yhat2, yhat3])
        _, resid_aug, _, _, _ = _ols_fit(X_aug, y)
        ss_res = float((y - fitted) @ (y - fitted))
        ss_res_aug = float(resid_aug @ resid_aug)
        q = 2  # added terms
        df2 = n - (k + q)
        if df2 <= 0 or ss_res_aug <= 0:
            raise ValueError("insufficient df for RESET")
        f_stat = ((ss_res - ss_res_aug) / q) / (ss_res_aug / df2)
        p = float(stats.f.sf(f_stat, q, df2)) if stats else None
        if p is not None and p < RESET_ALPHA:
            return AssumptionCheck(
                "functional_form",
                "MLR.1",
                "Correct functional form (linear in parameters)",
                "warn",
                f"Ramsey RESET rejects linearity (F={f_stat:.2f}, p={p:.3f}). Consider logs, "
                "polynomials, or interactions for a mis-specified conditional mean.",
                f_stat,
                p,
            )
        return AssumptionCheck(
            "functional_form",
            "MLR.1",
            "Correct functional form (linear in parameters)",
            "pass",
            f"Ramsey RESET does not reject linearity (F={f_stat:.2f}"
            + (f", p={p:.3f}" if p is not None else "")
            + ").",
            f_stat,
            p,
        )
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            "functional_form", "MLR.1", "Correct functional form (linear in parameters)",
            "skipped", f"RESET test could not be computed ({type(exc).__name__}).",
        )


def _collinearity_check(X, regressors) -> AssumptionCheck:
    n, k = X.shape
    rank = int(np.linalg.matrix_rank(X))
    if rank < k:
        return AssumptionCheck(
            "no_perfect_collinearity",
            "MLR.3",
            "No perfect collinearity",
            "fail",
            f"The design matrix is rank-deficient (rank {rank} < {k} parameters). At least one "
            "regressor is an exact linear combination of the others; OLS cannot separate them.",
        )
    # VIF for each non-intercept regressor.
    worst_vif = 0.0
    worst_name = None
    for j, name in enumerate(regressors, start=1):
        others = np.delete(X, j, axis=1)
        r2 = _aux_r_squared(X[:, j], others)
        vif = 1.0 / (1.0 - r2) if r2 < 1 else float("inf")
        if vif > worst_vif:
            worst_vif, worst_name = vif, name
    if worst_vif > VIF_WARN_THRESHOLD:
        return AssumptionCheck(
            "no_perfect_collinearity",
            "MLR.3",
            "No (near-)perfect collinearity",
            "warn",
            f"High multicollinearity: '{worst_name}' has VIF={worst_vif:.1f} (>10). Coefficients "
            "are imprecise. This does not bias OLS; consider whether all regressors are needed.",
            worst_vif,
        )
    return AssumptionCheck(
        "no_perfect_collinearity",
        "MLR.3",
        "No (near-)perfect collinearity",
        "pass",
        f"Full-rank design; worst VIF={worst_vif:.1f} (< 10).",
        worst_vif,
    )


def _homoskedasticity_check(X, resid, fitted, n, k, standard_errors, stats) -> AssumptionCheck:
    try:
        e2 = resid ** 2
        # Breusch-Pagan: regress squared residuals on the original regressors.
        r2_bp = _aux_r_squared(e2, X)
        lm_bp = n * r2_bp
        df_bp = k - 1
        p_bp = float(stats.chi2.sf(lm_bp, df_bp)) if stats and df_bp > 0 else None
        # White (special case): regress squared residuals on fitted and fitted^2.
        white_design = np.column_stack([np.ones(n), fitted, fitted ** 2])
        r2_w = _aux_r_squared(e2, white_design)
        lm_w = n * r2_w
        p_w = float(stats.chi2.sf(lm_w, 2)) if stats else None
        rejected = (p_bp is not None and p_bp < HET_TEST_ALPHA) or (p_w is not None and p_w < HET_TEST_ALPHA)
        se_text = str(standard_errors or "").lower()
        robust = any(tok in se_text for tok in ["hc", "robust", "cluster", "white"])
        if rejected and not robust:
            return AssumptionCheck(
                "homoskedasticity",
                "MLR.5",
                "Homoskedasticity (constant error variance)",
                "warn",
                f"Heteroskedasticity detected (Breusch-Pagan p={p_bp:.3f}, White p={p_w:.3f}). "
                "Declared inference is not robust; use heteroskedasticity-robust (HC) standard errors.",
                lm_bp,
                p_bp,
            )
        if rejected and robust:
            return AssumptionCheck(
                "homoskedasticity",
                "MLR.5",
                "Homoskedasticity (constant error variance)",
                "pass",
                f"Heteroskedasticity detected (Breusch-Pagan p={p_bp:.3f}), but robust standard "
                "errors are declared, which is the correct remedy.",
                lm_bp,
                p_bp,
            )
        return AssumptionCheck(
            "homoskedasticity",
            "MLR.5",
            "Homoskedasticity (constant error variance)",
            "pass",
            f"No strong evidence of heteroskedasticity (Breusch-Pagan p={p_bp:.3f}, White p={p_w:.3f}).",
            lm_bp,
            p_bp,
        )
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            "homoskedasticity", "MLR.5", "Homoskedasticity (constant error variance)",
            "skipped", f"Heteroskedasticity tests could not be computed ({type(exc).__name__}).",
        )


def _serial_correlation_check(X, resid, n, k, structure, stats) -> AssumptionCheck:
    if structure not in {"time-series", "pooled"}:
        return AssumptionCheck(
            "no_serial_correlation",
            "TS.5",
            "No serial correlation in errors",
            "declaration",
            "Relevant for time-series or time-ordered pooled data. Declare the time ordering to "
            "enable a Breusch-Godfrey test; for panels, cluster by unit to allow serial dependence.",
        )
    try:
        # Durbin-Watson.
        dw = float(np.sum(np.diff(resid) ** 2) / np.sum(resid ** 2))
        # Breusch-Godfrey with one lag.
        lag = np.concatenate([[0.0], resid[:-1]])
        design = np.column_stack([X, lag])
        r2_bg = _aux_r_squared(resid, design)
        lm_bg = (n - 1) * r2_bg
        p_bg = float(stats.chi2.sf(lm_bg, 1)) if stats else None
        if p_bg is not None and p_bg < SERIAL_ALPHA:
            return AssumptionCheck(
                "no_serial_correlation",
                "TS.5",
                "No serial correlation in errors",
                "warn",
                f"Serial correlation detected (Breusch-Godfrey p={p_bg:.3f}, Durbin-Watson={dw:.2f}). "
                "Use HAC (Newey-West) or clustered standard errors.",
                lm_bg,
                p_bg,
            )
        return AssumptionCheck(
            "no_serial_correlation",
            "TS.5",
            "No serial correlation in errors",
            "pass",
            f"No strong evidence of serial correlation (Breusch-Godfrey p={p_bg:.3f}, Durbin-Watson={dw:.2f}).",
            lm_bg,
            p_bg,
        )
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            "no_serial_correlation", "TS.5", "No serial correlation in errors",
            "skipped", f"Serial-correlation test could not be computed ({type(exc).__name__}).",
        )


def _normality_check(resid, n, stats) -> AssumptionCheck:
    try:
        e = resid - resid.mean()
        s2 = float((e ** 2).mean())
        if s2 <= 0:
            raise ValueError("degenerate residuals")
        skew = float((e ** 3).mean() / s2 ** 1.5)
        kurt = float((e ** 4).mean() / s2 ** 2)
        jb = n / 6.0 * (skew ** 2 + (kurt - 3.0) ** 2 / 4.0)
        p = float(stats.chi2.sf(jb, 2)) if stats else None
        if p is not None and p < NORMALITY_ALPHA:
            if n >= LARGE_SAMPLE_N:
                return AssumptionCheck(
                    "normality",
                    "MLR.6",
                    "Normality of errors",
                    "pass",
                    f"Residuals are non-normal (Jarque-Bera p={p:.3f}), but with n={n} the central "
                    "limit theorem justifies large-sample inference. Only exact small-sample tests are affected.",
                    jb,
                    p,
                )
            return AssumptionCheck(
                "normality",
                "MLR.6",
                "Normality of errors",
                "warn",
                f"Residuals are non-normal (Jarque-Bera p={p:.3f}) and n={n} is small, so exact "
                "t/F inference may be unreliable. Consider a transformation or a robust/bootstrap approach.",
                jb,
                p,
            )
        return AssumptionCheck(
            "normality",
            "MLR.6",
            "Normality of errors",
            "pass",
            f"No strong evidence against normal residuals (Jarque-Bera p={p:.3f}).",
            jb,
            p,
        )
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            "normality", "MLR.6", "Normality of errors",
            "skipped", f"Normality test could not be computed ({type(exc).__name__}).",
        )


def _influence_check(resid, leverage, sigma2, n, k) -> AssumptionCheck:
    try:
        with np.errstate(divide="ignore", invalid="ignore"):
            cooks = (resid ** 2 / (k * sigma2)) * (leverage / (1.0 - leverage) ** 2)
        cooks = np.nan_to_num(cooks, nan=0.0, posinf=np.inf)
        threshold = COOKS_MULTIPLIER / n
        n_influential = int(np.sum(cooks > threshold))
        high_leverage = int(np.sum(leverage > (2.0 * k) / n))
        if n_influential > 0:
            share = n_influential / n
            status = "warn" if share > 0.01 else "pass"
            return AssumptionCheck(
                "influential_obs",
                "Ch.9",
                "No unduly influential observations",
                status,
                f"{n_influential} observations exceed Cook's distance 4/n ({high_leverage} high-leverage). "
                "Report robustness to dropping them; check for data-entry errors or outliers.",
                float(n_influential),
            )
        return AssumptionCheck(
            "influential_obs",
            "Ch.9",
            "No unduly influential observations",
            "pass",
            "No observations exceed the Cook's distance 4/n threshold.",
            0.0,
        )
    except Exception as exc:  # noqa: BLE001
        return AssumptionCheck(
            "influential_obs", "Ch.9", "No unduly influential observations",
            "skipped", f"Influence diagnostics could not be computed ({type(exc).__name__}).",
        )


def _inference_check(structure, standard_errors) -> AssumptionCheck:
    se_text = str(standard_errors or "").lower()
    robust = any(tok in se_text for tok in ["hc", "robust", "cluster", "white", "driscoll", "kraay", "wild"])
    if structure in {"panel", "pooled", "time-series"} and "cluster" not in se_text and "kraay" not in se_text:
        return AssumptionCheck(
            "inference_choice",
            "Ch.8/12",
            "Inference matches the error structure",
            "warn",
            f"Structure '{structure}' typically requires clustered or HAC standard errors to allow "
            "within-group or serial dependence; declared inference does not.",
        )
    if not robust:
        return AssumptionCheck(
            "inference_choice",
            "Ch.8",
            "Inference matches the error structure",
            "warn",
            "Conventional standard errors assume homoskedasticity; declare heteroskedasticity-robust "
            "(HC) inference unless homoskedasticity is justified.",
        )
    return AssumptionCheck(
        "inference_choice",
        "Ch.8",
        "Inference matches the error structure",
        "pass",
        f"Robust/clustered inference is declared ('{standard_errors}').",
    )
