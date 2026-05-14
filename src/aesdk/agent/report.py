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

    rows = "\n".join(_event_row(index, event) for index, event in enumerate(events, start=1))
    diagnostics_rows = "\n".join(
        f"<tr><td>{_esc(item.get('code', ''))}</td><td>{_esc(item.get('severity', ''))}</td>"
        f"<td>{_esc(item.get('message', ''))}</td></tr>"
        for item in diagnostics
    ) or "<tr><td colspan=\"3\">No diagnostics recorded.</td></tr>"
    artifact_rows = "\n".join(_artifact_row(root, key, value) for key, value in artifacts.items())
    if not artifact_rows:
        artifact_rows = "<tr><td colspan=\"2\">No execution artifacts recorded.</td></tr>"

    ai_rows = _ai_use_rows(root, ai_use, passport)
    sibling_links = _sibling_artifacts(blob_target.parent, output)
    document = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{_esc(title)}</title>
  <style>
    body {{ margin: 0; font-family: Arial, Helvetica, sans-serif; background: #f6f7f9; color: #20242a; }}
    main {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 56px; }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    h2 {{ margin: 0 0 14px; font-size: 20px; }}
    h3 {{ margin: 0 0 8px; font-size: 16px; }}
    p {{ margin: 0 0 10px; }}
    a {{ color: #1d4ed8; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .muted {{ color: #647184; }}
    .grid {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 12px; margin: 20px 0; }}
    .card, section {{ background: #fff; border: 1px solid #d8dee7; border-radius: 8px; box-shadow: 0 1px 2px rgba(15,23,42,.06), 0 8px 24px rgba(15,23,42,.06); }}
    .card {{ padding: 16px; }}
    section {{ padding: 20px; margin-top: 18px; }}
    .metric {{ font-size: 24px; font-weight: 800; }}
    .label {{ color: #647184; font-size: 13px; }}
    .pass {{ color: #166534; background: #e9f7ee; border: 1px solid #b7dfc2; }}
    .warn {{ color: #854d0e; background: #fff7df; border: 1px solid #f1d48a; }}
    .block {{ color: #991b1b; background: #feecec; border: 1px solid #f4b4b4; }}
    .recorded {{ color: #334155; background: #eef2f7; border: 1px solid #cbd5e1; }}
    .pill {{ display: inline-flex; padding: 5px 10px; border-radius: 999px; font-size: 12px; font-weight: 800; text-transform: uppercase; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid #d8dee7; padding: 9px 8px; text-align: left; vertical-align: top; }}
    th {{ color: #647184; background: #f9fafc; font-size: 12px; text-transform: uppercase; letter-spacing: .04em; }}
    code {{ word-break: break-all; }}
    .artifacts {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 10px; }}
    .artifact {{ padding: 12px; border: 1px solid #d8dee7; border-radius: 8px; background: #fbfcfe; }}
    @media (max-width: 850px) {{ .grid, .artifacts {{ grid-template-columns: 1fr 1fr; }} }}
    @media (max-width: 560px) {{ .grid, .artifacts {{ grid-template-columns: 1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>{_esc(title)}</h1>
  <p class="muted">Project <strong>{_esc(data.get("project_id", ""))}</strong>, generated from <code>{_esc(str(blob_target))}</code>.</p>
  <div class="grid">
    <div class="card"><div class="metric">{_esc(validation_status)}</div><div class="label">Validation status</div></div>
    <div class="card"><div class="metric">{_esc(execution_status)}</div><div class="label">Execution status</div></div>
    <div class="card"><div class="metric">{_esc(language or "n/a")}</div><div class="label">Execution language</div></div>
    <div class="card"><div class="metric">{len(events)}</div><div class="label">Audit events</div></div>
  </div>

  <section>
    <h2>Workflow Events</h2>
    <table>
      <thead><tr><th>#</th><th>Event</th><th>Status</th><th>Timestamp</th><th>Hash</th></tr></thead>
      <tbody>{rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Execution Diagnostics</h2>
    <table>
      <thead><tr><th>Code</th><th>Severity</th><th>Message</th></tr></thead>
      <tbody>{diagnostics_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>AI Use</h2>
    <table>
      <thead><tr><th>Field</th><th>Value</th></tr></thead>
      <tbody>{ai_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Recorded Execution Artifacts</h2>
    <table>
      <thead><tr><th>Artifact</th><th>Path</th></tr></thead>
      <tbody>{artifact_rows}</tbody>
    </table>
  </section>

  <section>
    <h2>Nearby Files</h2>
    <div class="artifacts">{sibling_links}</div>
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
        path = candidate if candidate.is_absolute() or candidate.exists() else folder / candidate
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


def _artifact_row(root: Path, key: str, value: Any) -> str:
    text = str(value)
    path = Path(text)
    if path.exists():
        try:
            href = path.relative_to(root).as_posix()
        except ValueError:
            href = path.as_posix()
        rendered = f"<a href=\"{_esc(href)}\">{_esc(text)}</a>"
    else:
        rendered = _esc(text)
    return f"<tr><td>{_esc(key)}</td><td>{rendered}</td></tr>"


def _ai_use_rows(root: Path, ai_use: dict[str, Any], passport: dict[str, Any]) -> str:
    if not ai_use:
        return "<tr><td colspan=\"2\">No AI use metadata recorded in the proposal.</td></tr>"
    fields = [
        ("used", ai_use.get("used")),
        ("role", ai_use.get("role")),
        ("provider", ai_use.get("provider")),
        ("model", ai_use.get("model")),
        ("prompts_archived", ai_use.get("prompts_archived")),
        ("raw_outputs_archived", ai_use.get("raw_outputs_archived")),
        ("human_reviewed", ai_use.get("human_reviewed")),
        ("reproducible_without_ai", ai_use.get("reproducible_without_ai")),
        ("live_model_required", ai_use.get("live_model_required")),
        ("ai_output_used_as_data", ai_use.get("ai_output_used_as_data")),
        ("ai_derived_variables", ai_use.get("ai_derived_variables")),
        ("qa_sample_plan", ai_use.get("qa_sample_plan")),
        ("sensitivity_plan", ai_use.get("sensitivity_plan")),
        ("ai_passport_path", ai_use.get("ai_passport_path")),
    ]
    rows = []
    for key, value in fields:
        if value is None:
            continue
        rows.append(f"<tr><td>{_esc(key)}</td><td>{_format_ai_value(root, key, value)}</td></tr>")
    if passport:
        rows.append(f"<tr><td>passport_status</td><td>{_esc(passport.get('status', 'unknown'))}</td></tr>")
        rows.append(f"<tr><td>replication_statement</td><td>{_esc(passport.get('replication_statement', ''))}</td></tr>")
        for group, records in (passport.get("artifact_hashes") or {}).items():
            if isinstance(records, list):
                for record in records:
                    rows.append(
                        "<tr>"
                        f"<td>{_esc(group)}</td>"
                        f"<td>{_esc(record.get('original_path'))}: exists={_esc(record.get('exists'))}, "
                        f"sha256={_esc(record.get('sha256', 'missing'))}</td>"
                        "</tr>"
                    )
    return "\n".join(rows) or "<tr><td colspan=\"2\">AI use metadata is empty.</td></tr>"


def _format_ai_value(root: Path, key: str, value: Any) -> str:
    if key == "ai_passport_path":
        return _artifact_row(root, key, value).split("<td>", 2)[-1].removesuffix("</td></tr>")
    if isinstance(value, (list, tuple)):
        return _esc(", ".join(str(item) for item in value))
    return _esc(value)


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


def _status_class(status: Any) -> str:
    normalized = str(status).strip().lower()
    if normalized in {"pass", "warn", "block"}:
        return normalized
    return "recorded"
