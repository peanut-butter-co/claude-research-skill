import os


_TIER2 = [
    {
        "name": "browser_ext",
        "fetch_method": "browser-ext",
        "detect_type": "env",
        "detect_value": "CLAUDE_CHROME_EXT_AVAILABLE",
    },
    {
        "name": "chrome_mcp",
        "fetch_method": "chrome-mcp",
        "detect_type": "mcp",
        "detect_value": "chrome-devtools",
    },
    {
        "name": "playwright_mcp",
        "fetch_method": "playwright-mcp",
        "detect_type": "mcp",
        "detect_value": "playwright",
    },
]


def detect_available(env: dict | None = None, mcp_servers: list[str] | None = None) -> dict:
    env = env or {}

    if mcp_servers is None:
        raw = os.environ.get("MCP_SERVERS", "")
        mcp_servers = [s.strip() for s in raw.split(",") if s.strip()] if raw else []

    for entry in _TIER2:
        if entry["detect_type"] == "env":
            available = bool(
                env.get(entry["detect_value"]) or os.environ.get(entry["detect_value"])
            )
        else:
            available = entry["detect_value"] in mcp_servers

        if available:
            return {"available": True, "method": entry["name"], "fetch_method": entry["fetch_method"]}

    return {"available": False, "method": None, "fetch_method": None}
