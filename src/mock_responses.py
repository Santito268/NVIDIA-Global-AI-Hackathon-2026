"""Canned model answers used when LLM_MODE=mock (no Nebius credits needed)."""

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
}
