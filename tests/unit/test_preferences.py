from pathlib import Path

import pytest

from scripts.preferences import (
    add_never_suggest,
    is_never_suggest,
    load_preferences,
    save_preferences,
)


def test_load_missing_file_returns_empty(tmp_path):
    prefs = load_preferences(tmp_path)
    assert prefs == {"never_suggest": []}


def test_save_and_load_round_trip(tmp_path):
    data = {
        "never_suggest": [
            {
                "signature": ["google_places", "restaurant"],
                "integration_id": "google_places",
                "recorded_at": "2026-05-07T00:00:00+00:00",
            }
        ]
    }
    save_preferences(data, tmp_path)
    loaded = load_preferences(tmp_path)
    assert loaded == data


def test_add_never_suggest_creates_entry_with_sorted_signature(tmp_path):
    add_never_suggest(["restaurant", "google_places"], "google_places", tmp_path)
    prefs = load_preferences(tmp_path)
    assert len(prefs["never_suggest"]) == 1
    entry = prefs["never_suggest"][0]
    assert entry["signature"] == ["google_places", "restaurant"]
    assert entry["integration_id"] == "google_places"
    assert "recorded_at" in entry


def test_add_never_suggest_appends_to_existing(tmp_path):
    add_never_suggest(["tag_a"], "integration_a", tmp_path)
    add_never_suggest(["tag_b"], "integration_b", tmp_path)
    prefs = load_preferences(tmp_path)
    assert len(prefs["never_suggest"]) == 2


def test_is_never_suggest_returns_true_for_match(tmp_path):
    add_never_suggest(["google_places", "hotel"], "google_places", tmp_path)
    assert is_never_suggest(["google_places", "hotel"], tmp_path) is True


def test_is_never_suggest_returns_false_for_no_match(tmp_path):
    add_never_suggest(["google_places", "hotel"], "google_places", tmp_path)
    assert is_never_suggest(["google_places", "restaurant"], tmp_path) is False


def test_is_never_suggest_order_independent(tmp_path):
    add_never_suggest(["z_tag", "a_tag", "m_tag"], "some_integration", tmp_path)
    assert is_never_suggest(["m_tag", "z_tag", "a_tag"], tmp_path) is True
    assert is_never_suggest(["a_tag", "z_tag", "m_tag"], tmp_path) is True
