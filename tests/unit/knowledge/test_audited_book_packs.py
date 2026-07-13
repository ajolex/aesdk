"""The nonparametric, Bayesian, and GARCH packs are page-anchored and audited.

These three packs were upgraded from AI-drafted (pending human review) to
page-anchored against their local source PDFs, so they must (a) no longer be
pending, (b) carry verified pdf page anchors in both the pack and the source
map, and (c) point at a local_path for the primary source.
"""

from __future__ import annotations

from aesdk.knowledge.catalog import (
    get_knowledge_pack,
    get_method_protocol,
    get_method_source_map,
    get_source,
)

AUDITED = {
    "nonparametric": "li_racine_nonparametric_2007",
    "bayesian": "koop_poirier_tobias_2007",
    "garch": "tsay_financial_time_series_2010",
}


def test_book_packs_are_no_longer_pending() -> None:
    for method_id in AUDITED:
        pack = get_knowledge_pack(method_id)
        assert pack["maturity"]["status"] == "reviewed_guardrail"
        assert pack["maturity"]["status"] != "pending_human_review"
        assert get_method_protocol(method_id)["status"] != "pending_human_review"


def test_primary_source_anchor_has_page_numbers() -> None:
    for method_id, source_id in AUDITED.items():
        pack = get_knowledge_pack(method_id)
        primary = next(a for a in pack["source_anchors"] if a["source_id"] == source_id)
        pages = primary.get("local_pdf_pages")
        assert pages and all(isinstance(p, int) and p > 0 for p in pages)


def test_source_map_has_verified_locators() -> None:
    for method_id, source_id in AUDITED.items():
        entries = get_method_source_map(method_id)
        primary = next(e for e in entries if e["source_id"] == source_id)
        assert primary.get("local_path")
        locators = primary.get("locators")
        assert locators and all(loc.get("pdf_pages") for loc in locators)


def test_audited_sources_have_local_path() -> None:
    for source_id in AUDITED.values():
        assert get_source(source_id).get("local_path")
