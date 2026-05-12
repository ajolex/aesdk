"""HTML exporter for replication blobs."""

from __future__ import annotations

import html
import json
from pathlib import Path

from aesdk.trace.blob import ReplicationBlob


class HTMLExporter:
    """Write a compact HTML replication report."""

    def export(self, blob: ReplicationBlob, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        rows = []
        for event in blob.events:
            payload = html.escape(json.dumps(event.payload, indent=2, sort_keys=True))
            reasoning = ""
            if event.reasoning_log:
                reasoning = html.escape(json.dumps(event.reasoning_log.to_dict(), indent=2, sort_keys=True))
            rows.append(
                "<tr>"
                f"<td>{html.escape(event.timestamp)}</td>"
                f"<td><span class=\"event-type\">{html.escape(event.event_type)}</span></td>"
                f"<td><code>{html.escape(event.hash)}</code></td>"
                f"<td><pre>{payload}</pre></td>"
                f"<td><pre>{reasoning}</pre></td>"
                "</tr>"
            )
        body = "\n".join(rows)
        metadata = html.escape(json.dumps(blob.metadata, indent=2, sort_keys=True))
        document = f"""<html>
<head>
  <meta charset="utf-8">
  <title>Replication Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; color: #1f2933; }}
    h1 {{ margin-bottom: 0.25rem; }}
    .meta {{ background: #f6f8fa; border: 1px solid #d8dee4; padding: 1rem; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
    th, td {{ border: 1px solid #d8dee4; padding: 0.5rem; vertical-align: top; }}
    th {{ background: #eef2f6; text-align: left; }}
    pre {{ white-space: pre-wrap; margin: 0; }}
    code {{ word-break: break-all; }}
    .event-type {{ font-weight: 700; }}
  </style>
</head>
<body>
  <h1>Replication Report</h1>
  <p>Project: {html.escape(blob.project_id)}</p>
  <h2>Metadata</h2>
  <pre class="meta">{metadata}</pre>
  <table>
    <thead>
      <tr><th>Timestamp</th><th>Event</th><th>Hash</th><th>Payload</th><th>Reasoning Log</th></tr>
    </thead>
    <tbody>
      {body}
    </tbody>
  </table>
</body>
</html>
"""
        target.write_text(document, encoding="utf-8")
        return target
