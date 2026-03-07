import pytest
import yaml

from aesdk.core.errors import GovernanceBlockError
from aesdk.core.project import Project
from aesdk.trace.blob import ReplicationBlob


def test_did_workflow_blocked_and_blob_written(valid_pap_dict: dict, runtime_dir) -> None:
    pap_path = runtime_dir / "pap.yaml"
    pap_path.write_text(yaml.safe_dump(valid_pap_dict, sort_keys=False), encoding="utf-8")

    proposal = {
        "estimator": "TWFE",
        "standard_errors": "HC3",
        "clustering": "state",
        "treatment_level": "state",
    }

    blob_path = runtime_dir / ".aesdk.json"
    project = Project.create(
        pap_path=pap_path,
        blob_path=blob_path,
        context="production",
        conformance="strict",
        policy_version="1.1.0",
    )
    project.propose_model(proposal)
    result = project.validate()

    ids = {v.rule_id for v in result.violations}
    assert result.status == "block"
    assert "W-PANEL-001" in ids
    assert "AP-DID-003" in ids

    with pytest.raises(GovernanceBlockError):
        project.execute("print('should not run')")

    blob = ReplicationBlob.load(blob_path)
    event_types = [event.event_type for event in blob.events]
    assert event_types[0] == "init"
    assert "propose_model" in event_types
    assert "validate" in event_types
    passport = blob.metadata["governance_passport"]
    assert passport["execution_context"] == "production"
    assert passport["conformance_level"] == "strict"
    assert passport["policy_version"] == "1.1.0"
    assert passport["rulepack_hash"].startswith("sha256:")
