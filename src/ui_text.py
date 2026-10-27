"""Fixed interface texts, one dictionary per language (no model involved)."""

UI_TEXT: dict[str, dict[str, str]] = {
    "es": {
        "title": "Tutela Fácil EPS",
        "tagline": (
            "Cuéntanos tu problema con la EPS y te preparamos un derecho de petición o una "
            "tutela lista para radicar, con base legal verificada y explicada en palabras "
            "simples."
        ),
        "legal_notice": (
            "**No es asesoría legal.** Es una herramienta de apoyo: revisa el documento y, si "
            "puedes, consúltalo con un abogado o un consultorio jurídico antes de radicarlo."
        ),
        "privacy_notice": (
            "**Privacidad:** lo que escribes se envía a Nemotron (en Nebius) para procesarlo. "
            "No escribas nombres, cédulas, direcciones ni teléfonos: el documento trae espacios "
            "en blanco para que los llenes tú."
        ),
        "mock_notice": "Modo demostración: las respuestas son de ejemplo y no se usa la IA.",
        "input_label": "¿Qué pasó con tu EPS?",
        "input_placeholder": (
            "Ejemplo: A mi papá de 72 años le formularon insulina hace tres semanas y la EPS "
            "no se la ha entregado..."
        ),
        "sample_button": "Usar un caso de ejemplo",
        "generate_button": "Generar documento",
        "empty_input": "Escribe qué pasó con tu EPS antes de generar el documento.",
        "limit_reached": (
            "Llegaste al límite de {limit} casos de esta demostración. Gracias por probarla."
        ),
        "cases_left": "Casos disponibles en esta sesión: {left} de {limit}.",
        "status_running": "Preparando tu documento…",
        "status_done": "¡Listo! Tu documento está abajo.",
        "status_error": "No se pudo terminar el documento.",
        "step_intake": "Entendiendo tu caso (Nemotron Nano)…",
        "step_route": "Eligiendo el documento adecuado (Nemotron Nano)…",
        "step_research": "Buscando sentencias en sitios oficiales (Nemotron Super + Tavily)…",
        "step_draft": "Redactando el documento (Nemotron Super)…",
        "step_explain": "Explicándolo en palabras simples (Nemotron Nano)…",
        "error_message": "Algo falló. Intenta de nuevo en un momento.",
        "tab_explanation": "Explicación",
        "tab_document": "Documento",
        "tab_sources": "Fuentes",
        "tab_metrics": "Métricas",
        "document_type": "Documento recomendado",
        "summary": "En palabras simples",
        "key_points": "Lo que pide el documento",
        "to_fill": "Espacios que debes llenar",
        "next_steps": "Qué hacer después",
        "download": "Descargar documento (.md)",
        "sources_intro": (
            "Estos son los textos que encontró la búsqueda en sitios oficiales. Las citas del "
            "documento deben aparecer aquí palabra por palabra: compruébalas."
        ),
        "no_sources": "La búsqueda no encontró sentencias. El documento usa solo las leyes.",
        "cited": "Citada en el documento",
        "metrics_intro": "Modelo, tokens y tiempo de cada paso.",
        "total": "Total: {tokens} tokens en {seconds:.1f} s.",
    },
}

DOCUMENT_NAMES: dict[str, dict[str, str]] = {
    "es": {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"},
}
