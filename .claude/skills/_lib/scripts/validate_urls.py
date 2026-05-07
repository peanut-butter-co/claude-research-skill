from __future__ import annotations

import requests

HEADERS = {"User-Agent": "research-skill/1.0"}


def validate_url(url: str, timeout: int = 10) -> dict:
    result: dict = {
        "url": url,
        "ok": False,
        "status_code": None,
        "method_used": None,
        "error": None,
    }

    try:
        resp = requests.head(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        if 200 <= resp.status_code < 300:
            result["ok"] = True
            result["status_code"] = resp.status_code
            result["method_used"] = "HEAD"
            return result
        head_status = resp.status_code
    except Exception as head_exc:
        head_status = None
        _ = head_exc

    try:
        resp = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        result["status_code"] = resp.status_code
        result["method_used"] = "GET"
        if 200 <= resp.status_code < 300:
            result["ok"] = True
        return result
    except Exception as get_exc:
        result["status_code"] = head_status
        result["error"] = str(get_exc)
        return result


def validate_urls(urls: list[str], timeout: int = 10) -> list[dict]:
    return [validate_url(url, timeout=timeout) for url in urls]
