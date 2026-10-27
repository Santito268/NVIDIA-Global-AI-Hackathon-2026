"""Tests for the fixed parts of the documents that code builds (no model involved)."""

import pytest

from src import agent, config, document, prompts
from src.llm import CallMetrics, LLMError
from src.schemas import CaseFacts, RouteDecision

MIDDLE = {
    "tutela": "## Hechos\n1. x\n\n## Derechos fundamentales vulnerados o amenazados\n- y\n\n"
    "## Pretensiones\n1. z\n\n## Fundamentos de derecho\n- w\n",
    "derecho_de_peticion": "## Hechos\n1. x\n\n## Peticiones\n1. z\n\n"
    "## Fundamentos de derecho\n- w\n",
}


@pytest.fixture(autouse=True)
def mock_mode(monkeypatch):
    monkeypatch.setattr(config, "LLM_MODE", "mock")


def _facts(writer_is_affected_person: bool, eps: str | None = None) -> CaseFacts:
    return CaseFacts(
        eps=eps,
        problem_type="medicine_denied",
        events_summary="x",
        urgent_health_risk=True,
        special_protection=False,
        writer_is_affected_person=writer_is_affected_person,
    )


def _build(document_type: str, facts: CaseFacts) -> str:
    sections = document.extract_sections(MIDDLE[document_type], document_type)
    return document.build_document(document_type, facts, sections)


def test_tutela_for_a_relative_names_the_agente_oficioso():
    text = _build("tutela", _facts(writer_is_affected_person=False))
    assert "El accionante actúa como agente oficioso de [NOMBRE DEL PACIENTE]" in text
    assert "[RAZÓN POR LA QUE EL PACIENTE NO PUEDE ACTUAR]" in text
    assert "artículo 10 del Decreto 2591 de 1991" in text
    assert "Accionada: [NOMBRE DE LA EPS]." in text
    assert "Copia del documento de identidad del paciente." in text


def test_tutela_written_by_the_patient_has_no_agente_oficioso():
    text = _build("tutela", _facts(writer_is_affected_person=True, eps="EPS Ejemplo"))
    assert "agente oficioso" not in text
    assert "[NOMBRE DEL PACIENTE]" not in text
    assert "Accionada: EPS Ejemplo." in text


def test_tutela_sections_follow_the_legal_order():
    text = _build("tutela", _facts(writer_is_affected_person=True))
    order = ["# ACCIÓN DE TUTELA", "## Partes", "## Hechos", "## Derechos fundamentales",
             "## Pretensiones", "## Fundamentos de derecho", "## Pruebas y anexos",
             "## Juramento", "## Notificaciones", "## Firma"]  # fmt: skip
    positions = [text.index(heading) for heading in order]
    assert positions == sorted(positions)
    assert "artículo 37 del Decreto 2591 de 1991" in text


def test_peticion_for_a_relative_says_on_whose_behalf():
    text = _build("derecho_de_peticion", _facts(writer_is_affected_person=False))
    assert text.startswith("# DERECHO DE PETICIÓN")
    assert "a nombre de [NOMBRE DEL PACIENTE]" in text
    assert "## Juramento" not in text


def test_extract_sections_drops_what_the_model_must_not_write():
    text = "# TÍTULO\n## Partes\n- Accionado mal escrito\n\n" + MIDDLE["tutela"] + "## Firma\nX"
    sections = document.extract_sections(text, "tutela")
    assert list(sections) == document.MODEL_SECTIONS["tutela"]
    assert all("Accionado" not in s and "X" != s for s in sections.values())


def test_extract_sections_accepts_numbered_headings_and_colons():
    text = MIDDLE["derecho_de_peticion"].replace("## Peticiones", "## 2. Peticiones:")
    assert document.extract_sections(text, "derecho_de_peticion") is not None


def test_extract_sections_returns_none_when_a_section_is_missing():
    assert document.extract_sections("## Hechos\n1. x", "tutela") is None


def test_every_model_section_is_named_in_the_draft_prompt():
    for headings in document.MODEL_SECTIONS.values():
        for heading in headings:
            assert f"## {heading}" in prompts.DRAFT_SYSTEM


def test_draft_retries_once_then_fails_clearly(monkeypatch):
    calls = []

    def fake_chat(*args, **kwargs):
        calls.append(1)
        return "## Hechos\n1. x", CallMetrics("draft", "m", 0, 0, 0)

    monkeypatch.setattr(agent, "chat", fake_chat)
    route = RouteDecision(document_type="tutela", reason="x")
    with pytest.raises(LLMError):
        agent.run_draft(_facts(writer_is_affected_person=True), route, [])
    assert len(calls) == 2


def test_mock_draft_discards_the_wrong_parties_written_by_the_model():
    body = agent.run_case("Mi papá no recibe su insulina.").draft.body_markdown
    assert "Accionado" not in body
    assert body.count("## Partes") == 1 and body.count("# ACCIÓN DE TUTELA") == 1
    assert "El accionante actúa como agente oficioso" in body
