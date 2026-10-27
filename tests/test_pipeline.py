"""Pipeline tests. They run in mock mode: no network, no credits."""

import re
from types import SimpleNamespace

import httpx2  # the HTTP library openai uses; only to build its error objects
import openai
import pytest
from pydantic import ValidationError

from src import agent, config, document, legal, llm, translate, verify
from src.schemas import CaseFacts, ExplanationText, RouteDecision, SearchPlan, Source


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")


def test_extract_json_ignores_surrounding_text():
    text = 'Sure! ```json\n{"document_type": "tutela", "reason": "x"}\n```'
    assert llm.extract_json(text) == {"document_type": "tutela", "reason": "x"}


def test_extract_json_raises_without_object():
    with pytest.raises(ValueError):
        llm.extract_json("no json here")


def test_chat_json_retries_once_then_succeeds(monkeypatch):
    answers = iter(["not json", '{"document_type": "tutela", "reason": "riesgo"}'])
    monkeypatch.setattr(
        llm, "chat", lambda *a, **k: (next(answers), llm.CallMetrics("route", "mock", 0, 0, 0))
    )
    result, metrics = llm.chat_json([], "m", "route", RouteDecision)
    assert result.document_type == "tutela"
    assert len(metrics) == 2


def test_chat_json_gives_up_with_user_friendly_error(monkeypatch):
    monkeypatch.setattr(llm, "chat", lambda *a, **k: ("bad", llm.CallMetrics("x", "m", 0, 0, 0)))
    with pytest.raises(llm.LLMError):
        llm.chat_json([], "m", "route", RouteDecision)


def test_chat_sends_thinking_switch_to_nebius(monkeypatch):
    sent = {}

    class FakeCompletions:
        def create(self, **kwargs):
            sent.update(kwargs)
            message = SimpleNamespace(content="ok")
            return SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(config, "LLM_MODE", "live")
    monkeypatch.setattr(llm, "_client", lambda *args: fake_client)

    llm.chat([], "some-model", "intake", thinking=False)
    assert sent["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}
    assert sent["temperature"] == 0  # classification steps never change their answer


_REQUEST = httpx2.Request("POST", "https://example.test/v1/chat/completions")


@pytest.mark.parametrize(
    ("error", "code"),
    [
        (openai.APITimeoutError(request=_REQUEST), "timeout"),
        (openai.APIConnectionError(request=_REQUEST), "connection"),
        (
            openai.APIStatusError(
                "busy", response=httpx2.Response(503, request=_REQUEST), body=None
            ),
            "generic",
        ),
    ],
)
def test_nebius_errors_become_user_friendly_errors_with_a_code(monkeypatch, error, code):
    def failing_create(**kwargs):
        raise error

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=failing_create))
    )
    monkeypatch.setattr(config, "LLM_MODE", "live")
    monkeypatch.setattr(llm, "_client", lambda *args: fake_client)
    with pytest.raises(llm.LLMError) as raised:
        llm.chat([], "some-model", "intake")
    assert raised.value.code == code


def test_draft_waits_longer_but_never_retries_on_the_network(monkeypatch):
    used = []

    def fake_client(timeout, max_retries):
        used.append((timeout, max_retries))
        message = SimpleNamespace(content="## Hechos\nx")
        response = SimpleNamespace(choices=[SimpleNamespace(message=message)], usage=None)
        return SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=lambda **k: response))
        )

    monkeypatch.setattr(config, "LLM_MODE", "live")
    monkeypatch.setattr(llm, "_client", fake_client)
    llm.chat([], "m", "intake")
    with pytest.raises(llm.LLMError):  # the fake answer lacks sections: incomplete
        agent.run_draft(_facts(), agent.route_case(_facts()), [])
    assert used[0] == (config.REQUEST_TIMEOUT_S, config.MAX_RETRIES)
    assert used[1:] == [(config.DRAFT_TIMEOUT_S, config.DRAFT_MAX_RETRIES)] * 2
    # Worst wait before an error stays bounded (minutes, not the 8 of before).
    assert config.DRAFT_TIMEOUT_S * (1 + config.DRAFT_MAX_RETRIES) <= 180


@pytest.mark.parametrize(
    ("urgent", "special", "expected"),
    [
        (True, False, "tutela"),
        (False, True, "tutela"),
        (True, True, "tutela"),
        (False, False, "derecho_de_peticion"),
    ],
)
def test_route_is_a_fixed_rule_applied_by_code(urgent, special, expected):
    facts = _facts().model_copy(
        update={
            "urgent_health_risk": urgent,
            "special_protection": special,
            "special_protection_group": "older_adult" if special else None,
        }
    )
    route = agent.route_case(facts)
    assert route.document_type == expected
    assert ("(adulto mayor)" in route.reason) == special
    assert ("riesgo inminente la salud o la vida" in route.reason) == urgent

    english = agent.route_reason(facts, route.document_type, "en")
    assert ("(an older adult)" in english) == special
    assert ("health or life at imminent risk" in english) == urgent


def test_route_reasons_and_protection_groups_exist_in_every_language():
    for lang in config.LANGUAGES:
        assert agent.ROUTE_REASONS[lang].keys() == agent.ROUTE_REASONS["es"].keys()
        assert agent.PROTECTION_GROUPS[lang].keys() == agent.PROTECTION_GROUPS["es"].keys()


def test_run_case_in_mock_mode():
    result = agent.run_case("La EPS no me entrega un medicamento.")
    assert isinstance(result.facts, CaseFacts)
    assert result.route.document_type in ("tutela", "derecho_de_peticion")
    assert result.queries and result.sources
    assert result.draft.title == "Acción de tutela"
    assert [m.step for m in result.metrics] == ["intake", "research", "draft", "explain"]
    assert result.explanation.summary and result.explanation.key_points
    assert result.next_steps == agent.NEXT_STEPS["es"]["tutela"]
    assert "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]" in result.to_fill


def test_find_placeholders_lists_each_one_once_in_order():
    text = "[NOMBRE], cédula [CÉDULA]. Firma: [NOMBRE] [cita eliminada: no aparece en la fuente]"
    assert verify.find_placeholders(text) == ["[NOMBRE]", "[CÉDULA]"]


@pytest.mark.parametrize(
    "deadline",
    [
        "dentro de los diez días siguientes",
        "no puede pasar de 48 horas",
        "quince (15) días siguientes a su recepción",
    ],
)
def test_next_step_deadlines_match_the_official_text(deadline):
    official = " ".join(legal.corpus_excerpts()).lower()
    written = " ".join(step for steps in agent.NEXT_STEPS["es"].values() for step in steps)
    assert deadline in written
    key = {"no puede pasar de 48 horas": "exceder de 48 horas"}.get(deadline, deadline)
    assert key in official


def test_next_steps_in_every_language_cite_the_same_numbers():
    spanish = agent.NEXT_STEPS[config.SOURCE_LANGUAGE]
    for lang in config.LANGUAGES:
        steps = agent.NEXT_STEPS[lang]
        assert steps.keys() == spanish.keys()
        for document_type, spanish_steps in spanish.items():
            assert len(steps[document_type]) == len(spanish_steps)
            for step, spanish_step in zip(steps[document_type], spanish_steps, strict=True):
                assert re.findall(r"\d+", step) == re.findall(r"\d+", spanish_step)


def test_protect_and_restore_keep_quotes_urls_and_blanks_untouched():
    text = "Firma: [NOMBRE]. En https://x.gov.co/t-1 se lee: «la salud es un derecho»."
    protected, originals = translate.protect(text)
    assert protected == "Firma: ⟦1⟧. En ⟦2⟧ se lee: ⟦3⟧."
    translated = "Signature: ⟦1⟧. At ⟦2⟧ it reads: ⟦3⟧."
    assert translate.restore(translated, originals) == (
        "Signature: [NOMBRE]. At https://x.gov.co/t-1 it reads: «la salud es un derecho»."
    )


@pytest.mark.parametrize("broken", ["Signature: ⟦1⟧.", "⟦1⟧ ⟦1⟧ ⟦2⟧", "⟦1⟧ ⟦2⟧ ⟦3⟧"])
def test_restore_fails_if_the_translation_lost_or_invented_a_token(broken):
    with pytest.raises(llm.LLMError):
        translate.restore(broken, ["[NOMBRE]", "https://x.gov.co"])


def test_only_the_model_sections_are_sent_to_translation():
    draft = agent.run_case("La EPS no me entrega un medicamento.").draft
    assert list(draft.sections) == document.MODEL_SECTIONS["tutela"]
    translated, _ = translate.run_translate_sections(draft.sections, "English")
    assert translated == draft.sections  # the mock echoes: markers and tokens round-trip


def test_sections_translation_fails_if_a_section_marker_is_lost(monkeypatch):
    monkeypatch.setattr(
        translate, "chat", lambda *a, **k: ("⟦S1⟧\nFacts only", llm.CallMetrics("t", "m", 0, 0, 0))
    )
    with pytest.raises(llm.LLMError):
        translate.run_translate_sections({"Hechos": "h", "Peticiones": "p"}, "English")


def test_explanation_translation_must_keep_every_key_point():
    spanish = ExplanationText(summary="s", key_points=["a", "b", "c"])
    with pytest.raises(llm.LLMError):  # the mock answer has only 2 key points
        translate.run_translate_explanation(spanish, "English")


def test_draft_removes_invented_urls_and_keeps_verified_ones():
    verified = Source(title="T", url="https://corteconstitucional.gov.co/t-1", snippet="s")
    text = (
        "Ver https://corteconstitucional.gov.co/t-1. "
        "También https://www.blog-falso.com/inventada y (https://otro-falso.co/x)."
    )
    body, cited = verify.remove_unverified_urls(text, [verified])

    assert "https://corteconstitucional.gov.co/t-1" in body
    assert "blog-falso" not in body and "otro-falso" not in body
    assert body.count(verify.REMOVED_URL_NOTE) == 2
    assert cited == ["https://corteconstitucional.gov.co/t-1"]


def test_mock_draft_drops_the_fake_source():
    result = agent.run_case("La EPS no me entrega un medicamento.")
    assert "blog-falso" not in result.draft.body_markdown
    assert all("blog-falso" not in url for url in result.draft.cited_urls)


def test_quotes_must_be_copied_from_a_snippet_or_the_legal_code():
    snippet = "La EPS  debe entregar\nla insulina."
    source = Source(title="T", url="https://x.gov.co", snippet=snippet)
    law = legal.corpus_excerpts()[0]
    text = f"«la eps debe entregar la insulina» «{law}» «La Corte ordenó entregarla en 48 horas»"

    body = verify.remove_unverified_quotes(text, [source])
    assert "«la eps debe entregar la insulina»" in body
    assert f"«{law}»" in body
    assert "48 horas" not in body and body.count(verify.REMOVED_QUOTE_NOTE) == 1


@pytest.mark.parametrize(
    "quote", ["«... insulina glargina ...»", "«la EPS … entregar la insulina hoy mismo»"]
)
def test_short_quotes_or_quotes_with_gaps_are_removed(quote):
    snippet = "La EPS debe entregar la insulina glargina hoy mismo al paciente."
    source = Source(title="T", url="https://x.gov.co", snippet=snippet)
    assert verify.remove_unverified_quotes(quote, [source]) == verify.REMOVED_QUOTE_NOTE


def test_quotes_match_snippets_that_lost_their_accented_letters():
    # Real shape of a Tavily snippet from a Court ruling: accented letters are dropped.
    snippet = "ACCIN DE TUTELA-Hecho superado por prestacin del servicio de salud a los NIOS"
    source = Source(title="T", url="https://x.gov.co", snippet=snippet)
    right = "«acción de tutela-hecho superado por prestación del servicio de salud a los niños»"
    assert verify.remove_unverified_quotes(right, [source]) == right
    wrong = "«acción de tutela-hecho superado por negación del servicio de salud»"
    assert verify.remove_unverified_quotes(wrong, [source]) == verify.REMOVED_QUOTE_NOTE


def test_mock_draft_drops_the_invented_quote():
    body = agent.run_case("La EPS no me entrega un medicamento.").draft.body_markdown
    assert "«la EPS no puede negar un medicamento formulado»" in body
    assert "nadie dijo" not in body
    assert "Fuente inventada" not in body  # the whole line goes, not only the quote
    assert verify.REMOVED_QUOTE_NOTE not in body


def test_private_use_notes_of_the_legal_code_never_reach_the_document():
    text = (
        "- Artículo 49 de la Constitución Política (Uso: derecho a la salud).\n"
        "  Uso: citar cuando se niega un servicio\n"
        "- Artículo 86 de la Constitución Política."
    )
    clean, _, _ = verify.check_section(text, [])
    assert "Uso:" not in clean
    assert (
        clean
        == "- Artículo 49 de la Constitución Política.\n- Artículo 86 de la Constitución Política."
    )


def test_draft_counts_the_quotes_the_filter_removed():
    draft = agent.run_case("La EPS no me entrega un medicamento.").draft
    assert draft.removed_quotes == 1  # the mock invents exactly one quote


def test_items_with_a_removed_quote_are_dropped_whole():
    note = verify.REMOVED_QUOTE_NOTE
    text = (
        "- Artículo 49 de la Constitución Política: salud.\n"
        "- En la Sentencia T-1/24\n"
        f"  (https://x.gov.co) se lee: {note}.\n"
        "- Artículo 46 de la Constitución Política: tercera edad.\n"
        "\n"
        f"Un párrafo con {note}.\n"
        "\n"
        "1. Hecho que se queda."
    )
    assert verify.drop_items_with_removed_quotes(text) == (
        "- Artículo 49 de la Constitución Política: salud.\n"
        "- Artículo 46 de la Constitución Política: tercera edad.\n"
        "\n"
        "\n"
        "1. Hecho que se queda."
    )


def test_strip_reasoning_removes_think_block():
    assert llm.strip_reasoning("<think>borrador</think>\n# Tutela") == "# Tutela"
    assert llm.strip_reasoning("# Tutela") == "# Tutela"


def _fake_research(monkeypatch, queries: list[str], results_by_query: dict[str, list[Source]]):
    """Make Super 'answer' with `queries` and the search tool return canned sources."""
    plan = SearchPlan(queries=queries)
    monkeypatch.setattr(agent, "chat_json", lambda *a, **k: (plan, []))
    searched: list[str] = []

    def fake_search(query):
        searched.append(query)
        return results_by_query.get(query, [])

    monkeypatch.setattr(agent, "search_web", fake_search)
    return searched


def _route() -> RouteDecision:
    return RouteDecision(document_type="tutela", reason="x")


def _facts() -> CaseFacts:
    return CaseFacts(
        problem_type="medicine_denied",
        events_summary="x",
        urgent_health_risk=True,
        special_protection=False,
        writer_is_affected_person=True,
    )


def test_intake_contradiction_is_settled_by_code(monkeypatch):
    answer = _facts().model_copy(update={"writer_relationship": "hija"})
    monkeypatch.setattr(agent, "chat_json", lambda *a, **k: (answer, []))
    facts, _ = agent.run_intake("Mi hija tiene 5 años...")
    assert facts.writer_is_affected_person is False  # someone writes on her behalf


def test_intake_requires_the_model_to_say_who_writes():
    data = {"problem_type": "other", "events_summary": "x", "urgent_health_risk": False}
    with pytest.raises(ValidationError):
        CaseFacts.model_validate({**data, "special_protection": False})


def test_mock_intake_detects_agencia_oficiosa():
    facts, _ = agent.run_intake("Mi papá de 72 años no recibe su insulina.")
    assert facts.writer_is_affected_person is False
    assert facts.writer_relationship


def test_research_runs_at_most_the_configured_searches(monkeypatch):
    searched = _fake_research(monkeypatch, ["q1", "q2", "q3", "q4", "q5"], {})
    agent.run_research(_facts(), _route())
    assert searched == ["q1", "q2", "q3"]


def test_research_removes_duplicate_urls(monkeypatch):
    same = Source(title="T", url="https://corteconstitucional.gov.co/a", snippet="s")
    other = Source(title="U", url="https://secretariasenado.gov.co/b", snippet="s")
    _fake_research(monkeypatch, ["q1", "q2"], {"q1": [same], "q2": [same, other]})

    _, sources, _ = agent.run_research(_facts(), _route())
    assert [s.url for s in sources] == [same.url, other.url]


@pytest.mark.parametrize("text", ["", "   ", "x" * (config.MAX_INPUT_CHARS + 1)])
def test_validate_input_rejects_bad_descriptions(text):
    with pytest.raises(llm.LLMError):
        agent.validate_input(text)
