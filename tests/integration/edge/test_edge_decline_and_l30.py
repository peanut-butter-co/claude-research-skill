"""Edge case integration tests — batch 2 (T101).

Covers three edge scenarios from the SPECS:

1. FR-017a: Contradictory Tier A sources surface a "Disagreements" section.
2. FR-005: Optional integration declined "never-suggest-for-similar" persists
   the topic-type signature so it is not offered again.
3. `/last30days` not configured: an outline with `social_signal: true` still
   produces a valid report (graceful degradation).

Uses canned fixtures only; no live network calls; does NOT invoke
SKILL.md or Claude Code.
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.build_report import build_report
from scripts.preferences import (
    add_never_suggest,
    is_never_suggest,
    load_preferences,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent.parent


# ---------------------------------------------------------------------------
# 1. FR-017a — contradictory Tier A sources produce a Disagreements section
# ---------------------------------------------------------------------------


def test_edge_contradictory_tier_a_produces_disagreements_section():
    """Two Tier A sources contradicting each other on the same field must
    surface under the report's "## Disagreements" section.

    FR-017a: When ≥2 Tier A sources disagree on a claim, the report MUST
    surface the disagreement; silent omission is forbidden.

    The current `_disagreements_from_jsons` implementation in
    scripts/build_report.py groups Tier A sources by their `claim` field and
    reports a disagreement when ≥2 distinct claims exist on the same field.
    To trigger detection deterministically we attach explicit `claim` values
    to two Tier A sources on jest's `startup_time`.
    """
    # Minimal fields.yaml: just startup_time so the comparative table fits.
    fields_yaml = {"categories": {"performance": ["startup_time"]}}

    outline = {
        "mode": "comparative",
        "topic": "edge: contradictory Tier A on startup_time",
        "items": ["jest", "vitest"],
    }

    jest_with_conflict = {
        "item": "jest",
        "fields": {
            "startup_time": {
                "value": "~850ms (per primary docs); a community benchmark reports ~200ms",
                "sources": [
                    {
                        "url": "https://jestjs.io/docs/getting-started",
                        "title": "Jest Getting Started",
                        "tier": "A",
                        "date": "2024-01-15",
                        "claim": "~850ms",
                    },
                    {
                        "url": "https://meta.com/engineering/jest-bench",
                        "title": "Jest internal benchmark",
                        "tier": "A",
                        "date": "2024-06-01",
                        "claim": "~200ms",
                    },
                ],
            }
        },
        "uncertain": [],
        "pruned": False,
    }

    # Second item, no conflict — keeps the comparative shape valid.
    vitest_clean = {
        "item": "vitest",
        "fields": {
            "startup_time": {
                "value": "~120ms cold start",
                "sources": [
                    {
                        "url": "https://vitest.dev/guide/",
                        "title": "Vitest Guide",
                        "tier": "A",
                        "date": "2024-02-10",
                    }
                ],
            }
        },
        "uncertain": [],
        "pruned": False,
    }

    result = build_report(
        outline,
        [jest_with_conflict, vitest_clean],
        fields_yaml=fields_yaml,
    )
    md = result["report_md"]

    # Strong assertion: the Disagreements heading must be present.
    assert "## Disagreements" in md, (
        "Report must contain a '## Disagreements' section when two Tier A "
        "sources disagree (FR-017a). Got report:\n" + md
    )

    # And it must not be the empty 'None detected' placeholder for this case.
    assert "None detected" not in md.split("## Disagreements", 1)[1].split("##", 1)[0], (
        "Disagreements section must list the actual conflict, not the empty "
        "'None detected' placeholder, when ≥2 Tier A sources disagree."
    )

    # Both contradicting claims should appear in the report body.
    assert "~850ms" in md, "First Tier A claim must appear in the report"
    assert "~200ms" in md, "Second Tier A claim must appear in the report"


# ---------------------------------------------------------------------------
# 2. FR-005 — never-suggest preference round-trips through preferences.yaml
# ---------------------------------------------------------------------------


def test_edge_never_suggest_integration_not_offered(tmp_path):
    """Recording a topic-type signature as never-suggest must persist to
    preferences.yaml and block a subsequent suggestion for the same signature.

    FR-005: the "never" preference MUST persist in
    `.config/research-skill/preferences.yaml` keyed by topic-type signature
    (sorted tuple of matched integration ids ∪ entity-type tags).
    """
    signature = ["entity:local_business", "google_places"]

    # Step 1 — initially no preferences recorded for this signature.
    assert is_never_suggest(signature, config_dir=tmp_path) is False, (
        "Fresh config_dir must not report any signature as never-suggest"
    )

    # Step 2 — record the never-suggest preference via the public API.
    add_never_suggest(signature, "google_places", config_dir=tmp_path)

    # Step 3 — round-trip: load_preferences sees the entry on disk.
    prefs = load_preferences(config_dir=tmp_path)
    assert "never_suggest" in prefs, "Loaded preferences must have never_suggest key"
    assert len(prefs["never_suggest"]) == 1, (
        f"Expected exactly 1 never_suggest entry, got {len(prefs['never_suggest'])}"
    )
    entry = prefs["never_suggest"][0]
    assert entry["integration_id"] == "google_places"
    assert entry["signature"] == sorted(signature), (
        "Stored signature must be sorted (canonical form per FR-005)"
    )
    assert "recorded_at" in entry, "Stored entry must include a recorded_at timestamp"

    # Step 4 — is_never_suggest now returns True for the same signature
    # (and for the unsorted permutation, since the API normalises).
    assert is_never_suggest(signature, config_dir=tmp_path) is True
    assert is_never_suggest(list(reversed(signature)), config_dir=tmp_path) is True

    # Step 5 — preferences.yaml file actually exists at the expected path.
    prefs_file = tmp_path / "preferences.yaml"
    assert prefs_file.exists(), (
        "preferences.yaml must be created under config_dir after add_never_suggest"
    )
    on_disk = yaml.safe_load(prefs_file.read_text())
    assert on_disk["never_suggest"][0]["integration_id"] == "google_places"


def test_edge_never_suggest_fixture_format_matches_api(tmp_path):
    """The shipped fixture preferences/us4_never_suggest.yaml is a valid
    preferences file: load_preferences accepts it and is_never_suggest
    returns True for the recorded signature.
    """
    fixture_path = FIXTURES / "preferences" / "us4_never_suggest.yaml"
    # Copy the fixture into a fresh config_dir so we exercise the on-disk path.
    target = tmp_path / "preferences.yaml"
    target.write_text(fixture_path.read_text())

    prefs = load_preferences(config_dir=tmp_path)
    assert prefs["never_suggest"], "Fixture must yield at least one never_suggest entry"

    fixture_sig = prefs["never_suggest"][0]["signature"]
    assert is_never_suggest(fixture_sig, config_dir=tmp_path) is True, (
        "is_never_suggest must return True for a signature recorded in the fixture"
    )


# ---------------------------------------------------------------------------
# 3. /last30days not configured — graceful degradation
# ---------------------------------------------------------------------------


def test_edge_l30_not_configured_graceful_degradation():
    """An outline with `social_signal: true` must still produce a valid report
    even when `/last30days` is unavailable.

    SPECS Edge Case ("`/last30days` not configured"): if the social tool is
    unreachable, the skill proceeds with WebSearch+WebFetch only and notes
    the missing source. We can't actually invoke `/last30days` from a unit
    test, but we CAN verify the structural guarantee: build_report does not
    depend on social-signal data and does not crash when the outline asks
    for it but no social-derived sources are present in the item JSONs.
    """
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields_yaml = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )

    # Sanity-check the precondition: the fixture outline really does request
    # /last30days. If this ever changes, the test should fail loudly so we
    # update the scenario rather than silently passing.
    assert outline.get("config", {}).get("social_signal") is True, (
        "Precondition: jest_vitest_playwright.yaml outline must have "
        "social_signal: true so this test exercises the degraded path"
    )

    # Load all 5 item JSONs — none of them carry /last30days-derived sources,
    # which is the exact state we'd be in if the tool were unavailable.
    item_jsons = [
        json.loads((FIXTURES / "item_jsons" / f"us1_{item}.json").read_text())
        for item in ["jest", "vitest", "playwright", "mocha", "jasmine"]
    ]

    # Must not raise — graceful degradation.
    result = build_report(outline, item_jsons, fields_yaml=fields_yaml)

    # Must produce a non-empty report.
    md = result["report_md"]
    assert isinstance(md, str) and md.strip(), (
        "build_report must return a non-empty report_md even without /last30days"
    )

    # Report should still contain the comparison table (built from
    # WebSearch+WebFetch-derived item JSONs).
    assert "## Comparison" in md, (
        "Comparative report structure must survive missing /last30days data"
    )
    # All 5 items still appear.
    for item in ["jest", "vitest", "playwright", "mocha", "jasmine"]:
        assert item in md, f"Item {item!r} missing from degraded report"

    # Sources note still rendered.
    assert "## Sources note" in md, (
        "Sources note must still render without /last30days-derived sources"
    )


def test_edge_l30_not_configured_minimal_outline():
    """A minimal outline with social_signal=true and zero item JSONs must
    still produce a structurally valid report (no crash, no exception).
    """
    outline = {
        "mode": "comparative",
        "topic": "edge: l30 unavailable, no items",
        "items": ["jest"],
        "config": {"social_signal": True, "topic_integrations": []},
    }
    fields_yaml = {"categories": {"performance": ["startup_time"]}}

    result = build_report(outline, [], fields_yaml=fields_yaml)
    md = result["report_md"]
    assert isinstance(md, str) and md, "Empty-evidence report must still be a string"
    # Per build_report, empty item_jsons yields a 'No evidence found' stub.
    assert "No evidence found" in md, (
        "Empty item_jsons must produce a 'No evidence found' report, not crash"
    )
    assert result["gap_count"] == 0
    assert result["broken_url_count"] == 0
