"""CLI entrypoint for AESDK."""

from __future__ import annotations

import json
import os
import platform
import shutil
import subprocess
import sys
from importlib.metadata import PackageNotFoundError, version
from importlib.resources import files
from pathlib import Path
from typing import Any

import typer
import yaml

from aesdk.agent import (
    agent_context,
    append_interaction_log,
    draft_pap,
    intake_prompt,
    intake_task,
    preflight,
    run_analysis,
    run_setup,
    write_ai_passport,
    write_claude_runtime_metadata,
    write_codex_runtime_metadata,
    write_copilot_runtime_metadata,
    write_review_diff,
    write_workflow_report,
)
from aesdk.config import config
from aesdk.core.project import Project
from aesdk.governance.checks.citation_validator import verify_text
from aesdk.governance.policy import ConformanceLevel
from aesdk.knowledge import (
    get_knowledge_pack,
    get_method_protocol,
    get_method_source_map,
    get_source,
    list_knowledge_pack_ids,
    list_method_ids,
    list_source_ids,
    load_curriculum,
    load_official_software_sources,
    load_source_inventory,
    validate_knowledge_base,
)
from aesdk.protocol.validator import RuleRegistry, Validator
from aesdk.sandbox.runner import SandboxRunner, infer_language_from_path, normalize_language
from aesdk.sandbox.runner import (
    _R_EXECUTABLE_CANDIDATES,
    _R_EXECUTABLE_ENV,
    _STATA_EXECUTABLE_CANDIDATES,
    _STATA_EXECUTABLE_ENV,
)
from aesdk.trace import replay_execute_events
from aesdk.trace.blob import ReplicationBlob, sign_blob, verify_blob_signature

app = typer.Typer(help="Agentic Econometrics SDK")
cite_app = typer.Typer(help="Citation utilities")
audit_app = typer.Typer(help="Audit utilities")
methods_app = typer.Typer(help="Textbook-backed method protocols")
sources_app = typer.Typer(help="Registered textbook and literature sources")
agent_app = typer.Typer(help="Agent-facing preflight and context helpers")
rules_app = typer.Typer(help="Executable econometric governance rules")
app.add_typer(cite_app, name="cite")
app.add_typer(audit_app, name="audit")
app.add_typer(methods_app, name="methods")
app.add_typer(sources_app, name="sources")
app.add_typer(agent_app, name="agent")
app.add_typer(rules_app, name="rules")


def _load_json(path: str | Path) -> dict:
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _read_prompt_value(prompt: str | None, prompt_file: Path | None) -> str | None:
    if prompt and prompt_file:
        raise typer.BadParameter("Use either --prompt or --prompt-file, not both.")
    if prompt_file:
        return prompt_file.read_text(encoding="utf-8-sig")
    return prompt


def _package_version() -> str:
    try:
        return version("aesdk")
    except PackageNotFoundError:
        try:
            from aesdk._version import __version__
        except Exception:
            return "unknown"
        return __version__


def _resolve_executable(configured: str | None, candidates: tuple[str, ...]) -> str | None:
    if configured:
        configured_path = Path(configured)
        if configured_path.exists():
            return str(configured_path)
        discovered = shutil.which(configured)
        if discovered:
            return discovered
    for candidate in candidates:
        discovered = shutil.which(candidate)
        if discovered:
            return discovered
    return None


def _method_from_pap_strategy(pap_path: Path) -> str:
    from aesdk.governance.pap import validate_pap_file

    pap = validate_pap_file(pap_path)
    strategy = str(pap.get("identification", {}).get("strategy", "")).strip()
    mapping = {
        "OLS": "ols_cef",
        "IV": "iv_2sls",
        "2SLS": "iv_2sls",
        "FE": "panel_fe",
        "POLS": "panel_fe",
        "RE": "panel_fe",
        "DiD": "did",
        "TWFE": "did" if pap.get("did_block") else "panel_fe",
        "EventStudy": "did",
        "RCT": "experimental_rct",
        "RandomizedExperiment": "experimental_rct",
        "RDD": "rdd",
        "Matching": "matching",
        "SyntheticControl": "synthetic_control",
        "NonlinearDiD": "nonlinear_did",
        "GMM": "gmm",
        "Logit": "limited_dependent",
        "ConditionalLogit": "limited_dependent",
        "MixedLogit": "limited_dependent",
        "Probit": "limited_dependent",
        "ARIMA": "time_series",
    }
    return mapping.get(strategy, "ols_cef")


def _save_preparation_blob(
    *,
    pap: Path,
    proposal: Path,
    blob: Path | None,
    context: str,
    conformance: str,
    policy_version: str,
) -> tuple[Project, Any]:
    project = Project.create(
        pap_path=pap,
        proposal_path=proposal,
        blob_path=blob,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    project.propose_model(_load_json(proposal))
    validation = project.validate()
    return project, validation


@agent_app.command("context")
def agent_context_cmd(
    method: str = typer.Option(..., help="Method id, for example did or iv_2sls."),
    depth: str = typer.Option("protocol", help="Context depth: protocol|full"),
    output_format: str = typer.Option("markdown", "--format", help="Output format: markdown|json|yaml"),
) -> None:
    ctx = agent_context(method, depth=depth)
    if output_format.lower() == "markdown":
        typer.echo(ctx.to_markdown())
    elif output_format.lower() == "yaml":
        typer.echo(ctx.to_yaml())
    elif output_format.lower() == "json":
        typer.echo(json.dumps(ctx.to_dict(), indent=2))
    else:
        raise typer.BadParameter("format must be markdown, json, or yaml")


@agent_app.command("preflight")
def agent_preflight_cmd(
    method: str = typer.Option(..., help="Method id, for example did or iv_2sls."),
    pap: Path | None = typer.Option(None, exists=True, help="Optional PAP path."),
    proposal: Path | None = typer.Option(None, exists=True, help="Optional proposal JSON path."),
    conformance: str = typer.Option("strict", help="Conformance level: basic|strict|regulated"),
    output_format: str = typer.Option("text", "--format", help="Output format: text|json|markdown"),
    scan_data_file: bool = typer.Option(
        True,
        "--scan-data/--no-scan-data",
        help="Read the declared dataset and cross-check the PAP structure against it.",
    ),
    data: Path | None = typer.Option(
        None,
        "--data",
        exists=True,
        help="Explicit dataset path for the data scan (overrides data.source in the PAP).",
    ),
) -> None:
    result = preflight(
        method=method,
        pap_path=pap,
        proposal=proposal,
        conformance=conformance,
        scan_data_file=scan_data_file,
        data_path=data,
    )
    if output_format.lower() == "json":
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format.lower() == "markdown":
        typer.echo(result.agent_context_markdown())
        typer.echo("\n## Preflight Result\n")
        typer.echo(result.explain())
    elif output_format.lower() == "text":
        typer.echo(f"status={result.status} blocked={result.blocked}")
        typer.echo(result.explain())
    else:
        raise typer.BadParameter("format must be text, json, or markdown")
    if result.blocked:
        raise typer.Exit(code=1)


@agent_app.command("scan-data")
def agent_scan_data_cmd(
    method: str = typer.Option(..., help="Method id, for example did or iv_2sls."),
    pap: Path = typer.Option(..., exists=True, help="PAP path declaring the dataset and variables."),
    proposal: Path | None = typer.Option(None, exists=True, help="Optional proposal JSON path."),
    data: Path | None = typer.Option(
        None, "--data", exists=True, help="Explicit dataset path (overrides data.source in the PAP)."
    ),
    conformance: str = typer.Option("strict", help="Conformance level: basic|strict|regulated"),
    output_format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Read the declared dataset and cross-check the PAP structure against it."""

    from aesdk.data import scan_data as _scan_data
    from aesdk.governance.pap import validate_pap_file

    pap_doc = validate_pap_file(pap)
    loaded_proposal: dict[str, Any] = {}
    if proposal is not None:
        with Path(proposal).open("r", encoding="utf-8-sig") as handle:
            loaded_proposal = json.load(handle)
    base_dirs = [Path.cwd(), Path(pap).resolve().parent]
    result = _scan_data(
        method=method,
        pap=pap_doc,
        proposal=loaded_proposal,
        data_path=data,
        base_dirs=base_dirs,
        conformance=conformance,
    )
    if output_format.lower() == "json":
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format.lower() == "text":
        if not result.scanned:
            typer.echo(f"scanned=False reason={result.profile.reason_unresolved}")
        else:
            profile = result.profile
            typer.echo(
                f"scanned=True path={profile.path} rows={profile.n_rows} columns={profile.n_columns}"
            )
            typer.echo(
                f"units={profile.n_units} periods={profile.n_periods} "
                f"balanced={profile.balanced_panel} clusters={profile.n_clusters} "
                f"adoption_cohorts={profile.adoption_cohorts}"
            )
        if result.profile.ols_assumptions and result.profile.ols_assumptions.fitted:
            typer.echo("OLS assumption checklist (Wooldridge):")
            for check in result.profile.ols_assumptions.checks:
                typer.echo(f"  [{check.status}] {check.wooldridge} {check.name}")
        for finding in result.findings:
            typer.echo(f"- {finding.rule_id} severity={finding.severity.value}: {finding.message}")
            if finding.guidance:
                typer.echo(f"  guidance: {finding.guidance}")
    else:
        raise typer.BadParameter("format must be text or json")
    if any(finding.severity.value == "error" for finding in result.findings):
        raise typer.Exit(code=1)


@agent_app.command("check-ols")
def agent_check_ols_cmd(
    pap: Path = typer.Option(..., exists=True, help="PAP declaring the dataset, outcome, and regressors."),
    proposal: Path | None = typer.Option(None, exists=True, help="Optional proposal JSON path."),
    data: Path | None = typer.Option(
        None, "--data", exists=True, help="Explicit dataset path (overrides data.source in the PAP)."
    ),
    output_format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Fit the declared OLS model and run the ten-item Wooldridge assumption checklist."""

    from aesdk.data import scan_data as _scan_data
    from aesdk.governance.pap import validate_pap_file

    pap_doc = validate_pap_file(pap)
    loaded_proposal: dict[str, Any] = {}
    if proposal is not None:
        with Path(proposal).open("r", encoding="utf-8-sig") as handle:
            loaded_proposal = json.load(handle)
    base_dirs = [Path.cwd(), Path(pap).resolve().parent]
    result = _scan_data(
        method="ols_cef",
        pap=pap_doc,
        proposal=loaded_proposal,
        data_path=data,
        base_dirs=base_dirs,
        conformance="basic",
    )
    report = result.profile.ols_assumptions
    if output_format.lower() == "json":
        typer.echo(json.dumps(report.to_dict() if report else {"fitted": False}, indent=2))
        return
    if output_format.lower() != "text":
        raise typer.BadParameter("format must be text or json")
    if report is None or not report.fitted:
        reason = (report.reason_unfitted if report else result.profile.reason_unresolved) or "model not fitted"
        typer.echo(f"fitted=False reason={reason}")
        raise typer.Exit(code=1)
    typer.echo(f"fitted=True n={report.n_obs} k={report.n_params} r_squared={report.r_squared}")
    if report.dropped_non_numeric:
        typer.echo(f"dropped_non_numeric={report.dropped_non_numeric}")
    for check in report.checks:
        line = f"[{check.status}] {check.wooldridge} {check.name}"
        if check.p_value is not None:
            line += f" (p={check.p_value})"
        typer.echo(line)
        typer.echo(f"    {check.detail}")


@agent_app.command("draft-pap")
def agent_draft_pap_cmd(
    goal: str = typer.Option(..., help="Analysis goal/title."),
    method: str = typer.Option(..., help="Method id, for example did or iv_2sls."),
    data: Path | None = typer.Option(None, exists=True, help="Optional data file path."),
    outcome: str = typer.Option("outcome", help="Outcome variable."),
    treatment: str = typer.Option("treatment", help="Treatment variable."),
    covariate: list[str] = typer.Option([], help="Mandatory covariate. Repeat for multiple values."),
    unit: str | None = typer.Option(None, help="Panel/group unit variable."),
    time: str | None = typer.Option(None, help="Time variable."),
    author: str = typer.Option("AESDK Agent", help="PAP author."),
    design_origin: str | None = typer.Option(
        None,
        help="Optional design provenance: experimental_rct|observational|natural_experiment|administrative_rollout|unknown.",
    ),
    output: Path | None = typer.Option(None, help="Write YAML PAP to this path."),
) -> None:
    pap = draft_pap(
        goal=goal,
        method=method,
        data_path=data,
        outcome=outcome,
        treatment=treatment,
        covariates=covariate,
        unit=unit,
        time=time,
        author=author,
        design_origin=design_origin,
    )
    rendered = yaml.safe_dump(pap, sort_keys=False)
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        typer.echo(f"pap_written={output}")
    else:
        typer.echo(rendered)


@agent_app.command("intake")
def agent_intake_cmd(
    task: Path | None = typer.Option(None, exists=True, help="Task document path. PDF, TXT, and MD are supported."),
    prompt: str | None = typer.Option(None, help="Raw task prompt when no task document exists."),
    prompt_file: Path | None = typer.Option(None, exists=True, help="Text file containing the raw task prompt."),
    data: Path | None = typer.Option(None, exists=True, help="Optional analysis data path."),
    method: str | None = typer.Option(None, help="Optional method id. If omitted, AESDK infers a first draft."),
    output_dir: Path | None = typer.Option(None, help="Folder for pap.yaml, proposal.json, and extracted task text."),
    outcome: str = typer.Option("outcome", help="Outcome variable."),
    treatment: str = typer.Option("treatment", help="Treatment variable."),
    unit: str | None = typer.Option(None, help="Panel/group unit variable."),
    time: str | None = typer.Option(None, help="Time variable."),
    design_origin: str | None = typer.Option(
        None,
        help="Optional design provenance: experimental_rct|observational|natural_experiment|administrative_rollout|unknown.",
    ),
    title: str | None = typer.Option(None, help="Optional PAP title."),
    blob: Path | None = typer.Option(None, help="Output .aesdk.json path. Defaults to output-dir/.aesdk.json."),
    context: str = typer.Option("research", help="Execution context for the replication blob."),
    conformance: str = typer.Option("basic", help="Conformance level for the starter replication blob."),
    policy_version: str = typer.Option("1.0.0", help="Policy version tag for governance passport."),
) -> None:
    prompt_text = _read_prompt_value(prompt, prompt_file)
    if task is None and prompt_text is None:
        raise typer.BadParameter("Provide --task, --prompt, or --prompt-file.")
    if task is not None and prompt_text is not None:
        raise typer.BadParameter("Use task input or prompt input, not both.")
    if prompt_text is not None:
        result = intake_prompt(
            prompt=prompt_text,
            data_path=data,
            method=method,
            output_dir=output_dir,
            outcome=outcome,
            treatment=treatment,
            unit=unit,
            time=time,
            design_origin=design_origin,
            title=title,
        )
    else:
        assert task is not None
        result = intake_task(
            task_path=task,
            data_path=data,
            method=method,
            output_dir=output_dir,
            outcome=outcome,
            treatment=treatment,
            unit=unit,
            time=time,
            design_origin=design_origin,
            title=title,
        )
    typer.echo(f"method={result.method}")
    typer.echo(f"pap_written={result.pap_path}")
    typer.echo(f"proposal_written={result.proposal_path}")
    if result.task_text_path:
        typer.echo(f"task_text_written={result.task_text_path}")
    blob_path = blob or result.pap_path.parent / ".aesdk.json"
    project, validation = _save_preparation_blob(
        pap=result.pap_path,
        proposal=result.proposal_path,
        blob=blob_path,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    typer.echo(f"blob_written={project.blob_path}")
    typer.echo(f"status={validation.status} blocked={validation.blocked}")
    for violation in validation.violations:
        typer.echo(f"- {violation.rule_id} severity={violation.severity.value} message={violation.message}")
    if validation.blocked:
        raise typer.Exit(code=1)


@agent_app.command("prepare")
def agent_prepare_cmd(
    task: Path | None = typer.Option(None, exists=True, help="Optional task document path."),
    prompt: str | None = typer.Option(None, help="Raw task prompt when no task document exists."),
    prompt_file: Path | None = typer.Option(None, exists=True, help="Text file containing the raw task prompt."),
    data: Path | None = typer.Option(None, exists=True, help="Optional analysis data path."),
    method: str | None = typer.Option(None, help="Method id. If omitted, AESDK infers from intake or PAP."),
    pap: Path = typer.Option(Path("pap.yaml"), help="PAP path to create or validate."),
    proposal: Path = typer.Option(Path("proposal.json"), help="Proposal path to create or validate."),
    output_dir: Path = typer.Option(Path("."), help="Folder for starter files and the AESDK replication blob."),
    outcome: str = typer.Option("outcome", help="Outcome variable."),
    treatment: str = typer.Option("treatment", help="Treatment variable."),
    unit: str | None = typer.Option(None, help="Panel/group unit variable."),
    time: str | None = typer.Option(None, help="Time variable."),
    design_origin: str | None = typer.Option(
        None,
        help="Optional design provenance: experimental_rct|observational|natural_experiment|administrative_rollout|unknown.",
    ),
    title: str | None = typer.Option(None, help="Optional PAP title."),
    blob: Path | None = typer.Option(None, help="Output .aesdk.json path. Defaults to output-dir/.aesdk.json."),
    context: str = typer.Option("research", help="Execution context: research|production|regulated"),
    conformance: str = typer.Option("basic", help="Conformance level for the starter replication blob: basic|strict|regulated"),
    policy_version: str = typer.Option("1.0.0", help="Policy version tag for governance passport."),
) -> None:
    prompt_text = _read_prompt_value(prompt, prompt_file)
    active_output_dir = output_dir
    active_output_dir.mkdir(parents=True, exist_ok=True)
    pap_path = pap if pap.is_absolute() else active_output_dir / pap
    proposal_path = proposal if proposal.is_absolute() else active_output_dir / proposal

    if not pap_path.exists() or not proposal_path.exists():
        if task is None and prompt_text is None:
            raise typer.BadParameter(
                "pap/proposal do not exist yet. Provide --task, --prompt, or --prompt-file so AESDK can scaffold them."
            )
        if task is not None and prompt_text is not None:
            raise typer.BadParameter("Use task input or prompt input, not both.")
        if prompt_text is not None:
            intake = intake_prompt(
                prompt=prompt_text,
                data_path=data,
                method=method,
                output_dir=active_output_dir,
                outcome=outcome,
                treatment=treatment,
                unit=unit,
                time=time,
                design_origin=design_origin,
                title=title,
            )
        else:
            assert task is not None
            intake = intake_task(
                task_path=task,
                data_path=data,
                method=method,
                output_dir=active_output_dir,
                outcome=outcome,
                treatment=treatment,
                unit=unit,
                time=time,
                design_origin=design_origin,
                title=title,
            )
        pap_path = intake.pap_path
        proposal_path = intake.proposal_path
        active_method = intake.method
        typer.echo(f"method={active_method}")
        typer.echo(f"pap_written={pap_path}")
        typer.echo(f"proposal_written={proposal_path}")
        if intake.task_text_path:
            typer.echo(f"task_text_written={intake.task_text_path}")
    else:
        active_method = method or _method_from_pap_strategy(pap_path)
        typer.echo(f"method={active_method}")
        typer.echo(f"pap_existing={pap_path}")
        typer.echo(f"proposal_existing={proposal_path}")

    blob_path = blob or active_output_dir / ".aesdk.json"
    project, validation = _save_preparation_blob(
        pap=pap_path,
        proposal=proposal_path,
        blob=blob_path,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
    )
    typer.echo(f"blob_written={project.blob_path}")
    typer.echo(f"status={validation.status} blocked={validation.blocked}")
    for violation in validation.violations:
        typer.echo(f"- {violation.rule_id} severity={violation.severity.value} message={violation.message}")
    if validation.blocked:
        raise typer.Exit(code=1)


@agent_app.command("report")
def agent_report_cmd(
    blob: Path = typer.Option(..., exists=True, help="AESDK replication blob path."),
    output: Path | None = typer.Option(None, help="Optional HTML report output path."),
    title: str = typer.Option("AESDK Workflow Report", help="Report title."),
) -> None:
    target = write_workflow_report(blob_path=blob, output_path=output, title=title)
    typer.echo(f"report_written={target}")


@agent_app.command("ai-passport")
def agent_ai_passport_cmd(
    pap: Path = typer.Option(..., exists=True, help="PAP path containing optional ai_use metadata."),
    proposal: Path | None = typer.Option(None, exists=True, help="Optional proposal JSON path."),
    output: Path | None = typer.Option(None, help="Output ai.lock.json path."),
    summary_output: Path | None = typer.Option(None, "--summary-output", help="Optional compact JSON summary of evidence gaps and improvement opportunities."),
    allow_incomplete: bool = typer.Option(
        False,
        "--allow-incomplete",
        help="Write the passport even if AI evidence is incomplete and would otherwise block.",
    ),
) -> None:
    result = write_ai_passport(pap_path=pap, proposal_path=proposal, output_path=output, summary_output_path=summary_output)
    typer.echo(f"ai_passport_written={result.path}")
    if result.summary_path:
        typer.echo(f"ai_passport_summary_written={result.summary_path}")
    typer.echo(f"status={result.status}")
    if result.blocked and not allow_incomplete:
        for finding in result.passport.get("findings", []):
            typer.echo(f"- {finding.get('code')} severity={finding.get('severity')} message={finding.get('message')}")
        raise typer.Exit(code=1)


@agent_app.command("review-diff")
def agent_review_diff_cmd(
    ai_code: Path = typer.Option(..., exists=True, help="AI-generated code draft path."),
    final_code: Path = typer.Option(..., exists=True, help="Final code path after human edits/review."),
    output: Path = typer.Option(..., help="Output unified diff or patch path."),
    label_ai: str = typer.Option("ai_generated", help="Label for the AI draft side of the diff."),
    label_final: str = typer.Option("final_reviewed", help="Label for the final code side of the diff."),
) -> None:
    result = write_review_diff(
        ai_code_path=ai_code,
        final_code_path=final_code,
        output_path=output,
        label_ai=label_ai,
        label_final=label_final,
    )
    typer.echo(f"review_diff_written={result.path}")
    typer.echo(f"changed={str(result.changed).lower()} line_count={result.line_count}")


@agent_app.command("interaction-log")
def agent_interaction_log_cmd(
    output: Path = typer.Option(Path("review/followup_transcript.md"), help="Human-in-loop interaction log path."),
    speaker: str = typer.Option(..., help="Entry speaker: human|agent|system|other."),
    message: str = typer.Option(..., help="Interaction text to append."),
    source: str | None = typer.Option(None, help="Optional source, such as chat, code review, email, or meeting."),
) -> None:
    normalized = speaker.strip().lower()
    if normalized not in {"human", "agent", "system", "other"}:
        raise typer.BadParameter("speaker must be human, agent, system, or other")
    result = append_interaction_log(
        output_path=output,
        speaker=normalized,  # type: ignore[arg-type]
        message=message,
        source=source,
    )
    typer.echo(f"interaction_log_written={result.path}")
    typer.echo(f"entries={result.entry_count} sha256={result.sha256}")


@agent_app.command("codex-runtime")
def agent_codex_runtime_cmd(
    output: Path = typer.Option(Path("codex_runtime.json"), help="Output runtime metadata JSON path."),
    workspace: Path = typer.Option(Path("."), help="Workspace/repo path to inspect."),
    surface: str = typer.Option("Codex Desktop / IDE extension", help="Codex surface, for example Desktop or IDE extension."),
    session_model: str | None = typer.Option(None, help="Override active session model when known from /status or /model."),
    reasoning_effort: str | None = typer.Option(None, help="Override reasoning effort when known from /status, /model, or config."),
    reasoning_summary: str | None = typer.Option(None, help="Override reasoning summary config value when known."),
    verbosity: str | None = typer.Option(None, help="Override verbosity config value when known."),
    approval_policy: str | None = typer.Option(None, help="Override approval policy when known."),
    sandbox_mode: str | None = typer.Option(None, help="Override sandbox mode when known."),
    timezone: str = typer.Option("Asia/Manila", help="IANA timezone for timestamp rendering."),
) -> None:
    result = write_codex_runtime_metadata(
        output_path=output,
        workspace_path=workspace,
        surface=surface,
        session_model=session_model,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        verbosity=verbosity,
        approval_policy=approval_policy,
        sandbox_mode=sandbox_mode,
        timezone=timezone,
    )
    typer.echo(f"runtime_metadata_written={result.path}")
    typer.echo(result.metadata.get("metadata_block", ""))


@agent_app.command("claude-runtime")
def agent_claude_runtime_cmd(
    output: Path = typer.Option(Path("claude_runtime.json"), help="Output runtime metadata JSON path."),
    workspace: Path = typer.Option(Path("."), help="Workspace/repo path to inspect."),
    surface: str = typer.Option("Claude Code", help="Claude Code surface."),
    session_model: str | None = typer.Option(None, help="Override active session model when known from status/model UI."),
    reasoning_effort: str | None = typer.Option(None, help="Override reasoning effort when known."),
    reasoning_summary: str | None = typer.Option(None, help="Override reasoning summary when known."),
    verbosity: str | None = typer.Option(None, help="Override verbosity when known."),
    approval_policy: str | None = typer.Option(None, help="Override permission/approval policy when known."),
    sandbox_mode: str | None = typer.Option(None, help="Override sandbox mode when known."),
    timezone: str = typer.Option("Asia/Manila", help="IANA timezone for timestamp rendering."),
) -> None:
    result = write_claude_runtime_metadata(
        output_path=output,
        workspace_path=workspace,
        surface=surface,
        session_model=session_model,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        verbosity=verbosity,
        approval_policy=approval_policy,
        sandbox_mode=sandbox_mode,
        timezone=timezone,
    )
    typer.echo(f"runtime_metadata_written={result.path}")
    typer.echo(result.metadata.get("metadata_block", ""))


@agent_app.command("copilot-runtime")
def agent_copilot_runtime_cmd(
    output: Path = typer.Option(Path("copilot_runtime.json"), help="Output runtime metadata JSON path."),
    workspace: Path = typer.Option(Path("."), help="Workspace/repo path to inspect."),
    surface: str = typer.Option("VS Code / GitHub Copilot", help="Copilot surface."),
    session_model: str | None = typer.Option(None, help="Override active Copilot chat model when known."),
    reasoning_effort: str | None = typer.Option(None, help="Override reasoning effort when known."),
    reasoning_summary: str | None = typer.Option(None, help="Override reasoning summary when known."),
    verbosity: str | None = typer.Option(None, help="Override verbosity when known."),
    approval_policy: str | None = typer.Option(None, help="Override approval policy when known."),
    sandbox_mode: str | None = typer.Option(None, help="Override sandbox mode when known."),
    timezone: str = typer.Option("Asia/Manila", help="IANA timezone for timestamp rendering."),
) -> None:
    result = write_copilot_runtime_metadata(
        output_path=output,
        workspace_path=workspace,
        surface=surface,
        session_model=session_model,
        reasoning_effort=reasoning_effort,
        reasoning_summary=reasoning_summary,
        verbosity=verbosity,
        approval_policy=approval_policy,
        sandbox_mode=sandbox_mode,
        timezone=timezone,
    )
    typer.echo(f"runtime_metadata_written={result.path}")
    typer.echo(result.metadata.get("metadata_block", ""))


@agent_app.command("doctor")
def agent_doctor_cmd(
    output_format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Report installation, PATH, and runtime readiness for research agents."""

    checks: dict[str, Any] = {
        "aesdk_version": _package_version(),
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "cwd": str(Path.cwd()),
        "aesdk_console_script": shutil.which("aesdk"),
        "python_m_aesdk": False,
        "stata_executable": _resolve_executable(os.getenv(_STATA_EXECUTABLE_ENV), _STATA_EXECUTABLE_CANDIDATES),
        "rscript_executable": _resolve_executable(os.getenv(_R_EXECUTABLE_ENV), _R_EXECUTABLE_CANDIDATES),
        "cwd_writable": False,
        "method_registry_ok": False,
        "recommendations": [],
    }
    probe = subprocess.run(
        [sys.executable, "-m", "aesdk", "methods", "list"],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
    )
    checks["python_m_aesdk"] = probe.returncode == 0
    try:
        probe_file = Path.cwd() / ".aesdk_doctor_write_test"
        probe_file.write_text("ok", encoding="utf-8")
        probe_file.unlink(missing_ok=True)
        checks["cwd_writable"] = True
    except OSError:
        checks["cwd_writable"] = False
    try:
        checks["method_registry_ok"] = bool(list_method_ids())
    except Exception:
        checks["method_registry_ok"] = False
    if checks["aesdk_console_script"] is None:
        checks["recommendations"].append("The aesdk console command is not on PATH; use python -m aesdk or reinstall with pip.")
    if not checks["python_m_aesdk"]:
        checks["recommendations"].append("python -m aesdk is not working in this environment; verify the active Python environment.")
    if checks["stata_executable"] is None:
        checks["recommendations"].append("Stata was not found on PATH; Stata .do files will be gated but cannot execute here.")
    if checks["rscript_executable"] is None:
        checks["recommendations"].append("Rscript was not found on PATH; R scripts will be gated but cannot execute here.")
    if not checks["cwd_writable"]:
        checks["recommendations"].append("The current directory is not writable; .aesdk.json cannot be saved here.")
    if output_format.lower() == "json":
        typer.echo(json.dumps(checks, indent=2))
        return
    if output_format.lower() != "text":
        raise typer.BadParameter("format must be text or json")
    for key, value in checks.items():
        if key == "recommendations":
            continue
        typer.echo(f"{key}={value}")
    if checks["recommendations"]:
        typer.echo("recommendations:")
        for item in checks["recommendations"]:
            typer.echo(f"- {item}")


@agent_app.command("run")
def agent_run_cmd(
    method: str = typer.Option(...),
    pap: Path = typer.Option(..., exists=True),
    proposal: Path = typer.Option(..., exists=True),
    code_file: Path = typer.Option(..., exists=True),
    language: str | None = typer.Option(
        None,
        "--language",
        help="Analysis code language: python|stata|r. Defaults from code-file extension.",
    ),
    blob: Path | None = typer.Option(None),
    context: str = typer.Option("production"),
    conformance: str = typer.Option("strict"),
    policy_version: str = typer.Option("1.0.0"),
    acknowledge_warnings: bool = typer.Option(
        False,
        "--acknowledge-warnings",
        help="Proceed when preflight returns warn after researcher acknowledgement.",
    ),
    timeout_seconds: int | None = typer.Option(
        None,
        "--timeout-seconds",
        help="Execution timeout for Python, Stata, or R code. Useful for longer Stata/R jobs.",
    ),
) -> None:
    result = run_analysis(
        method=method,
        pap_path=pap,
        proposal=proposal,
        code_path=code_file,
        language=normalize_language(language) if language else infer_language_from_path(code_file),
        blob_path=blob,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
        acknowledge_warnings=acknowledge_warnings,
        timeout_seconds=timeout_seconds,
    )
    typer.echo(f"status={result.status} blocked={result.blocked} blob={result.blob_path}")
    if result.preflight.blocked or result.warning_acknowledgement_required:
        typer.echo(result.preflight.explain())
        if result.warning_acknowledgement_required:
            typer.echo("warning_acknowledgement_required=True")
        raise typer.Exit(code=1)
    if result.status == "block":
        if result.sandbox is not None:
            for diagnostic in result.sandbox.diagnostics:
                typer.echo(f"- {diagnostic.code} severity={diagnostic.severity} message={diagnostic.message}")
        raise typer.Exit(code=1)


@agent_app.command("template")
def agent_template_cmd(
    target: str = typer.Option("AGENTS.md", help="Template name: AGENTS.md or CLAUDE.md"),
) -> None:
    template = files("aesdk.agent.templates").joinpath(target)
    if not template.is_file():
        raise typer.BadParameter("target must be AGENTS.md or CLAUDE.md")
    typer.echo(template.read_text(encoding="utf-8"))


@methods_app.command("list")
def methods_list_cmd() -> None:
    for method_id in list_method_ids():
        typer.echo(method_id)


@methods_app.command("show")
def methods_show_cmd(
    method_id: str = typer.Argument(..., help="Method protocol id, for example did or iv_2sls."),
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    protocol = get_method_protocol(method_id)
    if output_format.lower() == "yaml":
        import yaml

        typer.echo(yaml.safe_dump(protocol, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(protocol, indent=2))


@methods_app.command("sources")
def methods_sources_cmd(
    method_id: str = typer.Argument(..., help="Method protocol id, for example did or iv_2sls."),
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    locators = get_method_source_map(method_id)
    if output_format.lower() == "yaml":
        import yaml

        typer.echo(yaml.safe_dump(locators, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(locators, indent=2))


@methods_app.command("packs")
def methods_packs_cmd() -> None:
    for method_id in list_knowledge_pack_ids():
        typer.echo(method_id)


@methods_app.command("curriculum")
def methods_curriculum_cmd(
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    curriculum = load_curriculum()
    if output_format.lower() == "yaml":
        typer.echo(yaml.safe_dump(curriculum, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(curriculum, indent=2))


@methods_app.command("pack")
def methods_pack_cmd(
    method_id: str = typer.Argument(..., help="Knowledge pack id, for example did or iv_2sls."),
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    pack = get_knowledge_pack(method_id)
    if output_format.lower() == "yaml":
        typer.echo(yaml.safe_dump(pack, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(pack, indent=2))


@methods_app.command("validate")
def methods_validate_cmd() -> None:
    errors = validate_knowledge_base()
    if not errors:
        typer.echo("knowledge_base=ok")
        return
    typer.echo("knowledge_base=failed")
    for error in errors:
        typer.echo(f"- {error}")
    raise typer.Exit(code=1)


@sources_app.command("list")
def sources_list_cmd() -> None:
    for source_id in list_source_ids():
        typer.echo(source_id)


@sources_app.command("show")
def sources_show_cmd(
    source_id: str = typer.Argument(..., help="Registered source id."),
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    source = get_source(source_id)
    if output_format.lower() == "yaml":
        import yaml

        typer.echo(yaml.safe_dump(source, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(source, indent=2))


@sources_app.command("inventory")
def sources_inventory_cmd(
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    inventory = load_source_inventory()
    if output_format.lower() == "yaml":
        typer.echo(yaml.safe_dump(inventory, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(inventory, indent=2))


@sources_app.command("software")
def sources_software_cmd(
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml"),
) -> None:
    sources = load_official_software_sources()
    if output_format.lower() == "yaml":
        typer.echo(yaml.safe_dump(sources, sort_keys=False))
        return
    if output_format.lower() != "json":
        raise typer.BadParameter("format must be json or yaml")
    typer.echo(json.dumps(sources, indent=2))


@rules_app.command("list")
def rules_list_cmd(
    output_format: str = typer.Option("json", "--format", help="Output format: json|yaml|text"),
) -> None:
    rules = RuleRegistry().all_rules
    if output_format.lower() == "yaml":
        typer.echo(yaml.safe_dump({"rules": rules}, sort_keys=False))
        return
    if output_format.lower() == "json":
        typer.echo(json.dumps({"rules": rules}, indent=2))
        return
    if output_format.lower() != "text":
        raise typer.BadParameter("format must be json, yaml, or text")
    for rule in rules:
        typer.echo(
            f"{rule.get('id')} | {rule.get('severity')} | "
            f"{rule.get('name')} | {rule.get('_source_file')}"
        )


@app.command("setup")
def setup_cmd(
    output_dir: Path = typer.Option(Path("."), "--output-dir", help="Project folder to set up."),
    template: str = typer.Option(
        "both",
        "--template",
        help="Which assistant instructions to save: both|AGENTS.md|CLAUDE.md|none.",
    ),
    force: bool = typer.Option(
        False, "--force", help="Overwrite existing AGENTS.md/CLAUDE.md instead of keeping them."
    ),
    output_format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Get AESDK ready in one step and print a plain-language summary.

    Verifies the install, saves the ready-made assistant instructions into the
    project, and explains what to do next. It never installs packages or changes
    system settings on its own.
    """

    result = run_setup(output_dir=output_dir, write_templates=template, force=force)
    if output_format.lower() == "json":
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format.lower() == "text":
        typer.echo(result.friendly_report())
    else:
        raise typer.BadParameter("format must be text or json")
    if not result.ready:
        raise typer.Exit(code=1)


@app.command("chat-guide")
def chat_guide_cmd(
    target: str = typer.Option(
        "claude", "--target", help="Which chat preset to print: chatgpt|claude|mcp."
    ),
) -> None:
    """Print a ready-to-paste preset for using AESDK inside ChatGPT or Claude chat."""

    from aesdk.chat import available_targets, chat_guide

    try:
        typer.echo(chat_guide(target))
    except ValueError:
        raise typer.BadParameter(f"target must be one of: {', '.join(available_targets())}")


@app.command("connect-claude")
def connect_claude_cmd(
    config_path: Path | None = typer.Option(
        None, "--config-path", help="Path to claude_desktop_config.json (auto-detected by default)."
    ),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would change without writing."),
    force: bool = typer.Option(
        False, "--force", help="Replace an unreadable/invalid existing config."
    ),
    output_format: str = typer.Option("text", "--format", help="Output format: text|json"),
) -> None:
    """Connect AESDK to Claude Desktop in one step (edits the config for you).

    Finds claude_desktop_config.json, adds the AESDK MCP server without disturbing
    other connectors, and backs up the previous file. Then restart Claude Desktop.
    """

    from aesdk.chat import connect_claude_desktop

    result = connect_claude_desktop(config_path=config_path, dry_run=dry_run, force=force)
    if output_format.lower() == "json":
        typer.echo(json.dumps(result.to_dict(), indent=2))
    elif output_format.lower() == "text":
        typer.echo(result.friendly_report())
    else:
        raise typer.BadParameter("format must be text or json")
    if not result.ok:
        raise typer.Exit(code=1)


@app.command("mcp")
def mcp_cmd(
    transport: str = typer.Option("stdio", "--transport", help="MCP transport (stdio)."),
) -> None:
    """Run the AESDK MCP server so chat clients (e.g. Claude) can call the checks.

    Requires the optional 'mcp' extra: pip install aesdk[mcp].
    """

    from aesdk.chat.server import run as run_server

    try:
        run_server(transport=transport)
    except RuntimeError as exc:
        typer.echo(str(exc))
        raise typer.Exit(code=1)


@app.command("init")
def init_cmd(
    pap: Path = typer.Option(..., exists=True),
    proposal: Path | None = typer.Option(None, exists=True, help="Optional proposal JSON path for artifact resolution."),
    blob: Path | None = typer.Option(None),
    context: str = typer.Option("research", help="Execution context: research|production|regulated"),
    conformance: str | None = typer.Option(None, help="Conformance level override: basic|strict|regulated"),
    policy_version: str = typer.Option("1.0.0", help="Policy version tag for governance passport."),
    attestation_endpoint: str | None = typer.Option(None, help="Optional remote attestation endpoint."),
    attestation_token: str | None = typer.Option(None, help="Optional bearer token for attestation endpoint."),
) -> None:
    project = Project.create(
        pap_path=pap,
        proposal_path=proposal,
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
    result = Validator(
        registry=registry,
        artifact_base_dirs=[Path.cwd(), pap.resolve().parent, proposal.resolve().parent],
        artifact_base_dirs_by_source={"pap": pap.resolve().parent, "proposal": proposal.resolve().parent},
    ).validate(
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
    if result.blocked:
        raise typer.Exit(code=1)


@app.command("execute")
def execute_cmd(
    pap: Path = typer.Option(..., exists=True),
    proposal: Path = typer.Option(..., exists=True),
    code_file: Path = typer.Option(..., exists=True),
    language: str | None = typer.Option(
        None,
        "--language",
        help="Analysis code language: python|stata|r. Defaults from code-file extension.",
    ),
    blob: Path | None = typer.Option(None),
    context: str = typer.Option("research"),
    conformance: str | None = typer.Option(None),
    policy_version: str = typer.Option("1.0.0"),
    timeout_seconds: int | None = typer.Option(
        None,
        "--timeout-seconds",
        help="Execution timeout for Python, Stata, or R code.",
    ),
) -> None:
    project = Project.create(
        pap_path=pap,
        blob_path=blob,
        context=context,
        conformance=conformance,
        policy_version=policy_version,
        sandbox_runner=SandboxRunner(
            mem_limit_mb=config.sandbox_mem_limit_mb,
            cpu_limit_sec=timeout_seconds or config.sandbox_cpu_limit_sec,
            artifact_dir=(blob.parent if blob else pap.parent),
        ),
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
    active_language = normalize_language(language) if language else infer_language_from_path(code_file)
    run_result = project.execute(code, language=active_language, timeout_seconds=timeout_seconds)
    typer.echo(f"execution_status={run_result.status}")
    if run_result.status == "block":
        for diagnostic in run_result.diagnostics:
            typer.echo(f"- {diagnostic.code} severity={diagnostic.severity} message={diagnostic.message}")
        raise typer.Exit(code=1)


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
    mode: str = typer.Option("hmac", help="Signing mode: hmac|kms-http|aws-kms|gcp-kms|azure-keyvault"),
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
) -> None:
    if text == "-":
        content = sys.stdin.read()
    else:
        content = Path(text).read_text(encoding="utf-8-sig")
    report = verify_text(content)
    typer.echo(
        f"dois_found={len(report.dois)} "
        f"invalid_format={report.invalid_format_count} "
        f"unreachable={report.unreachable_count}"
    )
    for item in report.dois:
        typer.echo(f"- doi={item.doi} format={item.valid_format} reachable={item.reachable}")
    if report.invalid_format_count or report.unreachable_count:
        raise typer.Exit(code=1)


if __name__ == "__main__":  # pragma: no cover
    app()
