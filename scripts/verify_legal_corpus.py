"""Check that every excerpt in data/legal/mini_codigo.json is verbatim and still valid law.

Usage:
  1. Save each official page (see "sources" in the JSON) as <raw_dir>/<page_id>.html, e.g.
     curl -L "https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=4125" \
          -o raw/4125.html
  2. python scripts/verify_legal_corpus.py raw

Re-run it whenever the laws may have changed: a failure means a human must review the entry.
"""

import json
import re
import sys
from pathlib import Path

from legal_text import article_text, decode, drop_struck_text, html_to_text

CORPUS = Path(__file__).resolve().parent.parent / "data" / "legal" / "mini_codigo.json"


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python scripts/verify_legal_corpus.py <raw_dir>")
    raw_dir = Path(sys.argv[1])
    corpus = json.loads(CORPUS.read_text(encoding="utf-8"))

    texts = {}
    for key, source in corpus["sources"].items():
        page = decode((raw_dir / f"{source['page_id']}.html").read_bytes())
        texts[key] = html_to_text(drop_struck_text(page))

    failures = 0
    for entry in corpus["articles"]:
        label = f"{entry['source']} art. {entry['article']}"
        official = normalize(article_text(texts[entry["source"]], entry["article"]))
        for excerpt in entry["excerpts"]:
            if normalize(excerpt) not in official:
                failures += 1
                print(f"FAIL {label}: not found verbatim (or declared inexequible): {excerpt[:80]}")
    total = sum(len(e["excerpts"]) for e in corpus["articles"])
    print(f"{total - failures}/{total} excerpts verified in {len(corpus['articles'])} articles")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
