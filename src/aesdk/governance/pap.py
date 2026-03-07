"""PAP schema loading and validation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import jsonschema
import yaml

from aesdk.core.errors import MissingPAPError, PAPValidationError

_DEFAULT_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "governance" / "schemas" / "pap_schema.yaml"


def load_yaml(path: str | Path) -> dict[str, Any]:
    target = Path(path)
    if not target.exists():
        raise MissingPAPError(f"File not found: {target}")
    with target.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise PAPValidationError(f"YAML root must be an object: {target}")
    return loaded


def load_pap(pap_path: str | Path) -> dict[str, Any]:
    return load_yaml(pap_path)


def load_pap_schema(schema_path: str | Path | None = None) -> dict[str, Any]:
    return load_yaml(schema_path or _DEFAULT_SCHEMA_PATH)


def validate_pap_dict(pap: dict[str, Any], schema: dict[str, Any] | None = None) -> None:
    active_schema = schema or load_pap_schema()
    validator = jsonschema.Draft7Validator(active_schema)
    errors = sorted(validator.iter_errors(pap), key=lambda err: list(err.path))
    if not errors:
        return
    details = "; ".join(f"{'/'.join(str(p) for p in e.path) or '$'}: {e.message}" for e in errors)
    raise PAPValidationError(f"PAP schema validation failed: {details}")


def validate_pap_file(pap_path: str | Path, schema_path: str | Path | None = None) -> dict[str, Any]:
    pap = load_pap(pap_path)
    schema = load_pap_schema(schema_path)
    validate_pap_dict(pap, schema)
    return pap
