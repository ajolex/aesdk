import pytest

from aesdk.knowledge import (
    get_knowledge_pack,
    get_method_protocol,
    get_method_source_map,
    get_source,
    list_knowledge_pack_ids,
    list_method_ids,
    list_source_ids,
    load_official_software_sources,
    load_source_inventory,
    load_sources,
    validate_knowledge_base,
)


def test_method_protocols_are_available() -> None:
    method_ids = list_method_ids()
    assert {
        "did",
        "gmm",
        "iv_2sls",
        "limited_dependent",
        "matching",
        "nonlinear_did",
        "synthetic_control",
        "time_series",
    }.issubset(method_ids)


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


def test_full_knowledge_packs_are_available() -> None:
    pack_ids = list_knowledge_pack_ids()
    assert {
        "did",
        "gmm",
        "iv_2sls",
        "limited_dependent",
        "matching",
        "nonlinear_did",
        "ols_cef",
        "panel_fe",
        "rdd",
        "synthetic_control",
        "time_series",
    }.issubset(pack_ids)

    pack = get_knowledge_pack("did")
    assert pack["method_id"] == "did"
    assert pack["decision_tree"]
    assert pack["code_recipes"]
    assert pack["source_anchors"]


def test_source_inventory_includes_all_local_books() -> None:
    inventory = load_source_inventory()
    file_names = {item["file_name"] for item in inventory["sources"]}
    assert "econometric_analysis_by_greence.pdf" in file_names
    assert "JamesHStock.pdf" in file_names
    assert "WorldBankImpactEval.pdf" in file_names


def test_official_software_sources_are_registered() -> None:
    software = load_official_software_sources()["sources"]
    assert "statsmodels" in software
    assert "did_r" in software
    assert "matchit" in software
    assert "synth" in software
    assert "statsmodels_tsa" in software
    assert "r_stats_glm" in software
    assert "scpi" in software
    assert "stata_teffects" in software
    assert "stata_xtreg" in software
    assert software["rdrobust"]["url"].startswith("https://")


def test_pack_item_ids_are_unique() -> None:
    for method_id in list_knowledge_pack_ids():
        pack = get_knowledge_pack(method_id)
        for section in ["decision_tree", "assumptions", "required_inputs", "diagnostics", "failure_modes", "code_recipes"]:
            ids = [item["id"] for item in pack[section]]
            assert len(ids) == len(set(ids)), f"{method_id} duplicates ids in {section}"


def test_pack_code_recipe_sources_are_registered() -> None:
    software_sources = load_official_software_sources()["sources"]
    for method_id in list_knowledge_pack_ids():
        pack = get_knowledge_pack(method_id)
        for recipe in pack["code_recipes"]:
            assert recipe["source"] in software_sources, f"{method_id} recipe source is not registered"


def test_public_packs_have_language_recipe_parity_or_documented_exception() -> None:
    required = {"python", "r", "stata"}
    for method_id in list_knowledge_pack_ids():
        pack = get_knowledge_pack(method_id)
        languages = {recipe["language"] for recipe in get_knowledge_pack(method_id)["code_recipes"]}
        missing = required - languages
        if not missing:
            continue
        coverage = pack.get("language_coverage", {})
        intentionally_missing = coverage.get("intentionally_missing", {})
        assert missing.issubset(intentionally_missing), f"{method_id} lacks Python/R/Stata recipe parity"
        assert set(coverage.get("supported_recipes", [])) == languages


def test_new_brain_packs_are_pending_human_signoff() -> None:
    reviewed_pack_ids = {
        "gmm",
        "limited_dependent",
        "matching",
        "nonlinear_did",
        "synthetic_control",
        "time_series",
    }
    for method_id in reviewed_pack_ids:
        pack = get_knowledge_pack(method_id)
        assert pack["maturity"]["status"] == "pending_human_review"
        assert pack["maturity"]["source_review"] == "ai_source_audited_pending_human_review"
        assert pack["audit"]["stage"] == "ai_reviewed_pending_human"
