"""Agent workflow report generation."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import yaml


def write_workflow_report(
    *,
    blob_path: str | Path,
    output_path: str | Path | None = None,
    title: str = "AESDK Workflow Report",
) -> Path:
    """Write a human-readable HTML report from an AESDK replication blob."""

    blob_target = Path(blob_path)
    data = json.loads(blob_target.read_text(encoding="utf-8"))
    output = Path(output_path) if output_path else blob_target.with_suffix(".workflow.html")
    output.parent.mkdir(parents=True, exist_ok=True)
    root = output.parent

    events = data.get("events", [])
    validate_event = _last_event(events, "validate")
    execute_event = _last_event(events, "execute")
    validation_status = (validate_event or {}).get("payload", {}).get("status", "not recorded")
    execution_payload = (execute_event or {}).get("payload", {})
    execution_status = execution_payload.get("status", "not recorded")
    language = execution_payload.get("language", "")
    diagnostics = execution_payload.get("diagnostics", [])
    artifacts = execution_payload.get("artifacts", {})
    ai_use = _ai_use_from_events(events)
    passport = _load_ai_passport(blob_target.parent, ai_use)
    passport_status = passport.get("status", "not recorded") if passport else "not recorded"
    review_message = _review_message(validation_status, execution_status, passport_status)

    rows = "\n".join(_event_row(index, event) for index, event in enumerate(events, start=1))
    validation_rows = _validation_rows(validate_event)
    diagnostics_rows = "\n".join(
        f"<tr><td>{_esc(item.get('code', ''))}</td><td>{_esc(item.get('severity', ''))}</td>"
        f"<td>{_esc(item.get('message', ''))}</td></tr>"
        for item in diagnostics
    ) or "<tr><td colspan=\"3\">No diagnostics recorded.</td></tr>"
    artifact_rows = "\n".join(_artifact_row(root, key, value) for key, value in artifacts.items())
    if not artifact_rows:
        artifact_rows = "<tr><td colspan=\"2\">No execution artifacts recorded.</td></tr>"

    ai_rows = _ai_use_rows(root, ai_use, passport)
    evidence_rows = _ai_evidence_rows(root, passport)
    sibling_links = _sibling_artifacts(blob_target.parent, output)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <style>
    :root {{
      --ink: #1f2933;
      --muted: #5f6b7a;
      --line: #d8dee7;
      --soft: #f5f7fa;
      --paper: #ffffff;
      --blue: #1f5f99;
      --green-bg: #eaf6ef;
      --green: #166534;
      --amber-bg: #fff5d6;
      --amber: #7c4a03;
      --red-bg: #fdeeee;
      --red: #9f1d1d;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: var(--paper); color: var(--ink); line-height: 1.45; }}
    header {{ border-bottom: 1px solid var(--line); background: #f8fafc; }}
    main, .header-inner {{ max-width: 1180px; margin: 0 auto; padding: 0 24px; }}
    .header-inner {{ padding-top: 28px; padding-bottom: 22px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; line-height: 1.15; }}
    h2 {{ margin: 0 0 10px; font-size: 19px; line-height: 1.25; }}
    h3 {{ margin: 0 0 8px; font-size: 15px; }}
    p {{ margin: 0 0 10px; }}
    a {{ color: var(--blue); text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    code {{ word-break: break-all; font-family: Consolas, Menlo, monospace; font-size: .94em; }}
    .muted {{ color: var(--muted); }}
    .summary {{ display: grid; grid-template-columns: minmax(0, 1.5fr) repeat(4, minmax(130px, 1fr)); gap: 12px; margin: 22px 0 26px; }}
    .summary-note, .metric-card, .file-card {{ border: 1px solid var(--line); border-radius: 8px; background: #fff; padding: 14px; }}
    .summary-note {{ background: #fbfcfe; }}
    .metric-value {{ margin-top: 8px; font-size: 18px; font-weight: 700; }}
    .label {{ color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    section {{ padding: 24px 0; border-top: 1px solid var(--line); }}
    .section-head {{ display: flex; align-items: baseline; justify-content: space-between; gap: 16px; margin-bottom: 12px; }}
    .section-note {{ color: var(--muted); font-size: 14px; max-width: 720px; }}
    .pass {{ color: var(--green); background: var(--green-bg); border: 1px solid #b8dec4; }}
    .warn {{ color: var(--amber); background: var(--amber-bg); border: 1px solid #edd38a; }}
    .block {{ color: var(--red); background: var(--red-bg); border: 1px solid #efb8b8; }}
    .recorded {{ color: #334155; background: #eef2f7; border: 1px solid #cbd5e1; }}
    .pill {{ display: inline-flex; align-items: center; min-height: 24px; padding: 4px 9px; border-radius: 999px; font-size: 12px; font-weight: 700; text-transform: uppercase; }}
    .table-wrap {{ overflow-x: auto; border: 1px solid var(--line); border-radius: 8px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; background: #fff; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 11px; text-align: left; vertical-align: top; }}
    tr:last-child td {{ border-bottom: 0; }}
    th {{ color: var(--muted); background: var(--soft); font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    td:first-child {{ font-weight: 600; }}
    .evidence-grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .file-card h3 {{ overflow-wrap: anywhere; }}
    .hash {{ color: var(--muted); font-size: 12px; }}
    @media (max-width: 960px) {{ .summary {{ grid-template-columns: 1fr 1fr; }} .summary-note {{ grid-column: 1 / -1; }} .evidence-grid {{ grid-template-columns: 1fr 1fr; }} }}
    @media (max-width: 640px) {{ main, .header-inner {{ padding-left: 16px; padding-right: 16px; }} .summary, .evidence-grid {{ grid-template-columns: 1fr; }} .section-head {{ display: block; }} }}
  </style>
</head>
<body>
<header>
  <div class="header-inner">
    <h1>{_esc(title)}</h1>
    <p class="muted">Project <strong>{_esc(data.get("project_id", ""))}</strong> generated from <code>{_esc(str(blob_target))}</code>.</p>
  </div>
</header>
<main>
  <div class="summary" aria-label="Review Summary">
    <div class="summary-note">
      <div class="label">Review Summary</div>
      <p>{_esc(review_message)}</p>
      <p class="muted">This report is intended for research review: it records what AESDK checked, what ran, and which files support replication.</p>
    </div>
    <div class="metric-card"><div class="label">Validation</div><div class="metric-value">{_status_pill(validation_status)}</div></div>
    <div class="metric-card"><div class="label">Execution</div><div class="metric-value">{_status_pill(execution_status)}</div></div>
    <div class="metric-card"><div class="label">AI Passport</div><div class="metric-value">{_status_pill(passport_status)}</div></div>
    <div class="metric-card"><div class="label">Language</div><div class="metric-value">{_esc(language or "n/a")}</div></div>
  </div>

  <section>
    <div class="section-head">
      <h2>Econometric Gatekeeping</h2>
      <p class="section-note">Rules that blocked or warned before analysis code ran.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Rule</th><th>Severity</th><th>Message</th><th>Guidance</th></tr></thead>
        <tbody>{validation_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>AI Use And Human Review</h2>
      <p class="section-note">Model, agent, human-in-loop, intervention, and review evidence recorded for this workflow.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Field</th><th>Value</th></tr></thead>
        <tbody>{ai_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>AI Evidence Archive</h2>
      <p class="section-note">Files hashed by the AI passport, including prompts, outputs, code, transcripts, patches, review notes, and runtime metadata.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Evidence Type</th><th>File</th><th>Status</th><th>Hash</th></tr></thead>
        <tbody>{evidence_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>Execution Diagnostics</h2>
      <p class="section-note">Runtime issues from Python, Stata, or R execution.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Code</th><th>Severity</th><th>Message</th></tr></thead>
        <tbody>{diagnostics_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>Recorded Execution Artifacts</h2>
      <p class="section-note">Files created or captured during governed execution.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>Artifact</th><th>Path</th></tr></thead>
        <tbody>{artifact_rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <div class="section-head">
      <h2>Workflow Timeline</h2>
      <p class="section-note">Audit events recorded in the AESDK replication blob.</p>
    </div>
    <div class="table-wrap">
      <table>
        <thead><tr><th>#</th><th>Event</th><th>Status</th><th>Timestamp</th><th>Hash</th></tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>
  </section>

  <section>
    <h2>Nearby Files</h2>
    <div class="evidence-grid">{sibling_links}</div>
  </section>
</main>
</body>
</html>
"""
    output.write_text(document, encoding="utf-8")
    return output


def _last_event(events: list[dict[str, Any]], event_type: str) -> dict[str, Any] | None:
    for event in reversed(events):
        if event.get("event_type") == event_type:
            return event
    return None


def _ai_use_from_events(events: list[dict[str, Any]]) -> dict[str, Any]:
    ai_use: dict[str, Any] = {}
    init_event = _last_event(events, "init")
    pap_path = (init_event or {}).get("payload", {}).get("pap_path")
    if pap_path:
        pap = _load_structured(Path(str(pap_path)))
        if isinstance(pap.get("ai_use"), dict):
            ai_use.update(pap["ai_use"])
    proposal_event = _last_event(events, "propose_model")
    proposal = (proposal_event or {}).get("payload", {}).get("proposal", {})
    if isinstance(proposal, dict) and isinstance(proposal.get("ai_use"), dict):
        ai_use.update({key: value for key, value in proposal["ai_use"].items() if value is not None})
    return ai_use


def _load_structured(path: Path) -> dict[str, Any]:
    if not path.exists() or not path.is_file():
        return {}
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() == ".json":
        loaded = json.loads(text)
    else:
        loaded = yaml.safe_load(text) or {}
    return loaded if isinstance(loaded, dict) else {}


def _load_ai_passport(folder: Path, ai_use: dict[str, Any]) -> dict[str, Any]:
    candidates = []
    if ai_use.get("ai_passport_path"):
        candidates.append(Path(str(ai_use["ai_passport_path"])))
    candidates.append(folder / "ai.lock.json")
    for candidate in candidates:
        path = candidate if candidate.is_absolute() else folder / candidate
        if path.exists() and path.is_file():
            try:
                return json.loads(path.read_text(encoding="utf-8-sig"))
            except json.JSONDecodeError:
                return {}
    return {}


def _event_row(index: int, event: dict[str, Any]) -> str:
    payload = event.get("payload", {})
    status = payload.get("status") or "recorded"
    status_class = _status_class(status)
    return (
        f"<tr><td>{index}</td><td>{_esc(event.get('event_type', ''))}</td>"
        f"<td><span class=\"pill {status_class}\">{_esc(status)}</span></td>"
        f"<td>{_esc(event.get('timestamp', ''))}</td><td><code>{_esc(event.get('hash', ''))}</code></td></tr>"
    )


def _validation_rows(validate_event: dict[str, Any] | None) -> str:
    violations = (validate_event or {}).get("payload", {}).get("violations", [])
    if not violations:
        return "<tr><td colspan=\"4\">No rule violations recorded.</td></tr>"
    rows = []
    for item in violations:
        rows.append(
            "<tr>"
            f"<td>{_esc(item.get('rule_id', ''))}</td>"
            f"<td>{_status_pill(item.get('severity', 'recorded'))}</td>"
            f"<td>{_esc(item.get('message', ''))}</td>"
            f"<td>{_esc(item.get('guidance', ''))}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _artifact_row(root: Path, key: str, value: Any) -> str:
    return f"<tr><td>{_esc(_field_label(key))}</td><td>{_artifact_link(root, value)}</td></tr>"


def _ai_use_rows(root: Path, ai_use: dict[str, Any], passport: dict[str, Any]) -> str:
    if not ai_use:
        return "<tr><td colspan=\"2\">No AI use metadata recorded in the proposal.</td></tr>"
    fields = [
        ("used", ai_use.get("used")),
        ("role", ai_use.get("role")),
        ("languages", ai_use.get("languages")),
        ("provider", ai_use.get("provider")),
        ("model", ai_use.get("model")),
        ("agent_tool", ai_use.get("agent_tool")),
        ("model_metadata_source", ai_use.get("model_metadata_source")),
        ("model_metadata_unavailable_reason", ai_use.get("model_metadata_unavailable_reason")),
        ("prompts_archived", ai_use.get("prompts_archived")),
        ("raw_outputs_archived", ai_use.get("raw_outputs_archived")),
        ("human_in_loop", ai_use.get("human_in_loop")),
        ("human_interaction_files", ai_use.get("human_interaction_files")),
        ("human_modified_code", ai_use.get("human_modified_code")),
        ("ai_code_draft_files", ai_use.get("ai_code_draft_files")),
        ("human_intervention_files", ai_use.get("human_intervention_files")),
        ("human_reviewed", ai_use.get("human_reviewed")),
        ("review_status", ai_use.get("review_status")),
        ("reviewer_role", ai_use.get("reviewer_role")),
        ("review_files", ai_use.get("review_files")),
        ("runtime_metadata_files", ai_use.get("runtime_metadata_files")),
        ("reproducible_without_ai", ai_use.get("reproducible_without_ai")),
        ("live_model_required", ai_use.get("live_model_required")),
        ("ai_output_used_as_data", ai_use.get("ai_output_used_as_data")),
        ("ai_derived_variables", ai_use.get("ai_derived_variables")),
        ("code_files", ai_use.get("code_files")),
        ("qa_sample_plan", ai_use.get("qa_sample_plan")),
        ("sensitivity_plan", ai_use.get("sensitivity_plan")),
        ("ai_passport_path", ai_use.get("ai_passport_path")),
    ]
    rows = []
    for key, value in fields:
        if value is None:
            continue
        rows.append(f"<tr><td>{_esc(_field_label(key))}</td><td>{_format_ai_value(root, key, value)}</td></tr>")
    if passport:
        rows.append(f"<tr><td>passport_status</td><td>{_status_pill(passport.get('status', 'unknown'))}</td></tr>")
        rows.append(f"<tr><td>Replication statement</td><td>{_esc(passport.get('replication_statement', ''))}</td></tr>")
    return "\n".join(rows) or "<tr><td colspan=\"2\">AI use metadata is empty.</td></tr>"


def _ai_evidence_rows(root: Path, passport: dict[str, Any]) -> str:
    artifact_hashes = passport.get("artifact_hashes") if isinstance(passport, dict) else None
    if not isinstance(artifact_hashes, dict):
        return "<tr><td colspan=\"4\">No AI evidence passport was found.</td></tr>"
    rows = []
    for group, records in artifact_hashes.items():
        if not isinstance(records, list):
            continue
        for record in records:
            exists = bool(record.get("exists"))
            status = "recorded" if exists else "block"
            sha = record.get("sha256")
            rows.append(
                "<tr>"
                f"<td>{_esc(_field_label(group))}</td>"
                f"<td>{_artifact_record_link(root, record)}</td>"
                f"<td>{_status_pill(status, 'found' if exists else 'missing')}</td>"
                f"<td><span class=\"hash\">sha256={_esc(sha or 'missing')}</span></td>"
                "</tr>"
            )
    return "\n".join(rows) or "<tr><td colspan=\"4\">No AI evidence files were listed.</td></tr>"


def _format_ai_value(root: Path, key: str, value: Any) -> str:
    if key == "ai_passport_path":
        return _artifact_row(root, key, value).split("<td>", 2)[-1].removesuffix("</td></tr>")
    if isinstance(value, (list, tuple)):
        if key.endswith("_files") or key in {"code_files"}:
            return ", ".join(_artifact_link(root, item) for item in value)
        return _esc(", ".join(str(item) for item in value))
    return _esc(value)


def _artifact_record_link(root: Path, record: dict[str, Any]) -> str:
    path_text = str(record.get("resolved_path") or record.get("original_path") or "")
    label = str(record.get("original_path") or path_text)
    return _artifact_link(root, path_text, label=label)


def _artifact_link(root: Path, value: Any, *, label: str | None = None) -> str:
    text = str(value)
    path = Path(text)
    resolved = path if path.is_absolute() else root / path
    if resolved.exists():
        try:
            href = resolved.relative_to(root).as_posix()
        except ValueError:
            href = resolved.as_posix()
        return f"<a href=\"{_esc(href)}\">{_esc(label or text)}</a>"
    return _esc(label or text)


def _sibling_artifacts(folder: Path, output: Path) -> str:
    interesting = []
    for path in sorted(folder.iterdir()):
        if path == output or path.name.startswith("."):
            continue
        if path.is_file() and path.suffix.lower() in {
            ".pdf",
            ".html",
            ".json",
            ".yaml",
            ".yml",
            ".do",
            ".r",
            ".py",
            ".csv",
            ".log",
            ".md",
            ".patch",
            ".diff",
        }:
            interesting.append(path)
        if path.is_dir() and path.name.lower() == "results":
            interesting.append(path)
    if not interesting:
        return "<p class=\"muted\">No nearby artifacts found.</p>"
    items = []
    for path in interesting:
        label = path.name + ("/" if path.is_dir() else "")
        items.append(
            "<div class=\"artifact\">"
            f"<h3>{_esc(label)}</h3>"
            f"<a href=\"{_esc(path.relative_to(folder).as_posix())}\">{_esc(path.relative_to(folder).as_posix())}</a>"
            "</div>"
        )
    return "\n".join(items)


def _esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _field_label(value: Any) -> str:
    text = str(value).strip().replace("_", " ")
    acronyms = {"ai": "AI", "qa": "QA", "id": "ID"}
    return " ".join(acronyms.get(part, part.capitalize()) for part in text.split())


def _review_message(validation_status: Any, execution_status: Any, passport_status: Any) -> str:
    statuses = {str(validation_status).lower(), str(execution_status).lower(), str(passport_status).lower()}
    if "block" in statuses:
        return "This workflow has a blocked item. Resolve the listed issue before treating the analysis as replication-ready."
    if "warn" in statuses:
        return "This workflow passed with warnings. A researcher should review the warning before relying on the results."
    if "pass" in statuses:
        return "AESDK did not record blocking issues for the analysis run and archived evidence shown below."
    return "This report records the available workflow evidence; some statuses were not recorded."


def _status_pill(status: Any, label: str | None = None) -> str:
    status_class = _status_class(status)
    return f"<span class=\"pill {status_class}\">{_esc(label or status)}</span>"


def _status_class(status: Any) -> str:
    normalized = str(status).strip().lower()
    if normalized in {"pass", "warn", "block"}:
        return normalized
    return "recorded"
