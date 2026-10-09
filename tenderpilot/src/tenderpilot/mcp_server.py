"""Serveur MCP : expose l'analyse d'appels d'offres comme outils utilisables par un assistant IA
(Claude Desktop, Cursor, ou tout client MCP).

Lancement : python -m tenderpilot.mcp_server
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server import MCPServer

from .graph import analyze, load_capabilities
from .llm import LLMClient

DEFAULT_CAPABILITIES = Path(__file__).resolve().parents[2] / "data" / "capacites_entreprise.yaml"
CAPABILITIES_PATH = os.getenv("TENDERPILOT_CAPABILITIES", str(DEFAULT_CAPABILITIES))

server = MCPServer(
    name="tenderpilot", instructions="Analyse des appels d'offres : exigences, conformité et brouillon de réponse."
)


def _run(document: str):
    return analyze(document, load_capabilities(CAPABILITIES_PATH), LLMClient.from_env())


@server.tool(description="Extrait les exigences d'un cahier des charges et calcule la matrice de conformité.")
def compliance_matrix(document: str) -> dict:
    result = _run(document)
    reqs = {r.id: r for r in result.requirements}
    return {
        "compliance_score": result.review.compliance_score,
        "decision": result.review.decision,
        "matrix": [
            {
                "id": m.requirement_id,
                "exigence": reqs[m.requirement_id].text,
                "categorie": reqs[m.requirement_id].category,
                "statut": m.status,
                "capacites": m.capability_ids,
                "justification": m.justification,
            }
            for m in result.matches
        ],
    }


@server.tool(description="Rédige un brouillon de mémoire technique, relu et vérifié par l'agent relecteur.")
def draft_response(document: str) -> dict:
    result = _run(document)
    return {"draft": result.draft, "decision": result.review.decision, "issues": [i.model_dump() for i in result.review.issues]}


if __name__ == "__main__":
    server.run()
