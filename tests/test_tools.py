"""Web search tool tests. Tavily is faked: no network, no credits."""

import pytest
from tavily import UsageLimitExceededError

from src import config, tools


class FakeTavily:
    """Stands in for TavilyClient and remembers what it was asked."""

    calls: list[dict] = []
    response: dict = {}
    error: Exception | None = None

    def __init__(self, api_key):
        pass

    def search(self, query, **kwargs):
        FakeTavily.calls.append({"query": query, **kwargs})
        if FakeTavily.error:
            raise FakeTavily.error
        return FakeTavily.response


@pytest.fixture
def fake_tavily(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "live")
    monkeypatch.setattr(tools, "TavilyClient", FakeTavily)
    FakeTavily.calls, FakeTavily.response, FakeTavily.error = [], {"results": []}, None
    return FakeTavily


def test_search_maps_results_and_trims_snippets(fake_tavily):
    fake_tavily.response = {
        "results": [
            {
                "title": "Sentencia",
                "url": "https://corteconstitucional.gov.co/x",
                "content": "a" * 900,
            },
            {"title": "Sin URL", "url": "", "content": "ignored"},
        ]
    }
    sources = tools.search_web("tutela medicamentos")

    assert len(sources) == 1
    assert sources[0].url == "https://corteconstitucional.gov.co/x"
    assert len(sources[0].snippet) == config.MAX_SNIPPET_CHARS


def test_search_uses_basic_depth_and_official_domains(fake_tavily):
    tools.search_web("tutela medicamentos")

    call = fake_tavily.calls[0]
    assert call["search_depth"] == "basic"
    assert call["include_domains"] == config.TRUSTED_DOMAINS


def test_usage_limit_becomes_friendly_error(fake_tavily):
    fake_tavily.error = UsageLimitExceededError("limit")
    with pytest.raises(tools.SearchError, match="used up"):
        tools.search_web("tutela medicamentos")


def test_mock_mode_never_calls_tavily(fake_tavily, monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")
    sources = tools.search_web("tutela medicamentos")

    assert sources
    assert fake_tavily.calls == []
