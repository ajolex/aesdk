"""Remote attestation providers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from aesdk.core.errors import AttestationError

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


@dataclass(frozen=True)
class AttestationEvidence:
    provider: str
    statement: str
    timestamp: str
    details: dict[str, Any] | None = None


class AttestationProvider(Protocol):
    def attest(self, passport: dict[str, Any]) -> AttestationEvidence:
        ...


class NoopAttestationProvider:
    """Local provider that records deterministic no-op evidence."""

    def attest(self, passport: dict[str, Any]) -> AttestationEvidence:
        return AttestationEvidence(
            provider="noop",
            statement="Remote attestation not configured; local no-op evidence recorded.",
            timestamp=datetime.now(timezone.utc).isoformat(),
            details={"mode": "noop"},
        )


class EndpointAttestationProvider:
    """HTTP attestation provider for real external attestation services."""

    def __init__(self, endpoint: str, token: str | None = None, timeout_seconds: float = 10.0):
        self.endpoint = endpoint.rstrip("/")
        self.token = token
        self.timeout_seconds = timeout_seconds

    def attest(self, passport: dict[str, Any]) -> AttestationEvidence:
        if requests is None:
            raise AttestationError("requests is required for endpoint attestation")
        url = f"{self.endpoint}/attest"
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        payload = {"passport": passport}
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise AttestationError(f"Remote attestation request failed: {exc}") from exc

        provider = body.get("provider", "endpoint")
        statement = body.get("statement", "Attestation completed")
        timestamp = body.get("timestamp", datetime.now(timezone.utc).isoformat())
        details = body.get("details")
        return AttestationEvidence(provider=provider, statement=statement, timestamp=timestamp, details=details)
