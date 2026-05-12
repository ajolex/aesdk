"""Runner for Econometric Specifications."""
from __future__ import annotations
from pathlib import Path
from typing import Any
import pandas as pd
from aesdk.curve.spec_engine import SpecEngine, SpecResult
from aesdk.plugins import plugins

class CurveRunner:
    """Orchestrates the execution of specifications against data."""
    def __init__(self, data_path: str | Path):
        self.data_path = Path(data_path)
        self.data = self._load_data()
        self.engine = SpecEngine(self.data)

    def _load_data(self) -> pd.DataFrame:
        if self.data_path.suffix == ".csv":
            return pd.read_csv(self.data_path)
        elif self.data_path.suffix == ".parquet":
            return pd.read_parquet(self.data_path)
        raise ValueError(f"Unsupported data format: {self.data_path.suffix}")

    def execute_spec(self, spec_type: str, params: dict[str, Any]) -> SpecResult:
        custom_estimator = plugins.get_estimator(spec_type)
        if custom_estimator is not None:
            return custom_estimator(self.data, **params)
        if spec_type == "did":
            return self.engine.run_did(**params)
        elif spec_type == "panel":
            return self.engine.run_panel_fixed_effects(**params)
        raise ValueError(f"Unsupported specification type: {spec_type}")
