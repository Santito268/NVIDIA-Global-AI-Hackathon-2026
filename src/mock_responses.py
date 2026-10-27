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
  "writer_is_affected_person": false,
  "writer_relationship": "hijo/a",
  "missing_info": ["copia de la fórmula médica", "respuesta escrita de la EPS"]
}""",
    "route": """{
  "document_type": "tutela",
  "reason": "La negativa pone en riesgo la salud de un adulto mayor, por eso procede la tutela."
}""",
    "draft": """# ACCIÓN DE TUTELA

Señor(a) Juez de la República (reparto)

**Accionante:** [NOMBRE], identificado(a) con cédula [CÉDULA], residente en [CIUDAD DE RESIDENCIA].
**Accionada:** EPS Ejemplo.

## Hechos
1. El médico tratante formuló insulina glargina el 1 de octubre de 2026.
2. La EPS no ha entregado el medicamento.

## Fundamentos de derecho
Constitución Política, art. 86; Decreto 2591 de 1991; Ley 1751 de 2015.
Sentencia T-000 de 2026 (ejemplo): https://www.corteconstitucional.gov.co/relatoria/ejemplo-1
Fuente inventada: https://www.blog-falso.com/no-verificada

## Juramento
Bajo la gravedad del juramento manifiesto que no he presentado otra tutela por los mismos hechos.

[FIRMA]
[NOMBRE] — [CÉDULA]
""",
    "research": """{
  "queries": [
    "tutela negación de medicamentos EPS",
    "derecho fundamental a la salud adulto mayor"
  ]
}""",
}
