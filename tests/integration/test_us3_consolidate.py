"""Integration tests for US3: learnings consolidation workflow.

Exercises write_learning, update_status, read_all, filter_pending,
group_by_type, and count_pending_older_than end-to-end using real filesystem
(tmp_path) and canned fixture files.

Does NOT call SKILL.md or invoke Claude Code.
Does NOT make network calls.
"""
from __future__ import annotations

import json
import re
from datetime import date, timedelta
from pathlib import Path

import frontmatter
import pytest
import yaml

from scripts.learnings_index import (
    count_pending_older_than,
    filter_pending,
    group_by_type,
    read_all,
)
from scripts.learnings_write import update_status, write_learning

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
LEARNINGS_FIXTURES = FIXTURES / "learnings"
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / ".claude" / "skills" / "_lib" / "data"

_ALL_TYPES = [
    "source-classification",
    "query-strategy",
    "tool-behavior",
    "domain-fact",
    "scoring-rule",
    "process-improvement",
    "pattern-validation",
]

_FIXTURE_FILES = {
    "source-classification": "us3_source_classification.md",
    "query-strategy": "us3_query_strategy.md",
    "tool-behavior": "us3_tool_behavior.md",
    "domain-fact": "us3_domain_fact.md",
    "scoring-rule": "us3_scoring_rule.md",
    "process-improvement": "us3_process_improvement.md",
    "pattern-validation": "us3_pattern_validation.md",
}


def _fixtures_available() -> bool:
    return any(LEARNINGS_FIXTURES.glob("*us3_source_classification.md"))


# ---------------------------------------------------------------------------
# Group A: Scenario 1 — write_learning produces correct entry
# ---------------------------------------------------------------------------


def test_write_learning_user_feedback_trigger(tmp_path):
    """write_learning with trigger='user-feedback' produces correct frontmatter."""
    path = write_learning(
        trigger="user-feedback",
        context="user corrected source tier for arxiv",
        type_="source-classification",
        body="ArXiv preprints should be tier B, not tier A.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    assert path.exists()
    post = frontmatter.load(str(path))
    assert post.metadata["trigger"] == "user-feedback"
    assert post.metadata["status"] == "pending"
    assert "type" in post.metadata
    assert post.metadata["type"] == "source-classification"


def test_write_learning_self_detection_trigger(tmp_path):
    """write_learning with trigger='self-detection' records correct trigger."""
    path = write_learning(
        trigger="self-detection",
        context="agent noticed inconsistent scoring across runs",
        type_="scoring-rule",
        body="Scoring is non-deterministic when date weight ties.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    assert path.exists()
    post = frontmatter.load(str(path))
    assert post.metadata["trigger"] == "self-detection"
    assert post.metadata["status"] == "pending"


def test_write_learning_session_close_trigger(tmp_path):
    """write_learning with trigger='session-close' records correct trigger."""
    path = write_learning(
        trigger="session-close",
        context="end of research session on LLM benchmarks",
        type_="process-improvement",
        body="Always verify benchmark publication date before citing.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    assert path.exists()
    post = frontmatter.load(str(path))
    assert post.metadata["trigger"] == "session-close"
    assert post.metadata["status"] == "pending"


def test_learning_entry_has_required_frontmatter_fields(tmp_path):
    """A freshly written learning has all 6 required frontmatter fields."""
    path = write_learning(
        trigger="user-feedback",
        context="query produced no results for obscure domain",
        type_="query-strategy",
        body="Try site-specific operators when broad queries fail.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    post = frontmatter.load(str(path))
    required_fields = ("id", "date", "trigger", "context", "type", "status")
    for field in required_fields:
        assert field in post.metadata, f"Required field missing: {field!r}"
    assert post.metadata["status"] == "pending"


def test_learning_id_format(tmp_path):
    """The id field follows the YYYY-MM-DD-NNN pattern."""
    path = write_learning(
        trigger="self-detection",
        context="anomaly in tool output",
        type_="tool-behavior",
        body="Tool returns empty list instead of error on bad input.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    post = frontmatter.load(str(path))
    entry_id = post.metadata["id"]
    pattern = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{3}$")
    assert pattern.match(entry_id), (
        f"id {entry_id!r} does not match YYYY-MM-DD-NNN format"
    )


# ---------------------------------------------------------------------------
# Group B: Scenario 2 — learnings index and grouping
# ---------------------------------------------------------------------------


def test_fixture_learnings_all_pending_types_present():
    """All 7 learning types are present in the fixture files as pending entries."""
    if not _fixtures_available():
        pytest.skip("Fixture not yet created by T074")

    entries = read_all(LEARNINGS_FIXTURES)
    pending = filter_pending(entries)
    groups = group_by_type(pending)

    for t in _ALL_TYPES:
        assert t in groups, f"Type {t!r} not found in pending fixture learnings"


def test_filter_pending_excludes_consolidated_and_discarded():
    """filter_pending excludes entries with status=consolidated or status=discarded."""
    if not _fixtures_available():
        pytest.skip("Fixture not yet created by T074")

    entries = read_all(LEARNINGS_FIXTURES)
    pending = filter_pending(entries)
    pending_ids = {e["id"] for e in pending}

    # Load the non-pending fixture files and check they are excluded
    consolidated_path = LEARNINGS_FIXTURES / "us3_consolidated.md"
    discarded_path = LEARNINGS_FIXTURES / "us3_discarded.md"

    if consolidated_path.exists():
        post = frontmatter.load(str(consolidated_path))
        assert post.metadata["id"] not in pending_ids, (
            "Consolidated entry must not appear in filter_pending results"
        )

    if discarded_path.exists():
        post = frontmatter.load(str(discarded_path))
        assert post.metadata["id"] not in pending_ids, (
            "Discarded entry must not appear in filter_pending results"
        )


def test_group_by_type_groups_correctly():
    """group_by_type returns exactly one pending entry per type for the 7 fixture types."""
    if not _fixtures_available():
        pytest.skip("Fixture not yet created by T074")

    entries = read_all(LEARNINGS_FIXTURES)
    pending = filter_pending(entries)
    groups = group_by_type(pending)

    for t in _ALL_TYPES:
        assert t in groups, f"Type {t!r} missing from groups"
        assert len(groups[t]) >= 1, f"Expected ≥1 pending entry for type {t!r}"


def test_count_pending_older_than_on_fixtures():
    """Fixture learnings dated 2026-01-15 are older than 30 days — count ≥ 7."""
    if not _fixtures_available():
        pytest.skip("Fixture not yet created by T074")

    entries = read_all(LEARNINGS_FIXTURES)
    count = count_pending_older_than(entries, 30)
    assert count >= 7, (
        f"Expected ≥7 pending entries older than 30 days, got {count}"
    )


# ---------------------------------------------------------------------------
# Group C: Scenario 3 — update_status simulates consolidation approval
# ---------------------------------------------------------------------------


def test_update_status_consolidated(tmp_path):
    """update_status('consolidated') sets status and preserves all other fields."""
    path = write_learning(
        trigger="user-feedback",
        context="consolidation test context",
        type_="domain-fact",
        body="Some domain fact body.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    original = frontmatter.load(str(path))
    original_trigger = original.metadata["trigger"]
    original_type = original.metadata["type"]
    original_id = original.metadata["id"]

    update_status(path, "consolidated")

    reloaded = frontmatter.load(str(path))
    assert reloaded.metadata["status"] == "consolidated"
    assert reloaded.metadata["trigger"] == original_trigger
    assert reloaded.metadata["type"] == original_type
    assert reloaded.metadata["id"] == original_id


def test_update_status_discarded(tmp_path):
    """update_status('discarded') sets status and preserves all other fields."""
    path = write_learning(
        trigger="self-detection",
        context="discarded test context",
        type_="pattern-validation",
        body="Some pattern validation body.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )
    original = frontmatter.load(str(path))
    original_trigger = original.metadata["trigger"]
    original_type = original.metadata["type"]
    original_id = original.metadata["id"]

    update_status(path, "discarded")

    reloaded = frontmatter.load(str(path))
    assert reloaded.metadata["status"] == "discarded"
    assert reloaded.metadata["trigger"] == original_trigger
    assert reloaded.metadata["type"] == original_type
    assert reloaded.metadata["id"] == original_id


def test_simulate_consolidation_of_source_classification(tmp_path):
    """Consolidating a source-classification entry removes it from filter_pending."""
    path = write_learning(
        trigger="user-feedback",
        context="arxiv tier reclassification",
        type_="source-classification",
        body="ArXiv should be tier B.",
        learnings_dir=tmp_path,
        today="2026-05-07",
    )

    # Before: should appear in read_all and filter_pending
    entries_before = read_all(tmp_path)
    pending_before = filter_pending(entries_before)
    assert len(pending_before) == 1, "Expected 1 pending entry before consolidation"
    assert pending_before[0]["type"] == "source-classification"

    # Consolidate
    update_status(path, "consolidated")

    # After: read_all still returns the entry, but filter_pending excludes it
    entries_after = read_all(tmp_path)
    assert len(entries_after) == 1, "Entry must still exist after consolidation"
    assert entries_after[0]["status"] == "consolidated"

    pending_after = filter_pending(entries_after)
    assert len(pending_after) == 0, "Consolidated entry must not appear in filter_pending"


def test_multiple_learnings_in_same_session(tmp_path):
    """Writing 3 learnings on the same date produces sequential IDs -001, -002, -003."""
    today = "2026-05-07"
    paths = []
    for i, (ctx, type_) in enumerate([
        ("first context", "query-strategy"),
        ("second context", "domain-fact"),
        ("third context", "tool-behavior"),
    ]):
        path = write_learning(
            trigger="session-close",
            context=ctx,
            type_=type_,
            body=f"Body {i + 1}.",
            learnings_dir=tmp_path,
            today=today,
        )
        paths.append(path)

    ids = []
    for path in paths:
        post = frontmatter.load(str(path))
        ids.append(post.metadata["id"])

    assert ids[0] == f"{today}-001", f"First ID should be {today}-001, got {ids[0]}"
    assert ids[1] == f"{today}-002", f"Second ID should be {today}-002, got {ids[1]}"
    assert ids[2] == f"{today}-003", f"Third ID should be {today}-003, got {ids[2]}"


def test_consolidate_leaves_pending_entries_for_skipped(tmp_path):
    """Consolidating 2 of 3 entries leaves the third still pending via filter_pending."""
    today = "2026-05-07"
    path_sc = write_learning(
        trigger="user-feedback",
        context="source classification learning",
        type_="source-classification",
        body="Source classification observation.",
        learnings_dir=tmp_path,
        today=today,
    )
    path_qs = write_learning(
        trigger="user-feedback",
        context="query strategy learning",
        type_="query-strategy",
        body="Query strategy observation.",
        learnings_dir=tmp_path,
        today=today,
    )
    path_df = write_learning(
        trigger="self-detection",
        context="domain fact learning",
        type_="domain-fact",
        body="Domain fact observation.",
        learnings_dir=tmp_path,
        today=today,
    )

    # Consolidate the first two, skip the third
    update_status(path_sc, "consolidated")
    update_status(path_qs, "consolidated")

    # Verify via filter_pending
    entries = read_all(tmp_path)
    pending = filter_pending(entries)

    assert len(pending) == 1, f"Expected 1 pending entry, got {len(pending)}"
    assert pending[0]["type"] == "domain-fact", (
        f"Remaining pending entry should be domain-fact, got {pending[0]['type']!r}"
    )
