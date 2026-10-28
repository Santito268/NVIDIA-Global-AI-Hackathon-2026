"""Rule-based checks for one evaluated case. Plain code, no model judges the model."""

import re

from src import legal, verify
from src.agent import CaseResult

# Every "Ley N de AAAA" / "Decreto N de AAAA" (and similar) mentioned in a document.
NORM_PATTERN = re.compile(
    r"\b(Ley|Decreto|Resolución|Circular|Acuerdo)\s+(\d[\d.]*)\s+de\s+(\d{4})", re.IGNORECASE
)
# Words that showed up in earlier live tests and must never reach a filed document.
FORBIDDEN_PATTERNS = {
    "costas": re.compile(r"\bcostas\b", re.IGNORECASE),
    "indemnización": re.compile(r"\bindemniza", re.IGNORECASE),
    "CN": re.compile(r"\bCN\b"),
    "officioso": re.compile(r"officioso", re.IGNORECASE),
    "nota de Uso": re.compile(r"\(?\bUso:"),
}
COURT_DOMAIN = "corteconstitucional.gov.co"


def _norm_key(kind: str, number: str, year: str) -> str:
    return f"{kind.capitalize()} {number.replace('.', '')} de {year}"


def allowed_norms() -> set[str]:
    """The numbered norms of the mini legal code, e.g. "Ley 1755 de 2015"."""
    names = " ".join(source["name"] for source in legal.load_corpus()["sources"].values())
    return {_norm_key(*m.groups()) for m in NORM_PATTERN.finditer(names)}


def unknown_norms(text: str) -> list[str]:
    """Numbered norms in `text` that are not in the mini legal code (possibly invented)."""
    allowed = allowed_norms()
    found = {_norm_key(*m.groups()) for m in NORM_PATTERN.finditer(text)}
    return sorted(found - allowed)


def forbidden_words(text: str) -> list[str]:
    """Names of the forbidden patterns found in `text`."""
    return [name for name, pattern in FORBIDDEN_PATTERNS.items() if pattern.search(text)]


def rulings_cited(result: CaseResult) -> int:
    """How many Constitutional Court rulings survived the quote and URL filters."""
    return sum(COURT_DOMAIN in url for url in result.draft.cited_urls)


def check_case(result: CaseResult, expected: dict) -> dict:
    """Grade one case. Every key ending in "_ok" is a pass/fail rule."""
    body = result.draft.body_markdown
    norms = unknown_norms(body)
    words = forbidden_words(body)
    # Only some cases say which problem type they are (e.g. the "other" case).
    problem_type = (
        {"problem_type_ok": result.facts.problem_type == expected["problem_type"]}
        if "problem_type" in expected
        else {}
    )
    return problem_type | {
        "document_type": result.route.document_type,
        "document_type_ok": result.route.document_type == expected["document_type"],
        "writer_ok": result.facts.writer_is_affected_person
        == expected["writer_is_affected_person"],
        "special_protection_ok": result.facts.special_protection == expected["special_protection"],
        "norms_ok": not norms,
        "unknown_norms": norms,
        "urls_ok": verify.REMOVED_URL_NOTE not in body,
        "forbidden_words_ok": not words,
        "forbidden_words": words,
        "rulings_cited": rulings_cited(result),
        "quotes_removed": result.draft.removed_quotes,
        "tokens": sum(m.prompt_tokens + m.completion_tokens for m in result.metrics),
        "latency_s": round(sum(m.latency_s for m in result.metrics), 1),
        # Saved so a failure can be traced to the step that caused it.
        "facts": result.facts.model_dump(),
        "route_reason": result.route.reason,
    }


def passed(grade: dict) -> bool:
    """A case passes only if every rule passes."""
    return all(value for key, value in grade.items() if key.endswith("_ok"))
