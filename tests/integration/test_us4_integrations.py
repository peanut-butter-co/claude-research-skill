"""Integration tests for US4: topic-driven integrations with never-suggest preferences.

Exercises the Python helper scripts end-to-end using YAML config and canned fixtures.
Does NOT call SKILL.md or invoke Claude Code.
Does NOT make network calls.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from scripts.preferences import add_never_suggest, is_never_suggest

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
TOPIC_INTEGRATIONS = DATA_DIR / "topic-integrations.yaml"


# ---------------------------------------------------------------------------
# Skip helpers for fixture-dependent tests
# ---------------------------------------------------------------------------


def _google_places_fixture_available() -> bool:
    return (FIXTURES / "integrations" / "google_places_madrid_cheese.json").exists()


def _cheese_outline_available() -> bool:
    return (FIXTURES / "outlines" / "cheese_shops_madrid.yaml").exists()


# ---------------------------------------------------------------------------
# Group A: Topic matching triggers integration (Scenario 1)
# ---------------------------------------------------------------------------


def test_topic_triggers_google_places_via_regex():
    """'best cheese shops in Madrid' must match google_places via its regex triggers."""
    config = yaml.safe_load(TOPIC_INTEGRATIONS.read_text())
    integrations = config["integrations"]
    google_places = integrations["google_places"]
    triggers = google_places["triggers"]

    topic = "best cheese shops in Madrid"
    matched = []
    for trigger in triggers:
        # entity: tags are not regex — skip them
        if trigger.startswith("entity:"):
            continue
        if re.search(trigger, topic):
            matched.append("google_places")
            break

    assert "google_places" in matched, (
        f"Expected 'google_places' in match list for topic {topic!r}, "
        f"but no trigger matched. Triggers: {triggers}"
    )


def test_topic_no_match_returns_empty():
    """'compare Python sorting algorithms' must NOT trigger google_places."""
    config = yaml.safe_load(TOPIC_INTEGRATIONS.read_text())
    integrations = config["integrations"]
    google_places = integrations["google_places"]
    triggers = google_places["triggers"]

    topic = "compare Python sorting algorithms"
    matched = []
    for trigger in triggers:
        if trigger.startswith("entity:"):
            continue
        if re.search(trigger, topic):
            matched.append("google_places")
            break

    assert matched == [], (
        f"Expected no matches for topic {topic!r}, but got: {matched}"
    )


def test_mode_detection_on_cheese_topic():
    """detect_mode_fast on 'best cheese shops in Madrid' must not crash."""
    from scripts.mode_detect import detect_mode_fast

    result = detect_mode_fast("best cheese shops in Madrid", data_dir=DATA_DIR)
    assert isinstance(result, dict), "detect_mode_fast must return a dict"
    assert "mode" in result, "Result dict must contain a 'mode' key"


# ---------------------------------------------------------------------------
# Group B: Never-suggest preferences (Scenario 3)
# ---------------------------------------------------------------------------


def test_is_never_suggest_returns_false_initially(tmp_path):
    """Fresh config_dir has no never-suggest entries → is_never_suggest returns False."""
    sig = ["google_places", "entity:local_business"]
    assert is_never_suggest(sig, config_dir=tmp_path) is False


def test_add_never_suggest_persists(tmp_path):
    """add_never_suggest then is_never_suggest returns True for the same signature."""
    sig = ["google_places", "entity:local_business"]
    add_never_suggest(sig, "google_places", config_dir=tmp_path)
    assert is_never_suggest(sig, config_dir=tmp_path) is True


def test_never_suggest_sig_is_sorted(tmp_path):
    """Signatures are normalised by sorting; reversed order still matches."""
    sig_unsorted = ["entity:local_business", "google_places"]
    add_never_suggest(sig_unsorted, "google_places", config_dir=tmp_path)

    sig_reversed = ["google_places", "entity:local_business"]
    assert is_never_suggest(sig_reversed, config_dir=tmp_path) is True


def test_never_suggest_different_sig_does_not_block(tmp_path):
    """A never-suggest entry for one sig must not block a different sig."""
    sig_a = ["google_places", "entity:local_business"]
    sig_b = ["google_places", "entity:restaurant"]
    add_never_suggest(sig_a, "google_places", config_dir=tmp_path)
    assert is_never_suggest(sig_b, config_dir=tmp_path) is False


def test_preferences_file_created_at_config_path(tmp_path):
    """After add_never_suggest, preferences.yaml exists and contains the entry."""
    sig = ["google_places", "entity:local_business"]
    add_never_suggest(sig, "google_places", config_dir=tmp_path)

    prefs_file = tmp_path / "preferences.yaml"
    assert prefs_file.exists(), "preferences.yaml must be created in config_dir"

    contents = yaml.safe_load(prefs_file.read_text())
    assert "never_suggest" in contents
    assert len(contents["never_suggest"]) == 1
    entry = contents["never_suggest"][0]
    assert entry["integration_id"] == "google_places"
    assert entry["signature"] == sorted(sig)


# ---------------------------------------------------------------------------
# Group C: Adapter integration (Scenario 2) — uses fixture files
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not _google_places_fixture_available(),
    reason="Fixture tests/fixtures/integrations/google_places_madrid_cheese.json not yet created (T083)",
)
def test_google_places_fixture_response_parses_to_sources():
    """Fixture JSON can be parsed into Source objects with tier=B, valid title, and place_id URL."""
    from scripts.integrations.base import Source

    fixture_path = FIXTURES / "integrations" / "google_places_madrid_cheese.json"
    data = json.loads(fixture_path.read_text())
    results = data.get("results", [])
    assert results, "Fixture must contain at least one result"

    sources: list[Source] = []
    for result in results[:10]:
        place_id = result.get("place_id", "")
        sources.append(
            Source(
                url=f"https://maps.google.com/maps/place/?q=place_id:{place_id}",
                title=result.get("name", ""),
                snippet=result.get("formatted_address", ""),
                tier="B",
                integration="google_places",
            )
        )

    assert len(sources) > 0, "Must produce at least one Source from fixture"
    for src in sources:
        assert src.tier == "B", f"Expected tier='B', got {src.tier!r}"
        assert src.title, f"Source title must be non-empty; got {src.title!r}"
        assert "place_id:" in src.url, (
            f"Source URL must contain 'place_id:'; got {src.url!r}"
        )


def test_google_places_adapter_not_configured_returns_empty():
    """GooglePlacesIntegration.enrich with empty env (no API key) returns []."""
    try:
        from scripts.integrations.google_places import GooglePlacesIntegration
    except ImportError:
        pytest.skip("scripts/integrations/google_places.py not yet created (T081)")

    integration = GooglePlacesIntegration()
    result = integration.enrich("cheese shops Madrid", env={})
    assert result == [], (
        f"Expected empty list when not configured, got {result!r}"
    )


@pytest.mark.skipif(
    not _cheese_outline_available(),
    reason="Fixture tests/fixtures/outlines/cheese_shops_madrid.yaml not yet created (T083)",
)
def test_cheese_shops_outline_has_google_places_integration():
    """cheese_shops_madrid.yaml outline must declare google_places in topic_integrations."""
    outline_path = FIXTURES / "outlines" / "cheese_shops_madrid.yaml"
    outline = yaml.safe_load(outline_path.read_text())

    config = outline.get("config", {})
    topic_integrations = config.get("topic_integrations", [])
    assert "google_places" in topic_integrations, (
        f"Expected 'google_places' in outline['config']['topic_integrations'], "
        f"got {topic_integrations!r}"
    )
