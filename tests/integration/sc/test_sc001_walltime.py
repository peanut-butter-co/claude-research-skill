"""SC-001: Wall-clock budget smoke test for 5-item comparative research.

No live network calls. Validates that the worst-case timing estimate for a
5-item comparative research session stays under the 15-minute (900s) budget,
given the p95 latency assumptions for WebSearch and WebFetch.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

# ---------------------------------------------------------------------------
# Timing constants (p95 latencies from SPECS.md / SC-001)
# ---------------------------------------------------------------------------

WEBSEARCH_P95 = 3   # seconds per query
WEBFETCH_P95 = 8    # seconds per fetch
MAX_SECONDS = 900   # 15 minutes
ITEM_FETCHES = 3    # typical fetches per item

# ---------------------------------------------------------------------------
# Fixture path
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
OUTLINE_PATH = FIXTURES / "outlines" / "jest_vitest_playwright.yaml"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sc001_comparative_walltime_estimate():
    """5-item comparative worst-case estimate must be under 15 min."""
    outline = yaml.safe_load(OUTLINE_PATH.read_text())

    n_items = len(outline["items"])
    query_budget = outline.get("config", {}).get("query_budget", 15)

    estimate = (
        n_items * query_budget * WEBSEARCH_P95
        + n_items * ITEM_FETCHES * WEBFETCH_P95
    )

    assert estimate < MAX_SECONDS, (
        f"Estimate {estimate}s exceeds {MAX_SECONDS}s wall-clock budget "
        f"(items={n_items}, query_budget={query_budget})"
    )


def test_sc001_budget_default_is_reasonable():
    """Default query_budget in the outline config must be <= 20.

    Ensures that a 5-item comparative run cannot blow the wall-clock budget
    even if no explicit override is supplied.
    """
    outline = yaml.safe_load(OUTLINE_PATH.read_text())

    query_budget = outline.get("config", {}).get("query_budget", 15)

    assert query_budget <= 20, (
        f"query_budget={query_budget} would exceed the safe ceiling of 20 "
        f"for a 5-item comparative run within the 15-minute budget"
    )
