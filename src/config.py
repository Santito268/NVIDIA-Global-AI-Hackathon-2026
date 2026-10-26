"""Central configuration. Every model name, URL and limit lives here."""

import os

from dotenv import load_dotenv

load_dotenv()

# "mock" returns canned responses (no credits needed); "live" calls Nebius Token Factory.
LLM_MODE: str = os.getenv("LLM_MODE", "mock").strip().lower()

NEBIUS_API_KEY: str = os.getenv("NEBIUS_API_KEY", "")
NEBIUS_BASE_URL: str = os.getenv("NEBIUS_BASE_URL", "")
TAVILY_API_KEY: str = os.getenv("TAVILY_API_KEY", "")

# Exact model IDs must be copied from the Nebius Token Factory catalog into .env.
NANO_MODEL: str = os.getenv("NEMOTRON_NANO_MODEL", "")
SUPER_MODEL: str = os.getenv("NEMOTRON_SUPER_MODEL", "")

# Request settings
REQUEST_TIMEOUT_S: float = 60.0
MAX_RETRIES: int = 3
DEFAULT_MAX_TOKENS: int = 1500

# Limits that protect credits on the public demo
MAX_INPUT_CHARS: int = 2000
MAX_SEARCHES_PER_CASE: int = 3
