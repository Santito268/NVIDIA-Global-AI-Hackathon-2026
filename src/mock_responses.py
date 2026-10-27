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
    # Only the sections the model writes. The title and the wrong "Partes" are there on
    # purpose: the app must drop them and build those parts itself.
    "draft": """# ACCIÓN DE TUTELA

## Partes
- Accionado actúa como agente oficioso (texto equivocado que la app debe descartar).

## Hechos
1. El médico tratante formuló insulina glargina al paciente el 1 de octubre de 2026.
2. La EPS no ha realizado el suministro del medicamento.

## Derechos fundamentales vulnerados o amenazados
- Derecho a la salud (artículo 49 de la Constitución Política).

## Pretensiones
1. Ordenar a la EPS, como medida provisional (artículo 7 del Decreto 2591 de 1991), el
   suministro de la insulina glargina dentro de las 48 horas siguientes.

## Fundamentos de derecho
- Artículo 49 de la Constitución Política: garantiza el acceso a los servicios de salud.
- En la Sentencia T-000 de 2026 (ejemplo)
  (https://www.corteconstitucional.gov.co/relatoria/ejemplo-1) se lee:
  «la EPS no puede negar un medicamento formulado».
- Fuente inventada (https://www.blog-falso.com/no-verificada): «una frase que nadie dijo».
""",
    "explain": """{
  "summary": "Es una acción de tutela: le pides a un juez que proteja la salud de tu familiar.",
  "key_points": [
    "Que la EPS entregue la insulina glargina en 48 horas.",
    "Que el juez tome una medida provisional, es decir, una orden urgente mientras decide."
  ]
}""",
    "translate_explanation": """{
  "reason": "[Example translation] The denial puts an older adult's health at risk.",
  "summary": "[Example translation] It is an acción de tutela (protection action).",
  "key_points": [
    "[Example translation] That the EPS delivers the insulin within 48 hours.",
    "[Example translation] That the judge orders a medida provisional (provisional measure)."
  ]
}""",
    # {input} is replaced by the text sent to the model, so the tokens ⟦n⟧ come back intact
    # and the protect/restore round trip is tested without credits.
    "translate_document": "### [Example translation]\n\n{input}",
    "research": """{
  "queries": [
    "tutela negación de medicamentos EPS",
    "derecho fundamental a la salud adulto mayor"
  ]
}""",
}
