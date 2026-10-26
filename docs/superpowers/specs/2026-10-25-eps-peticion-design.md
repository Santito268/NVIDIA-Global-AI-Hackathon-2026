# Design: Health-rights petition assistant (Colombia, EPS)

## Intent
Colombian citizens whose health insurer (EPS) denies a medicine, delays an
authorization, or does not schedule an appointment often don't know which legal
document fits their case (a *derecho de petición* or an *acción de tutela*) or
which laws to cite. This app turns a plain-language description of the problem
into a ready-to-file document, with its legal basis found on the web and a
plain-language explanation of what to do next.

**Success:** in the demo, a user types their case and in under a minute gets the
right document, with real sources and a clear explanation.

## Goals / non-goals / anti-goals
- **Goals:** health/EPS cases only (v1); correct document type; cited sources
  with URLs; bilingual UI (ES/EN) so judges can test it.
- **Non-goals:** other entities (utilities, government offices), filing the
  document for the user, tracking deadlines, `.docx` export (stretch).
- **Anti-goals:** citing laws that were not found in a real source; sending or
  storing users' personal data; presenting output as legal advice.

## Constraints
- Hackathon rules: the reasoning model must be NVIDIA Nemotron via Nebius Token
  Factory; public repo (MIT); public demo until 2026-12-15.
- Deadline 2026-10-30 12:00 Bogotá. Nebius credits expected ~2026-10-27, so the
  LLM layer must run in a mock mode until then.
- Public demo uses the author's API keys: per-session case limit, input length
  cap, fixed `max_tokens`.

## Approaches
1. **Fixed pipeline with one bounded agentic research step** *(chosen)*:
   predictable, testable and easy to explain; Nemotron Super decides what to
   search via tool calling, capped at 3 Tavily searches.
2. Fully autonomous agent loop: more impressive, but harder to make reliable in
   3 days and more expensive in credits.
3. RAG over a curated legal corpus: requires building and license-checking the
   corpus plus embeddings; does not fit the timeline.

## Pipeline
| Step | Model | Output |
|---|---|---|
| 1. Intake | Nemotron Nano | `CaseFacts` (EPS, denied service, dates, urgency/risk to life, special-protection subject, missing fields) |
| 2. Route | Nemotron Nano | `RouteDecision` (petition vs. tutela + reason) |
| 3. Research | Nemotron Super + Tavily (≤3 searches) | `list[Source]` with URLs |
| 4. Draft | Nemotron Super | `DraftDocument` in Spanish: facts, requests, legal grounds (only from sources), evidence, notifications |
| 5. Explain | Nemotron Nano | plain-language explanation, next steps, English summary |

Structured outputs are JSON validated with pydantic; on failure the step is
retried, then a clear error is shown.

## Decisions made by the builder (open to change)
- Personal data never goes to the API: the document uses placeholders such as
  `[NOMBRE]` and `[CÉDULA]` that the user fills in after downloading.
- The generated document is always in Spanish (it is filed in Colombia).
- Visible disclaimer: "This does not replace legal advice."
- `LLM_MODE=mock|live` in `src/config.py`; only `src/llm.py` changes behavior.

## Left to the builder
- Exact prompt wording, UI layout, app name, evaluation case set
  (8–10 fictional cases in `data/samples/`).
