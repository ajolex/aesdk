"""Tests for Trace Exporters."""
from __future__ import annotations
from pathlib import Path
import pytest
from aesdk.trace.blob import ReasoningLog, ReplicationBlob
from aesdk.trace.exporters.csv_exporter import CSVExporter
from aesdk.trace.exporters.html_exporter import HTMLExporter

@pytest.fixture
def mock_blob(tmp_path):
    blob = ReplicationBlob(
        project_id="test-proj",
        pap_path=tmp_path / "pap.yaml",
        environment={"os": "test"},
        metadata={}
    )
    blob.record("init", {"status": "ok"})
    blob.record("execute", {"code": "print(1)", "status": "pass"})
    blob.record(
        "code_change",
        {"path": "analysis.py"},
        reasoning_log=ReasoningLog(summary="Documented change", pap_section_or_override="robustness"),
    )
    return blob

def test_csv_exporter(mock_blob, tmp_path):
    out = tmp_path / "report.csv"
    CSVExporter().export(mock_blob, out)
    assert out.exists()
    content = out.read_text()
    assert "event_type" in content
    assert "init" in content
    assert "execute" in content

def test_html_exporter(mock_blob, tmp_path):
    out = tmp_path / "report.html"
    HTMLExporter().export(mock_blob, out)
    assert out.exists()
    content = out.read_text()
    assert "<html>" in content
    assert "Replication Report" in content
    assert "test-proj" in content
    assert "Reasoning Log" in content
    assert "Documented change" in content
