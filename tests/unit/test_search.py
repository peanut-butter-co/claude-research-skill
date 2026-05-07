import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from scripts.search import brave, exa, duckduckgo


_BRAVE_ENV = {"BRAVE_API_KEY": "test-brave-key"}
_EXA_ENV = {"EXA_API_KEY": "test-exa-key"}

_BRAVE_RESPONSE = {
    "web": {
        "results": [
            {"url": "https://example.com/a", "title": "Result A", "description": "Snippet A"},
            {"url": "https://example.com/b", "title": "Result B", "description": "Snippet B"},
        ]
    }
}

_EXA_RESPONSE = {
    "results": [
        {"url": "https://example.com/x", "title": "Exa Result X", "snippet": "Exa snippet X"},
        {"url": "https://example.com/y", "title": "Exa Result Y", "text": "Exa text Y"},
    ]
}

_DDG_HTML = """
<html><body>
<a class="result__a" href="https://example.com/1">Page One</a>
<span class="result__snippet">Snippet for page one</span>
<a class="result__a" href="https://example.com/2">Page Two</a>
<span class="result__snippet">Snippet for page two</span>
</body></html>
"""


def _mock_response(status_code: int, json_data: dict | None = None) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.ok = (200 <= status_code < 300)
    mock.json.return_value = json_data or {}
    return mock


# --- Brave ---

def test_brave_missing_key():
    result = brave.search("test query", env={})
    assert result["ok"] is False
    assert result["error"] == "BRAVE_API_KEY not configured"
    assert result["search_method"] == "brave"


def test_brave_200_with_results():
    with patch("scripts.search.brave.requests.get", return_value=_mock_response(200, _BRAVE_RESPONSE)):
        result = brave.search("test", env=_BRAVE_ENV)
    assert result["ok"] is True
    assert result["search_method"] == "brave"
    assert len(result["results"]) == 2
    assert result["results"][0]["url"] == "https://example.com/a"
    assert result["results"][0]["title"] == "Result A"
    assert result["results"][0]["snippet"] == "Snippet A"
    assert result["error"] is None


def test_brave_401():
    with patch("scripts.search.brave.requests.get", return_value=_mock_response(401)):
        result = brave.search("test", env=_BRAVE_ENV)
    assert result["ok"] is False
    assert "401" in result["error"]
    assert result["search_method"] == "brave"


def test_brave_429():
    with patch("scripts.search.brave.requests.get", return_value=_mock_response(429)):
        result = brave.search("test", env=_BRAVE_ENV)
    assert result["ok"] is False
    assert "429" in result["error"]
    assert result["search_method"] == "brave"


# --- Exa ---

def test_exa_missing_key():
    result = exa.search("test query", env={})
    assert result["ok"] is False
    assert result["error"] == "EXA_API_KEY not configured"
    assert result["search_method"] == "exa"


def test_exa_200_with_results():
    with patch("scripts.search.exa.requests.post", return_value=_mock_response(200, _EXA_RESPONSE)):
        result = exa.search("test", env=_EXA_ENV)
    assert result["ok"] is True
    assert result["search_method"] == "exa"
    assert len(result["results"]) == 2
    assert result["results"][0]["url"] == "https://example.com/x"
    assert result["results"][0]["snippet"] == "Exa snippet X"
    assert result["results"][1]["snippet"] == "Exa text Y"
    assert result["error"] is None


# --- DuckDuckGo ---

def _mock_ddg_urlopen(html: str):
    mock_resp = MagicMock()
    mock_resp.read.return_value = html.encode("utf-8")
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    return mock_resp


def test_duckduckgo_valid_html():
    with patch("scripts.search.duckduckgo.urllib.request.urlopen", return_value=_mock_ddg_urlopen(_DDG_HTML)):
        result = duckduckgo.search("test")
    assert result["ok"] is True
    assert result["search_method"] == "duckduckgo"
    assert len(result["results"]) >= 1
    assert result["results"][0]["url"] == "https://example.com/1"
    assert result["results"][0]["title"] == "Page One"
    assert result["error"] is None


def test_duckduckgo_empty_results():
    empty_html = "<html><body><p>No results found.</p></body></html>"
    with patch("scripts.search.duckduckgo.urllib.request.urlopen", return_value=_mock_ddg_urlopen(empty_html)):
        result = duckduckgo.search("test")
    assert result["ok"] is False
    assert result["error"] is not None
    assert result["search_method"] == "duckduckgo"


# --- Network exceptions ---

def test_brave_network_exception():
    with patch("scripts.search.brave.requests.get", side_effect=Exception("connection refused")):
        result = brave.search("test", env=_BRAVE_ENV)
    assert result["ok"] is False
    assert result["error"] == "connection refused"
    assert result["search_method"] == "brave"


def test_exa_network_exception():
    with patch("scripts.search.exa.requests.post", side_effect=Exception("timeout")):
        result = exa.search("test", env=_EXA_ENV)
    assert result["ok"] is False
    assert result["error"] == "timeout"
    assert result["search_method"] == "exa"


def test_duckduckgo_network_exception():
    with patch("scripts.search.duckduckgo.urllib.request.urlopen", side_effect=Exception("DNS failure")):
        result = duckduckgo.search("test")
    assert result["ok"] is False
    assert result["error"] == "DNS failure"
    assert result["search_method"] == "duckduckgo"
