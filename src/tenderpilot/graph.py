"""Orchestration des agents avec LangGraph, avec une trace observable de chaque étape.

extraction -> correspondance -> rédaction -> relecture --(défaut de rédaction ?)--> rédaction
                                                     \\--> fin
"""

from __future__ import annotations

import operator
import time
from collections.abc import Callable
from pathlib import Path
from typing import Annotated, TypedDict

import yaml
from langgraph.graph import END, START, StateGraph

from .agents import extractor, matcher, reviewer, writer
from .llm import LLMClient
from .models import AnalysisResult, Capability, Match, Requirement, Review, TraceEvent

MAX_ATTEMPTS = 2


class State(TypedDict, total=False):
    document: str
    capabilities: list[Capability]
    requirements: list[Requirement]
    matches: list[Match]
    draft: str
    review: Review
    attempts: int
    trace: Annotated[list[TraceEvent], operator.add]


def load_capabilities(path: str | Path) -> list[Capability]:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return [Capability(**item) for item in data["capacites"]]


def _traced(agent: str, fn: Callable[[State], tuple[dict, str, str]]) -> Callable[[State], dict]:
    """Enveloppe un agent : mesure sa durée et ajoute un événement à la trace."""

    def node(state: State) -> dict:
        start = time.perf_counter()
        update, summary, mode = fn(state)
        event = TraceEvent(agent=agent, duration_ms=round((time.perf_counter() - start) * 1000, 2), summary=summary, mode=mode)
        return {**update, "trace": [event]}

    return node


def build_graph(llm: LLMClient | None = None):
    def extract_node(state: State):
        reqs, mode = extractor.extract(state["document"], llm)
        return {"requirements": reqs}, f"{len(reqs)} exigences extraites", mode

    def match_node(state: State):
        matches = matcher.match_all(state["requirements"], state["capabilities"])
        counts = {s: sum(m.status == s for m in matches) for s in ("couvert", "partiel", "non couvert")}
        return {"matches": matches}, ", ".join(f"{n} {s}" for s, n in counts.items()), "règles"

    def write_node(state: State):
        feedback = reviewer.feedback_for(state["review"]) if state.get("review") else ""
        draft, mode = writer.write(state["requirements"], state["matches"], state["capabilities"], llm, feedback)
        attempts = state.get("attempts", 0) + 1
        return {"draft": draft, "attempts": attempts}, f"brouillon v{attempts} ({len(draft.split())} mots)", mode

    def review_node(state: State):
        result = reviewer.review(state["draft"], state["requirements"], state["matches"], state["capabilities"])
        return (
            {"review": result},
            f"score {result.compliance_score:.0%} – {result.decision} – {len(result.issues)} points",
            "règles",
        )

    def route_after_review(state: State) -> str:
        if reviewer.needs_rewrite(state["review"]) and state.get("attempts", 0) < MAX_ATTEMPTS:
            return "rédaction"
        return END

    graph = StateGraph(State)
    graph.add_node("extraction", _traced("Extraction", extract_node))
    graph.add_node("correspondance", _traced("Correspondance", match_node))
    graph.add_node("rédaction", _traced("Rédaction", write_node))
    graph.add_node("relecture", _traced("Relecture", review_node))
    graph.add_edge(START, "extraction")
    graph.add_edge("extraction", "correspondance")
    graph.add_edge("correspondance", "rédaction")
    graph.add_edge("rédaction", "relecture")
    graph.add_conditional_edges("relecture", route_after_review, {"rédaction": "rédaction", END: END})
    return graph.compile()


def analyze(document: str, capabilities: list[Capability], llm: LLMClient | None = None) -> AnalysisResult:
    final = build_graph(llm).invoke({"document": document, "capabilities": capabilities, "attempts": 0, "trace": []})
    return AnalysisResult(
        requirements=final["requirements"],
        matches=final["matches"],
        draft=final["draft"],
        review=final["review"],
        trace=final["trace"],
        attempts=final["attempts"],
    )
