from aesdk.governance.checks import citation_validator


def test_verify_text_enforces_online_reachability(monkeypatch) -> None:
    calls: list[str] = []

    def fake_verify(doi: str, timeout: float = 5.0) -> bool:
        calls.append(doi)
        return True

    monkeypatch.setattr(citation_validator, "verify_doi_reachable", fake_verify)

    report = citation_validator.verify_text("See https://doi.org/10.1111/ectj.12097", online=False)

    assert calls == ["10.1111/ectj.12097"]
    assert report.unreachable_count == 0
    assert report.hallucinated_count == 0


def test_unreachable_doi_counts_as_hallucinated(monkeypatch) -> None:
    monkeypatch.setattr(citation_validator, "verify_doi_reachable", lambda doi, timeout=5.0: False)

    report = citation_validator.verify_text("Unverified DOI: 10.9999/not-real")

    assert report.unreachable_count == 1
    assert report.hallucinated_count == 1


def test_malformed_doi_like_text_counts_as_invalid(monkeypatch) -> None:
    calls: list[str] = []
    monkeypatch.setattr(citation_validator, "verify_doi_reachable", lambda doi, timeout=5.0: calls.append(doi) or True)

    report = citation_validator.verify_text("Broken DOI: doi:10.bad")

    assert calls == []
    assert report.invalid_format_count == 1
    assert report.hallucinated_count == 1
