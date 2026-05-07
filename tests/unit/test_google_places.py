import pytest
import requests
from unittest.mock import MagicMock

from scripts.integrations.google_places import GooglePlacesIntegration


@pytest.fixture
def adapter():
    return GooglePlacesIntegration()


def _two_result_mock():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "name": "Quesería Cultivo",
                "formatted_address": "Calle del General Lacy 10, Madrid",
                "place_id": "ChIJxxx1",
            },
            {
                "name": "La Boulette",
                "formatted_address": "Calle de Argumosa 25, Madrid",
                "place_id": "ChIJxxx2",
            },
        ]
    }
    return mock_resp


# ---------------------------------------------------------------------------
# is_configured
# ---------------------------------------------------------------------------

def test_is_configured_with_key(adapter):
    assert adapter.is_configured({"GOOGLE_PLACES_KEY": "abc"}) is True


def test_is_configured_without_key(adapter):
    assert adapter.is_configured({}) is False


# ---------------------------------------------------------------------------
# enrich — no HTTP call when not configured
# ---------------------------------------------------------------------------

def test_enrich_returns_empty_when_not_configured(adapter, monkeypatch):
    called = []
    monkeypatch.setattr("scripts.integrations.google_places.requests.get", lambda *a, **kw: called.append(1))
    result = adapter.enrich("cheese shops Madrid", env={})
    assert result == []
    assert called == [], "requests.get should not be called when not configured"


# ---------------------------------------------------------------------------
# enrich — success path
# ---------------------------------------------------------------------------

def test_enrich_returns_sources_on_success(adapter, monkeypatch):
    monkeypatch.setattr(
        "scripts.integrations.google_places.requests.get",
        lambda *a, **kw: _two_result_mock(),
    )
    sources = adapter.enrich("cheese shops Madrid", env={"GOOGLE_PLACES_KEY": "key123"})
    assert len(sources) == 2


def test_enrich_source_has_correct_fields(adapter, monkeypatch):
    monkeypatch.setattr(
        "scripts.integrations.google_places.requests.get",
        lambda *a, **kw: _two_result_mock(),
    )
    sources = adapter.enrich("cheese shops Madrid", env={"GOOGLE_PLACES_KEY": "key123"})
    source = sources[0]
    assert source.tier == "B"
    assert source.integration == "google_places"
    assert source.url
    assert source.title
    assert source.snippet


def test_enrich_url_contains_place_id(adapter, monkeypatch):
    monkeypatch.setattr(
        "scripts.integrations.google_places.requests.get",
        lambda *a, **kw: _two_result_mock(),
    )
    sources = adapter.enrich("cheese shops Madrid", env={"GOOGLE_PLACES_KEY": "key123"})
    assert "place_id:" in sources[0].url
    assert "ChIJxxx1" in sources[0].url


# ---------------------------------------------------------------------------
# enrich — error paths
# ---------------------------------------------------------------------------

def test_enrich_returns_empty_on_http_error(adapter, monkeypatch):
    mock_resp = MagicMock()
    mock_resp.status_code = 500
    monkeypatch.setattr(
        "scripts.integrations.google_places.requests.get",
        lambda *a, **kw: mock_resp,
    )
    result = adapter.enrich("cheese shops Madrid", env={"GOOGLE_PLACES_KEY": "key123"})
    assert result == []


def test_enrich_returns_empty_on_connection_error(adapter, monkeypatch):
    def raise_conn_error(*a, **kw):
        raise requests.exceptions.ConnectionError("unreachable")

    monkeypatch.setattr(
        "scripts.integrations.google_places.requests.get",
        raise_conn_error,
    )
    result = adapter.enrich("cheese shops Madrid", env={"GOOGLE_PLACES_KEY": "key123"})
    assert result == []
