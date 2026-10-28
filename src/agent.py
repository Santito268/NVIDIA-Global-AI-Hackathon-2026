"""The pipeline: intake -> route (code) -> research -> draft -> explain.

The checks on the draft live in src/verify.py and the translation in src/translate.py.
"""

import json
import re
import sys
from collections.abc import Callable
from dataclasses import dataclass, field

from src import config, legal, prompts
from src.document import DOCUMENT_NAMES, build_document, extract_sections
from src.llm import CallMetrics, LLMError, chat, chat_json
from src.schemas import CaseFacts, DraftDocument, Explanation, RouteDecision, SearchPlan, Source
from src.tools import search_web
from src.translate import run_translate_input
from src.verify import check_section, find_placeholders

# Very common words that exist in only one of the two languages (used by detect_language).
ENGLISH_WORDS = frozenset(
    "the and of to is was my his her she they it for with have had been not did does "
    "doesn't didn't won't can't this that but on at an from their them since months weeks "
    "days ago years old".split()
)
SPANISH_WORDS = frozenset(
    "el la los las de del que y en un una por para con mi su sus es está tiene ha han hace "
    "pero ya porque desde meses semanas días años le les lo al".split()
)

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


def detect_language(text: str) -> str:
    """Return "en" or "es" by counting very common words of each language (code, no model call).

    Only words that do not exist in the other language count ("no" and "me" are both).
    A tie, or a text with none of them, counts as Spanish: the intake then decides.
    """
    words = re.findall(r"[a-záéíóúñü']+", text.lower())
    english = sum(word in ENGLISH_WORDS for word in words)
    spanish = sum(word in SPANISH_WORDS for word in words)
    return "en" if english > spanish else "es"


def validate_input(text: str, lang: str = config.SOURCE_LANGUAGE) -> str:
    """Reject descriptions that cannot be a case, before spending any credits.

    `lang` is the page language: English text is only accepted on the English page, where
    the user was told it will be translated.
    """
    text = text.strip()
    if not text:
        raise LLMError("Please describe your case.", "empty")
    if len(text) > config.MAX_INPUT_CHARS:
        raise LLMError(
            f"Please keep the description under {config.MAX_INPUT_CHARS} characters.", "too_long"
        )
    if len(text.split()) < config.MIN_INPUT_WORDS:
        raise LLMError("Please describe what happened in a few sentences.", "too_short")
    if detect_language(text) == "en" and lang != "en":
        raise LLMError("The text is in English but the page is in Spanish.", "wrong_language")
    return text


def run_intake(description: str) -> tuple[CaseFacts, list[CallMetrics]]:
    """Step 1 (Nano): extract the structured facts of the case."""
    messages = [
        {"role": "system", "content": prompts.INTAKE_SYSTEM},
        {"role": "user", "content": description},
    ]
    facts, metrics = chat_json(messages, config.NANO_MODEL, "intake", CaseFacts, thinking=False)
    # Nano once answered writer_relationship "hija" together with writer_is_affected_person
    # true (eval case 02). A relationship means someone writes for another person, by the
    # prompt's own rule, so code settles the contradiction.
    if facts.writer_relationship and facts.writer_is_affected_person:
        facts = facts.model_copy(update={"writer_is_affected_person": False})
    return facts, metrics


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
            timeout=config.DRAFT_TIMEOUT_S,
            max_retries=config.DRAFT_MAX_RETRIES,
        )
        all_metrics.append(metrics)
        sections = extract_sections(text, route.document_type)
        if sections:
            break
    if not sections:
        raise LLMError("The model returned an incomplete document.", "incomplete")

    checked: dict[str, str] = {}
    cited: list[str] = []
    removed_quotes = 0
    for heading, content in sections.items():
        checked[heading], urls, removed = check_section(content, sources)
        removed_quotes += removed
        cited += [url for url in urls if url not in cited]
    draft = DraftDocument(
        title=DOCUMENT_NAMES[config.SOURCE_LANGUAGE][route.document_type],
        body_markdown=build_document(route.document_type, facts, checked),
        sections=checked,
        cited_urls=cited,
        removed_quotes=removed_quotes,
    )
    return draft, all_metrics


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


def run_case(
    description: str,
    on_step: Callable[[str], None] | None = None,
    lang: str = config.SOURCE_LANGUAGE,
) -> CaseResult:
    """Run every pipeline step for one case; `on_step(name)` is called before each step.

    `lang` is the page language. A case written in English (only allowed on the English
    page) is first translated into Spanish by Nano.
    """
    notify = on_step or (lambda _step: None)
    description = validate_input(description, lang)
    notify("intake")
    intake_metrics: list[CallMetrics] = []
    if detect_language(description) == "en":
        description, intake_metrics = run_translate_input(description, config.LANGUAGES["en"])
    facts, metrics = run_intake(description)
    intake_metrics += metrics
    if not facts.is_eps_health_case:
        # Stop before Super and Tavily: an off-topic text costs only the intake (~1k tokens).
        raise LLMError("This text is not a problem with an EPS.", "off_topic", intake_metrics)
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
