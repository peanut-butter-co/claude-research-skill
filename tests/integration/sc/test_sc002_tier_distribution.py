"""SC-002: Tier distribution checker.

No live network calls. Parses source tiers directly from the five standard
item-JSON fixtures and asserts that:
  - >= 70% of all sources are Tier A or Tier B
  - < 5% of all sources are Tier D
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
ITEM_JSONS_DIR = FIXTURES / "item_jsons"

STANDARD_FIXTURES = [
    ITEM_JSONS_DIR / "us1_jest.json",
    ITEM_JSONS_DIR / "us1_vitest.json",
    ITEM_JSONS_DIR / "us1_playwright.json",
    ITEM_JSONS_DIR / "us1_mocha.json",
    ITEM_JSONS_DIR / "us1_jasmine.json",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def collect_tiers(item_json_paths: list[Path]) -> list[str]:
    """Return a flat list of tier strings from all sources in the given JSONs."""
    tiers: list[str] = []
    for path in item_json_paths:
        data = json.loads(path.read_text())
        for field_data in data.get("fields", {}).values():
            for source in field_data.get("sources", []):
                tier = source.get("tier", "Unknown")
                tiers.append(tier)
    return tiers


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sc002_tier_distribution_ab_majority():
    """A+B sources must be >= 70% and D sources must be < 5% of total."""
    tiers = collect_tiers(STANDARD_FIXTURES)

    assert tiers, "No sources found across the standard fixture files"

    total = len(tiers)
    ab_count = sum(1 for t in tiers if t in ("A", "B"))
    d_count = sum(1 for t in tiers if t == "D")

    ab_pct = ab_count / total
    d_pct = d_count / total

    assert ab_pct >= 0.70, (
        f"Tier A+B sources are {ab_pct:.1%} of total ({ab_count}/{total}); "
        f"required >= 70%"
    )
    assert d_pct < 0.05, (
        f"Tier D sources are {d_pct:.1%} of total ({d_count}/{total}); "
        f"required < 5%"
    )


def test_sc002_no_tier_d_sources_in_standard_fixtures():
    """The standard 5-item fixture set must contain zero Tier D sources."""
    tiers = collect_tiers(STANDARD_FIXTURES)

    assert tiers, "No sources found across the standard fixture files"

    d_count = sum(1 for t in tiers if t == "D")

    assert d_count == 0, (
        f"Found {d_count} Tier D source(s) in the standard fixture set; "
        f"expected 0"
    )
