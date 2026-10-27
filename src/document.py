"""Fixed parts of the legal documents, filled in by code like a form.

The model only writes the sections that need reasoning (MODEL_SECTIONS). Parties, annexes,
oath, notifications and signature always have the same shape, so code builds them and the
model cannot get them wrong. Contents follow Decreto 2591 de 1991 (arts. 10, 14, 37) and
Ley 1755 de 2015 (art. 16).

Every fixed text is hand-written in each language (no model translates it). The Spanish
version is the one to file; the others help readers who do not speak Spanish.
"""

import re

from src.schemas import CaseFacts

DOCUMENT_NAMES: dict[str, dict[str, str]] = {
    "es": {"tutela": "Acción de tutela", "derecho_de_peticion": "Derecho de petición"},
    "en": {
        "tutela": "Acción de tutela (constitutional protection action)",
        "derecho_de_peticion": "Derecho de petición (formal petition)",
    },
}

MODEL_SECTIONS: dict[str, list[str]] = {
    "tutela": [
        "Hechos",
        "Derechos fundamentales vulnerados o amenazados",
        "Pretensiones",
        "Fundamentos de derecho",
    ],
    "derecho_de_peticion": ["Hechos", "Peticiones", "Fundamentos de derecho"],
}

# Headings of the model's sections in each language (the keys are the Spanish headings).
SECTION_NAMES: dict[str, dict[str, str]] = {
    "es": {heading: heading for headings in MODEL_SECTIONS.values() for heading in headings},
    "en": {
        "Hechos": "Facts",
        "Derechos fundamentales vulnerados o amenazados": "Fundamental rights violated or "
        "threatened",
        "Pretensiones": "Requests to the judge",
        "Peticiones": "Requests",
        "Fundamentos de derecho": "Legal grounds",
    },
}

# The blanks the citizen fills in. Same keys in every language.
PLACEHOLDERS: dict[str, dict[str, str]] = {
    "es": {
        "name": "[NOMBRE]",
        "id": "[CÉDULA]",
        "city": "[CIUDAD DE RESIDENCIA]",
        "patient_name": "[NOMBRE DEL PACIENTE]",
        "patient_id": "[CÉDULA DEL PACIENTE]",
        "patient_reason": "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]",
        "eps": "[NOMBRE DE LA EPS]",
        "address": "[DIRECCIÓN]",
        "email": "[CORREO ELECTRÓNICO]",
        "phone": "[TELÉFONO]",
        "signature": "[FIRMA]",
    },
    "en": {
        "name": "[NAME]",
        "id": "[ID NUMBER]",
        "city": "[CITY OF RESIDENCE]",
        "patient_name": "[PATIENT NAME]",
        "patient_id": "[PATIENT ID NUMBER]",
        "patient_reason": "[REASON THE PATIENT CANNOT ACT]",
        "eps": "[EPS NAME]",
        "address": "[ADDRESS]",
        "email": "[EMAIL]",
        "phone": "[PHONE]",
        "signature": "[SIGNATURE]",
    },
}

# Fixed sentences. {placeholders} are filled from PLACEHOLDERS, {eps} with the insurer.
TEXTS: dict[str, dict[str, str]] = {
    "es": {
        "tutela_title": "# ACCIÓN DE TUTELA",
        "tutela_addressee": "Señor(a) Juez de la República (reparto)",
        "parties": "Partes",
        "petitioner": (
            "- Accionante: {name}, identificado(a) con cédula de ciudadanía {id}, residente "
            "en {city}."
        ),
        "agent": (
            "- El accionante actúa como agente oficioso de {patient_name}, identificado(a) con "
            "documento de identidad {patient_id}, quien no está en condiciones de promover su "
            "propia defensa porque {patient_reason} (artículo 10 del Decreto 2591 de 1991)."
        ),
        "respondent": "- Accionada: {eps}.",
        "evidence": "Pruebas y anexos",
        "oath_title": "Juramento",
        "oath": (
            "Bajo la gravedad del juramento manifiesto que no he presentado otra acción de "
            "tutela respecto de los mismos hechos y derechos (artículo 37 del Decreto 2591 de "
            "1991)."
        ),
        "petition_title": "# DERECHO DE PETICIÓN",
        "petition_addressee": "Señores",
        "petition_petitioner_title": "Peticionario",
        "petition_petitioner": (
            "{name}, identificado(a) con cédula de ciudadanía {id}, en ejercicio del derecho "
            "de petición (artículo 23 de la Constitución Política y Ley 1755 de 2015)"
            "{on_behalf}."
        ),
        "on_behalf": (
            ", a nombre de {patient_name}, identificado(a) con documento de identidad {patient_id}"
        ),
        "annexes": "Anexos",
        "annex_order": "Copia de la fórmula u orden médica.",
        "annex_record": "Copia de la historia clínica.",
        "annex_request": "Copia de la solicitud presentada a la EPS (si existe).",
        "annex_answer": "Copia de la respuesta o negativa de la EPS (si existe).",
        "annex_id": "Copia de la cédula de ciudadanía de quien firma.",
        "annex_patient_id": "Copia del documento de identidad del paciente.",
        "notifications": (
            "## Notificaciones\nDirección: {address}\nCorreo electrónico: {email}\n"
            "Teléfono: {phone}"
        ),
        "signature": "## Firma\n{signature}\n{name}\nC.C. {id}",
    },
    "en": {
        "tutela_title": "# ACCIÓN DE TUTELA (constitutional protection action)",
        "tutela_addressee": "To the Judge of the Republic (case assigned by distribution)",
        "parties": "Parties",
        "petitioner": (
            "- Petitioner (accionante): {name}, holder of citizenship ID card {id}, resident "
            "of {city}."
        ),
        "agent": (
            "- The petitioner acts as agente oficioso (on behalf) of {patient_name}, holder of "
            "identity document {patient_id}, who is unable to defend their own rights because "
            "{patient_reason} (article 10 of Decreto 2591 de 1991)."
        ),
        "respondent": "- Respondent (accionada): {eps}.",
        "evidence": "Evidence and annexes",
        "oath_title": "Oath",
        "oath": (
            "Under oath, I declare that I have not filed another tutela for the same facts and "
            "rights (article 37 of Decreto 2591 de 1991)."
        ),
        "petition_title": "# DERECHO DE PETICIÓN (formal petition)",
        "petition_addressee": "To:",
        "petition_petitioner_title": "Petitioner",
        "petition_petitioner": (
            "{name}, holder of citizenship ID card {id}, exercising the right of petition "
            "(article 23 of the Constitución Política and Ley 1755 de 2015){on_behalf}."
        ),
        "on_behalf": ", on behalf of {patient_name}, holder of identity document {patient_id}",
        "annexes": "Annexes",
        "annex_order": "Copy of the medical prescription or order.",
        "annex_record": "Copy of the medical record.",
        "annex_request": "Copy of the request submitted to the EPS (if any).",
        "annex_answer": "Copy of the EPS's answer or denial (if any).",
        "annex_id": "Copy of the citizenship ID card of the person who signs.",
        "annex_patient_id": "Copy of the patient's identity document.",
        "notifications": "## Notifications\nAddress: {address}\nEmail: {email}\nPhone: {phone}",
        "signature": "## Signature\n{signature}\n{name}\nID {id}",
    },
}

HEADING_PATTERN = re.compile(r"^##\s+(.+?)\s*:?\s*$", re.MULTILINE)


def _heading_key(heading: str) -> str:
    """Compare headings ignoring case and numbering such as '1.'."""
    return re.sub(r"^[\d.\s]+", "", heading).strip().casefold()


def extract_sections(text: str, document_type: str) -> dict[str, str] | None:
    """Keep only the model's allowed sections; None if any of them is missing.

    Anything else the model writes (a title, its own 'Partes', a signature) is dropped.
    """
    wanted = {_heading_key(h): h for h in MODEL_SECTIONS[document_type]}
    matches = list(HEADING_PATTERN.finditer(text))
    found: dict[str, str] = {}
    for i, match in enumerate(matches):
        heading = wanted.get(_heading_key(match.group(1)))
        if heading and heading not in found:
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            found[heading] = text[match.end() : end].strip()
    if any(not found.get(h) for h in MODEL_SECTIONS[document_type]):
        return None
    return found


def localize_placeholders(text: str, lang: str) -> str:
    """Rewrite the Spanish [BLANKS] of a text in `lang` (e.g. [NOMBRE] -> [NAME])."""
    for key, spanish in PLACEHOLDERS["es"].items():
        text = text.replace(spanish, PLACEHOLDERS[lang][key])
    return text


def _text(lang: str, key: str, facts: CaseFacts | None = None, **values: str) -> str:
    """A fixed sentence in `lang`, with its blanks and the EPS name filled in."""
    blanks = PLACEHOLDERS[lang]
    eps = facts.eps if facts and facts.eps else blanks["eps"]
    return TEXTS[lang][key].format(**blanks | {"eps": eps} | values)


def _annexes(facts: CaseFacts, lang: str) -> str:
    keys = ["annex_order", "annex_record", "annex_request", "annex_answer", "annex_id"]
    if not facts.writer_is_affected_person:
        keys.append("annex_patient_id")
    return "\n".join(f"- {_text(lang, key)}" for key in keys)


def _tutela_header(facts: CaseFacts, lang: str) -> str:
    parties = [_text(lang, "petitioner")]
    if not facts.writer_is_affected_person:
        parties.append(_text(lang, "agent"))
    parties.append(_text(lang, "respondent", facts))
    return (
        f"{_text(lang, 'tutela_title')}\n\n{_text(lang, 'tutela_addressee')}\n\n"
        f"## {_text(lang, 'parties')}\n" + "\n".join(parties)
    )


def _tutela_footer(facts: CaseFacts, lang: str) -> str:
    return (
        f"## {_text(lang, 'evidence')}\n{_annexes(facts, lang)}\n\n"
        f"## {_text(lang, 'oath_title')}\n{_text(lang, 'oath')}"
    )


def _peticion_header(facts: CaseFacts, lang: str) -> str:
    on_behalf = "" if facts.writer_is_affected_person else _text(lang, "on_behalf")
    eps = facts.eps or PLACEHOLDERS[lang]["eps"]
    return (
        f"{_text(lang, 'petition_title')}\n\n{_text(lang, 'petition_addressee')}\n{eps}\n\n"
        f"## {_text(lang, 'petition_petitioner_title')}\n"
        + _text(lang, "petition_petitioner", on_behalf=on_behalf)
    )


def _peticion_footer(facts: CaseFacts, lang: str) -> str:
    return f"## {_text(lang, 'annexes')}\n{_annexes(facts, lang)}"


def _closing(lang: str) -> str:
    return f"{_text(lang, 'notifications')}\n\n{_text(lang, 'signature')}"


def build_document(
    document_type: str, facts: CaseFacts, sections: dict[str, str], lang: str = "es"
) -> str:
    """Join the fixed parts with the model's sections, in the order the law expects.

    `sections` is keyed by the Spanish headings; their text must already be in `lang`.
    """
    if document_type == "tutela":
        header, footer = _tutela_header(facts, lang), _tutela_footer(facts, lang)
    else:
        header, footer = _peticion_header(facts, lang), _peticion_footer(facts, lang)
    middle = "\n\n".join(
        f"## {SECTION_NAMES[lang][h]}\n{sections[h]}" for h in MODEL_SECTIONS[document_type]
    )
    return "\n\n".join([header, middle, footer, _closing(lang)]) + "\n"
