"""CLI entrypoint for AESDK."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import typer

from aesdk.core.project import Project
from aesdk.governance.checks.citation_validator import verify_text
from aesdk.governance.policy import ConformanceLevel
from aesdk.protocol.validator import RuleRegistry, Validator
from aesdk.trace import replay_execute_events
from aesdk.trace.blob import ReplicationBlob, sign_blob, verify_blob_signature

app = typer.Typer(help="Agentic Econometrics SDK")
cite_app = typer.Typer(help="Citation utilities")
audit_app = typer.Typer(help="Audit utilities")
app.add_typer(cite_app, name="cite")
app.add_typer(audit_app, name="audit")


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


@app.command("init")
def init_cmd(
    pap: Path = typer.Option(..., exists=True),
    blob: Path | None = typer.Option(None),
    context: str = typer.Option("research", help="Execution context: research|production|regulated"),
    conformance: str | None = typer.Option(None, help="Conformance level override: basic|strict|regulated"),
    policy_version: str = typer.Option("1.0.0", help="Policy version tag for governance passport."),
    attestation_endpoint: str | None = typer.Option(None, help="Optional remote attestation endpoint."),
    attestation_token: str | None = typer.Option(None, help="Optional bearer token for attestation endpoint."),
) -> None:
    project = Project.create(
        pap_path=pap,
        blob_path=blob,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
        attestation_endpoint=attestation_endpoint,
        attestation_token=attestation_token,
    )
    typer.echo(f"initialized project={project.blob.project_id} blob={project.blob_path}")
    typer.echo(f"passport={project.governance_passport}")


@app.command("validate")
def validate_cmd(
    pap: Path = typer.Option(..., exists=True),
    proposal: Path = typer.Option(..., exists=True),
    rules_dir: Path | None = typer.Option(None),
    conformance: str = typer.Option("basic", help="Conformance level: basic|strict|regulated"),
) -> None:
    pap_dict = _load_json(pap) if pap.suffix.lower() == ".json" else None
    if pap_dict is None:
        from aesdk.governance.pap import validate_pap_file

        pap_dict = validate_pap_file(pap)
    proposal_dict = _load_json(proposal)
    registry = RuleRegistry(rules_dir=rules_dir) if rules_dir else RuleRegistry()
    result = Validator(registry=registry).validate(
        pap=pap_dict,
        proposal=proposal_dict,
        conformance=ConformanceLevel(conformance.lower()),
    )
    typer.echo(f"status={result.status}")
    for violation in result.violations:
        typer.echo(
            f"- {violation.rule_id} severity={violation.severity.value} citation={violation.citation}\n"
            f"  message={violation.message}"
        )


@app.command("execute")
def execute_cmd(
    pap: Path = typer.Option(..., exists=True),
    proposal: Path = typer.Option(..., exists=True),
    code_file: Path = typer.Option(..., exists=True),
    blob: Path | None = typer.Option(None),
    context: str = typer.Option("research"),
    conformance: str | None = typer.Option(None),
    policy_version: str = typer.Option("1.0.0"),
) -> None:
    project = Project.create(
        pap_path=pap,
        blob_path=blob,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    proposal_dict = _load_json(proposal)
    project.propose_model(proposal_dict)
    result = project.validate()
    if result.blocked:
        typer.echo("execution=blocked")
        for violation in result.violations:
            typer.echo(f"- {violation.rule_id} severity={violation.severity.value}")
        raise typer.Exit(code=1)

    code = code_file.read_text(encoding="utf-8-sig")
    run_result = project.execute(code)
    typer.echo(f"execution_status={run_result.status}")


@app.command("reproduce")
def reproduce_cmd(
    blob: Path = typer.Option(..., exists=True),
    replay: bool = typer.Option(False, help="Replay execute events using sandbox."),
    fail_on_replay_mismatch: bool = typer.Option(True, help="Exit non-zero when replay mismatches are found."),
) -> None:
    loaded = ReplicationBlob.load(blob)
    valid, errors = loaded.verify_integrity()
    typer.echo(f"integrity={'ok' if valid else 'failed'}")
    if loaded.metadata:
        typer.echo(f"metadata={loaded.metadata}")
    for event in loaded.events:
        typer.echo(f"- {event.timestamp} {event.event_type}")
    if not valid:
        for error in errors:
            typer.echo(f"error: {error}")
        raise typer.Exit(code=1)

    if replay:
        mismatches = 0
        typer.echo("replay:start")
        for item in replay_execute_events(blob):
            ok = item.code_hash_matches and item.recorded_status == item.replay_status
            typer.echo(
                f"replay:execute[{item.event_index}] recorded={item.recorded_status} replay={item.replay_status} "
                f"code_hash_match={item.code_hash_matches} ok={ok}"
            )
            if not ok:
                mismatches += 1
        typer.echo("replay:end")
        if mismatches and fail_on_replay_mismatch:
            raise typer.Exit(code=1)


@audit_app.command("sign")
def audit_sign_cmd(
    blob: Path = typer.Option(..., exists=True),
    mode: str = typer.Option("hmac", help="Signing mode: hmac|kms-http"),
    secret: str | None = typer.Option(None, help="HMAC secret (required for hmac mode)."),
    key_id: str = typer.Option("local", help="Identifier for signing key."),
    kms_endpoint: str | None = typer.Option(None, help="KMS HTTP endpoint (required for kms-http mode)."),
    kms_token: str | None = typer.Option(None, help="Bearer token for KMS endpoint."),
) -> None:
    sig_path = sign_blob(
        blob,
        mode=mode,
        secret=secret,
        key_id=key_id,
        kms_endpoint=kms_endpoint,
        kms_token=kms_token,
    )
    typer.echo(f"signature_written={sig_path}")


@audit_app.command("verify-signature")
def audit_verify_signature_cmd(
    blob: Path = typer.Option(..., exists=True),
    signature: Path = typer.Option(..., exists=True),
    secret: str | None = typer.Option(None, help="HMAC secret for hmac signatures."),
    kms_endpoint: str | None = typer.Option(None, help="KMS endpoint override for kms-http signatures."),
    kms_token: str | None = typer.Option(None, help="Bearer token for KMS endpoint."),
) -> None:
    ok, message = verify_blob_signature(
        blob,
        signature,
        secret=secret,
        kms_endpoint=kms_endpoint,
        kms_token=kms_token,
    )
    typer.echo(f"signature_valid={ok} message={message}")
    if not ok:
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
