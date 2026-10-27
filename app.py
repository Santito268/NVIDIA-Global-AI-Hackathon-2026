"""Streamlit interface: describe a problem with your EPS, get a ready-to-file document."""

import json
import threading
from datetime import date
from pathlib import Path

import streamlit as st

from src import config, legal, ui_style
from src.agent import NEXT_STEPS, CaseResult, route_reason, run_case
from src.document import DOCUMENT_NAMES, build_document, localize_placeholders
from src.llm import LLMError
from src.schemas import ExplanationText
from src.tools import SearchError
from src.translate import run_translate_explanation, run_translate_sections
from src.ui_text import UI_TEXT

ROOT = Path(__file__).resolve().parent
SAMPLES_DIR = ROOT / "data" / "samples"
# Button key -> file name. Each case has a hand-written copy per language (caso_01_en.txt).
SAMPLES = {"sample": "caso_01", "sample_2": "caso_02", "sample_3": "caso_03"}
EVAL_RESULTS = ROOT / "evals" / "results.json"
REPO_URL = "https://github.com/Santito268/NVIDIA-Global-AI-Hackathon-2026"
# Pipeline steps shown while a case runs, with the model that does each one.
STEPS = [
    ("intake", "Nemotron Nano"),
    ("research", "Nemotron Super + Tavily"),
    ("draft", "Nemotron Super"),
    ("explain", "Nemotron Nano"),
]


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
    # {language: {"explanation": ExplanationText, "sections": dict}, or None if it failed}
    st.session_state.setdefault("translations", {})
    st.session_state.setdefault("translation_metrics", [])
    # While a case runs, every widget is disabled: any click reruns the page, and a rerun
    # would stop the pipeline halfway (credits spent, no result).
    st.session_state.setdefault("running", False)
    st.session_state.setdefault("pending", None)  # the description waiting to be processed
    st.session_state.setdefault("last_error", None)  # error code of the last failed case


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


@st.cache_data
def eval_score() -> str:
    """'passed/total' from the last evaluation run, shown in the hero."""
    try:
        grades = json.loads(EVAL_RESULTS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "—"
    return f"{sum(g.get('passed', False) for g in grades)}/{len(grades)}"


@st.cache_data
def sample_text(key: str, lang: str) -> str:
    """Example case as written by hand in `lang` (Spanish has no suffix)."""
    suffix = "" if lang == config.SOURCE_LANGUAGE else f"_{lang}"
    return (SAMPLES_DIR / f"{SAMPLES[key]}{suffix}.txt").read_text(encoding="utf-8").strip()


def find_sample(text: str) -> str | None:
    """Key of the example case `text` is (in any language), or None if the user wrote it."""
    for key in SAMPLES:
        if any(text == sample_text(key, lang) for lang in config.LANGUAGES):
            return key
    return None


def load_sample(key: str) -> None:
    st.session_state.description = sample_text(key, language())


def show_sample_in_language() -> None:
    """After a language switch, an untouched example follows the new language."""
    key = find_sample(st.session_state.description)
    if key:
        st.session_state.description = sample_text(key, language())


def text_to_process(description: str) -> str:
    """The pipeline works in Spanish: an untouched example is sent as its Spanish original."""
    key = find_sample(description)
    return sample_text(key, config.SOURCE_LANGUAGE) if key else description


def show_stepper(placeholder, current: int) -> None:
    steps = [(t(f"step_{name}"), model) for name, model in STEPS]
    html = ui_style.stepper(t("status_running"), steps, current, t("wait_notice"))
    placeholder.markdown(html, unsafe_allow_html=True)


def generate(description: str) -> bool:
    """Run the pipeline once, showing progress; keep the result in the session."""
    st.session_state.cases_run += 1  # count before calling: a failed case also spends credits
    count_daily_case()
    placeholder = st.empty()
    order = [name for name, _ in STEPS]
    show_stepper(placeholder, 0)
    try:
        result = run_case(
            description, on_step=lambda step: show_stepper(placeholder, order.index(step))
        )
    except (LLMError, SearchError) as error:
        placeholder.empty()
        st.session_state.last_error = error.code  # shown after the rerun, in the chosen language
        return False
    show_stepper(placeholder, len(STEPS))
    st.session_state.result = result
    st.session_state.translations = {}  # translations belong to the previous case
    return True


def run_pending() -> None:
    """Second half of a click on Generate: the page is drawn with every widget disabled."""
    try:
        done = generate(st.session_state.pending)
    finally:
        # Also when the run is stopped: it must never start again by itself.
        st.session_state.running, st.session_state.pending = False, None
    if done:
        st.toast(t("status_done"), icon="✅")
    st.rerun()  # enable the widgets again and show the results or the error


def translate(result: CaseResult, spanish: ExplanationText, lang: str) -> dict | None:
    """Translate the case-specific texts once (Nano); None if the translation failed."""
    target = config.LANGUAGES[lang]
    try:
        with st.spinner(t("translating")):
            explanation, metrics = run_translate_explanation(spanish, target)
            st.session_state.translation_metrics += metrics
            sections, metrics = run_translate_sections(result.draft.sections, target)
            st.session_state.translation_metrics += metrics
    except LLMError:
        return None
    return {"explanation": explanation, "sections": sections}


def localized(result: CaseResult) -> tuple[str, ExplanationText, str]:
    """(language shown, explanation texts, document); translated once and then cached."""
    spanish = ExplanationText(
        summary=result.explanation.summary, key_points=result.explanation.key_points
    )
    lang = language()
    if lang != config.SOURCE_LANGUAGE:
        if lang not in st.session_state.translations:
            # A failure is cached too, so later clicks do not spend credits again.
            st.session_state.translations[lang] = translate(result, spanish, lang)
        translated = st.session_state.translations[lang]
        if translated:
            # Fixed parts are hand-written in `lang`; only the sections come from Nano.
            document = build_document(
                result.route.document_type, result.facts, translated["sections"], lang
            )
            return lang, translated["explanation"], localize_placeholders(document, lang)
        st.warning(t("translation_error"))
    return config.SOURCE_LANGUAGE, spanish, result.draft.body_markdown


def show_explanation(result: CaseResult, lang: str, text: ExplanationText) -> None:
    """Everything here is hand-written per language except the summary and key points."""
    document_type = result.route.document_type
    labels = {key: t(key, lang) for key in ("document_type", "summary", "key_points")}
    labels |= {key: t(key, lang) for key in ("to_fill", "next_steps")}
    html = ui_style.explanation(
        labels,
        DOCUMENT_NAMES[lang][document_type],
        route_reason(result.facts, document_type, lang),
        text.summary,
        text.key_points,
        [localize_placeholders(p, lang) for p in result.to_fill],
        NEXT_STEPS[lang][document_type],
    )
    st.markdown(html, unsafe_allow_html=True)


def show_document(result: CaseResult, document: str) -> None:
    # The download is always the Spanish original: it is the version to file.
    st.download_button(
        t("download"),
        data=result.draft.body_markdown,
        file_name=f"{result.route.document_type}.md",
        mime="text/markdown",
        icon=":material/download:",
    )
    if st.session_state.translations.get(language()):  # only when a translation is shown
        st.info(t("translation_notice"))
    with st.container(key="paper"):
        st.markdown(document)


def show_sources(result: CaseResult) -> None:
    if not result.sources:
        st.write(t("no_sources"))
        return
    st.caption(t("sources_intro"))
    for source in result.sources:
        cited = t("cited") if source.url in result.draft.cited_urls else None
        card = ui_style.source_card(source.title, source.url, source.snippet, cited)
        st.markdown(card, unsafe_allow_html=True)


def show_metrics(result: CaseResult) -> None:
    metrics = result.metrics + st.session_state.translation_metrics
    tokens = sum(m.prompt_tokens + m.completion_tokens for m in metrics)
    seconds = sum(m.latency_s for m in metrics)
    for column, (label, value) in zip(
        st.columns(3),
        [
            (t("metric_tokens"), f"{tokens:,}"),
            (t("metric_time"), f"{seconds:.1f} s"),
            (t("metric_calls"), str(len(metrics))),
        ],
        strict=True,
    ):
        column.metric(label, value)
    st.caption(t("metrics_intro"))
    rows = [
        {
            t("col_step"): m.step,
            t("col_model"): m.model,
            t("col_prompt_tokens"): m.prompt_tokens,
            t("col_completion_tokens"): m.completion_tokens,
            t("col_latency"): round(m.latency_s, 2),
        }
        for m in metrics
    ]
    st.dataframe(rows, hide_index=True, use_container_width=True)
    st.caption(t("total", tokens=tokens, seconds=seconds))


def show_result(result: CaseResult) -> None:
    lang, text, document = localized(result)
    document_type = result.route.document_type
    head = ui_style.result_head(
        t("result_title"), document_type, DOCUMENT_NAMES[language()][document_type]
    )
    st.markdown(head, unsafe_allow_html=True)
    explanation_tab, document_tab, sources_tab, metrics_tab = st.tabs(
        [t("tab_explanation"), t("tab_document"), t("tab_sources"), t("tab_metrics")]
    )
    with explanation_tab:
        show_explanation(result, lang, text)
    with document_tab:
        show_document(result, document)
    with sources_tab:
        show_sources(result)
    with metrics_tab:
        show_metrics(result)


def show_header() -> None:
    brand, switch = st.columns([3, 1], vertical_alignment="center")
    brand.markdown('<div class="sv-brand">⚖️ Sub<span>venio</span></div>', unsafe_allow_html=True)
    with switch.container(key="lang"):
        st.segmented_control(
            "Idioma / Language",
            options=list(config.LANGUAGES),
            format_func=config.LANGUAGES.get,
            default=config.SOURCE_LANGUAGE,
            key="language",
            label_visibility="collapsed",
            disabled=st.session_state.running,
        )
    stats = [
        (eval_score(), t("stat_eval")),
        (str(len(legal.load_corpus()["articles"])), t("stat_laws")),
        ("~30", t("stat_time")),
    ]
    st.markdown(
        ui_style.hero(t("title"), t("tagline"), t("hero_badge"), stats), unsafe_allow_html=True
    )
    steps = [("✍️", "how_1"), ("⚖️", "how_2"), ("📄", "how_3")]
    cards = [(icon, t(f"{key}_title"), t(f"{key}_text")) for icon, key in steps]
    st.markdown(ui_style.how_it_works(t("how_title"), cards), unsafe_allow_html=True)
    notes = [
        ("⚖️", t("legal_title"), t("legal_text")),
        ("🔒", t("privacy_title"), t("privacy_text")),
    ]
    st.markdown(ui_style.notes(notes), unsafe_allow_html=True)


def show_case_form() -> None:
    running = st.session_state.running
    st.markdown(f'<div class="sv-section">{t("case_title")}</div>', unsafe_allow_html=True)
    if config.LLM_MODE == "mock":
        st.caption(t("mock_notice"))
    st.caption(t("samples_label"))
    for column, key in zip(st.columns(3), SAMPLES, strict=True):
        column.button(
            t("sample_1" if key == "sample" else key),
            key=key,
            on_click=load_sample,
            args=(key,),
            use_container_width=True,
            disabled=running,
        )
    if t("input_language_note"):
        st.caption(t("input_language_note"))
    show_sample_in_language()  # must run before the text area is drawn
    st.text_area(
        t("input_label"),
        key="description",
        max_chars=config.MAX_INPUT_CHARS,
        height=170,
        placeholder=t("input_placeholder"),
        disabled=running,
    )

    limit = config.MAX_CASES_PER_SESSION
    left = limit - st.session_state.cases_run
    blocked = left <= 0 or daily_cases_left() <= 0
    button, info = st.columns([2, 5], vertical_alignment="center")
    clicked = button.button(
        t("generate_button"), key="generate", type="primary", disabled=blocked or running
    )
    with info:
        if left <= 0:
            st.warning(t("limit_reached", limit=limit))
        elif daily_cases_left() <= 0:
            st.warning(t("daily_limit_reached"))
        else:
            st.caption(t("cases_left", left=left, limit=limit))
    if clicked:
        description = st.session_state.description.strip()
        if daily_cases_left() <= 0:  # another visitor may have used the last case meanwhile
            st.warning(t("daily_limit_reached"))
        elif not description:
            st.error(t("empty_input"))
        else:
            # First half: remember the case and redraw the page with every widget disabled.
            st.session_state.pending = text_to_process(description)
            st.session_state.running, st.session_state.last_error = True, None
            st.rerun()
    if running:
        run_pending()
    elif st.session_state.last_error:
        st.error(t("error_message"))
        st.caption(t(f"error_{st.session_state.last_error}"))


def main() -> None:
    init_state()
    st.set_page_config(page_title=t("title"), page_icon="⚖️", layout="centered")
    st.markdown(ui_style.CSS, unsafe_allow_html=True)
    show_header()
    show_case_form()
    if st.session_state.result:
        show_result(st.session_state.result)
    st.markdown(ui_style.footer(t("footer"), t("footer_code"), REPO_URL), unsafe_allow_html=True)


main()
