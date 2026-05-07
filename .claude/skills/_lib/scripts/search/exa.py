import requests


def search(query: str, env: dict | None = None, count: int = 10, timeout: int = 10) -> dict:
    env = env or {}
    api_key = env.get("EXA_API_KEY")
    if not api_key:
        return {"ok": False, "results": [], "search_method": "exa", "error": "EXA_API_KEY not configured"}

    try:
        response = requests.post(
            "https://api.exa.ai/search",
            json={"query": query, "numResults": count},
            headers={
                "Content-Type": "application/json",
                "x-api-key": api_key,
            },
            timeout=timeout,
        )
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "exa", "error": str(exc)}

    if not response.ok:
        return {"ok": False, "results": [], "search_method": "exa", "error": f"Exa API: HTTP {response.status_code}"}

    try:
        data = response.json()
        raw = data.get("results", [])
        results = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": item.get("snippet") or item.get("text") or None,
            }
            for item in raw
        ]
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "exa", "error": f"Exa API: parse error: {exc}"}

    return {"ok": True, "results": results, "search_method": "exa", "error": None}
