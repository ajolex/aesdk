"""Governance policy profiles and conformance levels."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ConformanceLevel(str, Enum):
    BASIC = "basic"
    STRICT = "strict"
    REGULATED = "regulated"


class ExecutionContext(str, Enum):
    RESEARCH = "research"
    PRODUCTION = "production"
    REGULATED = "regulated"


@dataclass(frozen=True)
class PolicyProfile:
    name: str
    context: ExecutionContext
    conformance: ConformanceLevel


def default_profile_for_context(context: ExecutionContext) -> PolicyProfile:
    if context == ExecutionContext.PRODUCTION:
        return PolicyProfile(name="production_strict", context=context, conformance=ConformanceLevel.STRICT)
    if context == ExecutionContext.REGULATED:
        return PolicyProfile(name="regulated_hard", context=context, conformance=ConformanceLevel.REGULATED)
    return PolicyProfile(name="research_basic", context=context, conformance=ConformanceLevel.BASIC)


def resolve_profile(
    *,
    context: str | ExecutionContext = ExecutionContext.RESEARCH,
    conformance: str | ConformanceLevel | None = None,
) -> PolicyProfile:
    context_enum = context if isinstance(context, ExecutionContext) else ExecutionContext(str(context).lower())
    base = default_profile_for_context(context_enum)
    if conformance is None:
        return base
    conformance_enum = conformance if isinstance(conformance, ConformanceLevel) else ConformanceLevel(str(conformance).lower())
    return PolicyProfile(
        name=f"{context_enum.value}_{conformance_enum.value}",
        context=context_enum,
        conformance=conformance_enum,
    )


def compute_rulepack_hash(rules_dir: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(rules_dir.glob("*.rules.yaml")):
        digest.update(path.name.encode("utf-8"))
        digest.update(path.read_bytes())
    return "sha256:" + digest.hexdigest()
