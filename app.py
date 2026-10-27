"""Streamlit interface: describe a problem with your EPS, get a ready-to-file document."""

from pathlib import Path

import streamlit as st

from src import config
from src.agent import CaseResult, run_case
from src.llm import LLMError
from src.tools import SearchError
from src.ui_text import DOCUMENT_NAMES, UI_TEXT

SAMPLE_PATH = Path(__file__).resolve().parent / "data" / "samples" / "caso_01.txt"
LANGUAGE = "es"


def t(key: str, **values) -> str:
    """Interface text in the current language."""
    return UI_TEXT[LANGUAGE][key].format(**values)


def init_state() -> None:
    """Values that must survive Streamlit's reruns (a rerun happens on every click)."""
    st.session_state.setdefault("description", "")
    st.session_state.setdefault("result", None)
    st.session_state.setdefault("cases_run", 0)


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


def show_explanation(result: CaseResult) -> None:
    name = DOCUMENT_NAMES[LANGUAGE][result.route.document_type]
    st.info(f"**{t('document_type')}: {name}.** {result.route.reason}")
    st.subheader(t("summary"))
    st.write(result.explanation.summary)
    st.subheader(t("key_points"))
    st.markdown("\n".join(f"- {point}" for point in result.explanation.key_points))
    st.subheader(t("to_fill"))
    st.markdown(" ".join(f"`{placeholder}`" for placeholder in result.to_fill))
    st.subheader(t("next_steps"))
    st.markdown("\n".join(f"{i}. {step}" for i, step in enumerate(result.next_steps, 1)))


def show_document(result: CaseResult) -> None:
    st.download_button(
        t("download"),
        data=result.draft.body_markdown,
        file_name=f"{result.route.document_type}.md",
        mime="text/markdown",
    )
    with st.container(border=True):
        st.markdown(result.draft.body_markdown)


def show_sources(result: CaseResult) -> None:
    if not result.sources:
        st.write(t("no_sources"))
        return
    st.caption(t("sources_intro"))
    for source in result.sources:
        cited = f" — ✅ {t('cited')}" if source.url in result.draft.cited_urls else ""
        st.markdown(f"**{source.title}**{cited}  \n{source.url}")
        st.caption(source.snippet)


def show_metrics(result: CaseResult) -> None:
    st.caption(t("metrics_intro"))
    rows = [
        {
            "step": m.step,
            "model": m.model,
            "prompt_tokens": m.prompt_tokens,
            "completion_tokens": m.completion_tokens,
            "latency_s": round(m.latency_s, 2),
        }
        for m in result.metrics
    ]
    st.dataframe(rows, hide_index=True)
    tokens = sum(m.prompt_tokens + m.completion_tokens for m in result.metrics)
    st.write(t("total", tokens=tokens, seconds=sum(m.latency_s for m in result.metrics)))


def show_result(result: CaseResult) -> None:
    tabs = st.tabs([t("tab_explanation"), t("tab_document"), t("tab_sources"), t("tab_metrics")])
    for tab, show in zip(
        tabs, [show_explanation, show_document, show_sources, show_metrics], strict=True
    ):
        with tab:
            show(result)


def main() -> None:
    st.set_page_config(page_title=t("title"), page_icon="⚖️")
    init_state()

    st.title(t("title"))
    st.write(t("tagline"))
    st.warning(t("legal_notice"))
    st.info(t("privacy_notice"))
    if config.LLM_MODE == "mock":
        st.caption(t("mock_notice"))

    st.button(t("sample_button"), key="sample", on_click=load_sample)
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
