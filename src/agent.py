"""The pipeline: intake -> route (code) -> research -> draft -> explain."""

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from src import config, legal, prompts
from src.document import build_document, extract_sections
from src.llm import CallMetrics, LLMError, chat, chat_json
from src.schemas import (
    CaseFacts,
    DraftDocument,
    Explanation,
    ExplanationText,
    RouteDecision,
    SearchPlan,
    Source,
)
from src.tools import search_web

DOCUMENT_TITLES = {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"}
URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")
REMOVED_URL_NOTE = "[enlace eliminado: no proviene de una fuente verificada]"
QUOTE_PATTERN = re.compile(r"«([^«»]+)»")
REMOVED_QUOTE_NOTE = "[cita eliminada: no aparece en la fuente]"
MIN_QUOTE_WORDS = 6  # the shortest excerpt of the legal code has 6 words
ITEM_START_PATTERN = re.compile(r"^(?:[-*]|\d+[.)])\s")
PLACEHOLDER_PATTERN = re.compile(r"\[[A-ZÁÉÍÓÚÑ ]+\]")
# Text the translation must never touch: quotes, URLs and blanks. Each one is swapped for a
# numbered token before translating and put back afterwards.
PROTECTED_PATTERN = re.compile(
    "|".join(p.pattern for p in (QUOTE_PATTERN, URL_PATTERN, PLACEHOLDER_PATTERN))
)
TOKEN_PATTERN = re.compile(r"⟦\d+⟧")
SECTION_MARKER_PATTERN = re.compile(r"^⟦S(\d+)⟧[ \t]*$", re.MULTILINE)

# Why the document fits the case: hand-written in every language, chosen by route_case's rule.
ROUTE_REASONS: dict[str, dict[str, str]] = {
    "es": {
        "tutela": "Procede la tutela porque {reasons}.",
        "special": "el paciente es sujeto de especial protección constitucional{group}",
        "urgent": "la demora pone en riesgo inminente la salud o la vida del paciente",
        "and": " y ",
        "derecho_de_peticion": (
            "Procede el derecho de petición porque no hay un riesgo inminente para la salud: "
            "primero se le pide a la EPS una respuesta formal y de fondo."
        ),
    },
    "en": {
        "tutela": "A tutela is the right document because {reasons}.",
        "special": "the patient is a subject of special constitutional protection{group}",
        "urgent": "the delay puts the patient's health or life at imminent risk",
        "and": " and ",
        "derecho_de_peticion": (
            "A derecho de petición is the right document because there is no imminent risk "
            "to health: first, the EPS is asked for a formal answer on the merits."
        ),
    },
}
PROTECTION_GROUPS: dict[str, dict[str, str]] = {
    "es": {
        "child": "menor de edad",
        "older_adult": "adulto mayor",
        "disability": "persona con discapacidad",
        "pregnancy": "mujer embarazada",
        "serious_illness": "persona con una enfermedad grave",
    },
    "en": {
        "child": "a child or adolescent",
        "older_adult": "an older adult",
        "disability": "a person with a disability",
        "pregnancy": "a pregnant woman",
        "serious_illness": "a person with a serious illness",
    },
}

# Fixed, hand-written next steps per language: deadlines are legal facts, so the model never
# writes or translates them. Every legal statement is in the verified mini legal code
# (data/legal/mini_codigo.json); a test checks that every language cites the same numbers.
NEXT_STEPS: dict[str, dict[str, list[str]]] = {
    "es": {
        "tutela": [
            "Llena los espacios entre corchetes y revisa que los hechos sean correctos.",
            "Firma el documento. Al presentarlo declaras bajo juramento que no has presentado "
            "otra tutela por los mismos hechos y derechos (art. 37 del Decreto 2591 de 1991).",
            "Preséntalo ante un juez con los anexos. No necesitas abogado (art. 14 del Decreto "
            "2591 de 1991) y todos los días y horas son hábiles para presentarla (art. 1).",
            "El juez debe decidir dentro de los diez días siguientes, y el plazo para cumplir su "
            "orden no puede pasar de 48 horas (art. 29 del Decreto 2591 de 1991).",
            "Guarda una copia con la constancia de que lo presentaste.",
        ],
        "derecho_de_peticion": [
            "Llena los espacios entre corchetes y revisa que los hechos sean correctos.",
            "Firma el documento y radícalo ante la EPS con los anexos. Guarda una copia con la "
            "fecha en que lo recibieron.",
            "Las reglas del derecho de petición también se aplican a las EPS (art. 33 de la Ley "
            "1755 de 2015).",
            "Por regla general, la petición debe resolverse dentro de los quince (15) días "
            "siguientes a su recepción (art. 14 de la Ley 1755 de 2015).",
        ],
    },
    "en": {
        "tutela": [
            "Fill in the blanks in brackets and check that the facts are correct.",
            "Sign the document. By filing it you declare under oath that you have not filed "
            "another tutela for the same facts and rights (art. 37 of Decreto 2591 de 1991).",
            "File it before a judge with the annexes. You do not need a lawyer (art. 14 of "
            "Decreto 2591 de 1991) and it can be filed any day, at any time (art. 1).",
            "The judge must decide within the following ten days, and the deadline to comply "
            "with the order cannot exceed 48 hours (art. 29 of Decreto 2591 de 1991).",
            "Keep a copy with the proof that you filed it.",
        ],
        "derecho_de_peticion": [
            "Fill in the blanks in brackets and check that the facts are correct.",
            "Sign the document and file it with the EPS, with the annexes. Keep a copy showing "
            "the date they received it.",
            "The rules of the derecho de petición also apply to EPS (art. 33 of Ley 1755 de 2015).",
            "As a general rule, the petition must be answered within fifteen (15) days of its "
            "receipt (art. 14 of Ley 1755 de 2015).",
        ],
    },
}


@dataclass
class CaseResult:
    """Everything the pipeline produced for one case, plus what it cost."""

    facts: CaseFacts
    route: RouteDecision
    queries: list[str]
    sources: list[Source]
    draft: DraftDocument
    explanation: Explanation
    to_fill: list[str]
    next_steps: list[str]
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


def route_case(facts: CaseFacts) -> RouteDecision:
    """Step 2 (code, no model): choose the document with a fixed legal rule.

    Tutela when the delay puts health or life at imminent risk or the patient is a subject of
    special constitutional protection; otherwise a derecho de petición. A model call here
    flipped its answer in the evaluation set (D37), so the rule is applied by code.
    """
    tutela = facts.special_protection or facts.urgent_health_risk
    document_type = "tutela" if tutela else "derecho_de_peticion"
    return RouteDecision(
        document_type=document_type,
        reason=route_reason(facts, document_type, config.SOURCE_LANGUAGE),
    )


def route_reason(facts: CaseFacts, document_type: str, lang: str) -> str:
    """The hand-written reason for the chosen document, in `lang`."""
    texts = ROUTE_REASONS[lang]
    if document_type != "tutela":
        return texts[document_type]
    reasons = []
    if facts.special_protection:
        group = facts.special_protection_group
        name = f" ({PROTECTION_GROUPS[lang][group]})" if group else ""
        reasons.append(texts["special"].format(group=name))
    if facts.urgent_health_risk:
        reasons.append(texts["urgent"])
    return texts["tutela"].format(reasons=texts["and"].join(reasons))


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
        # A live test kept «... insulina glargina ...»: two words found in a snippet prove
        # nothing. A quote must be a real sentence fragment, with no gaps inside.
        long_enough = len(quote.split()) >= MIN_QUOTE_WORDS
        no_gaps = "…" not in quote and "..." not in quote
        if long_enough and no_gaps and any(quote in k for k in known):
            return match.group(0)
        return REMOVED_QUOTE_NOTE

    return QUOTE_PATTERN.sub(check, text)


def drop_items_with_removed_quotes(text: str) -> str:
    """Remove every list item or paragraph whose quote was removed.

    A ruling cited with "[cita eliminada]" proves nothing and looks broken to a judge; the
    laws from the verified legal code remain as the legal grounds.
    """
    blocks: list[list[str]] = []
    for line in text.split("\n"):
        starts_block = not line.strip() or ITEM_START_PATTERN.match(line)
        if not blocks or starts_block or not blocks[-1][-1].strip():
            blocks.append([line])
        else:
            blocks[-1].append(line)  # continuation of a multi-line item
    kept = [block for block in blocks if not any(REMOVED_QUOTE_NOTE in ln for ln in block)]
    return "\n".join(line for block in kept for line in block)


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
    all_metrics: list[CallMetrics] = []
    sections = None
    for _ in range(2):  # one retry if a required section is missing
        # Plain text instead of JSON: long documents break easily inside JSON strings.
        text, metrics = chat(
            messages,
            config.SUPER_MODEL,
            "draft",
            thinking=True,
            max_tokens=config.DRAFT_MAX_TOKENS,
            temperature=config.DRAFT_TEMPERATURE,
        )
        all_metrics.append(metrics)
        sections = extract_sections(text, route.document_type)
        if sections:
            break
    if not sections:
        raise LLMError("The model returned an incomplete document.", "incomplete")

    checked: dict[str, str] = {}
    cited: list[str] = []
    for heading, content in sections.items():
        content = drop_items_with_removed_quotes(remove_unverified_quotes(content, sources))
        checked[heading], urls = remove_unverified_urls(content, sources)
        cited += [url for url in urls if url not in cited]
    draft = DraftDocument(
        title=DOCUMENT_TITLES[route.document_type],
        body_markdown=build_document(route.document_type, facts, checked),
        sections=checked,
        cited_urls=cited,
    )
    return draft, all_metrics


def find_placeholders(text: str) -> list[str]:
    """List the [PLACEHOLDERS] the citizen still has to fill in, in order of appearance."""
    return list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(text)))


def run_explain(
    route: RouteDecision, draft: DraftDocument
) -> tuple[Explanation, list[CallMetrics]]:
    """Step 5 (Nano): explain the document in plain language."""
    case = {"document_type": route.document_type, "document": draft.body_markdown}
    messages = [
        {"role": "system", "content": prompts.EXPLAIN_SYSTEM},
        {"role": "user", "content": json.dumps(case, ensure_ascii=False)},
    ]
    return chat_json(messages, config.NANO_MODEL, "explain", Explanation, thinking=False)


def protect(text: str) -> tuple[str, list[str]]:
    """Swap quotes, URLs and blanks for tokens ⟦1⟧, ⟦2⟧...; return the text and the originals."""
    originals: list[str] = []

    def swap(match: re.Match) -> str:
        originals.append(match.group(0))
        return f"⟦{len(originals)}⟧"

    return PROTECTED_PATTERN.sub(swap, text), originals


def restore(text: str, originals: list[str]) -> str:
    """Put the originals back; fail if the translation lost, repeated or invented a token."""
    expected = [f"⟦{i}⟧" for i in range(1, len(originals) + 1)]
    if sorted(TOKEN_PATTERN.findall(text)) != sorted(expected):
        raise LLMError("The translation changed protected text. Showing the Spanish version.")
    for token, original in zip(expected, originals, strict=True):
        text = text.replace(token, original)
    return text


def run_translate_sections(
    sections: dict[str, str], language: str
) -> tuple[dict[str, str], list[CallMetrics]]:
    """Translate only the model's sections into `language` (e.g. "English"), in one Nano call.

    The fixed parts are hand-written per language (src/document.py), so they never reach the
    model. Quotes, URLs and blanks are protected with tokens; each section starts with a
    marker ⟦S1⟧, ⟦S2⟧... so the answer can be split back into the same sections.
    """
    headings = list(sections)
    joined = "\n\n".join(f"⟦S{i}⟧\n{sections[h]}" for i, h in enumerate(headings, 1))
    protected, originals = protect(joined)
    messages = [
        {"role": "system", "content": prompts.TRANSLATE_SECTIONS_SYSTEM.format(language=language)},
        {"role": "user", "content": protected},
    ]
    translation, metrics = chat(
        messages,
        config.NANO_MODEL,
        "translate_sections",
        thinking=False,
        max_tokens=config.DRAFT_MAX_TOKENS,
    )
    parts = SECTION_MARKER_PATTERN.split(restore(translation, originals))
    # split() gives [text before ⟦S1⟧, "1", section 1, "2", section 2, ...]
    numbers, texts = parts[1::2], parts[2::2]
    if numbers != [str(i) for i in range(1, len(headings) + 1)]:
        raise LLMError("The translation lost a section. Showing the Spanish version.")
    return {h: text.strip() for h, text in zip(headings, texts, strict=True)}, [metrics]


def run_translate_explanation(
    text: ExplanationText, language: str
) -> tuple[ExplanationText, list[CallMetrics]]:
    """Translate only the case-specific parts of the explanation, as validated JSON (Nano)."""
    messages = [
        {
            "role": "system",
            "content": prompts.TRANSLATE_EXPLANATION_SYSTEM.format(language=language),
        },
        {"role": "user", "content": text.model_dump_json()},
    ]
    translation, metrics = chat_json(
        messages, config.NANO_MODEL, "translate_explanation", ExplanationText, thinking=False
    )
    if len(translation.key_points) != len(text.key_points):
        raise LLMError("The translation lost a key point. Showing the Spanish version.")
    return translation, metrics


def run_case(description: str, on_step: Callable[[str], None] | None = None) -> CaseResult:
    """Run every pipeline step for one case; `on_step(name)` is called before each step."""
    notify = on_step or (lambda _step: None)
    description = validate_input(description)
    notify("intake")
    facts, intake_metrics = run_intake(description)
    route = route_case(facts)
    notify("research")
    queries, sources, research_metrics = run_research(facts, route)
    notify("draft")
    draft, draft_metrics = run_draft(facts, route, sources)
    notify("explain")
    explanation, explain_metrics = run_explain(route, draft)
    metrics = intake_metrics + research_metrics + draft_metrics + explain_metrics
    return CaseResult(
        facts,
        route,
        queries,
        sources,
        draft,
        explanation,
        to_fill=find_placeholders(draft.body_markdown),
        next_steps=NEXT_STEPS[config.SOURCE_LANGUAGE][route.document_type],
        metrics=metrics,
    )


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
    print("\nExplanation:\n" + result.explanation.summary)
    print("Key points:", *result.explanation.key_points, sep="\n  - ")
    print("To fill:", ", ".join(result.to_fill))
    print("Next steps:", *result.next_steps, sep="\n  - ")
    for m in result.metrics:
        tokens = f"{m.prompt_tokens}+{m.completion_tokens}"
        print(f"[{m.step}] {m.model} {tokens} tokens {m.latency_s:.2f}s")


if __name__ == "__main__":
    main()
