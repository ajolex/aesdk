"""Tests for the plain-language `aesdk setup` onboarding path."""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

import aesdk as ae
from aesdk.agent import run_setup
from aesdk.cli.main import app


def test_run_setup_reports_ready_and_writes_templates(tmp_path: Path) -> None:
    result = run_setup(output_dir=tmp_path, write_templates="both")
    assert result.ready is True
    assert result.aesdk_version
    assert result.method_count >= 12
    assert set(result.templates_written) == {"AGENTS.md", "CLAUDE.md"}
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").is_file()
    report = result.friendly_report()
    assert "ready" in report.lower()
    # Plain-language, no raw command dumps in the readiness headline.
    assert "aesdk agent preflight" not in report


def test_run_setup_keeps_existing_templates(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("my own notes", encoding="utf-8")
    result = run_setup(output_dir=tmp_path, write_templates="AGENTS.md")
    assert "AGENTS.md" in result.templates_present
    assert "AGENTS.md" not in result.templates_written
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "my own notes"


def test_run_setup_force_overwrites(tmp_path: Path) -> None:
    (tmp_path / "AGENTS.md").write_text("old", encoding="utf-8")
    result = run_setup(output_dir=tmp_path, write_templates="AGENTS.md", force=True)
    assert "AGENTS.md" in result.templates_written
    assert "AESDK" in (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def test_run_setup_none_writes_no_templates(tmp_path: Path) -> None:
    result = run_setup(output_dir=tmp_path, write_templates="none")
    assert result.templates_written == []
    assert not (tmp_path / "AGENTS.md").exists()


def test_setup_output_is_ascii(tmp_path: Path) -> None:
    # Non-technical users on Windows terminals should not see mojibake.
    report = run_setup(output_dir=tmp_path, write_templates="none").friendly_report()
    report.encode("ascii")


def test_setup_cli_text_and_json(tmp_path: Path) -> None:
    runner = CliRunner()
    text = runner.invoke(app, ["setup", "--output-dir", str(tmp_path), "--template", "none"])
    assert text.exit_code == 0
    assert "ready" in text.output.lower()
    payload = runner.invoke(
        app, ["setup", "--output-dir", str(tmp_path), "--template", "none", "--format", "json"]
    )
    assert payload.exit_code == 0
    data = json.loads(payload.output)
    assert data["ready"] is True
    assert data["method_count"] >= 12


def test_setup_exposed_on_public_api() -> None:
    assert hasattr(ae, "run_setup")
    assert hasattr(ae, "SetupResult")
