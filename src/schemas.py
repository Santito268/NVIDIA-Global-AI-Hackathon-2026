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
    special_protection_reason: str | None = None
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


class DraftDocument(BaseModel):
    """The ready-to-file document (draft step)."""

    title: str
    body_markdown: str
    cited_urls: list[str] = Field(default_factory=list)
