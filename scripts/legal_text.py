"""Extract article text, verbatim, from official Gestor Normativo (Función Pública) pages."""

import html
import re

HEADING = re.compile(r"^\s*ART[ÍI]CULO\s+(\d+)\s*[oº°]?\s*[\.\-]", re.IGNORECASE | re.MULTILINE)
# Editorial lines added by the publisher (cross-references, validity notes), not law text.
EDITORIAL = re.compile(
    r"^\(|^Ver |^Notas? |^Jurisprudencia|^Concordancias|^Legislaci[oó]n Anterior", re.IGNORECASE
)


def decode(raw: bytes) -> str:
    """These pages declare ISO-8859-1 but some are really UTF-8."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252")


def drop_struck_text(page: str) -> str:
    """Remove text the Gestor Normativo marks as affected by a ruling.

    It underlines (<u>) text declared inexequible and wraps some in "( ... )*". Removing it
    guarantees our excerpts never contain law that is no longer valid.
    """
    page = re.sub(r"(?is)<u>.*?</u>", " ", page)
    return re.sub(r"\([^()]*\)\s*\*", " ", page)


def html_to_text(page: str) -> str:
    """Turn the page into plain text, one paragraph per line."""
    page = re.sub(r"(?i)<br\s*/?>|</p>|</div>|</li>", "\n", page)
    text = html.unescape(re.sub(r"<[^>]+>", " ", page)).replace("\xa0", " ")
    lines = (re.sub(r"\s+", " ", line).strip() for line in text.splitlines())
    return "\n".join(line for line in lines if line)


def article_text(text: str, number: int) -> str:
    """Return the law text of one article (first heading match), without editorial lines."""
    headings = list(HEADING.finditer(text))
    for i, match in enumerate(headings):
        if int(match.group(1)) == number:
            end = headings[i + 1].start() if i + 1 < len(headings) else len(text)
            lines = text[match.start() : end].splitlines()
            return "\n".join(line for line in lines if not EDITORIAL.search(line))
    raise ValueError(f"Article {number} not found")
