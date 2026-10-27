"""Fixed interface texts, one dictionary per language (no model involved).

Every language must have the same keys (a test checks it). To add a language, copy the
"en" block, translate it and add the language to config.LANGUAGES.
"""

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
        "input_language_note": "",
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
        "translating": "Traduciendo con Nemotron Nano…",
        "translation_notice": "",
        "translation_error": "No se pudo traducir. Se muestra la versión en español.",
        "sources_intro": (
            "Estos son los textos que encontró la búsqueda en sitios oficiales. Las citas del "
            "documento deben aparecer aquí palabra por palabra: compruébalas."
        ),
        "no_sources": "La búsqueda no encontró sentencias. El documento usa solo las leyes.",
        "cited": "Citada en el documento",
        "metrics_intro": "Modelo, tokens y tiempo de cada paso.",
        "total": "Total: {tokens} tokens en {seconds:.1f} s.",
    },
    "en": {
        "title": "Tutela Fácil EPS",
        "tagline": (
            "Tell us about your problem with your Colombian health insurer (EPS) and we prepare "
            "a formal petition (derecho de petición) or a constitutional protection action "
            "(tutela), ready to file, with verified legal grounds explained in plain words."
        ),
        "legal_notice": (
            "**This is not legal advice.** It is a support tool: review the document and, if "
            "you can, check it with a lawyer or a free legal clinic before filing it."
        ),
        "privacy_notice": (
            "**Privacy:** what you write is sent to Nemotron (on Nebius) to be processed. Do "
            "not write names, ID numbers, addresses or phone numbers: the document has blanks "
            "for you to fill in."
        ),
        "mock_notice": "Demo mode: answers are examples and no AI is used.",
        "input_label": "What happened with your EPS?",
        "input_placeholder": (
            "Ejemplo: A mi papá de 72 años le formularon insulina hace tres semanas y la EPS "
            "no se la ha entregado..."
        ),
        "input_language_note": (
            "The app works in Spanish, the language of Colombian courts. Try the sample case, "
            "or write in Spanish."
        ),
        "sample_button": "Use a sample case",
        "generate_button": "Generate document",
        "empty_input": "Describe what happened with your EPS before generating the document.",
        "limit_reached": (
            "You reached the limit of {limit} cases for this demo. Thanks for trying it."
        ),
        "cases_left": "Cases left in this session: {left} of {limit}.",
        "status_running": "Preparing your document…",
        "status_done": "Done! Your document is below.",
        "status_error": "The document could not be finished.",
        "step_intake": "Understanding your case (Nemotron Nano)…",
        "step_route": "Choosing the right document (Nemotron Nano)…",
        "step_research": "Searching rulings on official sites (Nemotron Super + Tavily)…",
        "step_draft": "Writing the document (Nemotron Super)…",
        "step_explain": "Explaining it in plain words (Nemotron Nano)…",
        "error_message": "Something went wrong. Please try again in a moment.",
        "tab_explanation": "Explanation",
        "tab_document": "Document",
        "tab_sources": "Sources",
        "tab_metrics": "Metrics",
        "document_type": "Recommended document",
        "summary": "In plain words",
        "key_points": "What the document asks for",
        "to_fill": "Blanks you must fill in",
        "next_steps": "What to do next",
        "download": "Download the Spanish document to file (.md)",
        "translating": "Translating with Nemotron Nano…",
        "translation_notice": (
            "Reference translation by Nemotron Nano to help you understand the document. "
            "File the Spanish version."
        ),
        "translation_error": "The translation failed. Showing the Spanish version.",
        "sources_intro": (
            "These are the texts the search found on official Colombian sites (in Spanish). "
            "Every quote in the document must appear here word for word: check them."
        ),
        "no_sources": "The search found no rulings. The document relies on the laws only.",
        "cited": "Quoted in the document",
        "metrics_intro": "Model, tokens and time of each step.",
        "total": "Total: {tokens} tokens in {seconds:.1f} s.",
    },
}

DOCUMENT_NAMES: dict[str, dict[str, str]] = {
    "es": {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"},
    "en": {
        "tutela": "Acción de tutela (constitutional protection action)",
        "derecho_de_peticion": "Derecho de petición (formal petition)",
    },
}
