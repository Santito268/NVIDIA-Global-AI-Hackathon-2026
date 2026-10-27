"""Central configuration. Every model name, URL and limit lives here."""

import os

from dotenv import load_dotenv

load_dotenv()

# "mock" returns canned responses (no credits needed); "live" calls Nebius Token Factory.
LLM_MODE: str = os.getenv("LLM_MODE", "mock").strip().lower()
if LLM_MODE not in ("mock", "live"):
    # Fail loudly: a typo must never silently switch to paid "live" calls.
    raise ValueError(f"LLM_MODE must be 'mock' or 'live', got {LLM_MODE!r}. Check your .env.")

NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# Exact IDs from the Nebius Token Factory catalog (GET /v1/models). Override in .env if needed.
NANO_MODEL: str = os.getenv("NEMOTRON_NANO_MODEL") or "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"
SUPER_MODEL: str = os.getenv("NEMOTRON_SUPER_MODEL") or "nvidia/nemotron-3-super-120b-a12b"

# Request settings
REQUEST_TIMEOUT_S: float = 60.0
MAX_RETRIES: int = 3
DEFAULT_MAX_TOKENS: int = 1500
# Drafting reasons before writing a long document, so it needs more room.
DRAFT_MAX_TOKENS: int = 8000

# Limits that protect credits on the public demo
MAX_INPUT_CHARS: int = 2000
# Interface languages. The pipeline always works in Spanish (SOURCE_LANGUAGE); results are
# translated by Nano only when another language is chosen. To add one: a line here plus its
# texts in src/ui_text.py.
SOURCE_LANGUAGE: str = "es"
LANGUAGES: dict[str, str] = {"es": "Español", "en": "English"}

# Each case costs ~13k tokens and 3 Tavily searches: protects the public demo's credits.
MAX_CASES_PER_SESSION: int = 3
MAX_SEARCHES_PER_CASE: int = 3
RESULTS_PER_SEARCH: int = 3
MAX_SNIPPET_CHARS: int = 500

# Web research only looks at official Colombian legal and health sources, not blogs.
TRUSTED_DOMAINS: list[str] = [
    "corteconstitucional.gov.co",
    "secretariasenado.gov.co",
    "funcionpublica.gov.co",
    "minsalud.gov.co",
    "supersalud.gov.co",
]
