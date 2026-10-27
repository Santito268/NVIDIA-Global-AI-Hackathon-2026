"""Run the evaluation set: python -m evals.run_eval [case_id ...]

Live mode spends credits (~13k tokens per case). Tavily results are cached in
evals/tavily_cache.json, so re-running a case only spends searches for new queries.
Results are written to evals/results.md and evals/results.json (live mode only).
"""

import json
import sys
from pathlib import Path

from evals.checks import check_case, passed
from src import agent, config
from src.llm import LLMError
from src.schemas import Source
from src.tools import SearchError, search_web

EVALS_DIR = Path(__file__).resolve().parent
CASES_PATH = EVALS_DIR / "cases.json"
CACHE_PATH = EVALS_DIR / "tavily_cache.json"
RESULTS_MD = EVALS_DIR / "results.md"
RESULTS_JSON = EVALS_DIR / "results.json"


def load_cases(ids: list[str]) -> list[dict]:
    """All cases, or only the ones whose id is in `ids`."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))
    return [case for case in cases if not ids or case["id"] in ids]


def cached_search(cache: dict[str, list[dict]]):
    """A search_web replacement that reuses saved results for queries already searched."""

    def search(query: str, max_results: int = config.RESULTS_PER_SEARCH) -> list[Source]:
        if query not in cache:
            cache[query] = [s.model_dump() for s in search_web(query, max_results)]
        return [Source(**s) for s in cache[query]]

    return search


def evaluate(cases: list[dict]) -> list[dict]:
    """Run every case through the real pipeline and grade it; errors count as failures."""
    grades = []
    for case in cases:
        print(f"- {case['id']}…", flush=True)
        try:
            result = agent.run_case(case["description"])
        except (LLMError, SearchError) as error:
            grades.append({"id": case["id"], "error": str(error), "passed": False})
            continue
        grade = {"id": case["id"], **check_case(result, case["expected"])}
        grade["passed"] = passed(grade)
        grades.append(grade)
    return grades


def _mark(value: bool) -> str:
    return "✅" if value else "❌"


def summary_markdown(grades: list[dict]) -> str:
    """A results table for the README's Metrics / evaluation section."""
    rows = [
        "| Case | Document | Right document | Who writes | Special protection | Only verified "
        "laws | No invented URLs | No forbidden words | Rulings cited | Tokens | Time (s) |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for g in grades:
        if "error" in g:
            rows.append(f"| {g['id']} | error: {g['error']} |" + " |" * 9)
            continue
        rows.append(
            f"| {g['id']} | {g['document_type']} | {_mark(g['document_type_ok'])} | "
            f"{_mark(g['writer_ok'])} | {_mark(g['special_protection_ok'])} | "
            f"{_mark(g['norms_ok'])} | {_mark(g['urls_ok'])} | {_mark(g['forbidden_words_ok'])} "
            f"| {g['rulings_cited']} | {g['tokens']} | {g['latency_s']} |"
        )
    ok = [g for g in grades if "error" not in g]
    with_rulings = sum(g["rulings_cited"] > 0 for g in ok)
    total = len(grades)
    lines = [
        f"**{sum(g['passed'] for g in grades)}/{total} cases pass every rule.** "
        f"{with_rulings}/{total} documents cite at least one Constitutional Court ruling.",
    ]
    if ok:
        removed = sum(g.get("quotes_removed", 0) for g in ok)  # older results lack it
        lines.append(f"The quote filter removed {removed} quotes that were not exact copies.")
        tokens = sum(g["tokens"] for g in ok) / len(ok)
        seconds = sum(g["latency_s"] for g in ok) / len(ok)
        lines.append(f"Average per case: {tokens:,.0f} tokens and {seconds:.1f} s of model time.")
    return "\n".join(lines) + "\n\n" + "\n".join(rows) + "\n"


def main() -> None:
    cases = load_cases(sys.argv[1:])
    if not cases:
        sys.exit("No cases match the given ids.")
    cache = json.loads(CACHE_PATH.read_text(encoding="utf-8")) if CACHE_PATH.exists() else {}
    agent.search_web = cached_search(cache)  # only inside this script; the app is unchanged
    try:
        grades = evaluate(cases)
    finally:
        if config.LLM_MODE == "live":  # never save mock sources as if they were real
            CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=1), "utf-8")
    print("\n" + summary_markdown(grades))
    if config.LLM_MODE == "live":
        # Re-running some cases replaces only their rows in the saved results.
        saved = json.loads(RESULTS_JSON.read_text("utf-8")) if RESULTS_JSON.exists() else []
        by_id = {g["id"]: g for g in saved} | {g["id"]: g for g in grades}
        merged = [by_id[case["id"]] for case in load_cases([]) if case["id"] in by_id]
        RESULTS_JSON.write_text(json.dumps(merged, ensure_ascii=False, indent=1), "utf-8")
        RESULTS_MD.write_text(summary_markdown(merged), encoding="utf-8")


if __name__ == "__main__":
    main()
