"""CSV exporter for replication blobs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from aesdk.trace.blob import ReplicationBlob


class CSVExporter:
    """Write replication blob events as a flat CSV report."""

    def export(self, blob: ReplicationBlob, output_path: str | Path) -> Path:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=[
                    "project_id",
                    "event_id",
                    "event_type",
                    "timestamp",
                    "previous_hash",
                    "hash",
                    "payload",
                ],
            )
            writer.writeheader()
            for event in blob.events:
                writer.writerow(
                    {
                        "project_id": blob.project_id,
                        "event_id": event.event_id,
                        "event_type": event.event_type,
                        "timestamp": event.timestamp,
                        "previous_hash": event.previous_hash,
                        "hash": event.hash,
                        "payload": json.dumps(event.payload, sort_keys=True),
                    }
                )
        return target
