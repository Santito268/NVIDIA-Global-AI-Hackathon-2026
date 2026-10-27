"""Mini legal code tests: structure and how the draft step uses it (offline)."""

from src import agent, config, legal


def test_every_article_is_complete_and_points_to_a_known_source():
    corpus = legal.load_corpus()
    for entry in corpus["articles"]:
        assert entry["source"] in corpus["sources"]
        assert entry["title"] and entry["use"] and entry["excerpts"]


def test_no_duplicate_articles():
    keys = [(e["source"], e["article"]) for e in legal.load_corpus()["articles"]]
    assert len(keys) == len(set(keys))


def test_corpus_urls_are_official():
    assert all(url.startswith("https://www.funcionpublica.gov.co/") for url in legal.corpus_urls())


def test_prompt_block_mentions_key_articles():
    block = legal.format_for_prompt()
    assert "## Constitución Política de Colombia de 1991" in block
    assert "- Artículo 86: Acción de tutela" in block
    assert "- Artículo 10: Legitimidad e interés (agencia oficiosa)" in block


def test_corpus_url_survives_the_unverified_url_filter(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")
    url = next(iter(legal.corpus_urls()))
    body, cited = agent.remove_unverified_urls(f"Ver {url}", [])
    assert url in body
    assert cited == [url]
