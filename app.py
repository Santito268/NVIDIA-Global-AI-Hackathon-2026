"""Streamlit interface: describe a problem with your EPS, get a ready-to-file document."""

from pathlib import Path

import streamlit as st

from src import config
from src.agent import CaseResult, run_case, run_translate
from src.llm import LLMError
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
    st.session_state.setdefault("translations", {})  # {language: {"explanation", "document"}}
    st.session_state.setdefault("translation_metrics", [])


def load_sample() -> None:
    st.session_state.description = SAMPLE_PATH.read_text(encoding="utf-8")


def generate(description: str) -> None:
    """Run the pipeline once, showing progress, and keep the result in the session."""
    st.session_state.cases_run += 1  # count before calling: a failed case also spends credits
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


def explanation_markdown(result: CaseResult) -> str:
    """The explanation tab in Spanish, as one Markdown text (so it can be translated whole)."""
    es = config.SOURCE_LANGUAGE
    name = DOCUMENT_NAMES[es][result.route.document_type]
    key_points = "\n".join(f"- {point}" for point in result.explanation.key_points)
    to_fill = " ".join(f"`{placeholder}`" for placeholder in result.to_fill)
    next_steps = "\n".join(f"{i}. {step}" for i, step in enumerate(result.next_steps, 1))
    return (
        f"**{t('document_type', es)}: {name}.** {result.route.reason}\n\n"
        f"### {t('summary', es)}\n{result.explanation.summary}\n\n"
        f"### {t('key_points', es)}\n{key_points}\n\n"
        f"### {t('to_fill', es)}\n{to_fill}\n\n"
        f"### {t('next_steps', es)}\n{next_steps}"
    )


def localized(result: CaseResult) -> dict[str, str]:
    """Explanation and document in the chosen language; translated once and then cached."""
    spanish = {"explanation": explanation_markdown(result), "document": result.draft.body_markdown}
    lang = language()
    if lang == config.SOURCE_LANGUAGE:
        return spanish
    if lang not in st.session_state.translations:
        target = config.LANGUAGES[lang]
        try:
            with st.spinner(t("translating")):
                translated = {}
                for part, text in spanish.items():
                    translated[part], metrics = run_translate(text, target)
                    st.session_state.translation_metrics += metrics
        except LLMError:
            st.warning(t("translation_error"))
            return spanish
        st.session_state.translations[lang] = translated
    return st.session_state.translations[lang]


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
    if language() != config.SOURCE_LANGUAGE:
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
    else:
        st.caption(t("cases_left", left=left, limit=limit))
    if st.button(t("generate_button"), key="generate", type="primary", disabled=left <= 0):
        description = st.session_state.description.strip()
        if description:
            generate(description)
        else:
            st.error(t("empty_input"))

    if st.session_state.result:
        show_result(st.session_state.result)


main()
