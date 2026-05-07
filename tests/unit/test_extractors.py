from unittest.mock import MagicMock, patch

import pytest

from scripts.extractors import jina, exa, wayback, browser


# ---------------------------------------------------------------------------
# Jina
# ---------------------------------------------------------------------------

def _mock_response(status_code: int, text: str = "") -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.ok = 200 <= status_code < 300
    r.text = text
    return r


def test_jina_200_with_body():
    with patch("scripts.extractors.jina.requests.get", return_value=_mock_response(200, "hello")):
        result = jina.fetch("https://example.com")
    assert result["ok"] is True
    assert result["content"] == "hello"
    assert result["fetch_method"] == "jina"


def test_jina_non_2xx():
    with patch("scripts.extractors.jina.requests.get", return_value=_mock_response(403)):
        result = jina.fetch("https://example.com")
    assert result["ok"] is False
    assert result["fetch_method"] == "jina"


def test_jina_empty_body():
    with patch("scripts.extractors.jina.requests.get", return_value=_mock_response(200, "   ")):
        result = jina.fetch("https://example.com")
    assert result["ok"] is False
    assert "empty" in result["error"]


# ---------------------------------------------------------------------------
# Exa
# ---------------------------------------------------------------------------

def test_exa_missing_key():
    result = exa.fetch("https://example.com", env={})
    assert result["ok"] is False
    assert "EXA_API_KEY" in result["error"]


def test_exa_200_success():
    payload = {"results": [{"text": "article text"}]}
    mock_resp = MagicMock()
    mock_resp.ok = True
    mock_resp.status_code = 200
    mock_resp.json.return_value = payload

    with patch("scripts.extractors.exa.requests.post", return_value=mock_resp):
        result = exa.fetch("https://example.com", env={"EXA_API_KEY": "key123"})

    assert result["ok"] is True
    assert result["content"] == "article text"
    assert result["fetch_method"] == "exa"


def test_exa_401():
    mock_resp = MagicMock()
    mock_resp.ok = False
    mock_resp.status_code = 401

    with patch("scripts.extractors.exa.requests.post", return_value=mock_resp):
        result = exa.fetch("https://example.com", env={"EXA_API_KEY": "bad"})

    assert result["ok"] is False
    assert "401" in result["error"] or "unauthorized" in result["error"].lower()


# ---------------------------------------------------------------------------
# Wayback
# ---------------------------------------------------------------------------

def test_wayback_no_snapshot():
    avail_resp = MagicMock()
    avail_resp.ok = True
    avail_resp.json.return_value = {"archived_snapshots": {}}

    with patch("scripts.extractors.wayback.requests.get", return_value=avail_resp):
        result = wayback.fetch("https://example.com")

    assert result["ok"] is False
    assert "no snapshot" in result["error"]


def test_wayback_snapshot_found():
    avail_resp = MagicMock()
    avail_resp.ok = True
    avail_resp.json.return_value = {
        "archived_snapshots": {
            "closest": {"available": True, "url": "https://web.archive.org/web/20240101/https://example.com"}
        }
    }

    page_resp = MagicMock()
    page_resp.ok = True
    page_resp.text = "archived content"

    with patch("scripts.extractors.wayback.requests.get", side_effect=[avail_resp, page_resp]):
        result = wayback.fetch("https://example.com")

    assert result["ok"] is True
    assert result["content"] == "archived content"
    assert result["fetch_method"] == "wayback"


# ---------------------------------------------------------------------------
# Browser detection
# ---------------------------------------------------------------------------

def test_browser_chrome_ext_via_env_var(monkeypatch):
    monkeypatch.setenv("CLAUDE_CHROME_EXT_AVAILABLE", "1")
    monkeypatch.delenv("MCP_SERVERS", raising=False)
    result = browser.detect_available()
    assert result["available"] is True
    assert result["method"] == "browser_ext"


def test_browser_only_playwright_in_mcp(monkeypatch):
    monkeypatch.delenv("CLAUDE_CHROME_EXT_AVAILABLE", raising=False)
    result = browser.detect_available(mcp_servers=["playwright"])
    assert result["available"] is True
    assert result["method"] == "playwright_mcp"
    assert result["fetch_method"] == "playwright-mcp"


def test_browser_nothing_available(monkeypatch):
    monkeypatch.delenv("CLAUDE_CHROME_EXT_AVAILABLE", raising=False)
    result = browser.detect_available(env={}, mcp_servers=[])
    assert result["available"] is False
    assert result["method"] is None
    assert result["fetch_method"] is None


def test_browser_fallback_order_chrome_ext_wins(monkeypatch):
    monkeypatch.setenv("CLAUDE_CHROME_EXT_AVAILABLE", "1")
    result = browser.detect_available(mcp_servers=["chrome-devtools", "playwright"])
    assert result["method"] == "browser_ext"
    assert result["fetch_method"] == "browser-ext"


def test_browser_fallback_order_chrome_mcp_before_playwright(monkeypatch):
    monkeypatch.delenv("CLAUDE_CHROME_EXT_AVAILABLE", raising=False)
    result = browser.detect_available(mcp_servers=["playwright", "chrome-devtools"])
    assert result["method"] == "chrome_mcp"
    assert result["fetch_method"] == "chrome-mcp"
