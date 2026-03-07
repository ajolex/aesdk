import json

import pytest

from aesdk.trace.blob import ReasoningLog, ReplicationBlob, sign_blob, verify_blob_signature


def test_replication_blob_integrity_chain_verification(valid_pap_file) -> None:
    blob = ReplicationBlob(project_id="p1", pap_path=valid_pap_file, environment={"python": "test"})
    blob.record("init", {"x": 1})
    blob.record("validate", {"status": "pass"})

    ok, errors = blob.verify_integrity()
    assert ok
    assert errors == []

    blob._events[1].payload["status"] = "tampered"  # noqa: SLF001 - intentional tamper test
    ok2, errors2 = blob.verify_integrity()
    assert not ok2
    assert errors2


def test_reasoning_log_required_for_code_change(valid_pap_file) -> None:
    blob = ReplicationBlob(project_id="p1", pap_path=valid_pap_file, environment={})
    with pytest.raises(ValueError):
        blob.record("code_change", {"path": "x.py"})

    blob.record(
        "code_change",
        {"path": "x.py"},
        reasoning_log=ReasoningLog(summary="Change", pap_section_or_override="robustness"),
    )


def test_blob_signature_roundtrip(valid_pap_file, runtime_dir) -> None:
    blob = ReplicationBlob(project_id="p1", pap_path=valid_pap_file, environment={}, metadata={"x": 1})
    blob.record("init", {"x": 1})
    blob_path = runtime_dir / ".aesdk.json"
    blob.save(blob_path)

    sig_path = sign_blob(blob_path, secret="topsecret", key_id="test-key")
    ok, message = verify_blob_signature(blob_path, sig_path, secret="topsecret")
    assert ok
    assert message == "ok"

    payload = json.loads(blob_path.read_text(encoding="utf-8"))
    payload["project_id"] = "tampered"
    blob_path.write_text(json.dumps(payload), encoding="utf-8")

    ok2, _ = verify_blob_signature(blob_path, sig_path, secret="topsecret")
    assert not ok2
