"""Pipeline tests. They run in mock mode: no network, no credits."""

from types import SimpleNamespace

import pytest

from src import agent, config, llm
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
    assert [m.step for m in result.metrics] == ["intake", "route", "research"]


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
    )


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
