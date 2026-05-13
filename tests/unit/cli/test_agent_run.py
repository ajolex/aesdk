import json

from typer.testing import CliRunner

from aesdk.cli.main import app


def test_agent_run_prints_sandbox_diagnostics_for_missing_r_runtime(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_R", "definitely-not-rscript")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.R"
    code_path.write_text("print(1)", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "run",
            "--method",
            "did",
            "--pap",
            str(valid_pap_file),
            "--proposal",
            str(proposal_path),
            "--code-file",
            str(code_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=block blocked=True" in result.output
    assert "MISSING_RUNTIME" in result.output
    assert "Rscript executable was not found" in result.output


def test_agent_run_prints_sandbox_diagnostics_for_missing_stata_runtime(valid_pap_file, tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("AESDK_STATA", "definitely-not-stata")
    proposal_path = tmp_path / "proposal.json"
    proposal_path.write_text(
        json.dumps({"estimator": "DiD", "standard_errors": "cluster", "clustering": "state"}),
        encoding="utf-8",
    )
    code_path = tmp_path / "analysis.do"
    code_path.write_text("display 1", encoding="utf-8")

    result = CliRunner().invoke(
        app,
        [
            "agent",
            "run",
            "--method",
            "did",
            "--pap",
            str(valid_pap_file),
            "--proposal",
            str(proposal_path),
            "--code-file",
            str(code_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=block blocked=True" in result.output
    assert "MISSING_RUNTIME" in result.output
    assert "Stata executable was not found" in result.output
