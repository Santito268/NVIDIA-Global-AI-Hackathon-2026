"""Canned answers used when LLM_MODE=mock (no Nebius or Tavily credits needed)."""

MOCK_SOURCES: list[dict] = [
    {
        "title": "Sentencia T-000 de 2026 (ejemplo)",
        "url": "https://www.corteconstitucional.gov.co/relatoria/ejemplo-1",
        "content": "Fuente de ejemplo: la EPS no puede negar un medicamento formulado.",
    },
    {
        "title": "Ley de ejemplo sobre el derecho a la salud",
        "url": "https://www.secretariasenado.gov.co/ejemplo-2",
        "content": "Fuente de ejemplo: la salud es un derecho fundamental.",
    },
]

MOCK_RESPONSES: dict[str, str] = {
    "intake": """{
  "eps": "EPS Ejemplo",
  "problem_type": "medicine_denied",
  "service_requested": "insulina glargina",
  "events_summary": "La EPS negó la entrega de un medicamento formulado por el médico tratante.",
  "relevant_dates": ["2026-10-01"],
  "urgent_health_risk": true,
  "special_protection": true,
  "special_protection_reason": "adulto mayor",
  "missing_info": ["copia de la fórmula médica", "respuesta escrita de la EPS"]
}""",
    "route": """{
  "document_type": "tutela",
  "reason": "La negativa pone en riesgo la salud de un adulto mayor, por eso procede la tutela."
}""",
    "research": """{
  "queries": [
    "tutela negación de medicamentos EPS",
    "derecho fundamental a la salud adulto mayor"
  ]
}""",
}
