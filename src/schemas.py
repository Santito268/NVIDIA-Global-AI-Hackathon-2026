"""Pydantic models for every structured output of the pipeline."""

from typing import Literal

from pydantic import BaseModel, Field


class CaseFacts(BaseModel):
    """Facts extracted from the user's plain-language description (intake step)."""

    eps: str | None = Field(None, description="Name of the health insurer (EPS)")
    problem_type: Literal[
        "medicine_denied", "appointment_not_scheduled", "authorization_delayed", "other"
    ]
    service_requested: str | None = Field(None, description="Medicine, procedure or appointment")
    events_summary: str = Field(description="Short neutral summary of what happened")
    relevant_dates: list[str] = Field(default_factory=list)
    urgent_health_risk: bool = Field(description="True if delay risks the person's health or life")
    special_protection: bool = Field(description="Minor, older adult, disability, pregnancy, etc.")
    # A fixed list (not free text) so the app can name the group in every language.
    special_protection_group: (
        Literal["child", "older_adult", "disability", "pregnancy", "serious_illness"] | None
    ) = None
    # No default on purpose: the model must decide it (it changes who files the tutela).
    writer_is_affected_person: bool = Field(
        description="False if someone writes on behalf of the affected person (agencia oficiosa)"
    )
    writer_relationship: str | None = Field(
        None, description="Relationship of the writer to the affected person, e.g. 'hijo/a'"
    )
    missing_info: list[str] = Field(default_factory=list)


class RouteDecision(BaseModel):
    """Which legal document fits the case (route step)."""

    document_type: Literal["derecho_de_peticion", "tutela"]
    reason: str


class SearchPlan(BaseModel):
    """The web searches Nemotron Super wants to run (research step)."""

    queries: list[str] = Field(min_length=1)


class Source(BaseModel):
    """A web source found during research."""

    title: str
    url: str
    snippet: str


class Explanation(BaseModel):
    """Plain-language explanation of the document for the citizen (explain step)."""

    summary: str = Field(description="3-4 simple sentences: what the document is and asks")
    key_points: list[str] = Field(min_length=1, max_length=4)


class ExplanationText(BaseModel):
    """The case-specific texts of the explanation tab: the only parts the model translates."""

    summary: str
    key_points: list[str] = Field(min_length=1, max_length=4)


class DraftDocument(BaseModel):
    """The ready-to-file document (draft step)."""

    title: str
    body_markdown: str
    # The model's checked sections, keyed by Spanish heading: the only parts ever translated.
    sections: dict[str, str] = Field(default_factory=dict)
    cited_urls: list[str] = Field(default_factory=list)
