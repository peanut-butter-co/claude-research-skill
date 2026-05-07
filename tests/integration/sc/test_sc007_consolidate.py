"""SC-007: consolidation-history integration test.

Loads 5 simulated sessions from a YAML fixture, writes each correction as a
real learning entry via write_learning, then asserts that the source-classification
ArXiv pattern repeats >=3 times and that entries older than 7 days are surfaced
by count_pending_older_than.

No live network calls.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.learnings_index import (
    count_pending_older_than,
    filter_pending,
    group_by_type,
    read_all,
)
from scripts.learnings_write import write_learning

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURE_PATH = (
    REPO_ROOT / "tests" / "fixtures" / "sc" / "consolidation_history.yaml"
)

_ALL_TYPES = [
    "source-classification",
    "query-strategy",
    "tool-behavior",
    "domain-fact",
    "scoring-rule",
    "process-improvement",
    "pattern-validation",
]


def _load_fixture() -> list[dict]:
    with FIXTURE_PATH.open() as fh:
        data = yaml.safe_load(fh)
    return data["sessions"]


# ---------------------------------------------------------------------------
# Test 1: promotable rule detected after 5 sessions
# ---------------------------------------------------------------------------


def test_sc007_promotable_rule_detected_after_5_sessions(tmp_path):
    """After replaying 5 sessions from the fixture, source-classification has >=3
    pending entries (the ArXiv pattern), and at least one entry is older than 7
    days relative to today.
    """
    sessions = _load_fixture()

    for session in sessions:
        session_date = session["date"]
        for correction in session["corrections"]:
            write_learning(
                trigger=correction["trigger"],
                context=f"SC-007 fixture session {session_date}",
                type_=correction["type"],
                body=correction["body"],
                learnings_dir=tmp_path,
                today=session_date,
            )

    entries = read_all(tmp_path)
    pending = filter_pending(entries)
    groups = group_by_type(pending)

    # The ArXiv source-classification correction appears in sessions 1, 2, 3, and 5
    # — that is 4 entries; assert at least 3 are present.
    sc_entries = groups.get("source-classification", [])
    assert len(sc_entries) >= 3, (
        f"Expected >=3 pending source-classification entries to signal a "
        f"promotable rule, got {len(sc_entries)}"
    )

    # All fixture dates are in January 2026 — well older than 7 days from today
    # (2026-05-07), so count_pending_older_than must return >= 1.
    older_count = count_pending_older_than(entries, 7)
    assert older_count >= 1, (
        f"Expected >=1 pending entry older than 7 days, got {older_count}"
    )


# ---------------------------------------------------------------------------
# Test 2: all 7 types are representable
# ---------------------------------------------------------------------------


def test_sc007_all_7_types_representable(tmp_path):
    """Writing one entry per type produces a group_by_type dict with all 7 keys."""
    session_date = "2026-01-15"
    type_contexts = {
        "source-classification": "arxiv tier classification",
        "query-strategy": "arxiv subject category narrowing",
        "tool-behavior": "exa search returns empty on obscure domains",
        "domain-fact": "EU AI Act applies to GPAI models above 10^25 FLOPs",
        "scoring-rule": "official docs outweigh blog posts 3:1",
        "process-improvement": "always validate publication date before citing",
        "pattern-validation": "vs-operator improves comparative query quality",
    }

    for type_, context in type_contexts.items():
        write_learning(
            trigger="user-feedback",
            context=context,
            type_=type_,
            body=f"Sample body for type {type_}.",
            learnings_dir=tmp_path,
            today=session_date,
        )

    groups = group_by_type(filter_pending(read_all(tmp_path)))

    missing = [t for t in _ALL_TYPES if t not in groups]
    assert not missing, (
        f"The following types were not found in group_by_type result: {missing}"
    )
