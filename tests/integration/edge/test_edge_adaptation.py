"""Edge cases batch 3: adaptation, fallback, budget, and emergent dimensions.

Covers five scenarios from SPECS:
1. Mid-flight scope invalidation (FR-026) — represented here as an item flagged
   `budget_exhausted` with uncertain fields surfaced in the report.
2. WebFetch fails through Tier 1 -> Tier 2 fallback (FR-028) — represented as a
   `validate_urls` failure that returns a non-empty `error` and `ok=False`.
3. Emergent comparison dimension accepted (FR-030) — represented as an item with
   a `proposed_extensions[]` entry; the report builder must not crash on it.
4. Agent budget exhausted (FR-032 hard-stop) — every item flagged
   `budget_exhausted: true`; report still produced with many gaps.
5. Systemic tool failure (FR-026 systemic trigger) — pruned item with a reason
   surfaces in the Gaps section of the report.

These tests do NOT make live network calls. The validate_urls test uses
monkeypatch to stub `requests.head` and `requests.get`.
"""
from __future__ import annotations

import json
from pathlib import Path

import requests
import yaml

from scripts.build_report import UNCERTAIN_MARKER, build_report
from scripts.validate_urls import validate_url

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"


def _load_outline_and_fields() -> tuple[dict, dict]:
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )
    return outline, fields


def _load_other_four_items() -> list[dict]:
    """Load the four non-jest fixture items so we can inject custom jest variants."""
    return [
        json.loads((FIXTURES / "item_jsons" / f"us1_{name}.json").read_text())
        for name in ["vitest", "playwright", "mocha", "jasmine"]
    ]


# ---------------------------------------------------------------------------
# Test 1 — FR-032: budget exhausted item is marked uncertain in the report
# ---------------------------------------------------------------------------


def test_edge_budget_exhausted_item_marked_uncertain():
    """Item with `budget_exhausted: true` and uncertain fields still surfaces in
    the report with [uncertain] markers and at least one gap.
    """
    outline, fields = _load_outline_and_fields()
    others = _load_other_four_items()

    jest_exhausted = {
        "item": "jest",
        "fields": {
            # Two fields filled, the rest left out / explicitly uncertain.
            "startup_time": {
                "value": "~800ms cold start",
                "sources": [
                    {
                        "url": "https://jestjs.io/docs/getting-started",
                        "title": "Jest Getting Started",
                        "tier": "A",
                        "date": "2024-01-15",
                    }
                ],
            },
            "watch_mode_speed": {
                "value": UNCERTAIN_MARKER,
                "sources": [],
            },
            "typescript_support": {"value": None, "sources": []},
            # Remaining fields (esm_support, snapshot_testing, parallel_execution,
            # weekly_downloads, active_maintenance, notable_users) are absent
            # entirely — they should be picked up by _gaps_list as missing.
        },
        "uncertain": ["typescript_support"],
        "pruned": False,
        "emergent_threads_chased": [],
        "proposed_extensions": [],
        "budget_consumed": 15,
        "budget_exhausted": True,
        "_meta": {"agent_run": "2026-05-07T11:00:00", "hints_received": []},
    }

    item_jsons = [jest_exhausted, *others]
    result = build_report(outline, item_jsons, fields_yaml=fields)

    md = result["report_md"]

    # Report still generated — not blocked.
    assert md, "build_report must produce a non-empty report even when an agent exhausted budget"
    assert "jest" in md, "Item name must still appear in the report"

    # Gaps must include at least one uncertain field from the exhausted agent.
    assert result["gap_count"] >= 1, (
        f"Expected gap_count >= 1 from budget-exhausted agent, got {result['gap_count']}"
    )

    # The uncertain marker should appear, and the budget exhaustion note
    # should be visible somewhere (per build_report._per_item_section + _gaps_list).
    assert UNCERTAIN_MARKER in md, "[uncertain] marker must appear when fields are uncertain"
    assert "budget exhausted" in md.lower() or "budget_exhausted" in md.lower(), (
        "Budget-exhaustion note from FR-032 must be surfaced in the report"
    )


# ---------------------------------------------------------------------------
# Test 2 — FR-032: pruned item surfaces in Gaps section
# ---------------------------------------------------------------------------


def test_edge_pruned_item_shows_no_evidence():
    """Item with `pruned: true` is still mentioned (Gaps section) but has no data."""
    outline, fields = _load_outline_and_fields()
    others = _load_other_four_items()

    jest_pruned = {
        "item": "jest",
        "fields": {},
        "uncertain": [],
        "pruned": True,
        "prune_reason": "no credible sources found",
        "emergent_threads_chased": [],
        "proposed_extensions": [],
        "budget_consumed": 6,
        "budget_exhausted": False,
        "_meta": {"agent_run": "2026-05-07T11:30:00", "hints_received": []},
    }

    item_jsons = [jest_pruned, *others]
    result = build_report(outline, item_jsons, fields_yaml=fields)

    md = result["report_md"]
    assert md, "Report must still be produced when an item is pruned"
    assert "jest" in md, "Pruned item must still be mentioned by name in the report"
    assert result["gap_count"] >= 1, (
        f"Pruned item must contribute >=1 gap, got {result['gap_count']}"
    )
    # _per_item_section emits 'No evidence found (<reason>).' for pruned items
    # and _gaps_list emits 'entire scope pruned (no evidence found)'.
    assert "no evidence found" in md.lower() or "pruned" in md.lower(), (
        "Pruned item must be marked as having no evidence in the report"
    )


# ---------------------------------------------------------------------------
# Test 3 — FR-026 systemic: all agents budget-exhausted, report still written
# ---------------------------------------------------------------------------


def test_edge_all_items_budget_exhausted_report_still_written():
    """Even when every agent hits the budget cap, the report is produced.

    This is the FR-026 systemic-failure path: degrade gracefully and surface
    everything we know (which here is "nothing"), never block on report writing.
    """
    outline, fields = _load_outline_and_fields()

    def make_exhausted(name: str) -> dict:
        return {
            "item": name,
            "fields": {},
            "uncertain": [],
            "pruned": False,
            "emergent_threads_chased": [],
            "proposed_extensions": [],
            "budget_consumed": 15,
            "budget_exhausted": True,
            "_meta": {"agent_run": "2026-05-07T12:00:00", "hints_received": []},
        }

    item_jsons = [make_exhausted(n) for n in ["jest", "vitest", "playwright", "mocha", "jasmine"]]
    result = build_report(outline, item_jsons, fields_yaml=fields)

    md = result["report_md"]
    assert md, "Report must be produced even when every agent exhausted its budget"
    assert "## Comparison" in md, "Comparison section must still render"

    # Each item still listed (with [uncertain] cells) and surfaces in Gaps.
    for item in ["jest", "vitest", "playwright", "mocha", "jasmine"]:
        assert item in md, f"Item {item!r} must still appear when all agents are exhausted"

    # 5 items × 9 fields = 45 expected slots; gap_count should be substantial.
    # Be conservative: at least one gap per item.
    assert result["gap_count"] >= 5, (
        f"Expected >=5 gaps when all 5 items are budget-exhausted, got {result['gap_count']}"
    )


# ---------------------------------------------------------------------------
# Test 4 — FR-028: validate_urls returns ok=False with error on unreachable URL
# ---------------------------------------------------------------------------


def test_edge_validate_urls_returns_error_on_timeout(monkeypatch):
    """When both HEAD and GET raise (e.g. timeout), validate_url returns ok=False
    and a non-empty `error` field.

    No live network call: monkeypatch stubs requests.head/get to raise.
    """

    def _raise(*args, **kwargs):
        raise requests.exceptions.ConnectTimeout("simulated timeout")

    monkeypatch.setattr("scripts.validate_urls.requests.head", _raise)
    monkeypatch.setattr("scripts.validate_urls.requests.get", _raise)

    result = validate_url("http://192.0.2.1/nope", timeout=1)

    assert result["ok"] is False, "Unreachable URL must produce ok=False"
    assert result["error"], (
        f"Unreachable URL must produce a non-empty error field, got {result['error']!r}"
    )
    assert "timeout" in result["error"].lower() or "simulated" in result["error"].lower(), (
        f"Error string should reference the underlying failure, got {result['error']!r}"
    )
    assert result["url"] == "http://192.0.2.1/nope"


# ---------------------------------------------------------------------------
# Test 5 — FR-030: emergent extension in proposed_extensions is tolerated
# ---------------------------------------------------------------------------


def test_edge_emergent_extension_in_proposed_extensions():
    """An item carrying a `proposed_extensions[]` entry (FR-030 emergent
    dimension) must not break report generation. We do not assert that the
    comparative report renders the extension — build_report only surfaces
    proposed_extensions in narrative mode (`_cross_cutting`). For comparative
    mode, we simply verify the call succeeds and produces a usable report.
    """
    outline, fields = _load_outline_and_fields()
    others = _load_other_four_items()

    jest_with_extension = json.loads(
        (FIXTURES / "item_jsons" / "us1_jest.json").read_text()
    )
    jest_with_extension["proposed_extensions"] = [
        {
            "type": "field",
            "name": "bundle_size",
            "reasoning": "Bundle size differentiates lightweight runners from heavy ones; surfaced after agent saw repeated mentions across Tier A sources.",
            "description": "Add bundle_size as a comparison dimension across all items.",
        }
    ]

    item_jsons = [jest_with_extension, *others]

    # Should not raise.
    result = build_report(outline, item_jsons, fields_yaml=fields)

    md = result["report_md"]
    assert md, "Report must be produced when proposed_extensions are present"
    assert "## Comparison" in md, "Comparison section must still render"
    assert "jest" in md, "Item with proposed_extensions must still appear"

    # Smoke-test the narrative path too: the same item JSON in narrative mode
    # routes proposed_extensions through _cross_cutting, which would surface
    # the description. We don't run that here (outline is comparative) but
    # the call above is the load-bearing assertion: it does not crash.
