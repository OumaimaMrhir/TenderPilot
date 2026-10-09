from tenderpilot.graph import analyze


class FlakyWriterLLM:
    """Faux LLM : le premier brouillon invente une capacité, le second est correct."""

    provider = "faux"

    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, system, prompt):
        raise ValueError("pas de JSON : l'extracteur doit se rabattre sur les règles")

    def complete(self, system, prompt, max_tokens=2000):
        self.calls += 1
        ids = [line.split()[1] for line in prompt.splitlines() if line.startswith("- R")]
        body = "\n".join(f"### {i}\nRéponse appuyée sur nos capacités [CAP-01]" for i in ids)
        return body + ("\nAtout supplémentaire [CAP-99]" if self.calls == 1 else "")


def test_pipeline_runs_end_to_end(document, capabilities):
    result = analyze(document, capabilities)
    assert [e.agent for e in result.trace] == ["Extraction", "Correspondance", "Rédaction", "Relecture"]
    assert 0.8 <= result.review.compliance_score < 0.9
    assert result.review.decision == "validation humaine requise"


def test_reviewer_sends_draft_back_to_writer(document, capabilities):
    llm = FlakyWriterLLM()
    result = analyze(document, capabilities, llm)  # type: ignore[arg-type]
    assert result.attempts == 2
    assert [e.agent for e in result.trace].count("Rédaction") == 2
    assert "CAP-99" not in result.draft
    assert result.trace[0].mode == "règles"  # repli automatique de l'extracteur
