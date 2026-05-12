"""Plugin system for AESDK.
Allows users to inject custom validation rules or econometric estimators.
"""
from __future__ import annotations
from typing import Any, Callable, Dict
from dataclasses import dataclass

@dataclass
class PluginMetadata:
    name: str
    version: str
    description: str

class PluginManager:
    """Manages custom extensions for the SDK."""
    def __init__(self):
        self._custom_validators: Dict[str, Callable] = {}
        self._custom_estimators: Dict[str, Callable] = {}

    def register_validator(self, rule_id: str, validator_fn: Callable):
        """Registers a custom validation function."""
        self._custom_validators[rule_id] = validator_fn

    def register_estimator(self, name: str, estimator_fn: Callable):
        """Registers a custom econometric estimator."""
        self._custom_estimators[name] = estimator_fn

    def get_validator(self, rule_id: str):
        return self._custom_validators.get(rule_id)

    def get_estimator(self, name: str):
        return self._custom_estimators.get(name)

# Global plugin manager
plugins = PluginManager()
