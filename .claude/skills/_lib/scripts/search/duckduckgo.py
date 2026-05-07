import urllib.parse
import urllib.request
from html.parser import HTMLParser


class _DDGParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self._results: list[dict] = []
        self._current_url: str | None = None
        self._current_title_parts: list[str] = []
        self._in_title: bool = False
        self._current_snippet_parts: list[str] = []
        self._in_snippet: bool = False

    def handle_starttag(self, tag, attrs):
        attr_map = dict(attrs)
        classes = attr_map.get("class", "")
        if tag == "a" and "result__a" in classes:
            self._current_url = attr_map.get("href", "")
            self._current_title_parts = []
            self._in_title = True
        elif tag in ("span", "a") and "result__snippet" in classes:
            self._current_snippet_parts = []
            self._in_snippet = True

    def handle_endtag(self, tag):
        if self._in_title and tag == "a":
            self._in_title = False
            if self._current_url:
                self._results.append({
                    "url": self._current_url,
                    "title": "".join(self._current_title_parts).strip(),
                    "snippet": None,
                })
                self._current_url = None
        elif self._in_snippet and tag in ("span", "a"):
            self._in_snippet = False
            if self._results:
                self._results[-1]["snippet"] = "".join(self._current_snippet_parts).strip() or None

    def handle_data(self, data):
        if self._in_title:
            self._current_title_parts.append(data)
        elif self._in_snippet:
            self._current_snippet_parts.append(data)


def search(query: str, count: int = 10, timeout: int = 10) -> dict:
    url = f"https://duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; research-skill/1.0)"},
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "duckduckgo", "error": str(exc)}

    parser = _DDGParser()
    try:
        parser.feed(html)
    except Exception as exc:
        return {"ok": False, "results": [], "search_method": "duckduckgo", "error": f"parse error: {exc}"}

    results = [r for r in parser._results if r["url"]][:count]

    if not results:
        return {"ok": False, "results": [], "search_method": "duckduckgo", "error": "no results parsed"}

    return {"ok": True, "results": results, "search_method": "duckduckgo", "error": None}
