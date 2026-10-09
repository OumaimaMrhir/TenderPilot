"""Outils de traitement du texte : mots-clés et contraintes chiffrées."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

STOPWORDS = set(
    "le la les un une des de du au aux et ou en dans sur pour par avec sans ce cet cette ces qui que est sont être "
    "doit doivent devra devront il elle ils elles son sa ses leur leurs nos notre vos votre se ne pas plus "
    "titulaire candidat moins minimum maximum tard via chaque lors après avant sous dès afin".split()
)

NUMBER_WORDS = {
    "un": 1,
    "une": 1,
    "deux": 2,
    "trois": 3,
    "quatre": 4,
    "cinq": 5,
    "six": 6,
    "sept": 7,
    "huit": 8,
    "neuf": 9,
    "dix": 10,
}

# Pour ces unités, une valeur plus petite est meilleure (délais) ; pour les autres, plus grande est meilleure.
LOWER_IS_BETTER = {"heure", "heures", "h", "jour", "jours"}
COMPARABLE_UNITS = LOWER_IS_BETTER | {
    "%",
    "fois",
    "benne",
    "bennes",
    "compacteur",
    "compacteurs",
    "marché",
    "marchés",
    "véhicule",
    "véhicules",
}


def strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text) if unicodedata.category(c) != "Mn")


def keywords(text: str) -> set[str]:
    """Mots porteurs de sens, sans accents et réduits à une racine simple (6 lettres)."""
    words = re.findall(r"[a-zà-ÿ0-9]+", text.lower())
    return {strip_accents(w)[:6] for w in words if len(w) > 2 and w not in STOPWORDS and not w.isdigit()}


def similarity(a: str, b: str) -> float:
    """Part des mots-clés de `a` présents dans `b` (rappel lexical)."""
    ka, kb = keywords(a), keywords(b)
    return len(ka & kb) / len(ka) if ka else 0.0


@dataclass(frozen=True)
class Quantity:
    value: float
    unit: str


_QTY = re.compile(r"(\d+(?:[.,]\d+)?|" + "|".join(NUMBER_WORDS) + r")\s*(%|m³|[a-zà-ÿ]+)", re.IGNORECASE)


def quantities(text: str) -> list[Quantity]:
    """Extrait les couples (valeur, unité) : « 48 heures », « 75 % », « trois fois »…"""
    found = []
    for raw_value, unit in _QTY.findall(text):
        raw_value = raw_value.lower()
        value = NUMBER_WORDS.get(raw_value)
        if value is None:
            value = float(raw_value.replace(",", "."))
        found.append(Quantity(float(value), unit.lower()))
    return found


def _same_unit(a: str, b: str) -> bool:
    return a.rstrip("s") == b.rstrip("s")


def check_constraints(requirement: str, capability: str) -> list[str]:
    """Compare les contraintes chiffrées. Renvoie la liste des écarts (vide si tout est respecté)."""
    gaps = []
    offered = [q for q in quantities(capability) if q.unit in COMPARABLE_UNITS]
    for need in (q for q in quantities(requirement) if q.unit in COMPARABLE_UNITS):
        same = [q for q in offered if _same_unit(q.unit, need.unit)]
        if not same:
            continue
        best = min(same, key=lambda q: q.value) if need.unit in LOWER_IS_BETTER else max(same, key=lambda q: q.value)
        ok = best.value <= need.value if need.unit in LOWER_IS_BETTER else best.value >= need.value
        if not ok:
            gaps.append(f"exigé : {need.value:g} {need.unit}, proposé : {best.value:g} {best.unit}")
    return gaps
