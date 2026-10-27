"""Tests for the evaluation checks and runner. Mock mode: no network, no credits."""

import pytest

from evals import checks, run_eval
from src import agent, config
from src.schemas import Source


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")


def test_allowed_norms_come_from_the_legal_code():
    assert {"Decreto 2591 de 1991", "Ley 1755 de 2015", "Ley 1751 de 2015"} <= (
        checks.allowed_norms()
    )


def test_unknown_norms_flags_laws_outside_the_legal_code():
    text = "Según la Ley 1751 de 2015, el Decreto 2.591 de 1991 y la Ley 100 de 1993."
    assert checks.unknown_norms(text) == ["Ley 100 de 1993"]


def test_forbidden_words_are_found():
    text = "Condenar en costas. Artículo 49 CN. Agente officioso. (Uso: nota privada)"
    assert checks.forbidden_words(text) == ["costas", "CN", "officioso", "nota de Uso"]
    assert checks.forbidden_words("Artículo 49 de la Constitución Política (C.P.).") == []


def test_mock_case_is_graded():
    result = agent.run_case("La EPS no me entrega un medicamento.")
    expected = {"document_type": "tutela", "writer_is_affected_person": False}
    grade = checks.check_case(result, expected | {"special_protection": True})
    assert checks.passed(grade)
    assert grade["rulings_cited"] == 1  # the mock's only verified ruling

    grade = checks.check_case(result, expected | {"special_protection": False})
    assert not checks.passed(grade)


def test_every_case_has_an_id_a_description_and_expectations():
    cases = run_eval.load_cases([])
    assert len(cases) == len({case["id"] for case in cases}) >= 10
    for case in cases:
        assert case["description"].strip()
        assert set(case["expected"]) == {
            "document_type",
            "writer_is_affected_person",
            "special_protection",
        }


def test_cached_search_reuses_saved_results(monkeypatch):
    calls = []

    def fake_search(query, max_results=3):
        calls.append(query)
        return [Source(title="T", url="https://x.gov.co", snippet="s")]

    monkeypatch.setattr(run_eval, "search_web", fake_search)
    cache: dict = {}
    search = run_eval.cached_search(cache)
    assert search("tutela salud") == search("tutela salud")
    assert calls == ["tutela salud"]
    assert cache["tutela salud"][0]["url"] == "https://x.gov.co"


def test_summary_counts_passes_and_errors():
    grades = run_eval.evaluate(run_eval.load_cases(["01_insulina_adulto_mayor"]))
    grades.append({"id": "x", "error": "timeout", "passed": False})
    summary = run_eval.summary_markdown(grades)
    assert summary.startswith("**1/2 cases pass every rule.**")
    assert "| x | error: timeout |" in summary
