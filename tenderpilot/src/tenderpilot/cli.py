"""Ligne de commande : python -m tenderpilot.cli data/dce_gestion_dechets.md"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .graph import analyze, load_capabilities
from .llm import LLMClient


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyse un appel d'offres avec un système multi-agents.")
    parser.add_argument("document", help="Cahier des charges (Markdown ou texte)")
    parser.add_argument("--capabilities", default="data/capacites_entreprise.yaml")
    parser.add_argument("--out", default="reponse.md", help="Brouillon du mémoire technique")
    parser.add_argument("--trace", default="trace.json", help="Trace d'exécution et matrice de conformité (JSON)")
    args = parser.parse_args()

    result = analyze(Path(args.document).read_text(encoding="utf-8"), load_capabilities(args.capabilities), LLMClient.from_env())
    Path(args.out).write_text(result.draft, encoding="utf-8")
    Path(args.trace).write_text(json.dumps(result.model_dump(), ensure_ascii=False, indent=2), encoding="utf-8")

    for event in result.trace:
        print(f"[{event.agent:<14}] {event.duration_ms:>7.1f} ms  ({event.mode})  {event.summary}")
    print(f"\nConformité : {result.review.compliance_score:.0%} – {result.review.decision}")
    for issue in result.review.issues:
        print(f"  - {issue.requirement_id or '':<4} {issue.kind} : {issue.message}")
    print(f"\nBrouillon : {args.out}  |  Trace : {args.trace}")


if __name__ == "__main__":
    main()
