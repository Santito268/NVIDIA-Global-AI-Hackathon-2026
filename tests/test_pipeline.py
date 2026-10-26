"""Pipeline tests. They run in mock mode: no network, no credits."""

import pytest

from src import agent, config, llm
from src.schemas import CaseFacts, RouteDecision


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


def test_run_case_in_mock_mode():
    result = agent.run_case("La EPS no me entrega un medicamento.")
    assert isinstance(result.facts, CaseFacts)
    assert result.route.document_type in ("tutela", "derecho_de_peticion")
    assert [m.step for m in result.metrics] == ["intake", "route"]


@pytest.mark.parametrize("text", ["", "   ", "x" * (config.MAX_INPUT_CHARS + 1)])
def test_validate_input_rejects_bad_descriptions(text):
    with pytest.raises(llm.LLMError):
        agent.validate_input(text)
