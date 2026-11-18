"""Agent relecteur (garde-fou) : vérifie le brouillon avant toute soumission.

- chaque capacité citée doit exister (pas d'invention) ;
- chaque exigence doit être traitée dans le brouillon ;
- les exigences non couvertes ou partielles sont signalées pour arbitrage humain.
"""

from __future__ import annotations

import re

from ..models import Capability, Match, Requirement, Review, ReviewIssue

READY_THRESHOLD = 0.9


def review(draft: str, requirements: list[Requirement], matches: list[Match], capabilities: list[Capability]) -> Review:
    issues: list[ReviewIssue] = []
    known = {c.id for c in capabilities}

    for cited in sorted(set(re.findall(r"\[(CAP-\d+)\]", draft))):
        if cited not in known:
            issues.append(ReviewIssue(kind="citation_invalide", message=f"La capacité {cited} n'existe pas dans la base."))

    for req in requirements:
        if not re.search(rf"\b{re.escape(req.id)}\b", draft):
            issues.append(ReviewIssue(kind="exigence_oubliee", message="Exigence absente du brouillon.", requirement_id=req.id))

    for match in matches:
        if match.status == "non couvert":
            issues.append(
                ReviewIssue(kind="exigence_non_couverte", message=match.justification, requirement_id=match.requirement_id)
            )
        elif match.status == "partiel":
            issues.append(
                ReviewIssue(kind="exigence_partielle", message=match.justification, requirement_id=match.requirement_id)
            )

    total = len(matches) or 1
    score = sum(1.0 if m.status == "couvert" else 0.5 if m.status == "partiel" else 0.0 for m in matches) / total
    blocking = any(i.kind in {"citation_invalide", "exigence_oubliee", "exigence_non_couverte"} for i in issues)
    decision = "prêt à soumettre" if score >= READY_THRESHOLD and not blocking else "validation humaine requise"
    return Review(compliance_score=round(score, 3), decision=decision, issues=issues)


def needs_rewrite(result: Review) -> bool:
    """Seuls les défauts de rédaction justifient une nouvelle rédaction automatique."""
    return any(i.kind in {"citation_invalide", "exigence_oubliee"} for i in result.issues)


def feedback_for(result: Review) -> str:
    return "\n".join(
        f"- {i.message}" + (f" ({i.requirement_id})" if i.requirement_id else "")
        for i in result.issues
        if i.kind in {"citation_invalide", "exigence_oubliee"}
    )
