"""Provider-based KMS signing adapters for replication blob hashes."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Protocol

from aesdk.core.errors import BlobSignatureError

try:
    import requests
except Exception:  # pragma: no cover
    requests = None


class KMSProvider(Protocol):
    algorithm: str

    def sign(self, *, key_id: str, blob_sha256: str) -> str:
        ...

    def verify(self, *, key_id: str, blob_sha256: str, signature: str) -> bool:
        ...


@dataclass
class KMSHTTPProvider:
    endpoint: str
    token: str | None = None
    timeout_seconds: float = 10.0
    algorithm: str = "KMS-HTTP-SHA256"

    def sign(self, *, key_id: str, blob_sha256: str) -> str:
        if requests is None:
            raise BlobSignatureError("requests is required for kms-http signing")
        url = self.endpoint.rstrip("/") + "/sign"
        body = self._post(url, {"key_id": key_id, "blob_sha256": blob_sha256})
        signature = body.get("signature")
        if not signature:
            raise BlobSignatureError("kms-http sign response missing 'signature'")
        return str(signature)

    def verify(self, *, key_id: str, blob_sha256: str, signature: str) -> bool:
        if requests is None:
            raise BlobSignatureError("requests is required for kms-http verification")
        url = self.endpoint.rstrip("/") + "/verify"
        body = self._post(url, {"key_id": key_id, "blob_sha256": blob_sha256, "signature": signature})
        return bool(body.get("valid", False))

    def _post(self, url: str, payload: dict[str, str]) -> dict:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=self.timeout_seconds)
            response.raise_for_status()
            body = response.json()
        except Exception as exc:
            raise BlobSignatureError(f"kms-http request failed: {exc}") from exc
        if not isinstance(body, dict):
            raise BlobSignatureError("kms-http response must be a JSON object")
        return body


@dataclass
class AWSKMSProvider:
    region_name: str | None = None
    client: object | None = None
    algorithm: str = "AWS-KMS-RSASSA-PSS-SHA256"

    def _client(self):
        if self.client is not None:
            return self.client
        try:
            import boto3
        except ImportError as exc:
            raise BlobSignatureError("Install aesdk[cloud-kms] or boto3 for AWS KMS signing") from exc
        return boto3.client("kms", region_name=self.region_name)

    def sign(self, *, key_id: str, blob_sha256: str) -> str:
        response = self._client().sign(
            KeyId=key_id,
            Message=bytes.fromhex(blob_sha256),
            MessageType="DIGEST",
            SigningAlgorithm="RSASSA_PSS_SHA_256",
        )
        return base64.b64encode(response["Signature"]).decode("ascii")

    def verify(self, *, key_id: str, blob_sha256: str, signature: str) -> bool:
        response = self._client().verify(
            KeyId=key_id,
            Message=bytes.fromhex(blob_sha256),
            MessageType="DIGEST",
            Signature=base64.b64decode(signature),
            SigningAlgorithm="RSASSA_PSS_SHA_256",
        )
        return bool(response.get("SignatureValid", False))


@dataclass
class GCPKMSProvider:
    client: object | None = None
    algorithm: str = "GCP-KMS-RSA-SIGN-PSS-2048-SHA256"

    def _client(self):
        if self.client is not None:
            return self.client
        try:
            from google.cloud import kms_v1
        except ImportError as exc:
            raise BlobSignatureError("Install aesdk[cloud-kms] or google-cloud-kms for GCP KMS signing") from exc
        return kms_v1.KeyManagementServiceClient()

    def _digest(self, blob_sha256: str):
        try:
            from google.cloud.kms_v1.types import Digest
        except ImportError as exc:
            if self.client is not None:
                return {"sha256": bytes.fromhex(blob_sha256)}
            raise BlobSignatureError("Install google-cloud-kms for GCP KMS signing") from exc
        return Digest(sha256=bytes.fromhex(blob_sha256))

    def sign(self, *, key_id: str, blob_sha256: str) -> str:
        response = self._client().asymmetric_sign(request={"name": key_id, "digest": self._digest(blob_sha256)})
        return base64.b64encode(response.signature).decode("ascii")

    def verify(self, *, key_id: str, blob_sha256: str, signature: str) -> bool:
        try:
            from cryptography.exceptions import InvalidSignature
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import padding
        except ImportError as exc:
            raise BlobSignatureError("Install aesdk[cloud-kms] or cryptography for GCP KMS verification") from exc
        public_key_response = self._client().get_public_key(request={"name": key_id})
        public_key = serialization.load_pem_public_key(public_key_response.pem.encode("utf-8"))
        try:
            public_key.verify(
                base64.b64decode(signature),
                bytes.fromhex(blob_sha256),
                padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.MAX_LENGTH),
                hashes.SHA256(),
            )
        except InvalidSignature:
            return False
        return True


@dataclass
class AzureKeyVaultProvider:
    credential: object | None = None
    client: object | None = None
    algorithm: str = "AZURE-KEYVAULT-RS256"

    def _client(self, key_id: str):
        if self.client is not None:
            return self.client
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.keys.crypto import CryptographyClient
        except ImportError as exc:
            raise BlobSignatureError("Install aesdk[cloud-kms] or Azure Key Vault packages for Azure signing") from exc
        credential = self.credential or DefaultAzureCredential()
        return CryptographyClient(key_id, credential)

    def _signature_algorithm(self):
        try:
            from azure.keyvault.keys.crypto import SignatureAlgorithm
        except ImportError as exc:
            if self.client is not None:
                return "RS256"
            raise BlobSignatureError("Install aesdk[cloud-kms] or Azure Key Vault packages for Azure signing") from exc
        return SignatureAlgorithm.rs256

    def sign(self, *, key_id: str, blob_sha256: str) -> str:
        result = self._client(key_id).sign(self._signature_algorithm(), bytes.fromhex(blob_sha256))
        return base64.b64encode(result.signature).decode("ascii")

    def verify(self, *, key_id: str, blob_sha256: str, signature: str) -> bool:
        result = self._client(key_id).verify(
            self._signature_algorithm(),
            bytes.fromhex(blob_sha256),
            base64.b64decode(signature),
        )
        return bool(result.is_valid)


def provider_for_mode(
    mode: str,
    *,
    kms_endpoint: str | None = None,
    kms_token: str | None = None,
    timeout_seconds: float = 10.0,
) -> KMSProvider:
    if mode == "kms-http":
        if not kms_endpoint:
            raise BlobSignatureError("kms_endpoint is required for kms-http signing")
        return KMSHTTPProvider(kms_endpoint, token=kms_token, timeout_seconds=timeout_seconds)
    if mode == "aws-kms":
        return AWSKMSProvider()
    if mode == "gcp-kms":
        return GCPKMSProvider()
    if mode == "azure-keyvault":
        return AzureKeyVaultProvider()
    raise BlobSignatureError(f"Unsupported KMS provider mode: {mode}")
