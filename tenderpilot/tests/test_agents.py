from tenderpilot.agents import extractor, matcher, reviewer, writer
from tenderpilot.models import Requirement


def test_extractor_finds_requirements_with_categories(document):
    reqs, mode = extractor.extract(document)
    assert mode == "règles"
    assert len(reqs) == 15
    assert {r.category for r in reqs} == {"technique", "administratif", "financier", "RSE", "délai"}
    assert not any("remise des offres" in r.text for r in reqs)  # une information n'est pas une exigence


def test_matcher_detects_a_partial_coverage(capabilities):
    req = Requirement(id="R01", text="Les déchets dangereux doivent être collectés sous 48 heures par un transporteur agréé ADR.")
    match = matcher.match_requirement(req, capabilities)
    assert match.status == "partiel"
    assert "72" in match.justification


def test_matcher_flags_a_gap(capabilities):
    req = Requirement(id="R01", text="Le titulaire doit être opérationnel au plus tard le 1er mars 2027.")
    assert matcher.match_requirement(req, capabilities).status == "non couvert"


def test_reviewer_catches_invented_capability_and_missing_requirement(document, capabilities):
    reqs, _ = extractor.extract(document)
    matches = matcher.match_all(reqs, capabilities)
    draft, _ = writer.write(reqs, matches, capabilities)
    bad_draft = draft.replace("[CAP-04]", "[CAP-99]").replace("### R05", "### ")
    result = reviewer.review(bad_draft, reqs, matches, capabilities)
    kinds = {i.kind for i in result.issues}
    assert "citation_invalide" in kinds
    assert "exigence_oubliee" in kinds
    assert result.decision == "validation humaine requise"
    assert reviewer.needs_rewrite(result)
