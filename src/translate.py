"""On-demand translation of the model's texts (Nano), for readers who do not speak Spanish.

Only what the model wrote is translated; every fixed text is hand-written per language. Quotes,
URLs and blanks are swapped for numbered tokens before translating and put back afterwards,
so the translation can never change them.
"""

import re

from src import config, prompts
from src.llm import CallMetrics, LLMError, chat, chat_json
from src.schemas import ExplanationText
from src.verify import PLACEHOLDER_PATTERN, QUOTE_PATTERN, URL_PATTERN

# Text the translation must never touch: quotes, URLs and blanks.
PROTECTED_PATTERN = re.compile(
    "|".join(p.pattern for p in (QUOTE_PATTERN, URL_PATTERN, PLACEHOLDER_PATTERN))
)
TOKEN_PATTERN = re.compile(r"⟦\d+⟧")
SECTION_MARKER_PATTERN = re.compile(r"^⟦S(\d+)⟧[ \t]*$", re.MULTILINE)


def protect(text: str) -> tuple[str, list[str]]:
    """Swap quotes, URLs and blanks for tokens ⟦1⟧, ⟦2⟧...; return the text and the originals."""
    originals: list[str] = []

    def swap(match: re.Match) -> str:
        originals.append(match.group(0))
        return f"⟦{len(originals)}⟧"

    return PROTECTED_PATTERN.sub(swap, text), originals


def restore(text: str, originals: list[str]) -> str:
    """Put the originals back; fail if the translation lost, repeated or invented a token."""
    expected = [f"⟦{i}⟧" for i in range(1, len(originals) + 1)]
    if sorted(TOKEN_PATTERN.findall(text)) != sorted(expected):
        raise LLMError("The translation changed protected text. Showing the Spanish version.")
    for token, original in zip(expected, originals, strict=True):
        text = text.replace(token, original)
    return text


def run_translate_sections(
    sections: dict[str, str], language: str
) -> tuple[dict[str, str], list[CallMetrics]]:
    """Translate only the model's sections into `language` (e.g. "English"), in one Nano call.

    The fixed parts are hand-written per language (src/document.py), so they never reach the
    model. Each section starts with a marker ⟦S1⟧, ⟦S2⟧... so the answer can be split back
    into the same sections.
    """
    headings = list(sections)
    joined = "\n\n".join(f"⟦S{i}⟧\n{sections[h]}" for i, h in enumerate(headings, 1))
    protected, originals = protect(joined)
    messages = [
        {"role": "system", "content": prompts.TRANSLATE_SECTIONS_SYSTEM.format(language=language)},
        {"role": "user", "content": protected},
    ]
    translation, metrics = chat(
        messages,
        config.NANO_MODEL,
        "translate_sections",
        thinking=False,
        max_tokens=config.DRAFT_MAX_TOKENS,
    )
    parts = SECTION_MARKER_PATTERN.split(restore(translation, originals))
    # split() gives [text before ⟦S1⟧, "1", section 1, "2", section 2, ...]
    numbers, texts = parts[1::2], parts[2::2]
    if numbers != [str(i) for i in range(1, len(headings) + 1)]:
        raise LLMError("The translation lost a section. Showing the Spanish version.")
    return {h: text.strip() for h, text in zip(headings, texts, strict=True)}, [metrics]


def run_translate_explanation(
    text: ExplanationText, language: str
) -> tuple[ExplanationText, list[CallMetrics]]:
    """Translate only the case-specific parts of the explanation, as validated JSON (Nano)."""
    messages = [
        {
            "role": "system",
            "content": prompts.TRANSLATE_EXPLANATION_SYSTEM.format(language=language),
        },
        {"role": "user", "content": text.model_dump_json()},
    ]
    translation, metrics = chat_json(
        messages, config.NANO_MODEL, "translate_explanation", ExplanationText, thinking=False
    )
    if len(translation.key_points) != len(text.key_points):
        raise LLMError("The translation lost a key point. Showing the Spanish version.")
    return translation, metrics
