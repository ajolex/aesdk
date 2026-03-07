"""Sandboxed Python execution (MVP)."""

from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

import yaml

from aesdk.core.errors import ForbiddenCodePatternError, ImportWhitelistError

DEFAULT_WHITELIST_PATH = Path(__file__).resolve().parent / "whitelist.yaml"
_FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
_FORBIDDEN_ATTR_CALLS = {"system", "popen", "remove", "unlink", "rmdir", "rmtree", "rename", "replace"}


@dataclass
class SandboxDiagnostic:
    code: str
    message: str
    severity: str

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message, "severity": self.severity}


@dataclass
class SandboxResult:
    status: str
    diagnostics: list[SandboxDiagnostic]
    stdout: str = ""
    stderr: str = ""


class SandboxRunner:
    def __init__(self, whitelist_path: str | Path | None = None):
        self.whitelist_path = Path(whitelist_path or DEFAULT_WHITELIST_PATH)
        self.allowed_imports = self._load_whitelist(self.whitelist_path)

    def _load_whitelist(self, path: Path) -> set[str]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return set(data.get("allowed_imports", []))

    def run_python(self, code: str, timeout_seconds: int = 10) -> SandboxResult:
        diagnostics: list[SandboxDiagnostic] = []

        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            diagnostics.append(SandboxDiagnostic("SYNTAX", str(exc), "error"))
            return SandboxResult(status="block", diagnostics=diagnostics)

        forbidden_calls = self._find_forbidden_calls(tree)
        if forbidden_calls:
            message = f"Forbidden operations: {', '.join(sorted(forbidden_calls))}"
            diagnostics.append(SandboxDiagnostic("FORBIDDEN_CALL", message, "error"))
            raise ForbiddenCodePatternError(message)

        imports = self._extract_imports(tree)
        forbidden_imports = sorted(module for module in imports if module not in self.allowed_imports)
        if forbidden_imports:
            message = f"Forbidden imports: {', '.join(forbidden_imports)}"
            diagnostics.append(SandboxDiagnostic("IMPORT_WHITELIST", message, "error"))
            raise ImportWhitelistError(message)

        missing = [module for module in imports if importlib.util.find_spec(module) is None]
        if missing:
            diagnostics.append(
                SandboxDiagnostic("MISSING_DEP", f"Missing dependencies: {', '.join(sorted(missing))}", "error")
            )
            return SandboxResult(status="block", diagnostics=diagnostics)

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "sandbox_entry.py"
            script_path.write_text(code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                diagnostics.append(SandboxDiagnostic("TIMEOUT", str(exc), "error"))
                return SandboxResult(status="block", diagnostics=diagnostics)

        if proc.returncode != 0:
            diagnostics.append(SandboxDiagnostic("RUNTIME", proc.stderr.strip() or "Execution failed", "error"))
            return SandboxResult(status="block", diagnostics=diagnostics, stdout=proc.stdout, stderr=proc.stderr)

        diagnostics.append(SandboxDiagnostic("SMOKE", "Execution succeeded", "info"))
        return SandboxResult(status="pass", diagnostics=diagnostics, stdout=proc.stdout, stderr=proc.stderr)

    @staticmethod
    def _extract_imports(tree: ast.AST) -> set[str]:
        modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    modules.add(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module.split(".")[0])
        return modules

    @staticmethod
    def _find_forbidden_calls(tree: ast.AST) -> set[str]:
        found: set[str] = set()
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name) and node.func.id in _FORBIDDEN_CALLS:
                found.add(node.func.id)
            if isinstance(node.func, ast.Attribute) and node.func.attr in _FORBIDDEN_ATTR_CALLS:
                found.add(node.func.attr)
        return found
