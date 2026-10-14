"""Central configuration management for AESDK."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.environ[name])
    except (KeyError, ValueError):
        return default


@dataclass
class AESDKConfig:
    # Governance
    default_context: str = "research"
    default_conformance: str = "basic"
    policy_version: str = "1.0.0"

    # Sandbox. The memory cap is on virtual address space (RLIMIT_AS); numpy/
    # scipy/OpenBLAS reserve far more address space than they use, so a low cap
    # makes `import statsmodels` fail. Override with AESDK_SANDBOX_MEM_MB
    # (0 disables the cap) and AESDK_SANDBOX_CPU_SEC.
    sandbox_mem_limit_mb: int = field(default_factory=lambda: _env_int("AESDK_SANDBOX_MEM_MB", 4096))
    sandbox_cpu_limit_sec: int = field(default_factory=lambda: _env_int("AESDK_SANDBOX_CPU_SEC", 30))

    # Trace/Audit
    blob_storage_path: Path = Path(".aesdk.json")


    @classmethod
    def load_from_yaml(cls, path: Path) -> AESDKConfig:
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return cls(**data)

    def to_yaml(self, path: Path) -> None:
        with path.open("w", encoding="utf-8") as f:
            yaml.dump(self.__dict__, f)

# Global configuration singleton
config = AESDKConfig()
