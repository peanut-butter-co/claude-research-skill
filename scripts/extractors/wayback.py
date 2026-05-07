import requests


def fetch(url: str, timeout: int = 15) -> dict:
    try:
        avail = requests.get(
            f"https://archive.org/wayback/available?url={url}",
            timeout=timeout,
        )
    except Exception as exc:
        return {"ok": False, "content": None, "fetch_method": "wayback", "error": str(exc), "source_url": url}

    if not avail.ok:
        return {"ok": False, "content": None, "fetch_method": "wayback", "error": f"availability check HTTP {avail.status_code}", "source_url": url}

    snapshot = avail.json().get("archived_snapshots", {}).get("closest", {})
    if not snapshot.get("available") or not snapshot.get("url"):
        return {"ok": False, "content": None, "fetch_method": "wayback", "error": "no snapshot available", "source_url": url}

    snapshot_url = snapshot["url"]

    try:
        page = requests.get(snapshot_url, timeout=timeout)
    except Exception as exc:
        return {"ok": False, "content": None, "fetch_method": "wayback", "error": str(exc), "source_url": url}

    if not page.ok:
        return {"ok": False, "content": None, "fetch_method": "wayback", "error": f"snapshot fetch HTTP {page.status_code}", "source_url": url}

    return {"ok": True, "content": page.text, "fetch_method": "wayback", "error": None, "source_url": url}
