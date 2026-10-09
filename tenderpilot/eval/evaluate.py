"""Évaluation du pipeline sur un appel d'offres annoté à la main.

- Extraction : précision, rappel et F1 des exigences trouvées.
- Conformité : exactitude du statut (couvert / partiel / non couvert).

Usage : python eval/evaluate.py
"""

from __future__ import annotations

import json
from pathlib import Path

from tenderpilot.graph import analyze, load_capabilities
from tenderpilot.llm import LLMClient
from tenderpilot.text import similarity

ROOT = Path(__file__).resolve().parents[1]
MATCH_THRESHOLD = 0.5


def main() -> None:
    gold = json.loads((ROOT / "eval/gold_requirements.json").read_text(encoding="utf-8"))
    result = analyze(
        (ROOT / "data/dce_gestion_dechets.md").read_text(encoding="utf-8"),
        load_capabilities(ROOT / "data/capacites_entreprise.yaml"),
        LLMClient.from_env(),
    )
    statuses = {m.requirement_id: m.status for m in result.matches}

    matched_gold, used, correct_status = 0, set(), 0
    for item in gold:
        candidates = [(similarity(item["text"], r.text), r) for r in result.requirements if r.id not in used]
        score, best = max(candidates, key=lambda c: c[0], default=(0.0, None))
        if best is None or score < MATCH_THRESHOLD:
            print(f"[MANQUÉE ] {item['text']}")
            continue
        used.add(best.id)
        matched_gold += 1
        ok = statuses[best.id] == item["expected_status"]
        correct_status += ok
        flag = "OK" if ok else f"statut {statuses[best.id]} ≠ {item['expected_status']}"
        print(f"[{best.id:>8}] {flag:<28} {item['text']}")

    precision = matched_gold / len(result.requirements) if result.requirements else 0.0
    recall = matched_gold / len(gold)
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = correct_status / matched_gold if matched_gold else 0.0
    print(
        f"\nExtraction  – précision {precision:.0%} | rappel {recall:.0%} | F1 {f1:.2f}"
        f"\nConformité  – exactitude des statuts {accuracy:.0%} ({correct_status}/{matched_gold})"
        f"\nRelecture   – score {result.review.compliance_score:.0%}, décision : {result.review.decision}"
    )


if __name__ == "__main__":
    main()
