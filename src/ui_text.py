"""Fixed interface texts, one dictionary per language (no model involved).

Every language must have the same keys (a test checks it). To add a language, copy the
"en" block, translate it and add the language to config.LANGUAGES.
"""

UI_TEXT: dict[str, dict[str, str]] = {
    "es": {
        "title": "Subvenio",
        "tagline": (
            "Tu tutela o derecho de petición contra la EPS, listo en minutos. Con base legal "
            "verificada y explicado en palabras simples."
        ),
        "hero_badge": "Con tecnología de NVIDIA Nemotron · Nebius · Tavily",
        "stat_eval": "casos de prueba superados",
        "stat_laws": "artículos de ley verificados",
        "stat_time": "segundos por documento",
        "how_title": "Cómo funciona",
        "how_1_title": "Cuéntanos qué pasó",
        "how_1_text": "Con tus palabras, como se lo contarías a un amigo. Sin datos personales.",
        "how_2_title": "Nemotron revisa la ley",
        "how_2_text": (
            "Elige el documento, busca sentencias en sitios oficiales y redacta solo con citas "
            "verificadas."
        ),
        "how_3_title": "Revisa y radica",
        "how_3_text": "Llena los espacios en blanco y preséntalo. No necesitas abogado.",
        "legal_title": "No es asesoría legal",
        "legal_text": (
            "Es una herramienta de apoyo: revisa el documento y, si puedes, consúltalo con un "
            "abogado o un consultorio jurídico antes de radicarlo."
        ),
        "privacy_title": "Tu privacidad",
        "privacy_text": (
            "Lo que escribes se envía a Nemotron (en Nebius) para procesarlo. No escribas "
            "nombres, cédulas, direcciones ni teléfonos: el documento trae espacios en blanco."
        ),
        "mock_notice": "Modo demostración: las respuestas son de ejemplo y no se usa la IA.",
        "case_title": "Describe tu caso",
        "samples_label": "¿No sabes por dónde empezar? Prueba un ejemplo:",
        "sample_1": "💊 Insulina de un adulto mayor",
        "sample_2": "🧒 Cirugía de una niña",
        "sample_3": "🩺 Cita con dermatología",
        "input_label": "¿Qué pasó con tu EPS?",
        "input_placeholder": (
            "Ejemplo: A mi papá de 72 años le formularon insulina hace tres semanas y la EPS "
            "no se la ha entregado..."
        ),
        "input_language_note": "",
        "generate_button": "Generar mi documento",
        "empty_input": "Escribe qué pasó con tu EPS antes de generar el documento.",
        "limit_reached": (
            "Llegaste al límite de {limit} casos de esta demostración. Gracias por probarla."
        ),
        "cases_left": "Casos disponibles en esta sesión: {left} de {limit}.",
        "daily_limit_reached": (
            "La demostración llegó a su límite de casos por hoy. Vuelve mañana, por favor."
        ),
        "status_running": "Preparando tu documento",
        "status_done": "¡Listo! Tu documento está abajo.",
        "wait_notice": "Esto suele tardar entre 30 y 60 segundos. No cierres la página.",
        "step_intake": "Entendiendo tu caso",
        "step_research": "Buscando sentencias en sitios oficiales",
        "step_draft": "Redactando el documento",
        "step_explain": "Explicándolo en palabras simples",
        "error_message": "Algo falló. Intenta de nuevo en un momento.",
        "error_generic": "Ocurrió un error inesperado en el servicio de IA.",
        "error_config": "La app no está bien configurada (faltan claves). Avísale a quien la "
        "administra.",
        "error_timeout": "El modelo tardó demasiado en responder.",
        "error_connection": "No se pudo conectar con Nebius Token Factory.",
        "error_invalid": "El modelo devolvió una respuesta que no se pudo leer.",
        "error_incomplete": "El modelo devolvió un documento incompleto.",
        "error_search_failed": "La búsqueda en sitios oficiales falló.",
        "error_search_limit": "Se acabaron las búsquedas web gratuitas de este mes.",
        "result_title": "Tu documento está listo",
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
        "metric_tokens": "Tokens usados",
        "metric_time": "Tiempo del modelo",
        "metric_calls": "Llamadas a Nemotron",
        "col_step": "paso",
        "col_model": "modelo",
        "col_prompt_tokens": "tokens de entrada",
        "col_completion_tokens": "tokens de salida",
        "col_latency": "tiempo (s)",
        "total": "Total: {tokens} tokens en {seconds:.1f} s.",
        "footer": (
            "Subvenio es un proyecto para el Nebius x NVIDIA Global AI Hackathon 2026. "
            "No es asesoría legal."
        ),
        "footer_code": "Código en GitHub",
    },
    "en": {
        "title": "Subvenio",
        "tagline": (
            "Your tutela or formal petition against your Colombian health insurer (EPS), ready "
            "in minutes. With verified legal grounds, explained in plain words."
        ),
        "hero_badge": "Powered by NVIDIA Nemotron · Nebius · Tavily",
        "stat_eval": "test cases passed",
        "stat_laws": "verified legal articles",
        "stat_time": "seconds per document",
        "how_title": "How it works",
        "how_1_title": "Tell us what happened",
        "how_1_text": "In your own words, as you would tell a friend. No personal data.",
        "how_2_title": "Nemotron checks the law",
        "how_2_text": (
            "It picks the document, searches official sites for court rulings and writes with "
            "verified quotes only."
        ),
        "how_3_title": "Review and file",
        "how_3_text": "Fill in the blanks and file it. No lawyer needed.",
        "legal_title": "This is not legal advice",
        "legal_text": (
            "It is a support tool: review the document and, if you can, check it with a lawyer "
            "or a free legal clinic before filing it."
        ),
        "privacy_title": "Your privacy",
        "privacy_text": (
            "What you write is sent to Nemotron (on Nebius) to be processed. Do not write "
            "names, ID numbers, addresses or phone numbers: the document has blanks for them."
        ),
        "mock_notice": "Demo mode: answers are examples and no AI is used.",
        "case_title": "Describe your case",
        "samples_label": "Not sure where to start? Try an example:",
        "sample_1": "💊 Insulin for an older adult",
        "sample_2": "🧒 Surgery for a child",
        "sample_3": "🩺 Dermatology appointment",
        "input_label": "What happened with your EPS?",
        "input_placeholder": (
            "Example: My 72-year-old father was prescribed insulin three weeks ago and the EPS "
            "has not delivered it..."
        ),
        "input_language_note": (
            "The document is written in Spanish, the language of Colombian courts. The examples "
            "are shown in English and the app sends their Spanish original. If you write your "
            "own case, please write it in Spanish."
        ),
        "generate_button": "Generate my document",
        "empty_input": "Describe what happened with your EPS before generating the document.",
        "limit_reached": (
            "You reached the limit of {limit} cases for this demo. Thanks for trying it."
        ),
        "cases_left": "Cases left in this session: {left} of {limit}.",
        "daily_limit_reached": (
            "The demo reached its case limit for today. Please come back tomorrow."
        ),
        "status_running": "Preparing your document",
        "status_done": "Done! Your document is below.",
        "wait_notice": "This usually takes 30 to 60 seconds. Please keep the page open.",
        "step_intake": "Understanding your case",
        "step_research": "Searching rulings on official sites",
        "step_draft": "Writing the document",
        "step_explain": "Explaining it in plain words",
        "error_message": "Something went wrong. Please try again in a moment.",
        "error_generic": "An unexpected error happened in the AI service.",
        "error_config": "The app is not configured correctly (missing keys). Please tell its "
        "administrator.",
        "error_timeout": "The model took too long to answer.",
        "error_connection": "Could not connect to Nebius Token Factory.",
        "error_invalid": "The model returned an answer that could not be read.",
        "error_incomplete": "The model returned an incomplete document.",
        "error_search_failed": "The search on official sites failed.",
        "error_search_limit": "The free web searches for this month are used up.",
        "result_title": "Your document is ready",
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
        "metric_tokens": "Tokens used",
        "metric_time": "Model time",
        "metric_calls": "Nemotron calls",
        "col_step": "step",
        "col_model": "model",
        "col_prompt_tokens": "input tokens",
        "col_completion_tokens": "output tokens",
        "col_latency": "time (s)",
        "total": "Total: {tokens} tokens in {seconds:.1f} s.",
        "footer": (
            "Subvenio is a project for the Nebius x NVIDIA Global AI Hackathon 2026. "
            "It is not legal advice."
        ),
        "footer_code": "Code on GitHub",
    },
}

DOCUMENT_NAMES: dict[str, dict[str, str]] = {
    "es": {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"},
    "en": {
        "tutela": "Acción de tutela (constitutional protection action)",
        "derecho_de_peticion": "Derecho de petición (formal petition)",
    },
}
