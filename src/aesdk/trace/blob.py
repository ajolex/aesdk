"""Replication blob with append-only hash chain and signing utilities."""

from __future__ import annotations

import hashlib
import hmac
import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aesdk.core.errors import BlobIntegrityError, BlobSignatureError
from aesdk.trace.kms_providers import provider_for_mode

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


@dataclass
class ReasoningLog:
    summary: str
    pap_section_or_override: str
    econometric_principle: str = ""
    changes: list[str] | None = None
    triggered_by: str = "agent"
    override_rule_id: str | None = None

    def __post_init__(self) -> None:
        if not self.summary.strip():
            raise ValueError("ReasoningLog.summary is required")
        if not self.pap_section_or_override.strip():
            raise ValueError("ReasoningLog.pap_section_or_override is required")

    def to_dict(self) -> dict[str, Any]:
        return {
            "summary": self.summary,
            "pap_section_or_override": self.pap_section_or_override,
            "econometric_principle": self.econometric_principle,
            "changes": self.changes or [],
            "triggered_by": self.triggered_by,
            "override_rule_id": self.override_rule_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReasoningLog":
        return cls(
            summary=data["summary"],
            pap_section_or_override=data["pap_section_or_override"],
            econometric_principle=data.get("econometric_principle", ""),
            changes=data.get("changes", []),
            triggered_by=data.get("triggered_by", "agent"),
            override_rule_id=data.get("override_rule_id"),
        )


@dataclass
class BlobEvent:
    event_id: str
    event_type: str
    timestamp: str
    previous_hash: str
    payload: dict[str, Any]
    reasoning_log: ReasoningLog | None
    hash: str

    @classmethod
    def create(
        cls,
        *,
        event_type: str,
        payload: dict[str, Any],
        previous_hash: str,
        reasoning_log: ReasoningLog | None = None,
    ) -> "BlobEvent":
        event = cls(
            event_id=str(uuid.uuid4()),
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            previous_hash=previous_hash,
            payload=payload,
            reasoning_log=reasoning_log,
            hash="",
        )
        event.hash = _event_hash(event.to_dict(include_hash=False))
        return event

    def to_dict(self, include_hash: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "event_id": self.event_id,
            "event_type": self.event_type,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "payload": self.payload,
            "reasoning_log": self.reasoning_log.to_dict() if self.reasoning_log else None,
        }
        if include_hash:
            data["hash"] = self.hash
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BlobEvent":
        return cls(
            event_id=data["event_id"],
            event_type=data["event_type"],
            timestamp=data["timestamp"],
            previous_hash=data.get("previous_hash", ""),
            payload=data.get("payload", {}),
            reasoning_log=ReasoningLog.from_dict(data["reasoning_log"]) if data.get("reasoning_log") else None,
            hash=data["hash"],
        )


class ReplicationBlob:
    BLOB_VERSION = "1.2.0"

    def __init__(
        self,
        project_id: str,
        pap_path: str | Path,
        environment: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ):
        self.project_id = project_id
        self.pap_path = str(pap_path)
        self.pap_hash = self._hash_file(self.pap_path)
        self.environment = environment
        self.metadata = metadata or {}
        self._events: list[BlobEvent] = []

    @property
    def events(self) -> list[BlobEvent]:
        return list(self._events)

    def record(
        self,
        event_type: str,
        payload: dict[str, Any],
        reasoning_log: ReasoningLog | None = None,
    ) -> BlobEvent:
        if event_type == "code_change" and reasoning_log is None:
            raise ValueError("ReasoningLog is required for code_change events")
        previous_hash = self._events[-1].hash if self._events else ""
        event = BlobEvent.create(
            event_type=event_type,
            payload=payload,
            previous_hash=previous_hash,
            reasoning_log=reasoning_log,
        )
        self._events.append(event)
        return event

    def to_dict(self) -> dict[str, Any]:
        return {
            "blob_version": self.BLOB_VERSION,
            "project_id": self.project_id,
            "pap_path": self.pap_path,
            "pap_hash": self.pap_hash,
            "environment": self.environment,
            "metadata": self.metadata,
            "events": [event.to_dict() for event in self._events],
        }

    def save(self, path: str | Path) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)

    @classmethod
    def load(cls, path: str | Path) -> "ReplicationBlob":
        target = Path(path)
        with target.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        blob = cls(
            project_id=data["project_id"],
            pap_path=data["pap_path"],
            environment=data.get("environment", {}),
            metadata=data.get("metadata", {}),
        )
        blob.pap_hash = data["pap_hash"]
        blob._events = [BlobEvent.from_dict(item) for item in data.get("events", [])]
        return blob

    def verify_integrity(self) -> tuple[bool, list[str]]:
        errors: list[str] = []
        previous_hash = ""
        for index, event in enumerate(self._events):
            if event.previous_hash != previous_hash:
                errors.append(
                    f"Event {index} previous_hash mismatch: expected '{previous_hash}' got '{event.previous_hash}'"
                )
            computed = _event_hash(event.to_dict(include_hash=False))
            if computed != event.hash:
                errors.append(f"Event {index} hash mismatch: expected '{event.hash}' got '{computed}'")
            previous_hash = event.hash
        return (len(errors) == 0, errors)

    @staticmethod
    def _hash_file(path: str) -> str:
        target = Path(path)
        if not target.exists():
            return "missing"
        return "sha256:" + hashlib.sha256(target.read_bytes()).hexdigest()


def _event_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def canonical_blob_bytes(blob: ReplicationBlob | dict[str, Any]) -> bytes:
    payload = blob.to_dict() if isinstance(blob, ReplicationBlob) else blob
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_blob(
    blob_path: str | Path,
    *,
    mode: str = "hmac",
    secret: str | None = None,
    key_id: str = "local",
    kms_endpoint: str | None = None,
    kms_token: str | None = None,
    timeout_seconds: float = 10.0,
) -> Path:
    blob_file = Path(blob_path)
    payload = json.loads(blob_file.read_text(encoding="utf-8"))
    canonical = canonical_blob_bytes(payload)
    blob_sha256 = hashlib.sha256(canonical).hexdigest()

    if mode == "hmac":
        if not secret:
            raise BlobSignatureError("secret is required for hmac signing")
        signature = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        signature_doc = {
            "algorithm": "HMAC-SHA256",
            "key_id": key_id,
            "blob_sha256": blob_sha256,
            "signature": signature,
            "signed_at": datetime.now(timezone.utc).isoformat(),
        }
    elif mode in {"kms-http", "aws-kms", "gcp-kms", "azure-keyvault"}:
        provider = provider_for_mode(
            mode,
            kms_endpoint=kms_endpoint,
            kms_token=kms_token,
            timeout_seconds=timeout_seconds,
        )
        signature = provider.sign(key_id=key_id, blob_sha256=blob_sha256)
        signature_doc = {
            "algorithm": provider.algorithm,
            "key_id": key_id,
            "blob_sha256": blob_sha256,
            "signature": signature,
            "signed_at": datetime.now(timezone.utc).isoformat(),
        }
        if kms_endpoint:
            signature_doc["kms_endpoint"] = kms_endpoint
    else:
        raise BlobSignatureError(f"Unsupported signing mode: {mode}")

    sig_path = blob_file.with_suffix(blob_file.suffix + ".sig.json")
    sig_path.write_text(json.dumps(signature_doc, indent=2), encoding="utf-8")
    return sig_path


def verify_blob_signature(
    blob_path: str | Path,
    signature_path: str | Path,
    *,
    secret: str | None = None,
    kms_endpoint: str | None = None,
    kms_token: str | None = None,
    timeout_seconds: float = 10.0,
) -> tuple[bool, str]:
    blob_file = Path(blob_path)
    sig_file = Path(signature_path)
    payload = json.loads(blob_file.read_text(encoding="utf-8"))
    sig_doc = json.loads(sig_file.read_text(encoding="utf-8"))

    canonical = canonical_blob_bytes(payload)
    recomputed_blob_sha = hashlib.sha256(canonical).hexdigest()
    if recomputed_blob_sha != sig_doc.get("blob_sha256"):
        return False, "blob_sha256 mismatch"

    algorithm = sig_doc.get("algorithm", "")
    if algorithm == "HMAC-SHA256":
        if not secret:
            raise BlobSignatureError("secret is required for hmac signature verification")
        expected_sig = hmac.new(secret.encode("utf-8"), canonical, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, sig_doc.get("signature", "")):
            return False, "signature mismatch"
        return True, "ok"

    if algorithm in {"KMS-HTTP-SHA256", "AWS-KMS-RSASSA-PSS-SHA256", "GCP-KMS-RSA-SIGN-PSS-2048-SHA256", "AZURE-KEYVAULT-RS256"}:
        mode_by_algorithm = {
            "KMS-HTTP-SHA256": "kms-http",
            "AWS-KMS-RSASSA-PSS-SHA256": "aws-kms",
            "GCP-KMS-RSA-SIGN-PSS-2048-SHA256": "gcp-kms",
            "AZURE-KEYVAULT-RS256": "azure-keyvault",
        }
        endpoint = kms_endpoint or sig_doc.get("kms_endpoint")
        provider = provider_for_mode(
            mode_by_algorithm[algorithm],
            kms_endpoint=endpoint,
            kms_token=kms_token,
            timeout_seconds=timeout_seconds,
        )
        valid = provider.verify(
            key_id=sig_doc.get("key_id", ""),
            blob_sha256=recomputed_blob_sha,
            signature=sig_doc.get("signature", ""),
        )
        return (True, "ok") if valid else (False, "signature mismatch")

    raise BlobSignatureError(f"Unsupported signature algorithm: {algorithm}")


def _kms_http_sign(
    *,
    endpoint: str,
    key_id: str,
    blob_sha256: str,
    token: str | None,
    timeout_seconds: float,
) -> str:
    if requests is None:
        raise BlobSignatureError("requests is required for kms-http signing")
    url = endpoint.rstrip("/") + "/sign"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"key_id": key_id, "blob_sha256": blob_sha256}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        raise BlobSignatureError(f"kms-http sign request failed: {exc}") from exc
    signature = body.get("signature")
    if not signature:
        raise BlobSignatureError("kms-http sign response missing 'signature'")
    return str(signature)


def _kms_http_verify(
    *,
    endpoint: str,
    key_id: str,
    blob_sha256: str,
    signature: str,
    token: str | None,
    timeout_seconds: float,
) -> bool:
    if requests is None:
        raise BlobSignatureError("requests is required for kms-http verification")
    url = endpoint.rstrip("/") + "/verify"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {"key_id": key_id, "blob_sha256": blob_sha256, "signature": signature}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=timeout_seconds)
        response.raise_for_status()
        body = response.json()
    except Exception as exc:
        raise BlobSignatureError(f"kms-http verify request failed: {exc}") from exc
    return bool(body.get("valid", False))


def verify_integrity(blob_or_path: ReplicationBlob | str | Path) -> tuple[bool, list[str]]:
    blob = blob_or_path
    if isinstance(blob_or_path, (str, Path)):
        blob = ReplicationBlob.load(blob_or_path)
    assert isinstance(blob, ReplicationBlob)
    valid, errors = blob.verify_integrity()
    if not valid:
        raise BlobIntegrityError("Replication blob failed integrity check: " + "; ".join(errors))
    return valid, errors
