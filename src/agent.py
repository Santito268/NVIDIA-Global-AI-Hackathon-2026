"""The pipeline: intake -> route -> research -> draft (explain comes next)."""

import json
import re
import sys
from dataclasses import dataclass, field

from src import config, legal, prompts
from src.llm import CallMetrics, LLMError, chat, chat_json
from src.schemas import CaseFacts, DraftDocument, RouteDecision, SearchPlan, Source
from src.tools import search_web

DOCUMENT_TITLES = {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"}
URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")
REMOVED_URL_NOTE = "[enlace eliminado: no proviene de una fuente verificada]"
QUOTE_PATTERN = re.compile(r"«([^«»]+)»")
REMOVED_QUOTE_NOTE = "[cita eliminada: no aparece en la fuente]"


@dataclass
class CaseResult:
    """Everything the pipeline produced for one case, plus what it cost."""

    facts: CaseFacts
    route: RouteDecision
    queries: list[str]
    sources: list[Source]
    draft: DraftDocument
    metrics: list[CallMetrics] = field(default_factory=list)


def validate_input(text: str) -> str:
    """Reject empty or too-long descriptions before spending any credits."""
    text = text.strip()
    if not text:
        raise LLMError("Please describe your case.")
    if len(text) > config.MAX_INPUT_CHARS:
        raise LLMError(f"Please keep the description under {config.MAX_INPUT_CHARS} characters.")
    return text


def run_intake(description: str) -> tuple[CaseFacts, list[CallMetrics]]:
    """Step 1 (Nano): extract the structured facts of the case."""
    messages = [
        {"role": "system", "content": prompts.INTAKE_SYSTEM},
        {"role": "user", "content": description},
    ]
    return chat_json(messages, config.NANO_MODEL, "intake", CaseFacts, thinking=False)


def run_route(facts: CaseFacts) -> tuple[RouteDecision, list[CallMetrics]]:
    """Step 2 (Nano): decide between derecho de petición and tutela."""
    messages = [
        {"role": "system", "content": prompts.ROUTE_SYSTEM},
        {"role": "user", "content": facts.model_dump_json()},
    ]
    return chat_json(messages, config.NANO_MODEL, "route", RouteDecision, thinking=False)


def run_research(
    facts: CaseFacts, route: RouteDecision
) -> tuple[list[str], list[Source], list[CallMetrics]]:
    """Step 3 (Super + Tavily): Super chooses what to search; our code runs the searches."""
    case = {"facts": facts.model_dump(), "document_type": route.document_type}
    messages = [
        {"role": "system", "content": prompts.RESEARCH_SYSTEM},
        {"role": "user", "content": json.dumps(case, ensure_ascii=False)},
    ]
    plan, metrics = chat_json(messages, config.SUPER_MODEL, "research", SearchPlan, thinking=False)

    # Hard cap on searches protects the free Tavily plan, whatever the model asks for.
    queries = plan.queries[: config.MAX_SEARCHES_PER_CASE]
    sources: dict[str, Source] = {}
    for query in queries:
        for source in search_web(query):
            sources.setdefault(source.url, source)  # same URL from two searches: keep one
    return queries, list(sources.values()), metrics


def remove_unverified_urls(text: str, sources: list[Source]) -> tuple[str, list[str]]:
    """Replace every URL not found by research nor in the legal code; return text and URLs kept."""
    known = {s.url for s in sources} | legal.corpus_urls()
    cited: list[str] = []

    def check(match: re.Match) -> str:
        url = match.group(0).rstrip(".,;:")
        if url in known:
            if url not in cited:
                cited.append(url)
            return match.group(0)
        return REMOVED_URL_NOTE

    return URL_PATTERN.sub(check, text), cited


def _normalize(text: str) -> str:
    """Compare quotes ignoring case, extra spaces and edge punctuation or ellipses."""
    return " ".join(text.split()).casefold().strip(" .,;:…")


def remove_unverified_quotes(text: str, sources: list[Source]) -> str:
    """Replace every «quote» that is not copied word for word from a snippet or the legal code."""
    known = [_normalize(s.snippet) for s in sources]
    known += [_normalize(e) for e in legal.corpus_excerpts()]

    def check(match: re.Match) -> str:
        quote = _normalize(match.group(1))
        if quote and any(quote in k for k in known):
            return match.group(0)
        return REMOVED_QUOTE_NOTE

    return QUOTE_PATTERN.sub(check, text)


def run_draft(
    facts: CaseFacts, route: RouteDecision, sources: list[Source]
) -> tuple[DraftDocument, list[CallMetrics]]:
    """Step 4 (Super, with reasoning): write the document, citing only verified sources."""
    case = {
        "document_type": route.document_type,
        "reason": route.reason,
        "facts": facts.model_dump(),
        "sources": [s.model_dump() for s in sources],
    }
    user_content = (
        f"LEGAL CODE:\n{legal.format_for_prompt()}\n\n"
        f"CASE AND SOURCES:\n{json.dumps(case, ensure_ascii=False)}"
    )
    messages = [
        {"role": "system", "content": prompts.DRAFT_SYSTEM},
        {"role": "user", "content": user_content},
    ]
    # Plain text instead of JSON: long documents break easily inside JSON strings.
    text, metrics = chat(
        messages, config.SUPER_MODEL, "draft", thinking=True, max_tokens=config.DRAFT_MAX_TOKENS
    )
    if not text:
        raise LLMError("The model returned an empty document. Please try again.")

    body, cited = remove_unverified_urls(remove_unverified_quotes(text, sources), sources)
    draft = DraftDocument(
        title=DOCUMENT_TITLES[route.document_type], body_markdown=body, cited_urls=cited
    )
    return draft, [metrics]


def run_case(description: str) -> CaseResult:
    """Run every pipeline step for one case."""
    description = validate_input(description)
    facts, intake_metrics = run_intake(description)
    route, route_metrics = run_route(facts)
    queries, sources, research_metrics = run_research(facts, route)
    draft, draft_metrics = run_draft(facts, route, sources)
    metrics = intake_metrics + route_metrics + research_metrics + draft_metrics
    return CaseResult(facts, route, queries, sources, draft, metrics)


def main() -> None:
    """CLI: python -m src.agent data/samples/caso_01.txt"""
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m src.agent <case_file.txt>")
    with open(sys.argv[1], encoding="utf-8") as f:
        result = run_case(f.read())
    print(result.facts.model_dump_json(indent=2))
    print(result.route.model_dump_json(indent=2))
    print("Searches:", *result.queries, sep="\n  - ")
    print("Sources:")
    for s in result.sources:
        print(f"  - {s.title}\n    {s.url}")
    print("\n" + "=" * 70 + "\n" + result.draft.body_markdown + "\n" + "=" * 70)
    print("Cited sources:", *result.draft.cited_urls, sep="\n  - ")
    for m in result.metrics:
        tokens = f"{m.prompt_tokens}+{m.completion_tokens}"
        print(f"[{m.step}] {m.model} {tokens} tokens {m.latency_s:.2f}s")


if __name__ == "__main__":
    main()
