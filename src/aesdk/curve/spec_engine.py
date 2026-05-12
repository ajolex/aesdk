"""Econometric specification engine for AESDK."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd
import statsmodels.formula.api as smf


@dataclass
class SpecResult:
    estimator_name: str
    coefficients: dict[str, float]
    std_errors: dict[str, float]
    p_values: dict[str, float]
    r_squared: float
    n_observations: int
    diagnostics: dict[str, Any]


class SpecEngine:
    """Execute textbook-standard econometric specifications."""

    def __init__(self, data: pd.DataFrame):
        self.data = data

    @staticmethod
    def _terms(names: list[str] | None) -> list[str]:
        return [name for name in (names or []) if name]

    @staticmethod
    def _result_from_fit(*, estimator_name: str, fit: Any, diagnostics: dict[str, Any]) -> SpecResult:
        return SpecResult(
            estimator_name=estimator_name,
            coefficients={str(k): float(v) for k, v in fit.params.items()},
            std_errors={str(k): float(v) for k, v in fit.bse.items()},
            p_values={str(k): float(v) for k, v in fit.pvalues.items()},
            r_squared=float(getattr(fit, "rsquared", float("nan"))),
            n_observations=int(fit.nobs),
            diagnostics=diagnostics,
        )

    def run_did(
        self,
        outcome: str,
        treatment: str,
        time: str,
        covariates: list[str] | None = None,
        fixed_effects: list[str] | None = None,
        cluster: str | None = None,
    ) -> SpecResult:
        """Run OLS DiD with registered covariates and optional fixed effects."""

        rhs = [treatment, *self._terms(covariates)]
        for fixed_effect in self._terms(fixed_effects or [time]):
            rhs.append(f"C({fixed_effect})")
        formula = f"{outcome} ~ " + " + ".join(rhs)
        model = smf.ols(formula, data=self.data)
        if cluster:
            fit = model.fit(cov_type="cluster", cov_kwds={"groups": self.data[cluster]})
            inference = f"clustered by {cluster}"
        else:
            fit = model.fit(cov_type="HC3")
            inference = "HC3 robust"
        return self._result_from_fit(
            estimator_name="Difference-in-Differences (OLS)",
            fit=fit,
            diagnostics={
                "formula": formula,
                "inference": inference,
                "treatment_variable": treatment,
                "time_variable": time,
            },
        )

    def run_panel_fixed_effects(
        self,
        outcome: str,
        covariates: list[str],
        entity_id: str,
        time_id: str,
        cluster: str | None = None,
    ) -> SpecResult:
        """Run linear panel fixed effects via entity and time dummies."""

        rhs = [*self._terms(covariates), f"C({entity_id})", f"C({time_id})"]
        formula = f"{outcome} ~ " + " + ".join(rhs)
        model = smf.ols(formula, data=self.data)
        cluster_var = cluster or entity_id
        fit = model.fit(cov_type="cluster", cov_kwds={"groups": self.data[cluster_var]})
        return self._result_from_fit(
            estimator_name="Panel Fixed Effects",
            fit=fit,
            diagnostics={
                "formula": formula,
                "entity_effects": True,
                "time_effects": True,
                "inference": f"clustered by {cluster_var}",
            },
        )
