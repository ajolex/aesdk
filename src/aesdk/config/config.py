"""Central configuration management for AESDK."""
from __future__ import annotations
import os
from pathlib import Path
from dataclasses import dataclass, field
import yaml

@dataclass
class AESDKConfig:
    # Governance
    default_context: str = "research"
    default_conformance: str = "basic"
    policy_version: str = "1.0.0"
    
    # Sandbox
    sandbox_mem_limit_mb: int = 512
    sandbox_cpu_limit_sec: int = 30
    
    # Trace/Audit
    blob_storage_path: Path = Path(".aesdk.json")
    
    # LLM
    default_model: str = "gpt-4o"

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
