"""Sandboxed analysis-code execution."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Iterator

import yaml

from aesdk.core.errors import ForbiddenCodePatternError, ImportWhitelistError

DEFAULT_WHITELIST_PATH = Path(__file__).resolve().parent / "whitelist.yaml"
_FORBIDDEN_CALLS = {"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"}
_FORBIDDEN_ATTR_CALLS = {"system", "popen", "remove", "unlink", "rmdir", "rmtree", "rename", "replace"}
_STATA_EXECUTABLE_ENV = "AESDK_STATA"
_R_EXECUTABLE_ENV = "AESDK_R"
_STATA_EXECUTABLE_CANDIDATES = (
    "stata-mp",
    "stata-se",
    "stata-be",
    "stata",
    "StataMP-64.exe",
    "StataSE-64.exe",
    "StataBE-64.exe",
    "StataNowMP-64.exe",
    "StataMP.exe",
    "StataSE.exe",
    "StataBE.exe",
)
_R_EXECUTABLE_CANDIDATES = (
    "Rscript",
    "Rscript.exe",
)
_FORBIDDEN_STATA_COMMANDS = {
    "!",
    "shell",
    "winexec",
    "erase",
    "rm",
    "rmdir",
}
_FORBIDDEN_STATA_PREFIXES = (
    "copy http:",
    "copy https:",
    "net install",
    "ssc install",
    "github install",
)
_FORBIDDEN_R_PATTERNS = {
    r"\bassignInNamespace\s*\(": "assignInNamespace",
    r"\bsetwd\s*\(": "setwd",
    r"\bsystem\s*\(": "system",
    r"\bsystem2\s*\(": "system2",
    r"\bshell\s*\(": "shell",
    r"\bfile\.create\s*\(": "file.create",
    r"\bfile\.remove\s*\(": "file.remove",
    r"\bfile\.rename\s*\(": "file.rename",
    r"\bfile\.copy\s*\(": "file.copy",
    r"\bwriteLines\s*\(": "writeLines",
    r"\bunlink\s*\(": "unlink",
    r"\binstall\.packages\s*\(": "install.packages",
    r"\bupdate\.packages\s*\(": "update.packages",
    r"\bremotes::install_[a-z_]+\s*\(": "remotes::install_*",
    r"\bdevtools::install_[a-z_]+\s*\(": "devtools::install_*",
    r"\bpak::pkg_install\s*\(": "pak::pkg_install",
    r"\bdownload\.file\s*\(": "download.file",
    r"\bsource\s*\(\s*['\"]https?://": "source(http)",
    r"\burl\s*\(\s*['\"]https?://": "url(http)",
}

try:
    import resource
except Exception:  # pragma: no cover - unavailable on Windows
    resource = None


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
    artifacts: dict[str, str] = field(default_factory=dict)


class SandboxRunner:
    def __init__(
        self,
        whitelist_path: str | Path | None = None,
        *,
        mem_limit_mb: int = 512,
        cpu_limit_sec: int = 30,
        stata_executable: str | Path | None = None,
        r_executable: str | Path | None = None,
        artifact_dir: str | Path | None = None,
        python_seed: int | str | None = None,
        r_seed: int | str | None = None,
        stata_seed: int | str | None = None,
    ):
        self.whitelist_path = Path(whitelist_path or DEFAULT_WHITELIST_PATH)
        whitelist = self._load_whitelist(self.whitelist_path)
        self.allowed_imports = set(whitelist.get("allowed_imports", []))
        self.allowed_r_packages = set(whitelist.get("allowed_r_packages", []))
        self.mem_limit_mb = mem_limit_mb
        self.cpu_limit_sec = cpu_limit_sec
        self.stata_executable = str(stata_executable) if stata_executable else None
        self.r_executable = str(r_executable) if r_executable else None
        self.artifact_dir = Path(artifact_dir) if artifact_dir else None
        self.python_seed = str(python_seed) if python_seed is not None else None
        self.r_seed = str(r_seed) if r_seed is not None else None
        self.stata_seed = str(stata_seed) if stata_seed is not None else None

    def _load_whitelist(self, path: Path) -> dict[str, list[str]]:
        with path.open("r", encoding="utf-8") as handle:
            data = yaml.safe_load(handle) or {}
        return data

    def run(self, code: str, *, language: str = "python", timeout_seconds: int | None = None) -> SandboxResult:
        """Run analysis code in the requested language."""

        normalized = normalize_language(language)
        if normalized == "python":
            return self.run_python(code, timeout_seconds=timeout_seconds)
        if normalized == "stata":
            return self.run_stata(code, timeout_seconds=timeout_seconds)
        if normalized == "r":
            return self.run_r(code, timeout_seconds=timeout_seconds)
        return SandboxResult(
            status="block",
            diagnostics=[
                SandboxDiagnostic(
                    "UNSUPPORTED_LANGUAGE",
                    f"Unsupported analysis language: {language}. Supported languages: python, stata, r.",
                    "error",
                )
            ],
        )

    def run_python(self, code: str, timeout_seconds: int | None = None) -> SandboxResult:
        diagnostics: list[SandboxDiagnostic] = []
        active_timeout = timeout_seconds or self.cpu_limit_sec

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

        seed_value, seed_injected = self._prepare_python_seed(tree)
        artifacts = {"python_seed": seed_value, "python_seed_injected": str(seed_injected).lower()}

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "sandbox_entry.py"
            script_path.write_text(code, encoding="utf-8")
            execution_path = script_path
            if seed_injected:
                execution_path = Path(tmpdir) / "aesdk_python_runner.py"
                execution_path.write_text(self._python_seed_runner(script_path, seed_value), encoding="utf-8")
            try:
                proc = subprocess.run(
                    [sys.executable, str(execution_path)],
                    capture_output=True,
                    text=True,
                    timeout=active_timeout,
                    check=False,
                    preexec_fn=self._preexec_resource_limits(active_timeout),
                )
            except subprocess.TimeoutExpired as exc:
                diagnostics.append(SandboxDiagnostic("TIMEOUT", str(exc), "error"))
                return SandboxResult(status="block", diagnostics=diagnostics, artifacts=artifacts)

        if proc.returncode != 0:
            diagnostics.append(SandboxDiagnostic("RUNTIME", proc.stderr.strip() or "Execution failed", "error"))
            return SandboxResult(
                status="block",
                diagnostics=diagnostics,
                stdout=proc.stdout,
                stderr=proc.stderr,
                artifacts=artifacts,
            )

        diagnostics.append(SandboxDiagnostic("SMOKE", "Execution succeeded", "info"))
        return SandboxResult(status="pass", diagnostics=diagnostics, stdout=proc.stdout, stderr=proc.stderr, artifacts=artifacts)

    def run_stata(self, code: str, timeout_seconds: int | None = None) -> SandboxResult:
        diagnostics: list[SandboxDiagnostic] = []
        active_timeout = timeout_seconds or self.cpu_limit_sec

        forbidden = self._find_forbidden_stata_patterns(code)
        if forbidden:
            message = f"Forbidden Stata operations: {', '.join(sorted(forbidden))}"
            diagnostics.append(SandboxDiagnostic("FORBIDDEN_STATA_COMMAND", message, "error"))
            raise ForbiddenCodePatternError(message)

        executable = self._resolve_stata_executable()
        if executable is None:
            diagnostics.append(
                SandboxDiagnostic(
                    "MISSING_RUNTIME",
                    "Stata executable was not found. Set AESDK_STATA to the Stata executable path.",
                    "error",
                )
            )
            return SandboxResult(status="block", diagnostics=diagnostics)

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "sandbox_entry.do"
            seed_value, seeded_code, seed_injected = self._prepare_stata_code(code)
            artifact_stem = f"stata_sandbox_{hashlib.sha256(seeded_code.encode('utf-8')).hexdigest()[:12]}"
            script_path.write_text(seeded_code, encoding="utf-8")
            command = self._stata_command(executable, script_path)
            cwd_log_path = Path.cwd() / script_path.with_suffix(".log").name
            cwd_log_preexisting = cwd_log_path.exists()
            cwd_log_mtime = cwd_log_path.stat().st_mtime if cwd_log_preexisting else None
            cwd_log_size = cwd_log_path.stat().st_size if cwd_log_preexisting else None
            try:
                proc = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=active_timeout,
                    check=False,
                    preexec_fn=self._preexec_resource_limits(active_timeout),
                )
            except subprocess.TimeoutExpired as exc:
                diagnostics.append(SandboxDiagnostic("TIMEOUT", str(exc), "error"))
                return SandboxResult(status="block", diagnostics=diagnostics)

            log_path = script_path.with_suffix(".log")
            log_candidates = [log_path]
            if cwd_log_path != log_path:
                log_candidates.append(cwd_log_path)
            active_log_path = self._active_stata_log_path(
                log_candidates,
                cwd_log_path=cwd_log_path,
                cwd_log_preexisting=cwd_log_preexisting,
                cwd_log_mtime=cwd_log_mtime,
                cwd_log_size=cwd_log_size,
            )
            log_text = active_log_path.read_text(encoding="utf-8", errors="replace") if active_log_path else ""
            artifacts = self._capture_stata_log_artifact(
                active_log_path,
                cwd_log_path=cwd_log_path,
                cwd_log_preexisting=cwd_log_preexisting,
                cwd_log_mtime=cwd_log_mtime,
                artifact_stem=artifact_stem,
            )
            artifacts["stata_seed"] = seed_value
            artifacts["stata_seed_injected"] = str(seed_injected).lower()

        stdout = "\n".join(item for item in [proc.stdout, log_text] if item).strip()
        if proc.returncode != 0:
            message = proc.stderr.strip() or "Stata execution failed"
            diagnostics.append(SandboxDiagnostic("RUNTIME", message, "error"))
            return SandboxResult(status="block", diagnostics=diagnostics, stdout=stdout, stderr=proc.stderr, artifacts=artifacts)

        diagnostics.append(SandboxDiagnostic("SMOKE", "Execution succeeded", "info"))
        return SandboxResult(status="pass", diagnostics=diagnostics, stdout=stdout, stderr=proc.stderr, artifacts=artifacts)

    def run_r(self, code: str, timeout_seconds: int | None = None) -> SandboxResult:
        diagnostics: list[SandboxDiagnostic] = []
        active_timeout = timeout_seconds or self.cpu_limit_sec

        forbidden = self._find_forbidden_r_patterns(code)
        if forbidden:
            message = f"Forbidden R operations: {', '.join(sorted(forbidden))}"
            diagnostics.append(SandboxDiagnostic("FORBIDDEN_R_COMMAND", message, "error"))
            raise ForbiddenCodePatternError(message)

        packages = self._extract_r_packages(code)
        forbidden_packages = sorted(package for package in packages if package not in self.allowed_r_packages)
        if forbidden_packages:
            message = f"Forbidden R packages: {', '.join(forbidden_packages)}"
            diagnostics.append(SandboxDiagnostic("R_PACKAGE_WHITELIST", message, "error"))
            raise ImportWhitelistError(message)

        executable = self._resolve_r_executable()
        if executable is None:
            diagnostics.append(
                SandboxDiagnostic(
                    "MISSING_RUNTIME",
                    "Rscript executable was not found. Set AESDK_R to the Rscript executable path.",
                    "error",
                )
            )
            return SandboxResult(status="block", diagnostics=diagnostics)

        missing = self._find_missing_r_packages(executable, packages, active_timeout)
        if missing:
            diagnostics.append(
                SandboxDiagnostic("MISSING_DEP", f"Missing R packages: {', '.join(sorted(missing))}", "error")
            )
            return SandboxResult(status="block", diagnostics=diagnostics)

        seed_value, seeded_code, seed_injected = self._prepare_r_code(code)
        artifacts = {"r_seed": seed_value, "r_seed_injected": str(seed_injected).lower()}

        with tempfile.TemporaryDirectory() as tmpdir:
            script_path = Path(tmpdir) / "sandbox_entry.R"
            script_path.write_text(seeded_code, encoding="utf-8")
            try:
                proc = subprocess.run(
                    [executable, "--vanilla", str(script_path)],
                    capture_output=True,
                    text=True,
                    timeout=active_timeout,
                    check=False,
                    preexec_fn=self._preexec_resource_limits(active_timeout),
                )
            except subprocess.TimeoutExpired as exc:
                diagnostics.append(SandboxDiagnostic("TIMEOUT", str(exc), "error"))
                return SandboxResult(status="block", diagnostics=diagnostics, artifacts=artifacts)

        if proc.returncode != 0:
            diagnostics.append(SandboxDiagnostic("RUNTIME", proc.stderr.strip() or "R execution failed", "error"))
            return SandboxResult(
                status="block",
                diagnostics=diagnostics,
                stdout=proc.stdout,
                stderr=proc.stderr,
                artifacts=artifacts,
            )

        diagnostics.append(SandboxDiagnostic("SMOKE", "Execution succeeded", "info"))
        return SandboxResult(status="pass", diagnostics=diagnostics, stdout=proc.stdout, stderr=proc.stderr, artifacts=artifacts)

    def _preexec_resource_limits(self, cpu_limit_sec: int | None = None):
        if os.name == "nt" or resource is None:
            return None

        mem_limit_mb = self.mem_limit_mb
        active_cpu_limit_sec = cpu_limit_sec or self.cpu_limit_sec

        def apply_limits() -> None:
            if mem_limit_mb > 0:
                mem_bytes = mem_limit_mb * 1024 * 1024
                resource.setrlimit(resource.RLIMIT_AS, (mem_bytes, mem_bytes))
            if active_cpu_limit_sec > 0:
                resource.setrlimit(resource.RLIMIT_CPU, (active_cpu_limit_sec, active_cpu_limit_sec))

        return apply_limits

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

    def _prepare_python_seed(self, tree: ast.AST) -> tuple[str, bool]:
        existing_seed = self._extract_python_seed(tree)
        if existing_seed:
            return existing_seed, False
        return self.python_seed or _date_seed(), True

    @staticmethod
    def _extract_python_seed(tree: ast.AST) -> str | None:
        random_aliases = {"random"}
        numpy_aliases = {"numpy"}
        random_seed_aliases: set[str] = set()
        numpy_seed_aliases: set[str] = set()
        default_rng_aliases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "random":
                        random_aliases.add(alias.asname or alias.name)
                    if alias.name == "numpy":
                        numpy_aliases.add(alias.asname or alias.name)
            if isinstance(node, ast.ImportFrom):
                if node.module == "random":
                    for alias in node.names:
                        if alias.name == "seed":
                            random_seed_aliases.add(alias.asname or alias.name)
                if node.module == "numpy.random":
                    for alias in node.names:
                        if alias.name == "seed":
                            numpy_seed_aliases.add(alias.asname or alias.name)
                        if alias.name == "default_rng":
                            default_rng_aliases.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not node.args:
                continue
            if not isinstance(node.args[0], ast.Constant) or not isinstance(node.args[0].value, int):
                continue
            if _is_python_seed_call(node.func, random_aliases, numpy_aliases, random_seed_aliases, numpy_seed_aliases):
                return str(node.args[0].value)
            if _is_python_default_rng_call(node.func, numpy_aliases, default_rng_aliases):
                return str(node.args[0].value)
        return None

    @staticmethod
    def _python_seed_runner(script_path: Path, seed_value: str) -> str:
        script_literal = repr(str(script_path))
        return f"""import random as _aesdk_random
import runpy as _aesdk_runpy

_aesdk_random.seed({seed_value})
try:
    import numpy as _aesdk_numpy
    _aesdk_numpy.random.seed({seed_value})
except Exception:
    pass

_aesdk_runpy.run_path({script_literal}, run_name="__main__")
"""

    def _resolve_stata_executable(self) -> str | None:
        configured = self.stata_executable or os.getenv(_STATA_EXECUTABLE_ENV)
        if configured:
            configured_path = Path(configured)
            if configured_path.exists():
                return str(configured_path)
            discovered = shutil.which(configured)
            return discovered

        for candidate in _STATA_EXECUTABLE_CANDIDATES:
            discovered = shutil.which(candidate)
            if discovered:
                return discovered
        return None

    def _resolve_r_executable(self) -> str | None:
        configured = self.r_executable or os.getenv(_R_EXECUTABLE_ENV)
        if configured:
            configured_path = Path(configured)
            if configured_path.exists():
                return str(configured_path)
            discovered = shutil.which(configured)
            return discovered

        for candidate in _R_EXECUTABLE_CANDIDATES:
            discovered = shutil.which(candidate)
            if discovered:
                return discovered
        return None

    @staticmethod
    def _stata_command(executable: str, script_path: Path) -> list[str]:
        batch_flag = "/e" if os.name == "nt" or executable.lower().endswith(".exe") else "-b"
        return [executable, batch_flag, "do", str(script_path)]

    def _prepare_stata_code(self, code: str) -> tuple[str, str, bool]:
        existing_seed = self._extract_stata_seed(code)
        if existing_seed:
            return existing_seed, code, False
        seed_value = self.stata_seed or _date_seed()
        return seed_value, f"set seed {seed_value}\n{code}", True

    @staticmethod
    def _extract_stata_seed(code: str) -> str | None:
        for line in _iter_stata_code_lines(code):
            match = re.match(r"^set\s+seed\s+([0-9]+)\b", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _prepare_r_code(self, code: str) -> tuple[str, str, bool]:
        existing_seed = self._extract_r_seed(code)
        if existing_seed:
            return existing_seed, code, False
        seed_value = self.r_seed or _date_seed()
        return seed_value, f"set.seed({seed_value})\n{code}", True

    @staticmethod
    def _extract_r_seed(code: str) -> str | None:
        for line in _iter_r_code_lines(code):
            match = re.match(r"^set\.seed\s*\(\s*([0-9]+)\s*\)", line, flags=re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _capture_stata_log_artifact(
        self,
        log_path: Path | None,
        *,
        cwd_log_path: Path,
        cwd_log_preexisting: bool,
        cwd_log_mtime: float | None,
        artifact_stem: str,
    ) -> dict[str, str]:
        if log_path is None or not log_path.exists():
            return {}
        artifacts: dict[str, str] = {}
        if self.artifact_dir is not None:
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            target = self.artifact_dir / f"{artifact_stem}.log"
            shutil.copyfile(log_path, target)
            artifacts["stata_log_path"] = str(target)
        elif log_path == cwd_log_path:
            artifacts["stata_log_path"] = str(log_path)

        if log_path == cwd_log_path and cwd_log_path.name == "sandbox_entry.log":
            changed = not cwd_log_preexisting
            if cwd_log_preexisting and cwd_log_mtime is not None:
                changed = cwd_log_path.stat().st_mtime != cwd_log_mtime
            if changed and not cwd_log_preexisting:
                cwd_log_path.unlink(missing_ok=True)
        return artifacts

    @staticmethod
    def _active_stata_log_path(
        log_candidates: list[Path],
        *,
        cwd_log_path: Path,
        cwd_log_preexisting: bool,
        cwd_log_mtime: float | None,
        cwd_log_size: int | None,
    ) -> Path | None:
        for path in log_candidates:
            if not path.exists():
                continue
            if path != cwd_log_path:
                return path
            if not cwd_log_preexisting:
                return path
            current = path.stat()
            if current.st_mtime != cwd_log_mtime or current.st_size != cwd_log_size:
                return path
        return None

    @staticmethod
    def _find_forbidden_stata_patterns(code: str) -> set[str]:
        found: set[str] = set()
        for line in _iter_stata_code_lines(code):
            normalized = line.lower().strip()
            if not normalized:
                continue
            if normalized.startswith("!"):
                found.add("!")
                continue
            tokens = [token for token in re.split(r"[\s:]+", normalized) if token]
            for token in tokens:
                if token in _FORBIDDEN_STATA_COMMANDS:
                    found.add(token)
            for index, token in enumerate(tokens[:-1]):
                pair = f"{token} {tokens[index + 1]}"
                if pair in _FORBIDDEN_STATA_PREFIXES:
                    found.add(pair)
            if "copy" in tokens and any(token.startswith(("http", "https")) for token in tokens):
                found.add("copy http:")
            for prefix in _FORBIDDEN_STATA_PREFIXES:
                if normalized.startswith(prefix):
                    found.add(prefix)
        return found

    @staticmethod
    def _find_forbidden_r_patterns(code: str) -> set[str]:
        found: set[str] = set()
        for line in _iter_r_code_lines(code):
            for pattern, label in _FORBIDDEN_R_PATTERNS.items():
                if re.search(pattern, line, flags=re.IGNORECASE):
                    found.add(label)
        return found

    @staticmethod
    def _extract_r_packages(code: str) -> set[str]:
        packages: set[str] = set()
        pattern = re.compile(r"\b(?:library|require)\s*\(\s*['\"]?([A-Za-z][A-Za-z0-9._]*)['\"]?", re.IGNORECASE)
        for line in _iter_r_code_lines(code):
            match = pattern.search(line)
            if match:
                packages.add(match.group(1))
        return packages

    @staticmethod
    def _find_missing_r_packages(executable: str, packages: set[str], timeout_seconds: int) -> list[str]:
        missing: list[str] = []
        for package in sorted(packages):
            check = f"if (!requireNamespace('{package}', quietly = TRUE)) quit(status = 1)"
            try:
                proc = subprocess.run(
                    [executable, "--vanilla", "-e", check],
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                missing.append(package)
                continue
            if proc.returncode != 0:
                missing.append(package)
        return missing


def normalize_language(language: str | None) -> str:
    if not language:
        return "python"
    normalized = language.lower().strip()
    aliases = {
        "py": "python",
        "python3": "python",
        "do": "stata",
        "do-file": "stata",
        "dofile": "stata",
        "rscript": "r",
    }
    return aliases.get(normalized, normalized)


def infer_language_from_path(path: str | Path | None, default: str = "python") -> str:
    if path is None:
        return normalize_language(default)
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        return "python"
    if suffix == ".do":
        return "stata"
    if suffix == ".r":
        return "r"
    return normalize_language(default)


def _date_seed() -> str:
    return date.today().strftime("%Y%m%d")


def _is_python_seed_call(
    func: ast.expr,
    random_aliases: set[str],
    numpy_aliases: set[str],
    random_seed_aliases: set[str],
    numpy_seed_aliases: set[str],
) -> bool:
    if isinstance(func, ast.Name):
        return func.id in random_seed_aliases or func.id in numpy_seed_aliases
    if not isinstance(func, ast.Attribute) or func.attr != "seed":
        return False
    owner = func.value
    if isinstance(owner, ast.Name):
        return owner.id in random_aliases
    if isinstance(owner, ast.Attribute) and owner.attr == "random" and isinstance(owner.value, ast.Name):
        return owner.value.id in numpy_aliases
    return False


def _is_python_default_rng_call(
    func: ast.expr,
    numpy_aliases: set[str],
    default_rng_aliases: set[str],
) -> bool:
    if isinstance(func, ast.Name):
        return func.id in default_rng_aliases
    if not isinstance(func, ast.Attribute) or func.attr != "default_rng":
        return False
    owner = func.value
    return isinstance(owner, ast.Attribute) and owner.attr == "random" and isinstance(owner.value, ast.Name) and owner.value.id in numpy_aliases


def _iter_stata_code_lines(code: str) -> Iterator[str]:
    in_block_comment = False
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if in_block_comment:
            end = line.find("*/")
            if end == -1:
                continue
            line = line[end + 2 :].strip()
            in_block_comment = False
        while "/*" in line:
            start = line.find("/*")
            end = line.find("*/", start + 2)
            if end == -1:
                line = line[:start].strip()
                in_block_comment = True
                break
            line = f"{line[:start]} {line[end + 2:]}".strip()
        if in_block_comment and not line:
            continue
        if not line or line.startswith("*"):
            continue
        line = re.sub(r"(^|\s)//.*$", "", line).strip()
        if line:
            yield line


def _iter_r_code_lines(code: str) -> Iterator[str]:
    for raw_line in code.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"(^|\s)#.*$", "", line).strip()
        if line:
            yield line
