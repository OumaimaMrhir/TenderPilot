"""Modèles de données partagés par les agents."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Category = Literal["technique", "administratif", "financier", "RSE", "délai", "autre"]
Status = Literal["couvert", "partiel", "non couvert"]


class Requirement(BaseModel):
    id: str
    text: str
    category: Category = "autre"
    mandatory: bool = True


class Capability(BaseModel):
    id: str
    titre: str
    description: str


class Match(BaseModel):
    requirement_id: str
    status: Status
    capability_ids: list[str] = Field(default_factory=list)
    score: float = 0.0
    justification: str = ""


class ReviewIssue(BaseModel):
    kind: Literal["citation_invalide", "exigence_non_couverte", "exigence_partielle", "exigence_oubliee"]
    message: str
    requirement_id: str | None = None


class Review(BaseModel):
    compliance_score: float
    decision: Literal["prêt à soumettre", "validation humaine requise"]
    issues: list[ReviewIssue] = Field(default_factory=list)


class TraceEvent(BaseModel):
    agent: str
    duration_ms: float
    summary: str
    mode: str = "règles"


class AnalysisResult(BaseModel):
    requirements: list[Requirement]
    matches: list[Match]
    draft: str
    review: Review
    trace: list[TraceEvent]
    attempts: int
