"""Checks that run on the model's draft, by plain code: no model judges another model.

Every URL must come from the research or the legal code, and every «quote» must be copied
word for word from a snippet or the legal code. What fails is removed before anyone sees it.
"""

import re

from src import legal
from src.schemas import Source

URL_PATTERN = re.compile(r"https?://[^\s)\]>]+")
REMOVED_URL_NOTE = "[enlace eliminado: no proviene de una fuente verificada]"
QUOTE_PATTERN = re.compile(r"«([^«»]+)»")
REMOVED_QUOTE_NOTE = "[cita eliminada: no aparece en la fuente]"
MIN_QUOTE_WORDS = 6  # the shortest excerpt of the legal code has 6 words
ITEM_START_PATTERN = re.compile(r"^(?:[-*]|\d+[.)])\s")
PLACEHOLDER_PATTERN = re.compile(r"\[[A-ZÁÉÍÓÚÑ ]+\]")
# The legal code's private "Uso:" guidance (src/legal.py) leaked into a draft in eval case 05,
# inline "(Uso: ...)" or as its own line. The prompt forbids it; code makes sure.
USE_NOTE_PATTERN = re.compile(r"[ \t]*\(Uso:[^)]*\)|^[ \t]*-?[ \t]*Uso:.*\n?", re.MULTILINE)


def remove_unverified_urls(text: str, sources: list[Source]) -> tuple[str, list[str]]:
    """Replace every URL not found by research nor in the legal code; return text and URLs kept."""
    known = {s.url for s in sources} | legal.corpus_urls()
    cited: list[str] = []

    def check(match: re.Match) -> str:
        url = match.group(0).rstrip(".,;:")
        if url in known:
            if url not in cited:
                cited.append(url)
            return match.group(0)
        return REMOVED_URL_NOTE

    return URL_PATTERN.sub(check, text), cited


# Tavily drops accented letters from most Court snippets ("prestación" arrives as "prestacin":
# 79 of 86 cached ruling snippets). A correct quote would never match, so both sides drop them.
_DROP_ACCENTED = str.maketrans("", "", "áéíóúüñ")


def _normalize(text: str) -> str:
    """Compare quotes ignoring case, accented letters, extra spaces and edge punctuation."""
    text = text.casefold().translate(_DROP_ACCENTED)
    return " ".join(text.split()).strip(" .,;:…")


def remove_unverified_quotes(text: str, sources: list[Source]) -> str:
    """Replace every «quote» that is not copied word for word from a snippet or the legal code."""
    known = [_normalize(s.snippet) for s in sources]
    known += [_normalize(e) for e in legal.corpus_excerpts()]

    def check(match: re.Match) -> str:
        quote = _normalize(match.group(1))
        # A live test kept «... insulina glargina ...»: two words found in a snippet prove
        # nothing. A quote must be a real sentence fragment, with no gaps inside.
        long_enough = len(quote.split()) >= MIN_QUOTE_WORDS
        no_gaps = "…" not in quote and "..." not in quote
        if long_enough and no_gaps and any(quote in k for k in known):
            return match.group(0)
        return REMOVED_QUOTE_NOTE

    return QUOTE_PATTERN.sub(check, text)


def drop_items_with_removed_quotes(text: str) -> str:
    """Remove every list item or paragraph whose quote was removed.

    A ruling cited with "[cita eliminada]" proves nothing and looks broken to a judge; the
    laws from the verified legal code remain as the legal grounds.
    """
    blocks: list[list[str]] = []
    for line in text.split("\n"):
        starts_block = not line.strip() or ITEM_START_PATTERN.match(line)
        if not blocks or starts_block or not blocks[-1][-1].strip():
            blocks.append([line])
        else:
            blocks[-1].append(line)  # continuation of a multi-line item
    kept = [block for block in blocks if not any(REMOVED_QUOTE_NOTE in ln for ln in block)]
    return "\n".join(line for block in kept for line in block)


def check_section(text: str, sources: list[Source]) -> tuple[str, list[str], int]:
    """All the checks for one section of the draft: clean text, URLs kept, quotes removed."""
    text = remove_unverified_quotes(USE_NOTE_PATTERN.sub("", text), sources)
    removed = text.count(REMOVED_QUOTE_NOTE)  # measured by the evaluation set
    text, urls = remove_unverified_urls(drop_items_with_removed_quotes(text), sources)
    return text, urls, removed


def find_placeholders(text: str) -> list[str]:
    """List the [PLACEHOLDERS] the citizen still has to fill in, in order of appearance."""
    return list(dict.fromkeys(PLACEHOLDER_PATTERN.findall(text)))
