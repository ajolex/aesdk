"""CLI entrypoint for AESDK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from aesdk.core.project import Project
from aesdk.governance.checks.citation_validator import verify_text
from aesdk.governance.pap import validate_pap_file
from aesdk.protocol.validator import RuleRegistry, Validator
from aesdk.trace.blob import ReplicationBlob

app = typer.Typer(help="Agentic Econometrics SDK")
cite_app = typer.Typer(help="Citation utilities")
app.add_typer(cite_app, name="cite")


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@app.command("init")
def init_cmd(pap: Path = typer.Option(..., exists=True), blob: Path | None = typer.Option(None)) -> None:
    project = Project.create(pap_path=pap, blob_path=blob)
    typer.echo(f"initialized project={project.blob.project_id} blob={project.blob_path}")


@app.command("validate")
def validate_cmd(
    pap: Path = typer.Option(..., exists=True),
    proposal: Path = typer.Option(..., exists=True),
    rules_dir: Path | None = typer.Option(None),
) -> None:
    pap_dict = validate_pap_file(pap)
    proposal_dict = _load_json(proposal)
    registry = RuleRegistry(rules_dir=rules_dir) if rules_dir else RuleRegistry()
    result = Validator(registry=registry).validate(pap=pap_dict, proposal=proposal_dict)
    typer.echo(f"status={result.status}")
    for violation in result.violations:
        typer.echo(
            f"- {violation.rule_id} severity={violation.severity.value} citation={violation.citation}\n"
            f"  message={violation.message}"
        )


@app.command("reproduce")
def reproduce_cmd(blob: Path = typer.Option(..., exists=True)) -> None:
    loaded = ReplicationBlob.load(blob)
    valid, errors = loaded.verify_integrity()
    typer.echo(f"integrity={'ok' if valid else 'failed'}")
    for event in loaded.events:
        typer.echo(f"- {event.timestamp} {event.event_type}")
    if not valid:
        for error in errors:
            typer.echo(f"error: {error}")
        raise typer.Exit(code=1)


@cite_app.command("verify")
def cite_verify_cmd(
    text: str = typer.Option("-", help="Path to text file or '-' for stdin."),
    online: bool = typer.Option(False, help="Enable online DOI reachability checks."),
) -> None:
    if text == "-":
        content = sys.stdin.read()
    else:
        content = Path(text).read_text(encoding="utf-8-sig")
    report = verify_text(content, online=online)
    typer.echo(f"dois_found={len(report.dois)} invalid_format={report.invalid_format_count}")
    for item in report.dois:
        typer.echo(f"- doi={item.doi} format={item.valid_format} reachable={item.reachable}")


if __name__ == "__main__":  # pragma: no cover
    app()
