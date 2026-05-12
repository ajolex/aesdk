from aesdk.trace.blob import sign_blob, verify_blob_signature


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


def test_kms_http_sign_and_verify(monkeypatch, runtime_dir):
    blob_path = runtime_dir / '.aesdk.json'
    blob_path.write_text('{"project_id":"p","pap_path":"x","pap_hash":"h","environment":{},"metadata":{},"events":[]}', encoding='utf-8')

    def fake_post(url, json, headers, timeout):  # noqa: ANN001
        if url.endswith('/sign'):
            return _FakeResponse({'signature': 'kms-signature-123'})
        if url.endswith('/verify'):
            return _FakeResponse({'valid': True})
        raise AssertionError('unexpected endpoint')

    import aesdk.trace.kms_providers as mod

    monkeypatch.setattr(mod.requests, 'post', fake_post)

    sig_path = sign_blob(blob_path, mode='kms-http', key_id='k1', kms_endpoint='https://kms.example')
    ok, message = verify_blob_signature(blob_path, sig_path, kms_endpoint='https://kms.example')

    assert ok is True
    assert message == 'ok'


def test_aws_kms_provider_with_injected_client():
    from aesdk.trace.kms_providers import AWSKMSProvider

    class FakeAWSClient:
        def sign(self, **kwargs):  # noqa: ANN003
            assert kwargs["MessageType"] == "DIGEST"
            return {"Signature": b"signed"}

        def verify(self, **kwargs):  # noqa: ANN003
            assert kwargs["Signature"] == b"signed"
            return {"SignatureValid": True}

    provider = AWSKMSProvider(client=FakeAWSClient())
    signature = provider.sign(key_id="key", blob_sha256="00" * 32)
    assert provider.verify(key_id="key", blob_sha256="00" * 32, signature=signature)
