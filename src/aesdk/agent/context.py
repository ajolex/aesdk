"""Context packets for AI agents before they write econometric code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from aesdk.knowledge import get_knowledge_pack, get_method_protocol, get_method_source_map


@dataclass(frozen=True)
class AgentContext:
    method_id: str
    protocol: dict[str, Any]
    sources: list[dict[str, Any]]
    knowledge_pack: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {
            "method_id": self.method_id,
            "protocol": self.protocol,
            "sources": self.sources,
        }
        if self.knowledge_pack is not None:
            data["knowledge_pack"] = self.knowledge_pack
        return data

    def to_yaml(self) -> str:
        return yaml.safe_dump(self.to_dict(), sort_keys=False)

    def to_markdown(self) -> str:
        blocks = [
            f"# AESDK Agent Context: {self.method_id}",
            "",
            "## Binding Instructions",
            "- Do not write econometric execution code until AESDK preflight passes.",
            "- Treat `block` as a hard stop.",
            "- Treat `warn` as requiring documented researcher acknowledgement.",
            "- Do not invent assumptions, diagnostics, or citations.",
            "",
            f"## Method: {self.protocol.get('name', self.method_id)}",
            "",
            f"Purpose: {self.protocol.get('purpose', '')}",
            "",
            "## Required Assumptions",
            *[f"- {item}" for item in self.protocol.get("assumptions", [])],
            "",
            "## Required PAP Fields",
            *[f"- `{item}`" for item in self.protocol.get("required_pap_fields", [])],
            "",
            "## Diagnostics",
            *[f"- {item}" for item in self.protocol.get("diagnostics", [])],
            "",
            "## Blocks Or Warnings",
            *[f"- {item}" for item in self.protocol.get("blocks_or_warnings", [])],
            "",
            "## Source Locators",
        ]
        for source in self.sources:
            blocks.append(f"- `{source.get('source_id')}`")
            for locator in source.get("locators", []):
                topic = locator.get("topic", "source locator")
                pages = locator.get("pdf_pages")
                suffix = f" pages={pages}" if pages else ""
                blocks.append(f"  - {topic}{suffix}")
        if self.knowledge_pack is not None:
            pack = self.knowledge_pack
            maturity = pack.get("maturity", {})
            blocks.extend(
                [
                    "",
                    "## Knowledge Pack Maturity",
                    f"- status: {maturity.get('status', 'unknown')}",
                    f"- source_review: {maturity.get('source_review', 'unknown')}",
                    f"- code_recipes: {maturity.get('code_recipes', 'unknown')}",
                    "",
                    "## Estimator Decision Tree",
                ]
            )
            blocks.extend([f"- {item.get('if')} -> {item.get('then')}" for item in pack.get("decision_tree", [])])
            blocks.extend(["", "## Failure Modes"])
            blocks.extend([f"- {item.get('risk')}: {item.get('response')}" for item in pack.get("failure_modes", [])])
            blocks.extend(["", "## Code Recipes"])
            blocks.extend([f"- {item.get('id')}: {item.get('language')} / {item.get('package')}" for item in pack.get("code_recipes", [])])
            blocks.extend(["", "## Reporting Checklist"])
            blocks.extend([f"- {item}" for item in pack.get("reporting_checklist", [])])
        return "\n".join(blocks).rstrip() + "\n"


def agent_context(method: str, *, depth: str = "protocol") -> AgentContext:
    """Return an agent-ready context packet for one econometric method."""

    normalized_depth = depth.lower().strip()
    if normalized_depth not in {"protocol", "full"}:
        raise ValueError("depth must be 'protocol' or 'full'")
    return AgentContext(
        method_id=method,
        protocol=get_method_protocol(method),
        sources=get_method_source_map(method),
        knowledge_pack=get_knowledge_pack(method) if normalized_depth == "full" else None,
    )
