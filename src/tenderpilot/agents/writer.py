"""Agent de rédaction : produit un mémoire technique structuré, chaque affirmation citant sa capacité."""

from __future__ import annotations

from collections import defaultdict

from ..llm import LLMClient
from ..models import Capability, Match, Requirement

SYSTEM = (
    "Tu rédiges le mémoire technique d'une réponse à appel d'offres. Pour chaque exigence, rédige une réponse "
    "concise et professionnelle en t'appuyant UNIQUEMENT sur les capacités fournies, et cite la capacité entre "
    "crochets, par exemple [CAP-03]. N'invente aucune capacité. Pour une exigence non couverte, écris « À compléter "
    "par l'équipe » ; pour une exigence partielle, signale l'écart et propose une action. Structure en Markdown, "
    "une section par catégorie, chaque exigence en titre de niveau 3 précédé de son identifiant (ex. ### R03)."
)

ORDER = ["technique", "administratif", "financier", "RSE", "délai", "autre"]


def write_rules(requirements: list[Requirement], matches: list[Match], capabilities: list[Capability]) -> str:
    caps = {c.id: c for c in capabilities}
    by_req = {m.requirement_id: m for m in matches}
    sections: dict[str, list[str]] = defaultdict(list)
    for req in requirements:
        match = by_req[req.id]
        lines = [f"### {req.id} – {req.text}"]
        if match.status == "non couvert":
            lines.append("**À compléter par l'équipe** : aucune capacité documentée ne répond à cette exigence.")
        else:
            cap = caps[match.capability_ids[0]]
            lines.append(f"{cap.description} [{cap.id}]")
            if match.status == "partiel":
                lines.append(f"**Point d'attention** : {match.justification} Action à arbitrer avant la remise de l'offre.")
        sections[req.category].append("\n\n".join(lines))
    out = ["# Mémoire technique – projet de réponse"]
    for category in ORDER:
        if sections[category]:
            out.append(f"## {category.capitalize()}")
            out.extend(sections[category])
    return "\n\n".join(out) + "\n"


def write_llm(
    requirements: list[Requirement], matches: list[Match], capabilities: list[Capability], llm: LLMClient, feedback: str = ""
) -> str:
    by_req = {m.requirement_id: m for m in matches}
    lines = ["Capacités :"] + [f"- {c.id} : {c.titre} – {c.description}" for c in capabilities]
    lines.append("\nExigences et statut :")
    for r in requirements:
        m = by_req[r.id]
        lines.append(f"- {r.id} [{r.category}] {r.text} -> {m.status} {m.capability_ids} ({m.justification})")
    if feedback:
        lines.append(f"\nCorrections demandées par le relecteur :\n{feedback}")
    return llm.complete(SYSTEM, "\n".join(lines), max_tokens=3000)


def write(
    requirements: list[Requirement],
    matches: list[Match],
    capabilities: list[Capability],
    llm: LLMClient | None = None,
    feedback: str = "",
) -> tuple[str, str]:
    if llm:
        try:
            return write_llm(requirements, matches, capabilities, llm, feedback), f"llm:{llm.provider}"
        except Exception:
            pass
    return write_rules(requirements, matches, capabilities), "règles"
