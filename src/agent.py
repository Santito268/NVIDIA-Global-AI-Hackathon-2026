"""The pipeline: intake -> route (research, draft and explain come next)."""

import sys
from dataclasses import dataclass, field

from src import config, prompts
from src.llm import CallMetrics, LLMError, chat_json
from src.schemas import CaseFacts, RouteDecision


@dataclass
class CaseResult:
    """Everything the pipeline produced for one case, plus what it cost."""

    facts: CaseFacts
    route: RouteDecision
    metrics: list[CallMetrics] = field(default_factory=list)


def validate_input(text: str) -> str:
    """Reject empty or too-long descriptions before spending any credits."""
    text = text.strip()
    if not text:
        raise LLMError("Please describe your case.")
    if len(text) > config.MAX_INPUT_CHARS:
        raise LLMError(f"Please keep the description under {config.MAX_INPUT_CHARS} characters.")
    return text


def run_intake(description: str) -> tuple[CaseFacts, list[CallMetrics]]:
    """Step 1 (Nano): extract the structured facts of the case."""
    messages = [
        {"role": "system", "content": prompts.INTAKE_SYSTEM},
        {"role": "user", "content": description},
    ]
    return chat_json(messages, config.NANO_MODEL, "intake", CaseFacts)


def run_route(facts: CaseFacts) -> tuple[RouteDecision, list[CallMetrics]]:
    """Step 2 (Nano): decide between derecho de petición and tutela."""
    messages = [
        {"role": "system", "content": prompts.ROUTE_SYSTEM},
        {"role": "user", "content": facts.model_dump_json()},
    ]
    return chat_json(messages, config.NANO_MODEL, "route", RouteDecision)


def run_case(description: str) -> CaseResult:
    """Run every pipeline step for one case."""
    description = validate_input(description)
    facts, intake_metrics = run_intake(description)
    route, route_metrics = run_route(facts)
    return CaseResult(facts, route, intake_metrics + route_metrics)


def main() -> None:
    """CLI: python -m src.agent data/samples/caso_01.txt"""
    if len(sys.argv) != 2:
        sys.exit("Usage: python -m src.agent <case_file.txt>")
    with open(sys.argv[1], encoding="utf-8") as f:
        result = run_case(f.read())
    print(result.facts.model_dump_json(indent=2))
    print(result.route.model_dump_json(indent=2))
    for m in result.metrics:
        tokens = f"{m.prompt_tokens}+{m.completion_tokens}"
        print(f"[{m.step}] {m.model} {tokens} tokens {m.latency_s:.2f}s")


if __name__ == "__main__":
    main()
