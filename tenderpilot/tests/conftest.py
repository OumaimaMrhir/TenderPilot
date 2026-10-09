from pathlib import Path

import pytest

from tenderpilot.graph import load_capabilities

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def document() -> str:
    return (ROOT / "data/dce_gestion_dechets.md").read_text(encoding="utf-8")


@pytest.fixture
def capabilities():
    return load_capabilities(ROOT / "data/capacites_entreprise.yaml")
