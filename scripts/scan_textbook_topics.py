"""Scan local PDFs for method-topic page locators.

The output is a compact locator report: source file, topic id, and pages where
topic terms appear. It intentionally excludes extracted prose.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

import yaml


TOPICS: dict[str, list[str]] = {
    "ols_cef": ["conditional expectation", "ordinary least squares", "heteroskedasticity", "robust standard errors"],
    "iv_2sls": ["instrumental variables", "two-stage least squares", "2sls", "weak instruments", "first stage"],
    "panel_fe": ["fixed effects", "unobserved effects", "panel data", "cluster"],
    "did": ["difference-in-differences", "differences-in-differences", "parallel trends", "event study"],
    "rdd": ["regression discontinuity", "running variable", "bandwidth", "cutoff"],
}


def _extract_page_text(page) -> str:
    try:
        return page.extract_text() or ""
    except Exception:
        return ""


def scan_pdf(path: Path, max_pages_per_topic: int) -> dict[str, list[int]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - developer environment helper
        raise SystemExit("Install pypdf to scan textbook topics.") from exc

    reader = PdfReader(str(path))
    hits = {topic: [] for topic in TOPICS}
    patterns = {
        topic: [re.compile(re.escape(term), re.IGNORECASE) for term in terms]
        for topic, terms in TOPICS.items()
    }
    for index, page in enumerate(reader.pages, start=1):
        text = _extract_page_text(page)
        if not text:
            continue
        for topic, topic_patterns in patterns.items():
            if len(hits[topic]) >= max_pages_per_topic:
                continue
            if any(pattern.search(text) for pattern in topic_patterns):
                hits[topic].append(index)
    return {topic: pages for topic, pages in hits.items() if pages}


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan local PDFs for compact AESDK topic locators.")
    parser.add_argument("--tools-dir", default="tools", help="Directory containing local source PDFs.")
    parser.add_argument("--output", default="docs/source_topic_locator_report.yaml")
    parser.add_argument("--max-pages-per-topic", type=int, default=12)
    args = parser.parse_args()

    report = []
    for path in sorted(Path(args.tools_dir).glob("*.pdf")):
        report.append(
            {
                "file_name": path.name,
                "local_path": str(path).replace("\\", "/"),
                "topics": scan_pdf(path, args.max_pages_per_topic),
            }
        )

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(yaml.safe_dump({"version": "generated", "sources": report}, sort_keys=False), encoding="utf-8")
    print(f"wrote={output} sources={len(report)}")


if __name__ == "__main__":
    main()
