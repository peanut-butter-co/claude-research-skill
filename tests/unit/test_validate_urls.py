from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.validate_urls import validate_url, validate_urls


def _mock_response(status_code: int) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    return resp


def test_head_200_returns_ok_no_get():
    with patch("scripts.validate_urls.requests.head", return_value=_mock_response(200)) as mock_head, \
         patch("scripts.validate_urls.requests.get") as mock_get:
        result = validate_url("https://example.com")

    assert result["ok"] is True
    assert result["method_used"] == "HEAD"
    assert result["status_code"] == 200
    assert result["error"] is None
    mock_get.assert_not_called()


def test_head_404_fallback_get_200():
    with patch("scripts.validate_urls.requests.head", return_value=_mock_response(404)), \
         patch("scripts.validate_urls.requests.get", return_value=_mock_response(200)):
        result = validate_url("https://example.com")

    assert result["ok"] is True
    assert result["method_used"] == "GET"
    assert result["status_code"] == 200
    assert result["error"] is None


def test_head_403_fallback_get_403():
    with patch("scripts.validate_urls.requests.head", return_value=_mock_response(403)), \
         patch("scripts.validate_urls.requests.get", return_value=_mock_response(403)):
        result = validate_url("https://example.com")

    assert result["ok"] is False
    assert result["method_used"] == "GET"
    assert result["status_code"] == 403
    assert result["error"] is None


def test_head_raises_fallback_get_200():
    with patch("scripts.validate_urls.requests.head", side_effect=requests.RequestException("timeout")), \
         patch("scripts.validate_urls.requests.get", return_value=_mock_response(200)):
        result = validate_url("https://example.com")

    assert result["ok"] is True
    assert result["method_used"] == "GET"
    assert result["status_code"] == 200
    assert result["error"] is None


def test_both_raise_exception():
    with patch("scripts.validate_urls.requests.head", side_effect=requests.RequestException("head failed")), \
         patch("scripts.validate_urls.requests.get", side_effect=requests.RequestException("get failed")):
        result = validate_url("https://example.com")

    assert result["ok"] is False
    assert result["error"] == "get failed"
    assert result["status_code"] is None


def test_validate_urls_preserves_order():
    responses = [200, 404, 200]
    side_effects = [_mock_response(code) for code in responses]

    with patch("scripts.validate_urls.requests.head", side_effect=side_effects), \
         patch("scripts.validate_urls.requests.get", return_value=_mock_response(200)):
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        results = validate_urls(urls)

    assert len(results) == 3
    assert [r["url"] for r in results] == urls
    assert results[0]["ok"] is True
    assert results[1]["ok"] is True
    assert results[2]["ok"] is True
