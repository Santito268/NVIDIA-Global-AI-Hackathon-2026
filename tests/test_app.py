"""Interface tests with Streamlit's AppTest. Mock mode: no network, no credits."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import agent, config
from src.llm import LLMError
from src.ui_text import DOCUMENT_NAMES, UI_TEXT

TEXT = UI_TEXT["es"]
APP_PATH = Path(__file__).resolve().parent.parent / "app.py"


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")


def _app() -> AppTest:
    at = AppTest.from_file(str(APP_PATH), default_timeout=60)
    return at.run()


def _all_text(at: AppTest) -> str:
    parts = [m.value for m in at.markdown] + [c.value for c in at.caption]
    parts += (
        [e.value for e in at.error] + [w.value for w in at.warning] + [i.value for i in at.info]
    )
    return "\n".join(parts)


def test_sample_case_produces_the_four_tabs():
    at = _app()
    at.button(key="sample").click().run()
    assert "insulina" in at.text_area(key="description").value
    at.button(key="generate").click().run()

    assert not at.exception
    assert [tab.label for tab in at.tabs] == [
        TEXT["tab_explanation"],
        TEXT["tab_document"],
        TEXT["tab_sources"],
        TEXT["tab_metrics"],
    ]
    text = _all_text(at)
    assert "# ACCIÓN DE TUTELA" in text
    assert "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]" in text
    assert "Fuente de ejemplo" in text  # Tavily snippets are shown
    assert len(at.dataframe) == 1


def test_empty_description_shows_an_error_and_spends_nothing():
    at = _app()
    at.button(key="generate").click().run()
    assert at.error[0].value == TEXT["empty_input"]
    assert at.session_state.cases_run == 0


def test_generate_is_disabled_after_the_session_limit():
    at = _app()
    at.session_state.cases_run = config.MAX_CASES_PER_SESSION
    at.run()
    assert at.button(key="generate").disabled
    assert str(config.MAX_CASES_PER_SESSION) in at.warning[-1].value


def test_generate_is_disabled_when_the_daily_limit_is_reached(monkeypatch):
    monkeypatch.setattr(config, "MAX_CASES_PER_DAY", 0)
    at = _app()
    assert at.button(key="generate").disabled
    assert TEXT["daily_limit_reached"] in [w.value for w in at.warning]


def test_pipeline_error_is_shown_without_crashing(monkeypatch):
    def failing_run_case(*args, **kwargs):
        raise LLMError("The AI service took too long to answer.")

    monkeypatch.setattr(agent, "run_case", failing_run_case)
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()

    assert not at.exception
    assert TEXT["error_message"] in [e.value for e in at.error]
    assert at.session_state.result is None


def test_every_language_has_all_the_interface_texts():
    assert set(UI_TEXT) == set(config.LANGUAGES)
    for texts in UI_TEXT.values():
        assert texts.keys() == TEXT.keys()


def test_page_starts_in_spanish():
    at = _app()
    assert at.segmented_control(key="language").value == "es"
    assert at.button(key="generate").label == TEXT["generate_button"]


def _count_translations(monkeypatch) -> list[str]:
    """Wrap both translation functions so a test can count the calls to Nano."""
    calls: list[str] = []
    for name in ("run_translate_explanation", "run_translate_document"):
        real = getattr(agent, name)

        def counting(text, language, real=real, name=name):
            calls.append(name)
            return real(text, language)

        monkeypatch.setattr(agent, name, counting)
    return calls


def test_switching_to_english_translates_the_results_once(monkeypatch):
    calls = _count_translations(monkeypatch)
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    assert calls == []  # Spanish: nothing to translate

    at.segmented_control(key="language").set_value("en").run()
    english = UI_TEXT["en"]
    assert at.button(key="generate").label == english["generate_button"]
    assert [tab.label for tab in at.tabs][0] == english["tab_explanation"]
    assert english["translation_notice"] in [i.value for i in at.info]
    text = _all_text(at)
    assert "[Example translation]" in text
    assert calls == ["run_translate_explanation", "run_translate_document"]

    at.segmented_control(key="language").set_value("es").run()
    at.segmented_control(key="language").set_value("en").run()
    assert len(calls) == 2  # cached: switching back and forth costs nothing


def test_english_headings_and_next_steps_come_from_code_not_from_the_model():
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    at.segmented_control(key="language").set_value("en").run()
    text = _all_text(at)
    assert f"**{UI_TEXT['en']['document_type']}: {DOCUMENT_NAMES['en']['tutela']}.**" in text
    assert agent.NEXT_STEPS["en"]["tutela"][3] in text
    assert "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]" in text  # blanks stay in Spanish
    assert "Documento recomendado" not in text


def test_failed_translation_falls_back_to_spanish_and_is_not_retried(monkeypatch):
    calls = []

    def failing_translate(text, language):
        calls.append(language)
        raise LLMError("The translation changed protected text.")

    monkeypatch.setattr(agent, "run_translate_explanation", failing_translate)
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    at.segmented_control(key="language").set_value("en").run()

    assert not at.exception
    assert UI_TEXT["en"]["translation_error"] in [w.value for w in at.warning]
    assert UI_TEXT["en"]["translation_notice"] not in [i.value for i in at.info]
    assert "# ACCIÓN DE TUTELA" in _all_text(at)
    at.segmented_control(key="language").set_value("es").run()
    at.segmented_control(key="language").set_value("en").run()
    assert len(calls) == 1
