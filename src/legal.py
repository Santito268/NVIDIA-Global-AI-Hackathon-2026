"""The mini legal code: verified official articles the draft step can rely on."""

import json
from functools import lru_cache
from pathlib import Path

CORPUS_PATH = Path(__file__).resolve().parent.parent / "data" / "legal" / "mini_codigo.json"


@lru_cache(maxsize=1)
def load_corpus() -> dict:
    """Read data/legal/mini_codigo.json once."""
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def corpus_urls() -> set[str]:
    """Official URLs of the corpus; they count as verified sources."""
    return {source["url"] for source in load_corpus()["sources"].values()}


def corpus_excerpts() -> list[str]:
    """Verbatim official excerpts of the corpus; the draft may quote them."""
    return [e for entry in load_corpus()["articles"] for e in entry["excerpts"]]


def format_for_prompt() -> str:
    """Render the articles grouped by norm (URL once per norm) so the model can read and cite."""
    corpus = load_corpus()
    blocks = []
    for key, source in corpus["sources"].items():
        blocks.append(f"## {source['name']} (URL: {source['url']})")
        for entry in corpus["articles"]:
            if entry["source"] == key:
                excerpts = " […] ".join(f"«{e}»" for e in entry["excerpts"])
                blocks.append(
                    f"- Artículo {entry['article']}: {entry['title']}\n"
                    f"  Uso: {entry['use']}\n"
                    f"  Texto oficial: {excerpts}"
                )
    return "\n".join(blocks)
