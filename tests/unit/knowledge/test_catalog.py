import pytest
import yaml
from pathlib import Path

from aesdk.knowledge import (
    get_knowledge_pack,
    get_method_protocol,
    get_method_source_map,
    get_source,
    list_knowledge_pack_ids,
    list_curriculum_stage_ids,
    list_method_ids,
    list_source_ids,
    load_curriculum,
    load_official_software_sources,
    load_source_inventory,
    load_sources,
    validate_knowledge_base,
)
from aesdk.sandbox.runner import DEFAULT_WHITELIST_PATH, SandboxRunner


def test_method_protocols_are_available() -> None:
    method_ids = list_method_ids()
    assert {
        "did",
        "gmm",
        "experimental_rct",
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


def test_curriculum_stages_are_registered() -> None:
    curriculum = load_curriculum()["curriculum"]
    assert {
        "foundations_mechanics",
        "identification_pivot",
        "theoretical_microfoundations",
        "advanced_empirical_research",
    }.issubset(list_curriculum_stage_ids())
    assert "ols_cef" in curriculum["foundations_mechanics"]["method_ids"]
    assert "did" in curriculum["advanced_empirical_research"]["method_ids"]
    assert "experimental_rct" in curriculum["advanced_empirical_research"]["method_ids"]


def test_methods_are_mapped_to_curriculum() -> None:
    for method_id in list_method_ids():
        protocol = get_method_protocol(method_id)
        curriculum = protocol["curriculum"]
        assert curriculum["stage"]
        assert curriculum["topics"]


def test_registered_sources_have_online_locators() -> None:
    for source_id, source in load_sources()["sources"].items():
        online = source.get("online", {})
        assert online.get("doi") or online.get("url"), f"{source_id} lacks online locator"


def test_full_knowledge_packs_are_available() -> None:
    pack_ids = list_knowledge_pack_ids()
    assert {
        "did",
        "experimental_rct",
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


def test_knowledge_packs_are_method_topic_organized() -> None:
    for method_id in list_knowledge_pack_ids():
        pack = get_knowledge_pack(method_id)
        protocol = get_method_protocol(method_id)
        organization = pack["organization"]
        assert organization["type"] == "method_topic_pack"
        assert organization["curriculum_stage"] == protocol["curriculum"]["stage"]
        assert set(organization["curriculum_topics"]) == set(protocol["curriculum"]["topics"])


def test_governance_rule_files_are_topic_not_author_named() -> None:
    rules_dir = Path("src/aesdk/governance/rules")
    forbidden = {"wooldridge", "angrist", "pischke", "greene", "hansen"}
    for path in rules_dir.glob("*.rules.yaml"):
        name = path.name.lower()
        assert not any(token in name for token in forbidden), f"{path.name} is author-named"
        rule_file = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        source = rule_file.get("source", {})
        assert source.get("organization") in {"method_topic", "cross_cutting_topic"}
        assert source.get("topic")


def test_every_method_pack_has_executable_rule_coverage() -> None:
    rules_dir = Path("src/aesdk/governance/rules")
    method_rule_files = {
        "ols_cef": "ols_cef.rules.yaml",
        "iv_2sls": "iv_2sls.rules.yaml",
        "panel_fe": "panel_inference.rules.yaml",
        "did": "did.rules.yaml",
        "experimental_rct": "experimental_rct.rules.yaml",
        "rdd": "rdd.rules.yaml",
        "matching": "matching.rules.yaml",
        "synthetic_control": "synthetic_control.rules.yaml",
        "nonlinear_did": "nonlinear_did.rules.yaml",
        "gmm": "gmm.rules.yaml",
        "limited_dependent": "limited_dependent.rules.yaml",
        "time_series": "time_series.rules.yaml",
    }
    assert set(method_rule_files) == set(list_knowledge_pack_ids())
    for method_id, file_name in method_rule_files.items():
        path = rules_dir / file_name
        assert path.exists(), f"{method_id} lacks executable rule file"
        rule_file = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        assert rule_file.get("rules"), f"{method_id} rule file has no rules"


def test_source_inventory_includes_all_local_books() -> None:
    inventory = load_source_inventory()
    file_names = {item["file_name"] for item in inventory["sources"]}
    assert "econometric_analysis_by_greence.pdf" in file_names
    assert "JamesHStock.pdf" in file_names
    assert "WorldBankImpactEval.pdf" in file_names
    assert "2015-01-EN-The-gold-standard-for-randomized-evaluations-from-discussion-of-method-to-political-economy.pdf" in file_names


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


def test_recipe_packages_are_supported_by_language_sandbox_allowlists() -> None:
    runner = SandboxRunner(DEFAULT_WHITELIST_PATH)
    for method_id in list_knowledge_pack_ids():
        for recipe in get_knowledge_pack(method_id)["code_recipes"]:
            language = recipe["language"]
            package = recipe["package"]
            if language == "python":
                assert package in runner.allowed_imports, f"{method_id} Python recipe package is not whitelisted"
            if language == "r":
                assert package in runner.allowed_r_packages, f"{method_id} R recipe package is not whitelisted"


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
