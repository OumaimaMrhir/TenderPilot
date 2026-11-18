"""Agent de correspondance : confronte chaque exigence aux capacités de l'entreprise."""

from __future__ import annotations

from ..models import Capability, Match, Requirement
from ..text import check_constraints, similarity

COVERED_THRESHOLD = 0.34


def match_requirement(requirement: Requirement, capabilities: list[Capability]) -> Match:
    scored = sorted(
        ((similarity(requirement.text, f"{c.titre} {c.description}"), c) for c in capabilities),
        key=lambda item: item[0],
        reverse=True,
    )
    best_score, best = scored[0] if scored else (0.0, None)
    if best is None or best_score < COVERED_THRESHOLD:
        return Match(
            requirement_id=requirement.id,
            status="non couvert",
            score=round(best_score, 2),
            justification="Aucune capacité ne répond à cette exigence.",
        )
    gaps = check_constraints(requirement.text, best.description)
    if gaps:
        return Match(
            requirement_id=requirement.id,
            status="partiel",
            capability_ids=[best.id],
            score=round(best_score, 2),
            justification="Capacité existante mais insuffisante (" + "; ".join(gaps) + ").",
        )
    return Match(
        requirement_id=requirement.id,
        status="couvert",
        capability_ids=[best.id],
        score=round(best_score, 2),
        justification=f"Couvert par {best.id} – {best.titre}.",
    )


def match_all(requirements: list[Requirement], capabilities: list[Capability]) -> list[Match]:
    return [match_requirement(r, capabilities) for r in requirements]
