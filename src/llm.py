"""Single entry point for every model call (Nebius Token Factory or mock)."""

import json
import logging
import time
from dataclasses import dataclass
from functools import lru_cache
from typing import TypeVar

import openai
from pydantic import BaseModel, ValidationError

from src import config
from src.mock_responses import MOCK_RESPONSES

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Raised with a message that is safe to show to the user.

    `code` names the kind of error, so the app can show a hand-written message in the
    user's language (src/ui_text.py, key "error_<code>").
    """

    def __init__(self, message: str, code: str = "generic") -> None:
        super().__init__(message)
        self.code = code


@dataclass
class CallMetrics:
    """What one model call cost, for the metrics panel and README."""

    step: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    latency_s: float


@lru_cache(maxsize=4)
def _client(timeout: float, max_retries: int) -> openai.OpenAI:
    """The OpenAI-compatible client for Token Factory; one per (timeout, retries) pair."""
    if not config.NEBIUS_API_KEY or not config.NEBIUS_BASE_URL:
        raise LLMError(
            "Nebius is not configured: set NEBIUS_API_KEY and NEBIUS_BASE_URL.", "config"
        )
    return openai.OpenAI(
        api_key=config.NEBIUS_API_KEY,
        base_url=config.NEBIUS_BASE_URL,
        timeout=timeout,
        max_retries=max_retries,  # the library waits a little longer before each retry
    )


def chat(
    messages: list[dict],
    model: str,
    step: str,
    thinking: bool = False,
    max_tokens: int = config.DEFAULT_MAX_TOKENS,
    temperature: float = config.TEMPERATURE,
    timeout: float = config.REQUEST_TIMEOUT_S,
    max_retries: int = config.MAX_RETRIES,
) -> tuple[str, CallMetrics]:
    """Send a chat request and return the answer text and its metrics.

    `thinking` toggles Nemotron's reasoning trace. Off cut intake tokens ~5x with the same result,
    so it is only turned on for steps that need real reasoning.
    """
    start = time.perf_counter()

    if config.LLM_MODE == "mock":
        # "{input}" lets a canned answer echo the request (used by the document translation).
        text = MOCK_RESPONSES.get(step, "")
        if messages:
            text = text.replace("{input}", messages[-1]["content"])
        metrics = CallMetrics(step, "mock", 0, 0, time.perf_counter() - start)
        return text, metrics

    if not model:
        raise LLMError(
            f"No model configured for step '{step}'. Check the model IDs in .env.", "config"
        )
    try:
        response = _client(timeout, max_retries).chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
            extra_body={"chat_template_kwargs": {"enable_thinking": thinking}},
        )
    except openai.APITimeoutError as exc:
        raise LLMError("The model took too long to answer.", "timeout") from exc
    except openai.APIConnectionError as exc:
        raise LLMError("Could not reach Nebius Token Factory.", "connection") from exc
    except openai.APIStatusError as exc:
        raise LLMError(f"Nebius returned an error (HTTP {exc.status_code}).") from exc

    usage = response.usage
    metrics = CallMetrics(
        step=step,
        model=model,
        prompt_tokens=usage.prompt_tokens if usage else 0,
        completion_tokens=usage.completion_tokens if usage else 0,
        latency_s=time.perf_counter() - start,
    )
    # Log only metadata: never the prompt, the answer or any key.
    logger.info(
        "step=%s model=%s tokens=%d+%d latency=%.2fs",
        metrics.step,
        metrics.model,
        metrics.prompt_tokens,
        metrics.completion_tokens,
        metrics.latency_s,
    )
    return strip_reasoning(response.choices[0].message.content or ""), metrics


def strip_reasoning(text: str) -> str:
    """Remove a <think>...</think> reasoning trace if the model mixed it into the answer."""
    if "</think>" in text:
        text = text.split("</think>", 1)[1]
    return text.strip()


def extract_json(text: str) -> dict:
    """Parse the first JSON object in a model answer (tolerates code fences or reasoning text)."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end <= start:
        raise ValueError("No JSON object found in the model answer.")
    return json.loads(text[start : end + 1])


def chat_json(
    messages: list[dict], model: str, step: str, schema: type[T], thinking: bool = False
) -> tuple[T, list[CallMetrics]]:
    """Ask for JSON and validate it; on invalid output, retry once telling the model the error."""
    all_metrics: list[CallMetrics] = []
    for attempt in range(2):
        text, metrics = chat(messages, model, step, thinking=thinking)
        all_metrics.append(metrics)
        try:
            return schema.model_validate(extract_json(text)), all_metrics
        except (ValueError, ValidationError) as exc:
            logger.warning("step=%s invalid JSON on attempt %d", step, attempt + 1)
            messages = [
                *messages,
                {"role": "assistant", "content": text},
                {"role": "user", "content": f"Invalid JSON: {exc}. Answer only with valid JSON."},
            ]
    raise LLMError(
        f"The model returned an invalid answer in step '{step}'. Please try again.", "invalid"
    )
