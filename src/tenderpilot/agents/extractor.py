"""Agent d'extraction : repère les exigences du cahier des charges et les classe par catégorie."""

from __future__ import annotations

import re

from ..llm import LLMClient
from ..models import Requirement

OBLIGATION = re.compile(
    r"\b(doit|doivent|devra|devront|obligatoire|exigée?s?|est exigé|au minimum|au moins|minimum|au plus tard)\b", re.IGNORECASE
)

SECTION_CATEGORIES = [
    ("technique", "technique"),
    ("administrati", "administratif"),
    ("financi", "financier"),
    ("rse", "RSE"),
    ("environnement", "RSE"),
    ("délai", "délai"),
    ("planning", "délai"),
]

SYSTEM = (
    "Tu es un expert en réponse aux appels d'offres. Extrais chaque exigence imposée au candidat ou au titulaire. "
    'Format : liste JSON d\'objets {"text": str, "category": "technique|administratif|financier|RSE|délai|autre", '
    '"mandatory": bool}. Reformule chaque exigence en une phrase courte et fidèle.'
)


def _category_for(heading: str) -> str:
    heading = heading.lower()
    for marker, category in SECTION_CATEGORIES:
        if marker in heading:
            return category
    return "autre"


def extract_rules(document: str) -> list[Requirement]:
    """Extraction déterministe : phrases contenant une obligation, catégorie déduite du titre de section."""
    requirements: list[Requirement] = []
    category = "autre"
    for line in document.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            category = _category_for(line)
            continue
        for sentence in re.split(r"(?<=[.!?])\s+", line):
            if OBLIGATION.search(sentence):
                requirements.append(
                    Requirement(id=f"R{len(requirements) + 1:02d}", text=sentence.strip(), category=category)  # type: ignore[arg-type]
                )
    return requirements


def extract_llm(document: str, llm: LLMClient) -> list[Requirement]:
    items = llm.complete_json(SYSTEM, document)
    if not isinstance(items, list):
        raise ValueError("Format inattendu")
    return [
        Requirement(
            id=f"R{i:02d}", text=item["text"], category=item.get("category", "autre"), mandatory=item.get("mandatory", True)
        )
        for i, item in enumerate(items, start=1)
    ]


def extract(document: str, llm: LLMClient | None = None) -> tuple[list[Requirement], str]:
    if llm:
        try:
            return extract_llm(document, llm), f"llm:{llm.provider}"
        except Exception:  # repli sûr : on ne bloque jamais le pipeline sur une réponse LLM invalide
            pass
    return extract_rules(document), "règles"
