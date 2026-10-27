"""Pipeline tests. They run in mock mode: no network, no credits."""

from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from src import agent, config, legal, llm
from src.schemas import CaseFacts, RouteDecision, SearchPlan, Source


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
    monkeypatch.setattr(llm, "_client", lambda: fake_client)

    llm.chat([], "some-model", "intake", thinking=False)
    assert sent["extra_body"] == {"chat_template_kwargs": {"enable_thinking": False}}


def test_run_case_in_mock_mode():
    result = agent.run_case("La EPS no me entrega un medicamento.")
    assert isinstance(result.facts, CaseFacts)
    assert result.route.document_type in ("tutela", "derecho_de_peticion")
    assert result.queries and result.sources
    assert result.draft.title == "Acción de tutela"
    assert [m.step for m in result.metrics] == ["intake", "route", "research", "draft", "explain"]
    assert result.explanation.summary and result.explanation.key_points
    assert result.next_steps == agent.NEXT_STEPS["tutela"]
    assert "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]" in result.to_fill


def test_find_placeholders_lists_each_one_once_in_order():
    text = "[NOMBRE], cédula [CÉDULA]. Firma: [NOMBRE] [cita eliminada: no aparece en la fuente]"
    assert agent.find_placeholders(text) == ["[NOMBRE]", "[CÉDULA]"]


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
    written = " ".join(step for steps in agent.NEXT_STEPS.values() for step in steps)
    assert deadline in written
    key = {"no puede pasar de 48 horas": "exceder de 48 horas"}.get(deadline, deadline)
    assert key in official


def test_draft_removes_invented_urls_and_keeps_verified_ones():
    verified = Source(title="T", url="https://corteconstitucional.gov.co/t-1", snippet="s")
    text = (
        "Ver https://corteconstitucional.gov.co/t-1. "
        "También https://www.blog-falso.com/inventada y (https://otro-falso.co/x)."
    )
    body, cited = agent.remove_unverified_urls(text, [verified])

    assert "https://corteconstitucional.gov.co/t-1" in body
    assert "blog-falso" not in body and "otro-falso" not in body
    assert body.count(agent.REMOVED_URL_NOTE) == 2
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

    body = agent.remove_unverified_quotes(text, [source])
    assert "«la eps debe entregar la insulina»" in body
    assert f"«{law}»" in body
    assert "48 horas" not in body and body.count(agent.REMOVED_QUOTE_NOTE) == 1


def test_mock_draft_drops_the_invented_quote():
    body = agent.run_case("La EPS no me entrega un medicamento.").draft.body_markdown
    assert "«la EPS no puede negar un medicamento formulado»" in body
    assert "nadie dijo" not in body


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
