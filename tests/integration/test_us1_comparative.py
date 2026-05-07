"""Integration tests for US1: comparative research with scored sources.

Exercises the Python helper scripts end-to-end using canned fixtures.
Does NOT call SKILL.md or invoke Claude Code.
Does NOT make network calls (all fixture URLs are fake/example domains).
"""
from __future__ import annotations

import csv
import io
import json
import re
import time
from pathlib import Path

import pytest
import yaml

from scripts.build_report import BROKEN_URL_MARKER, build_report
from scripts.lockfile import acquire, check_stale, release
from scripts.score_source import assign_tier, score_source
from scripts.slug import make_slug

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data"


# ---------------------------------------------------------------------------
# Scenario 0 helpers: slug + lockfile
# ---------------------------------------------------------------------------


def test_slug_generates_correct_case_id():
    """'compare 5 JS testing frameworks' → lowercase hyphenated slug ≤ 60 chars."""
    slug = make_slug("compare 5 JS testing frameworks")
    assert len(slug) <= 60
    assert slug.islower()
    assert " " not in slug
    # stop words dropped: "for", "the", "of", etc.
    # "compare", "5", "js", "testing", "frameworks" are not stop words → all kept
    assert "compare" in slug
    assert "js" in slug or "5" in slug  # digits pass through


def test_lockfile_acquire_release(tmp_path):
    """acquire() writes .lock file; release() removes it."""
    acquire(tmp_path)
    assert (tmp_path / ".lock").exists()
    release(tmp_path)
    assert not (tmp_path / ".lock").exists()


def test_lockfile_double_acquire_raises(tmp_path):
    """A second acquire() on an already-locked path raises RuntimeError."""
    acquire(tmp_path)
    try:
        with pytest.raises(RuntimeError):
            acquire(tmp_path)
    finally:
        release(tmp_path)


def test_lockfile_stale_detection(tmp_path):
    """check_stale() on an ancient lockfile with a non-existent PID returns bool."""
    lockfile = tmp_path / ".lock"
    lockfile.write_text("pid=99999999\nstart=1970-01-01T00:00:00\n")
    # Age >> 1 h and PID 99999999 is almost certainly not running.
    result = check_stale(tmp_path, ttl_seconds=3600)
    assert isinstance(result, bool)


# ---------------------------------------------------------------------------
# Scenario 1: Planning artifacts written
# ---------------------------------------------------------------------------


def test_planning_artifacts_written(tmp_path):
    """Simulate the planning step: write outline + fields + search-log, then assert."""
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )

    case_dir = tmp_path / "tasks" / "compare-5-js-testing-frameworks"
    case_dir.mkdir(parents=True)

    (case_dir / "outline.yaml").write_text(yaml.dump(outline))
    (case_dir / "fields.yaml").write_text(yaml.dump(fields))
    (case_dir / "search-log.md").write_text("## Session 2026-05-07 10:00\n")

    assert (case_dir / "outline.yaml").exists()
    assert (case_dir / "fields.yaml").exists()
    assert (case_dir / "search-log.md").exists()

    loaded = yaml.safe_load((case_dir / "outline.yaml").read_text())
    assert loaded["mode"] == "comparative"
    assert len(loaded["items"]) == 5


# ---------------------------------------------------------------------------
# Scenario 2: One parallel agent per item — tiered sources
# ---------------------------------------------------------------------------


def test_item_jsons_have_tiered_sources():
    """Each item JSON has ≥1 source with a valid tier label."""
    items = ["jest", "vitest", "playwright", "mocha", "jasmine"]
    for item in items:
        path = FIXTURES / "item_jsons" / f"us1_{item}.json"
        data = json.loads(path.read_text())
        all_sources: list[dict] = []
        for field_data in data.get("fields", {}).values():
            all_sources.extend(field_data.get("sources", []))
        assert len(all_sources) > 0, f"{item} has no sources"
        for src in all_sources:
            assert src["tier"] in (
                "A",
                "B",
                "C",
                "D",
                "Unknown",
            ), f"{item} source has invalid tier: {src['tier']!r}"


def test_source_scoring_produces_nonzero_score():
    """assign_tier and score_source produce positive scores on fixture data."""
    jest_data = json.loads((FIXTURES / "item_jsons" / "us1_jest.json").read_text())
    sources = jest_data["fields"]["startup_time"]["sources"]
    assert sources, "us1_jest.json must have startup_time sources for this test"
    for src in sources:
        result = score_source(
            src["url"],
            src["tier"],
            src["date"],
            data_dir=DATA_DIR,
        )
        assert result["score_raw"] > 0, f"score_raw is 0 for {src['url']}"
        assert result["tier_weight"] > 0, f"tier_weight is 0 for {src['url']}"


# ---------------------------------------------------------------------------
# Scenario 3: report.md + report.csv — comparison table + inline citations
# ---------------------------------------------------------------------------


def _load_standard_inputs() -> tuple[dict, dict, list[dict]]:
    """Load outline, fields, and all 5 item JSONs from fixtures."""
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )
    item_jsons = [
        json.loads((FIXTURES / "item_jsons" / f"us1_{item}.json").read_text())
        for item in ["jest", "vitest", "playwright", "mocha", "jasmine"]
    ]
    return outline, fields, item_jsons


def test_report_comparative_structure():
    """build_report() produces ## Comparison table, ## Sources note, all 5 items."""
    outline, fields, item_jsons = _load_standard_inputs()
    result = build_report(outline, item_jsons, fields_yaml=fields)
    md = result["report_md"]
    report_csv = result["report_csv"]

    # Markdown structure
    assert "## Comparison" in md, "Missing ## Comparison section"
    assert "## Sources note" in md, "Missing ## Sources note section"
    for item in ["jest", "vitest", "playwright", "mocha", "jasmine"]:
        assert item in md, f"Item {item!r} not found in report"

    # CSV structure
    rows = list(csv.reader(io.StringIO(report_csv)))
    assert len(rows) >= 1, "CSV must have at least a header row"
    assert rows[0][0] == "item", f"First CSV column must be 'item', got {rows[0][0]!r}"
    assert len(rows) == 6, f"Expected header + 5 data rows, got {len(rows)} rows"
    item_names_in_csv = {r[0] for r in rows[1:]}
    assert item_names_in_csv == {
        "jest",
        "vitest",
        "playwright",
        "mocha",
        "jasmine",
    }, f"CSV item names mismatch: {item_names_in_csv}"


def test_report_inline_citation_format():
    """Inline citations follow '[Title • Tier X](url)' format."""
    outline, fields, item_jsons = _load_standard_inputs()
    result = build_report(outline, item_jsons, fields_yaml=fields)
    citation_pattern = re.compile(r"\[.+ • Tier [ABCD]\]\(https?://")
    assert citation_pattern.search(result["report_md"]) is not None, (
        "No inline citation matching '[Title • Tier X](https://…)' found in report"
    )


def test_report_csv_header_matches_fields():
    """CSV header row matches fields defined in fields.yaml."""
    outline, fields_yaml, item_jsons = _load_standard_inputs()
    result = build_report(outline, item_jsons, fields_yaml=fields_yaml)
    rows = list(csv.reader(io.StringIO(result["report_csv"])))
    header = rows[0]
    assert header[0] == "item"
    # All fields from fields.yaml categories must appear in CSV header
    expected_fields: list[str] = []
    for category_fields in fields_yaml.get("categories", {}).values():
        expected_fields.extend(category_fields or [])
    for f in expected_fields:
        assert f in header, f"Field {f!r} missing from CSV header"


# ---------------------------------------------------------------------------
# Scenario 4: Broken URL → visible gap marker, never silenced
# ---------------------------------------------------------------------------


def test_broken_url_shows_gap_marker():
    """A broken URL in url_validation must produce BROKEN_URL_MARKER in the report."""
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )

    jest_broken = json.loads(
        (FIXTURES / "item_jsons" / "us1_jest_broken_url.json").read_text()
    )
    other_items = [
        json.loads((FIXTURES / "item_jsons" / f"us1_{item}.json").read_text())
        for item in ["vitest", "playwright", "mocha", "jasmine"]
    ]
    item_jsons = [jest_broken] + other_items

    broken_url = "https://broken.example.com/jest-perf"
    url_validation = {
        broken_url: {
            "url": broken_url,
            "ok": False,
            "status_code": 404,
            "method_used": "GET",
            "error": "404 Not Found",
        }
    }

    result = build_report(
        outline, item_jsons, fields_yaml=fields, url_validation=url_validation
    )
    md = result["report_md"]

    assert BROKEN_URL_MARKER in md, (
        f"BROKEN_URL_MARKER ({BROKEN_URL_MARKER!r}) must appear in report"
    )
    assert "### Broken URLs" in md, "### Broken URLs section must exist"
    assert broken_url in md, "The broken URL itself must be listed in the report"
    assert result["broken_url_count"] >= 1, (
        f"broken_url_count must be ≥1, got {result['broken_url_count']}"
    )


def test_broken_url_not_silenced_when_only_source():
    """When all sources for a field are broken, BROKEN_URL_MARKER replaces the value."""
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )

    # Build a minimal item where startup_time has only the broken URL as source
    broken_url = "https://broken.example.com/jest-perf"
    jest_only_broken: dict = {
        "item": "jest",
        "fields": {
            "startup_time": {
                "value": "~850ms cold start",
                "sources": [
                    {
                        "url": broken_url,
                        "title": "Jest Performance Benchmarks",
                        "tier": "B",
                        "date": "2024-11-01",
                    }
                ],
            }
        },
    }
    other_items = [
        json.loads((FIXTURES / "item_jsons" / f"us1_{item}.json").read_text())
        for item in ["vitest", "playwright", "mocha", "jasmine"]
    ]
    item_jsons = [jest_only_broken] + other_items

    url_validation = {
        broken_url: {
            "url": broken_url,
            "ok": False,
            "status_code": 404,
            "method_used": "GET",
            "error": "404 Not Found",
        }
    }

    result = build_report(
        outline, item_jsons, fields_yaml=fields, url_validation=url_validation
    )
    assert BROKEN_URL_MARKER in result["report_md"]
    assert result["broken_url_count"] >= 1


# ---------------------------------------------------------------------------
# Scenario 5: Uncertain field shown in report
# ---------------------------------------------------------------------------


def test_uncertain_field_in_report():
    """playwright's startup_time is uncertain in fixture → [uncertain] or gap_count ≥ 1."""
    outline, fields, item_jsons = _load_standard_inputs()
    result = build_report(outline, item_jsons, fields_yaml=fields)
    # playwright startup_time value is "[uncertain]" in the fixture
    assert "[uncertain]" in result["report_md"] or result["gap_count"] >= 1, (
        "Expected [uncertain] marker or gap_count ≥ 1 for playwright startup_time"
    )
