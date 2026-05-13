"""Build a compact AESDK source inventory from local PDFs.

This script reads metadata only. It does not copy textbook text into package
artifacts.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import yaml


def _pdf_pages(path: Path) -> int | None:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - developer environment helper
        raise SystemExit("Install pypdf to build the source inventory.") from exc
    try:
        return len(PdfReader(str(path)).pages)
    except Exception:
        return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Create metadata-only source inventory for local AESDK PDFs.")
    parser.add_argument("--tools-dir", default="tools", help="Directory containing local source PDFs.")
    parser.add_argument("--output", default="src/aesdk/knowledge/source_inventory.generated.yaml")
    args = parser.parse_args()

    tools_dir = Path(args.tools_dir)
    sources = []
    for path in sorted(tools_dir.glob("*.pdf")):
        sources.append(
            {
                "file_name": path.name,
                "local_path": str(path).replace("\\", "/"),
                "pages": _pdf_pages(path),
                "extraction_status": "inventory_only",
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(
            {
                "version": "generated",
                "policy": {
                    "packaged_content": "metadata only",
                    "excluded_content": ["full PDFs", "extracted textbook text", "long verbatim passages"],
                },
                "sources": sources,
            },
            sort_keys=False,
        ),
        encoding="utf-8",
    )
    print(f"wrote={output} sources={len(sources)}")


if __name__ == "__main__":
    main()
