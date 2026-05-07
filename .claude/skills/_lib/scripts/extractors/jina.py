import requests


def fetch(url: str, timeout: int = 15) -> dict:
    try:
        resp = requests.get(f"https://r.jina.ai/{url}", timeout=timeout)
    except Exception as exc:
        return {"ok": False, "content": None, "fetch_method": "jina", "error": str(exc), "source_url": url}

    if not resp.ok or not resp.text.strip():
        return {
            "ok": False,
            "content": None,
            "fetch_method": "jina",
            "error": f"HTTP {resp.status_code}" if not resp.ok else "empty body",
            "source_url": url,
        }

    return {"ok": True, "content": resp.text, "fetch_method": "jina", "error": None, "source_url": url}
