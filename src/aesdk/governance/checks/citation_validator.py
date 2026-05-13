"""Citation checks with enforced online DOI verification."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

try:
    import requests
except Exception:  # pragma: no cover - optional dependency behavior
    requests = None

DOI_PATTERN = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9a-z]+\b")
DOI_CANDIDATE_PATTERN = re.compile(r"(?i)(?:doi:\s*|https?://(?:dx\.)?doi\.org/)?(10\.\S+)")
TRAILING_PUNCTUATION = ".,;:)]}>\"'"


@dataclass
class DOICheckResult:
    doi: str
    valid_format: bool
    reachable: bool


@dataclass
class CitationCheckReport:
    dois: list[DOICheckResult]

    @property
    def invalid_format_count(self) -> int:
        return sum(1 for item in self.dois if not item.valid_format)

    @property
    def unreachable_count(self) -> int:
        return sum(1 for item in self.dois if item.valid_format and not item.reachable)

    @property
    def hallucinated_count(self) -> int:
        return self.invalid_format_count + self.unreachable_count

    @property
    def uncertain_count(self) -> int:
        return 0


def extract_dois(text: str) -> list[str]:
    return DOI_PATTERN.findall(text)


def extract_doi_candidates(text: str) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    for match in DOI_CANDIDATE_PATTERN.findall(text):
        candidate = match.strip().rstrip(TRAILING_PUNCTUATION)
        if candidate and candidate not in seen:
            candidates.append(candidate)
            seen.add(candidate)
    return candidates


def verify_doi_reachable(doi: str, timeout: float = 5.0) -> bool:
    if requests is None:
        return False
    try:
        response = requests.head(
            f"https://doi.org/{doi}",
            allow_redirects=False,
            timeout=timeout,
            headers={"User-Agent": "AESDK/0.1"},
        )
        if response.status_code < 400 or response.is_redirect:
            return True
        if response.status_code in {403, 405, 429}:
            response = requests.get(
                f"https://doi.org/{doi}",
                allow_redirects=False,
                timeout=timeout,
                headers={"User-Agent": "AESDK/0.1"},
            )
            return response.status_code < 400 or response.is_redirect
    except Exception:
        return False
    return False


def verify_text(text: str, online: bool | None = None) -> CitationCheckReport:
    """Verify every DOI in text.

    The ``online`` argument is retained for older callers, but online DOI
    resolution is now mandatory for public-review readiness.
    """

    results: list[DOICheckResult] = []
    for doi in extract_doi_candidates(text):
        if not DOI_PATTERN.fullmatch(doi):
            results.append(DOICheckResult(doi=doi, valid_format=False, reachable=False))
            continue
        reachable = verify_doi_reachable(doi)
        results.append(DOICheckResult(doi=doi, valid_format=True, reachable=reachable))
    return CitationCheckReport(dois=results)


def verify_lines(lines: Iterable[str], online: bool | None = None) -> CitationCheckReport:
    return verify_text("\n".join(lines), online=online)
