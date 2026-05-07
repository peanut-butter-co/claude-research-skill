import requests


def search(query: str, env: dict | None = None, count: int = 10, timeout: int = 10) -> dict:
    env = env or {}
    api_key = env.get("BRAVE_API_KEY")
    if not api_key:
        return {"ok": False, "results": [], "search_method": "brave", "error": "BRAVE_API_KEY not configured"}

    try:
        response = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": count},
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            timeout=timeout,
        )
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "brave", "error": str(exc)}

    if response.status_code == 401:
        return {"ok": False, "results": [], "search_method": "brave", "error": "Brave API: unauthorized (401)"}
    if response.status_code == 429:
        return {"ok": False, "results": [], "search_method": "brave", "error": "Brave API: rate limited (429)"}
    if not response.ok:
        return {"ok": False, "results": [], "search_method": "brave", "error": f"Brave API: HTTP {response.status_code}"}

    try:
        data = response.json()
        raw = data.get("web", {}).get("results", [])
        results = [
            {
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "snippet": item.get("description") or None,
            }
            for item in raw
        ]
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "brave", "error": f"Brave API: parse error: {exc}"}

    return {"ok": True, "results": results, "search_method": "brave", "error": None}
