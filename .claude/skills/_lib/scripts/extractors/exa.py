import requests


def fetch(url: str, env: dict | None = None, timeout: int = 15) -> dict:
    env = env or {}
    api_key = env.get("EXA_API_KEY")

    if not api_key:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": "EXA_API_KEY not configured", "source_url": url}

    try:
        resp = requests.post(
            "https://api.exa.ai/contents",
            json={"ids": [url]},
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            timeout=timeout,
        )
    except Exception as exc:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": str(exc), "source_url": url}

    if resp.status_code == 401:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": "unauthorized: invalid EXA_API_KEY", "source_url": url}

    if resp.status_code == 429:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": "rate limited", "source_url": url}

    if not resp.ok:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": f"HTTP {resp.status_code}", "source_url": url}

    data = resp.json()
    results = data.get("results") or []
    text = results[0].get("text") or results[0].get("content") if results else None

    if not text:
        return {"ok": False, "content": None, "fetch_method": "exa", "error": "no content in response", "source_url": url}

    return {"ok": True, "content": text, "fetch_method": "exa", "error": None, "source_url": url}
