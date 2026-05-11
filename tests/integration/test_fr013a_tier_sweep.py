"""Integration regression for FR-013a (tier-determinism sweep).

Models the real bug observed on case `busca-todos-los-eventos-producidos-por-fever-originals-en/`:
agents wrote literal `tier: A` for non-registry domains and omitted `tier` entirely on others.
The orchestrator-side sweep (`enforce_tiers`) MUST overwrite invented tiers with
deterministic results from `assign_tier()`, fill missing tiers, and mark malformed URLs as
extraction_failed without losing them.

No live network calls. Loads a fixture agent JSON, runs the sweep, asserts.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.score_source import enforce_tiers

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fr013a"

TIERS_YAML = """\
domains:
  nature.com:
    tier: A
  reddit.com:
    tier: C
"""

GRAPH_YAML = """\
parents:
  nature.com: "springer-nature"
  reddit.com: "reddit"
"""


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "source-tiers.yaml").write_text(TIERS_YAML, encoding="utf-8")
    (tmp_path / "publisher-graph.yaml").write_text(GRAPH_YAML, encoding="utf-8")
    return tmp_path


def _load_fixture() -> dict:
    return json.loads((FIXTURES / "agent_invented_tier.json").read_text())


def test_sweep_overwrites_invented_tier_a_to_unknown(data_dir: Path):
    j = _load_fixture()
    summary = enforce_tiers([j], data_dir=data_dir)
    sources = j["fields"]["summary"]["sources"]
    assert sources[0]["tier"] == "Unknown"
    assert sources[0]["unclassified"] is True
    assert "score_raw" in sources[0]
    assert summary["corrected"] >= 1


def test_sweep_keeps_real_tier_a_from_registry(data_dir: Path):
    j = _load_fixture()
    enforce_tiers([j], data_dir=data_dir)
    sources = j["fields"]["summary"]["sources"]
    assert sources[1]["tier"] == "A"
    assert sources[1]["unclassified"] is False
    assert sources[1]["tier_source"] == "registry"


def test_sweep_fills_missing_tier_field(data_dir: Path):
    j = _load_fixture()
    enforce_tiers([j], data_dir=data_dir)
    reddit_src = j["fields"]["summary"]["sources"][2]
    assert reddit_src["tier"] == "C"
    assert reddit_src["unclassified"] is False


def test_sweep_marks_empty_url_extraction_failed(data_dir: Path):
    j = _load_fixture()
    summary = enforce_tiers([j], data_dir=data_dir)
    broken = j["fields"]["summary"]["sources"][3]
    assert broken.get("extraction_failed") is True
    assert summary["malformed"] == 1


def test_sweep_is_idempotent(data_dir: Path):
    j = _load_fixture()
    s1 = enforce_tiers([j], data_dir=data_dir)
    s2 = enforce_tiers([j], data_dir=data_dir)
    assert s1["corrected"] >= 1
    assert s2["corrected"] == 0
    assert s2["unchanged"] >= 2  # at least the two valid sources


def test_sweep_summary_includes_agent_id(data_dir: Path):
    j = _load_fixture()
    summary = enforce_tiers([j], data_dir=data_dir)
    assert "test subquery" in summary["by_agent"]
    assert summary["by_agent"]["test subquery"] >= 1
