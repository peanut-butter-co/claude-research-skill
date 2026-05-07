from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from scripts.score_source import (
    apply_cross_citation_bonus,
    assign_tier,
    compare_sources,
    get_publisher,
    score_source,
)


TIERS_YAML = """\
domains:
  nature.com:
    tier: A
    notes: "Nature"
  nytimes.com:
    tier: B
    notes: "NYT"
  reddit.com:
    tier: C
  ehow.com:
    tier: D
"""

GRAPH_YAML = """\
parents:
  nature.com: "springer-nature"
  scientificamerican.com: "springer-nature"
  nytimes.com: "nyt-company"
  thewirecutter.com: "nyt-company"
  bbc.com: "bbc"
  bbc.co.uk: "bbc"
"""


@pytest.fixture
def data_dir(tmp_path: Path) -> Path:
    (tmp_path / "source-tiers.yaml").write_text(TIERS_YAML, encoding="utf-8")
    (tmp_path / "publisher-graph.yaml").write_text(GRAPH_YAML, encoding="utf-8")
    return tmp_path


def _iso_days_ago(days: int) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days)
    return dt.date().isoformat()


def test_assign_tier_known_domain_from_registry(data_dir: Path):
    result = assign_tier("https://www.nature.com/articles/abc", data_dir=data_dir)
    assert result["tier"] == "A"
    assert result["source"] == "registry"
    assert result["unclassified"] is False
    assert result["heuristic_flags"] == []


def test_assign_tier_unknown_domain_marks_unclassified(data_dir: Path):
    result = assign_tier("https://random-blog-xyz.example/post", data_dir=data_dir)
    assert result["tier"] == "Unknown"
    assert result["source"] == "heuristic"
    assert result["unclassified"] is True


def test_assign_tier_edu_pushed_to_b(data_dir: Path):
    result = assign_tier("https://cs.stanford.edu/research/paper", data_dir=data_dir)
    assert result["tier"] == "B"
    assert result["source"] == "heuristic"
    assert result["unclassified"] is True


def test_assign_tier_gov_pushed_to_b(data_dir: Path):
    result = assign_tier("https://nasa.gov/missions/artemis", data_dir=data_dir)
    assert result["tier"] == "B"


def test_assign_tier_listicle_url_flagged(data_dir: Path):
    result = assign_tier("https://random-site.example/top-10-best-laptops", data_dir=data_dir)
    assert "listicle_no_author" in result["heuristic_flags"]
    assert result["tier"] == "D"
    assert result["unclassified"] is True


def test_assign_tier_medium_pseudonym_flagged(data_dir: Path):
    result = assign_tier("https://medium.com/@anon_writer/some-essay-abc", data_dir=data_dir)
    assert "medium_pseudonym" in result["heuristic_flags"]
    assert result["tier"] == "D"


def test_assign_tier_doi_pushes_to_b(data_dir: Path):
    result = assign_tier(
        "https://obscure-publisher.example/paper",
        title="A study, doi: 10.1234/abc.5678",
        data_dir=data_dir,
    )
    assert result["tier"] == "B"


def test_score_source_tier_a_recent(data_dir: Path):
    result = score_source(
        "https://www.nature.com/articles/abc",
        tier="A",
        pub_date=_iso_days_ago(100),
        data_dir=data_dir,
    )
    assert result["tier_weight"] == 4
    assert result["recency_bonus"] == 1.0
    assert result["score_raw"] == 4.0
    assert result["cross_citation_bonus_eligible"] is True


def test_score_source_tier_b_two_years(data_dir: Path):
    result = score_source(
        "https://www.nytimes.com/article",
        tier="B",
        pub_date=_iso_days_ago(int(2 * 365.25)),
        data_dir=data_dir,
    )
    assert result["tier_weight"] == 3
    assert result["recency_bonus"] == 0.8
    assert result["score_raw"] == pytest.approx(2.4)


def test_score_source_tier_c_eligibility_false(data_dir: Path):
    result = score_source(
        "https://reddit.com/r/x",
        tier="C",
        pub_date=_iso_days_ago(30),
        data_dir=data_dir,
    )
    assert result["cross_citation_bonus_eligible"] is False


def test_score_source_historical_inverts_recency(data_dir: Path):
    recent = score_source(
        "https://www.nature.com/x",
        tier="A",
        pub_date=_iso_days_ago(30),
        is_historical_topic=True,
        data_dir=data_dir,
    )
    old = score_source(
        "https://www.nature.com/y",
        tier="A",
        pub_date=_iso_days_ago(int(7 * 365.25)),
        is_historical_topic=True,
        data_dir=data_dir,
    )
    assert recent["recency_bonus"] == 0.4
    assert old["recency_bonus"] == 1.0
    assert old["score_raw"] > recent["score_raw"]


def test_score_source_no_pub_date_uses_neutral(data_dir: Path):
    result = score_source("https://x.example", tier="B", pub_date=None, data_dir=data_dir)
    assert result["recency_bonus"] == 0.6


def test_get_publisher_known_domain(data_dir: Path):
    assert get_publisher("https://www.nature.com/x", data_dir=data_dir) == "springer-nature"
    assert get_publisher("scientificamerican.com", data_dir=data_dir) == "springer-nature"


def test_get_publisher_defaults_to_root(data_dir: Path):
    assert get_publisher("https://random-blog-xyz.example/path", data_dir=data_dir) == "random-blog-xyz.example"


def test_apply_cross_citation_bonus_independent_sources(data_dir: Path):
    s1 = score_source("https://www.nature.com/a", "B", _iso_days_ago(100), data_dir=data_dir)
    s2 = score_source("https://www.bbc.com/b", "B", _iso_days_ago(100), data_dir=data_dir)
    out = apply_cross_citation_bonus([s1, s2], data_dir=data_dir)
    assert all(s["cross_citation_bonus"] == 0.5 for s in out)
    assert all(s["score"] == s["score_raw"] + 0.5 for s in out)


def test_apply_cross_citation_bonus_same_publisher_no_bonus(data_dir: Path):
    s1 = score_source("https://www.nytimes.com/a", "B", _iso_days_ago(100), data_dir=data_dir)
    s2 = score_source("https://www.thewirecutter.com/b", "B", _iso_days_ago(100), data_dir=data_dir)
    out = apply_cross_citation_bonus([s1, s2], data_dir=data_dir)
    assert all(s["cross_citation_bonus"] == 0.0 for s in out)
    assert all(s["score"] == s["score_raw"] for s in out)


def test_apply_cross_citation_bonus_ignores_tier_c(data_dir: Path):
    a = score_source("https://www.nature.com/a", "A", _iso_days_ago(100), data_dir=data_dir)
    c = score_source("https://reddit.com/r/x", "C", _iso_days_ago(100), data_dir=data_dir)
    out = apply_cross_citation_bonus([a, c], data_dir=data_dir)
    assert out[0]["cross_citation_bonus"] == 0.0
    assert out[1]["cross_citation_bonus"] == 0.0


def test_compare_sources_higher_score_wins(data_dir: Path):
    a = score_source("https://www.nature.com/a", "A", _iso_days_ago(100), data_dir=data_dir)
    b = score_source("https://www.nytimes.com/b", "B", _iso_days_ago(100), data_dir=data_dir)
    assert compare_sources(a, b) == -1
    assert compare_sources(b, a) == 1


def test_compare_sources_tie_score_higher_tier_weight_wins(data_dir: Path):
    a = {
        "url": "https://x.example",
        "tier": "A",
        "tier_weight": 4,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": _iso_days_ago(100),
    }
    b = {
        "url": "https://y.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": _iso_days_ago(100),
    }
    assert compare_sources(a, b) == -1
    assert compare_sources(b, a) == 1


def test_compare_sources_tie_then_more_recent_wins(data_dir: Path):
    a = {
        "url": "https://x.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": _iso_days_ago(30),
    }
    b = {
        "url": "https://y.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": _iso_days_ago(800),
    }
    assert compare_sources(a, b) == -1
    assert compare_sources(b, a) == 1


def test_compare_sources_full_tie_contradiction_sets_conflict(data_dir: Path):
    pub = _iso_days_ago(100)
    a = {
        "url": "https://x.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": pub,
        "claim": "X is true",
    }
    b = {
        "url": "https://y.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": pub,
        "claim": "X is false",
    }
    assert compare_sources(a, b) == 0
    assert a.get("conflict") is True
    assert b.get("conflict") is True


def test_compare_sources_full_tie_same_claim_no_conflict(data_dir: Path):
    pub = _iso_days_ago(100)
    a = {
        "url": "https://x.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": pub,
        "claim": "X is true",
    }
    b = {
        "url": "https://y.example",
        "tier": "B",
        "tier_weight": 3,
        "score_raw": 2.4,
        "score": 2.4,
        "pub_date": pub,
        "claim": "X is true",
    }
    assert compare_sources(a, b) == 0
    assert "conflict" not in a
    assert "conflict" not in b
