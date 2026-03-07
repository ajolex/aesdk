from aesdk.core.attestation import EndpointAttestationProvider


class _FakeResponse:
    def __init__(self, body: dict):
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._body


def test_endpoint_attestation_provider_success(monkeypatch):
    def fake_post(url, json, headers, timeout):  # noqa: ANN001
        assert url.endswith('/attest')
        assert 'passport' in json
        assert timeout == 10.0
        return _FakeResponse(
            {
                'provider': 'attestor-v1',
                'statement': 'verified',
                'timestamp': '2026-03-08T00:00:00+00:00',
                'details': {'nonce': 'abc'},
            }
        )

    import aesdk.core.attestation as mod

    monkeypatch.setattr(mod.requests, 'post', fake_post)
    provider = EndpointAttestationProvider('https://attest.example')
    evidence = provider.attest({'policy_version': '1.0.0'})

    assert evidence.provider == 'attestor-v1'
    assert evidence.statement == 'verified'
    assert evidence.details == {'nonce': 'abc'}
