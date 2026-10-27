"""Fixed parts of the legal documents, filled in by code like a form.

The model only writes the sections that need reasoning (MODEL_SECTIONS). Parties, annexes,
oath, notifications and signature always have the same shape, so code builds them and the
model cannot get them wrong. Contents follow Decreto 2591 de 1991 (arts. 10, 14, 37) and
Ley 1755 de 2015 (art. 16).
"""

import re

from src.schemas import CaseFacts

MODEL_SECTIONS: dict[str, list[str]] = {
    "tutela": [
        "Hechos",
        "Derechos fundamentales vulnerados o amenazados",
        "Pretensiones",
        "Fundamentos de derecho",
    ],
    "derecho_de_peticion": ["Hechos", "Peticiones", "Fundamentos de derecho"],
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


def _eps(facts: CaseFacts) -> str:
    return facts.eps or "[NOMBRE DE LA EPS]"


def _annexes(facts: CaseFacts) -> str:
    annexes = [
        "Copia de la fórmula u orden médica.",
        "Copia de la historia clínica.",
        "Copia de la solicitud presentada a la EPS (si existe).",
        "Copia de la respuesta o negativa de la EPS (si existe).",
        "Copia de la cédula de ciudadanía de quien firma.",
    ]
    if not facts.writer_is_affected_person:
        annexes.append("Copia del documento de identidad del paciente.")
    return "\n".join(f"- {a}" for a in annexes)


def _tutela_header(facts: CaseFacts) -> str:
    parties = [
        "- Accionante: [NOMBRE], identificado(a) con cédula de ciudadanía [CÉDULA], "
        "residente en [CIUDAD DE RESIDENCIA]."
    ]
    if not facts.writer_is_affected_person:
        parties.append(
            "- El accionante actúa como agente oficioso de [NOMBRE DEL PACIENTE], "
            "identificado(a) con documento de identidad [CÉDULA DEL PACIENTE], quien no está "
            "en condiciones de promover su propia defensa porque "
            "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR] (artículo 10 del Decreto 2591 de "
            "1991)."
        )
    parties.append(f"- Accionada: {_eps(facts)}.")
    return (
        "# ACCIÓN DE TUTELA\n\nSeñor(a) Juez de la República (reparto)\n\n## Partes\n"
        + "\n".join(parties)
    )


def _tutela_footer(facts: CaseFacts) -> str:
    return (
        f"## Pruebas y anexos\n{_annexes(facts)}\n\n"
        "## Juramento\nBajo la gravedad del juramento manifiesto que no he presentado otra "
        "acción de tutela respecto de los mismos hechos y derechos (artículo 37 del Decreto "
        "2591 de 1991)."
    )


def _peticion_header(facts: CaseFacts) -> str:
    on_behalf = (
        ""
        if facts.writer_is_affected_person
        else ", a nombre de [NOMBRE DEL PACIENTE], identificado(a) con documento de "
        "identidad [CÉDULA DEL PACIENTE]"
    )
    return (
        f"# DERECHO DE PETICIÓN\n\nSeñores\n{_eps(facts)}\n\n## Peticionario\n"
        "[NOMBRE], identificado(a) con cédula de ciudadanía [CÉDULA], en ejercicio del "
        "derecho de petición (artículo 23 de la Constitución Política y Ley 1755 de 2015)"
        f"{on_behalf}."
    )


def _peticion_footer(facts: CaseFacts) -> str:
    return f"## Anexos\n{_annexes(facts)}"


def _closing() -> str:
    return (
        "## Notificaciones\n"
        "Dirección: [DIRECCIÓN]\nCorreo electrónico: [CORREO ELECTRÓNICO]\nTeléfono: [TELÉFONO]"
        "\n\n## Firma\n[FIRMA]\n[NOMBRE]\nC.C. [CÉDULA]"
    )


def build_document(document_type: str, facts: CaseFacts, sections: dict[str, str]) -> str:
    """Join the fixed parts with the model's sections, in the order the law expects."""
    if document_type == "tutela":
        header, footer = _tutela_header(facts), _tutela_footer(facts)
    else:
        header, footer = _peticion_header(facts), _peticion_footer(facts)
    middle = "\n\n".join(f"## {h}\n{sections[h]}" for h in MODEL_SECTIONS[document_type])
    return "\n\n".join([header, middle, footer, _closing()]) + "\n"
