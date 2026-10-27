"""Streamlit interface: describe a problem with your EPS, get a ready-to-file document."""

import threading
from datetime import date
from pathlib import Path

import streamlit as st

from src import config
from src.agent import (
    NEXT_STEPS,
    CaseResult,
    run_case,
    run_translate_document,
    run_translate_explanation,
)
from src.llm import LLMError
from src.schemas import ExplanationText
from src.tools import SearchError
from src.ui_text import DOCUMENT_NAMES, UI_TEXT

SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "samples" / "caso_01.txt"


def language() -> str:
    """Chosen interface language; Spanish if the button is deselected."""
    return st.session_state.get("language") or config.SOURCE_LANGUAGE


def t(key: str, lang: str | None = None, **values) -> str:
    """Interface text in the chosen language (or in `lang`)."""
    return UI_TEXT[lang or language()][key].format(**values)


def init_state() -> None:
    """Values that must survive Streamlit's reruns (a rerun happens on every click)."""
    st.session_state.setdefault("description", "")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("cases_run", 0)
    # {language: {"explanation": ExplanationText, "document": str}, or None if it failed}
    st.session_state.setdefault("translations", {})
    st.session_state.setdefault("translation_metrics", [])


@st.cache_resource
def daily_usage() -> dict:
    """One counter shared by every visitor of this server (session limits reset on reload)."""
    return {"day": None, "cases": 0, "lock": threading.Lock()}


def daily_cases_left() -> int:
    """Cases the whole app can still run today; the count restarts every day."""
    usage = daily_usage()
    with usage["lock"]:
        if usage["day"] != date.today():
            usage["day"], usage["cases"] = date.today(), 0
        return config.MAX_CASES_PER_DAY - usage["cases"]


def count_daily_case() -> None:
    usage = daily_usage()
    with usage["lock"]:
        usage["cases"] += 1


def load_sample() -> None:
    st.session_state.description = SAMPLE_PATH.read_text(encoding="utf-8")


def generate(description: str) -> None:
    """Run the pipeline once, showing progress, and keep the result in the session."""
    st.session_state.cases_run += 1  # count before calling: a failed case also spends credits
    count_daily_case()
    with st.status(t("status_running"), expanded=True) as status:
        try:
            result = run_case(description, on_step=lambda step: st.write(t(f"step_{step}")))
        except (LLMError, SearchError) as error:
            status.update(label=t("status_error"), state="error")
            st.error(t("error_message"))
            st.caption(str(error))
            return
        status.update(label=t("status_done"), state="complete", expanded=False)
    st.session_state.result = result
    st.session_state.translations = {}  # translations belong to the previous case


def explanation_markdown(result: CaseResult, lang: str, text: ExplanationText) -> str:
    """The explanation tab. Headings, document name, blanks and next steps come from code in
    every language; only `text` (reason, summary, key points) is ever translated by Nano."""
    document_type = result.route.document_type
    name = DOCUMENT_NAMES[lang][document_type]
    key_points = "\n".join(f"- {point}" for point in text.key_points)
    to_fill = " ".join(f"`{placeholder}`" for placeholder in result.to_fill)
    steps = NEXT_STEPS[lang][document_type]
    next_steps = "\n".join(f"{i}. {step}" for i, step in enumerate(steps, 1))
    return (
        f"**{t('document_type', lang)}: {name}.** {text.reason}\n\n"
        f"### {t('summary', lang)}\n{text.summary}\n\n"
        f"### {t('key_points', lang)}\n{key_points}\n\n"
        f"### {t('to_fill', lang)}\n{to_fill}\n\n"
        f"### {t('next_steps', lang)}\n{next_steps}"
    )


def translate(result: CaseResult, spanish: ExplanationText, lang: str) -> dict | None:
    """Translate the case texts and the document once; None if the translation failed."""
    target = config.LANGUAGES[lang]
    try:
        with st.spinner(t("translating")):
            explanation, metrics = run_translate_explanation(spanish, target)
            st.session_state.translation_metrics += metrics
            document, metrics = run_translate_document(result.draft.body_markdown, target)
            st.session_state.translation_metrics += metrics
    except LLMError:
        return None
    return {"explanation": explanation, "document": document}


def localized(result: CaseResult) -> dict[str, str]:
    """Explanation and document in the chosen language; translated once and then cached."""
    spanish = ExplanationText(
        reason=result.route.reason,
        summary=result.explanation.summary,
        key_points=result.explanation.key_points,
    )
    lang = language()
    if lang != config.SOURCE_LANGUAGE:
        if lang not in st.session_state.translations:
            # A failure is cached too, so later clicks do not spend credits again.
            st.session_state.translations[lang] = translate(result, spanish, lang)
        translated = st.session_state.translations[lang]
        if translated:
            return {
                "explanation": explanation_markdown(result, lang, translated["explanation"]),
                "document": translated["document"],
            }
        st.warning(t("translation_error"))
    es = config.SOURCE_LANGUAGE
    return {
        "explanation": explanation_markdown(result, es, spanish),
        "document": result.draft.body_markdown,
    }


def show_explanation(result: CaseResult, texts: dict[str, str]) -> None:
    st.markdown(texts["explanation"])


def show_document(result: CaseResult, texts: dict[str, str]) -> None:
    # The download is always the Spanish original: it is the version to file.
    st.download_button(
        t("download"),
        data=result.draft.body_markdown,
        file_name=f"{result.route.document_type}.md",
        mime="text/markdown",
    )
    if st.session_state.translations.get(language()):  # only when a translation is shown
        st.info(t("translation_notice"))
    with st.container(border=True):
        st.markdown(texts["document"])


def show_sources(result: CaseResult, texts: dict[str, str]) -> None:
    if not result.sources:
        st.write(t("no_sources"))
        return
    st.caption(t("sources_intro"))
    for source in result.sources:
        cited = f" — ✅ {t('cited')}" if source.url in result.draft.cited_urls else ""
        st.markdown(f"**{source.title}**{cited}  \n{source.url}")
        st.caption(source.snippet)


def show_metrics(result: CaseResult, texts: dict[str, str]) -> None:
    st.caption(t("metrics_intro"))
    metrics = result.metrics + st.session_state.translation_metrics
    rows = [
        {
            "step": m.step,
            "model": m.model,
            "prompt_tokens": m.prompt_tokens,
            "completion_tokens": m.completion_tokens,
            "latency_s": round(m.latency_s, 2),
        }
        for m in metrics
    ]
    st.dataframe(rows, hide_index=True)
    tokens = sum(m.prompt_tokens + m.completion_tokens for m in metrics)
    st.write(t("total", tokens=tokens, seconds=sum(m.latency_s for m in metrics)))


def show_result(result: CaseResult) -> None:
    texts = localized(result)
    tabs = st.tabs([t("tab_explanation"), t("tab_document"), t("tab_sources"), t("tab_metrics")])
    for tab, show in zip(
        tabs, [show_explanation, show_document, show_sources, show_metrics], strict=True
    ):
        with tab:
            show(result, texts)


def main() -> None:
    init_state()
    st.set_page_config(page_title=t("title"), page_icon="⚖️")

    st.segmented_control(
        "Idioma / Language",
        options=list(config.LANGUAGES),
        format_func=config.LANGUAGES.get,
        default=config.SOURCE_LANGUAGE,
        key="language",
        label_visibility="collapsed",
    )
    st.title(t("title"))
    st.write(t("tagline"))
    st.warning(t("legal_notice"))
    st.info(t("privacy_notice"))
    if config.LLM_MODE == "mock":
        st.caption(t("mock_notice"))

    st.button(t("sample_button"), key="sample", on_click=load_sample)
    if t("input_language_note"):
        st.caption(t("input_language_note"))
    st.text_area(
        t("input_label"),
        key="description",
        max_chars=config.MAX_INPUT_CHARS,
        height=180,
        placeholder=t("input_placeholder"),
    )

    limit = config.MAX_CASES_PER_SESSION
    left = limit - st.session_state.cases_run
    if left <= 0:
        st.warning(t("limit_reached", limit=limit))
    elif daily_cases_left() <= 0:
        st.warning(t("daily_limit_reached"))
    else:
        st.caption(t("cases_left", left=left, limit=limit))
    blocked = left <= 0 or daily_cases_left() <= 0
    if st.button(t("generate_button"), key="generate", type="primary", disabled=blocked):
        description = st.session_state.description.strip()
        if daily_cases_left() <= 0:  # another visitor may have used the last case meanwhile
            st.warning(t("daily_limit_reached"))
        elif description:
            generate(description)
        else:
            st.error(t("empty_input"))

    if st.session_state.result:
        show_result(st.session_state.result)


main()
