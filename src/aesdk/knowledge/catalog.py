"""Load bundled AESDK econometric knowledge resources."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

import yaml


def _load_yaml_resource(name: str) -> dict[str, Any]:
    resource = files("aesdk.knowledge").joinpath(name)
    with resource.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Knowledge resource must be a mapping: {name}")
    return loaded


def _load_pack_resource(method_id: str) -> dict[str, Any]:
    resource = files("aesdk.knowledge").joinpath("packs", f"{method_id}.yaml")
    if not resource.is_file():
        known = ", ".join(list_knowledge_pack_ids())
        raise KeyError(f"Unknown knowledge pack '{method_id}'. Known packs: {known}")
    with resource.open("r", encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Knowledge pack must be a mapping: {method_id}")
    return loaded


def load_sources() -> dict[str, Any]:
    """Return registered textbook and literature sources."""

    return _load_yaml_resource("sources.yaml")


def load_method_protocols() -> dict[str, Any]:
    """Return textbook-backed method protocols keyed by method id."""

    return _load_yaml_resource("method_protocols.yaml")


def load_source_map() -> dict[str, Any]:
    """Return method-to-source locators for bundled textbook context."""

    return _load_yaml_resource("source_map.yaml")


def load_source_inventory() -> dict[str, Any]:
    """Return local source inventory metadata for textbook-derived context."""

    return _load_yaml_resource("source_inventory.yaml")


def load_official_software_sources() -> dict[str, Any]:
    """Return official software documentation sources used by code recipes."""

    return _load_yaml_resource("official_software_sources.yaml")


def get_knowledge_pack(method_id: str) -> dict[str, Any]:
    """Return the full-depth knowledge pack for one econometric method."""

    return _load_pack_resource(method_id)


def list_method_ids() -> list[str]:
    """Return sorted method protocol ids."""

    protocols = load_method_protocols().get("methods", {})
    return sorted(protocols)


def list_knowledge_pack_ids() -> list[str]:
    """Return sorted full-depth method knowledge pack ids."""

    resource = files("aesdk.knowledge").joinpath("packs")
    if not resource.is_dir():
        return []
    return sorted(item.name.removesuffix(".yaml") for item in resource.iterdir() if item.name.endswith(".yaml"))


def list_source_ids() -> list[str]:
    """Return sorted registered source ids."""

    sources = load_sources().get("sources", {})
    return sorted(sources)


def get_source(source_id: str) -> dict[str, Any]:
    """Return one registered source by id."""

    sources = load_sources().get("sources", {})
    try:
        source = sources[source_id]
    except KeyError as exc:
        known = ", ".join(sorted(sources))
        raise KeyError(f"Unknown source '{source_id}'. Known sources: {known}") from exc
    if not isinstance(source, dict):
        raise ValueError(f"Source must be a mapping: {source_id}")
    return source


def get_method_protocol(method_id: str) -> dict[str, Any]:
    """Return one method protocol by id."""

    protocols = load_method_protocols().get("methods", {})
    try:
        protocol = protocols[method_id]
    except KeyError as exc:
        known = ", ".join(sorted(protocols))
        raise KeyError(f"Unknown method protocol '{method_id}'. Known protocols: {known}") from exc
    if not isinstance(protocol, dict):
        raise ValueError(f"Method protocol must be a mapping: {method_id}")
    return protocol


def get_method_source_map(method_id: str) -> list[dict[str, Any]]:
    """Return source locators for one method id."""

    method_sources = load_source_map().get("method_sources", {})
    try:
        locators = method_sources[method_id]
    except KeyError as exc:
        known = ", ".join(sorted(method_sources))
        raise KeyError(f"Unknown method source map '{method_id}'. Known methods: {known}") from exc
    if not isinstance(locators, list):
        raise ValueError(f"Method source map must be a list: {method_id}")
    return locators


def validate_knowledge_base() -> list[str]:
    """Return structural errors in bundled knowledge metadata."""

    errors: list[str] = []
    sources = load_sources().get("sources", {})
    software_sources = load_official_software_sources().get("sources", {})
    protocols = load_method_protocols().get("methods", {})
    source_map = load_source_map().get("method_sources", {})
    pack_ids = list_knowledge_pack_ids()

    for method_id, protocol in protocols.items():
        if not isinstance(protocol, dict):
            errors.append(f"Method protocol is not a mapping: {method_id}")
            continue
        for source_ref in protocol.get("sources", []):
            source_id = source_ref.get("id") if isinstance(source_ref, dict) else None
            if source_id not in sources:
                errors.append(f"Method {method_id} references unknown source: {source_id}")

    for method_id, locators in source_map.items():
        if method_id not in protocols:
            errors.append(f"Source map references unknown method: {method_id}")
        if not isinstance(locators, list):
            errors.append(f"Source map entry is not a list: {method_id}")
            continue
        for item in locators:
            if not isinstance(item, dict):
                errors.append(f"Source map locator is not a mapping: {method_id}")
                continue
            source_id = item.get("source_id")
            if source_id not in sources:
                errors.append(f"Source map for {method_id} references unknown source: {source_id}")

    for method_id in pack_ids:
        pack = get_knowledge_pack(method_id)
        if method_id not in protocols:
            errors.append(f"Knowledge pack references unknown method protocol: {method_id}")
        if pack.get("method_id") != method_id:
            errors.append(f"Knowledge pack method_id mismatch: {method_id}")
        for required in ["decision_tree", "assumptions", "required_inputs", "diagnostics", "failure_modes", "code_recipes", "reporting_checklist", "source_anchors"]:
            if not pack.get(required):
                errors.append(f"Knowledge pack missing {required}: {method_id}")
        _validate_unique_pack_items(pack, method_id, errors)
        for recipe in pack.get("code_recipes", []):
            source_id = recipe.get("source") if isinstance(recipe, dict) else None
            if source_id not in software_sources:
                errors.append(f"Knowledge pack {method_id} recipe references unknown software source: {source_id}")
        for anchor in pack.get("source_anchors", []):
            source_id = anchor.get("source_id") if isinstance(anchor, dict) else None
            if source_id not in sources:
                errors.append(f"Knowledge pack {method_id} references unknown source: {source_id}")

    return errors


def _validate_unique_pack_items(pack: dict[str, Any], method_id: str, errors: list[str]) -> None:
    for section in ["decision_tree", "assumptions", "required_inputs", "diagnostics", "failure_modes", "code_recipes"]:
        seen: set[str] = set()
        for item in pack.get(section, []):
            if not isinstance(item, dict):
                continue
            item_id = item.get("id")
            if not item_id:
                errors.append(f"Knowledge pack {method_id} {section} item is missing id")
                continue
            if item_id in seen:
                errors.append(f"Knowledge pack {method_id} duplicates {section} id: {item_id}")
            seen.add(item_id)
