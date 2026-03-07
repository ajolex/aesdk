"""Citation checks (MVP DOI format + optional online verification)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

try:
    import requests
except Exception:  # pragma: no cover - optional dependency behavior
    requests = None

DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+\b")


@dataclass
class DOICheckResult:
    doi: str
    valid_format: bool
    reachable: bool | None


@dataclass
class CitationCheckReport:
    dois: list[DOICheckResult]

    @property
    def invalid_format_count(self) -> int:
        return sum(1 for item in self.dois if not item.valid_format)


def extract_dois(text: str) -> list[str]:
    return DOI_PATTERN.findall(text)


def verify_doi_reachable(doi: str, timeout: float = 5.0) -> bool | None:
    if requests is None:
        return None
    try:
        response = requests.head(
            f"https://doi.org/{doi}",
            allow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "AESDK/0.1"},
        )
        return response.status_code < 400
    except Exception:
        return None


def verify_text(text: str, online: bool = False) -> CitationCheckReport:
    dois = extract_dois(text)
    results: list[DOICheckResult] = []
    for doi in dois:
        reachable = verify_doi_reachable(doi) if online else None
        results.append(DOICheckResult(doi=doi, valid_format=True, reachable=reachable))
    return CitationCheckReport(dois=results)


def verify_lines(lines: Iterable[str], online: bool = False) -> CitationCheckReport:
    return verify_text("\n".join(lines), online=online)
