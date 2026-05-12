"""Context packets for AI agents before they write econometric code."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import yaml

from aesdk.knowledge import get_method_protocol, get_method_source_map


@dataclass(frozen=True)
class AgentContext:
    method_id: str
    protocol: dict[str, Any]
    sources: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "method_id": self.method_id,
            "protocol": self.protocol,
            "sources": self.sources,
        }

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
        return "\n".join(blocks).rstrip() + "\n"


def agent_context(method: str) -> AgentContext:
    """Return an agent-ready context packet for one econometric method."""

    return AgentContext(
        method_id=method,
        protocol=get_method_protocol(method),
        sources=get_method_source_map(method),
    )
