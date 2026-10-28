"""Interface tests with Streamlit's AppTest. Mock mode: no network, no credits."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from src import agent, config, translate
from src.document import DOCUMENT_NAMES
from src.llm import LLMError
from src.ui_text import UI_TEXT

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


def test_examples_are_shown_in_english_but_processed_in_spanish(monkeypatch):
    received = []
    real_run_case = agent.run_case

    def recording_run_case(description, **kwargs):
        received.append(description)
        return real_run_case(description, **kwargs)

    monkeypatch.setattr(agent, "run_case", recording_run_case)
    at = _app()
    at.button(key="sample_2").click().run()
    assert "Mi hija" in at.text_area(key="description").value

    at.segmented_control(key="language").set_value("en").run()
    assert "My daughter" in at.text_area(key="description").value  # follows the language
    at.button(key="generate").click().run()
    assert received[0].startswith("Mi hija")  # the pipeline gets the Spanish original

    at.segmented_control(key="language").set_value("es").run()
    assert "Mi hija" in at.text_area(key="description").value


@pytest.mark.parametrize("fails", [False, True])
def test_widgets_are_released_after_a_case_and_it_never_runs_twice(monkeypatch, fails):
    calls = []
    real_run_case = agent.run_case

    def counting_run_case(description, **kwargs):
        calls.append(description)
        if fails:
            raise LLMError("The model took too long to answer.", "timeout")
        return real_run_case(description, **kwargs)

    monkeypatch.setattr(agent, "run_case", counting_run_case)
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    assert len(calls) == 1
    assert not at.session_state.running and at.session_state.pending is None
    assert not at.segmented_control(key="language").disabled
    assert not at.text_area(key="description").disabled
    assert (TEXT["error_timeout"] in [c.value for c in at.caption]) == fails

    at.segmented_control(key="language").set_value("en").run()  # any later click
    assert len(calls) == 1  # the case is not run again


def test_every_example_has_a_hand_written_copy_in_every_language():
    samples = APP_PATH.parent / "data" / "samples"
    for name in ("caso_01", "caso_02", "caso_03"):
        for lang in config.LANGUAGES:
            suffix = "" if lang == config.SOURCE_LANGUAGE else f"_{lang}"
            assert (samples / f"{name}{suffix}.txt").read_text(encoding="utf-8").strip()


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
    for name in ("run_translate_explanation", "run_translate_sections"):
        real = getattr(translate, name)

        def counting(text, language, real=real, name=name):
            calls.append(name)
            return real(text, language)

        monkeypatch.setattr(translate, name, counting)
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
    assert calls == ["run_translate_explanation", "run_translate_sections"]

    at.segmented_control(key="language").set_value("es").run()
    at.segmented_control(key="language").set_value("en").run()
    assert len(calls) == 2  # cached: switching back and forth costs nothing


def test_english_headings_and_next_steps_come_from_code_not_from_the_model():
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    at.segmented_control(key="language").set_value("en").run()
    text = _all_text(at)
    assert f"<b>{UI_TEXT['en']['document_type']}: {DOCUMENT_NAMES['en']['tutela']}.</b>" in text
    assert agent.NEXT_STEPS["en"]["tutela"][3] in text
    assert "A tutela is the right document because" in text  # hand-written reason
    assert "## Parties" in text and "# ACCIÓN DE TUTELA (constitutional" in text
    assert "[REASON THE PATIENT CANNOT ACT]" in text  # blanks hand-written in English
    assert "[NOMBRE]" not in text and "Documento recomendado" not in text
    # The download is still the Spanish original.
    assert at.session_state.result.draft.body_markdown.startswith("# ACCIÓN DE TUTELA\n")


def test_errors_are_shown_in_the_chosen_language(monkeypatch):
    def failing_run_case(*args, **kwargs):
        raise LLMError("The model took too long to answer.", "timeout")

    monkeypatch.setattr(agent, "run_case", failing_run_case)
    at = _app()
    at.button(key="sample").click().run()
    at.button(key="generate").click().run()
    assert TEXT["error_timeout"] in [c.value for c in at.caption]


def test_failed_translation_falls_back_to_spanish_and_is_not_retried(monkeypatch):
    calls = []

    def failing_translate(text, language):
        calls.append(language)
        raise LLMError("The translation changed protected text.")

    monkeypatch.setattr(translate, "run_translate_explanation", failing_translate)
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


def _run_case_spy(monkeypatch) -> list[str]:
    """Record what the app sends to the pipeline (and still run it in mock mode)."""
    received = []
    real_run_case = agent.run_case

    def recording_run_case(description, **kwargs):
        received.append(description)
        return real_run_case(description, **kwargs)

    monkeypatch.setattr(agent, "run_case", recording_run_case)
    return received


def test_an_edited_example_is_sent_as_the_user_wrote_it(monkeypatch):
    received = _run_case_spy(monkeypatch)
    at = _app()
    at.button(key="sample").click().run()
    edited = at.text_area(key="description").value + " Además, vivo en una zona rural."
    at.text_area(key="description").set_value(edited).run()
    at.button(key="generate").click().run()
    assert received == [edited]


def test_too_short_text_is_rejected_without_using_a_case(monkeypatch):
    received = _run_case_spy(monkeypatch)
    at = _app()
    at.text_area(key="description").set_value("hola").run()
    at.button(key="generate").click().run()
    assert TEXT["error_too_short"] in [w.value for w in at.warning]
    assert received == [] and at.session_state.cases_run == 0


def test_english_text_on_the_spanish_page_asks_to_switch_language(monkeypatch):
    received = _run_case_spy(monkeypatch)
    at = _app()
    english = "My mother is 70 and the EPS has not given her the insulin for a month"
    at.text_area(key="description").set_value(english).run()
    at.button(key="generate").click().run()
    assert TEXT["error_wrong_language"] in [w.value for w in at.warning]
    assert received == [] and at.session_state.cases_run == 0

    at.segmented_control(key="language").set_value("en").run()
    at.button(key="generate").click().run()
    assert received == [english]  # accepted on the English page
    assert at.session_state.result is not None


def test_off_topic_text_shows_a_notice_and_no_document(monkeypatch):
    def off_topic_run_case(*args, **kwargs):
        raise LLMError("This text is not a problem with an EPS.", "off_topic")

    monkeypatch.setattr(agent, "run_case", off_topic_run_case)
    at = _app()
    at.text_area(key="description").set_value("Dame una receta de arepas con queso").run()
    at.button(key="generate").click().run()

    assert not at.exception
    assert TEXT["error_off_topic"] in [w.value for w in at.warning]
    assert TEXT["error_message"] not in [e.value for e in at.error]
    assert at.session_state.result is None
    assert at.session_state.cases_run == 1  # the intake call was spent, so it counts


def test_every_error_code_has_a_text_in_every_language():
    codes = {"empty", "too_long", "too_short", "wrong_language", "off_topic", "invalid"}
    for lang in config.LANGUAGES:
        assert all(UI_TEXT[lang][f"error_{code}"] for code in codes)
