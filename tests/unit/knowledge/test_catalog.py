import pytest

from aesdk.knowledge import (
    get_method_protocol,
    get_method_source_map,
    get_source,
    list_method_ids,
    list_source_ids,
    load_sources,
    validate_knowledge_base,
)


def test_method_protocols_are_available() -> None:
    method_ids = list_method_ids()
    assert "did" in method_ids
    assert "iv_2sls" in method_ids


def test_get_method_protocol_returns_source_linked_protocol() -> None:
    protocol = get_method_protocol("did")
    assert protocol["name"] == "Differences-in-Differences"
    assert protocol["sources"]


def test_unknown_method_protocol_raises_helpful_error() -> None:
    with pytest.raises(KeyError, match="Known protocols"):
        get_method_protocol("not_a_method")


def test_sources_include_local_textbooks() -> None:
    sources = load_sources()["sources"]
    assert "wooldridge_cross_section_panel" in sources
    assert "angrist_pischke_mhe" in sources


def test_source_registry_helpers() -> None:
    source_ids = list_source_ids()
    assert "wooldridge_cross_section_panel" in source_ids
    source = get_source("angrist_pischke_mhe")
    assert source["local_path"] == "tools/MostlyHarmlessEconometrics.pdf"


def test_method_source_map_contains_pdf_locators() -> None:
    locators = get_method_source_map("did")
    assert locators
    assert any(item["source_id"] == "angrist_pischke_mhe" for item in locators)


def test_knowledge_base_validates() -> None:
    assert validate_knowledge_base() == []
