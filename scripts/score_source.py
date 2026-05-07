from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

DEFAULT_DATA_DIR = Path(__file__).parent.parent / "data"

TIER_WEIGHTS = {"A": 4, "B": 3, "C": 2, "D": 0.5, "Unknown": 2}

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[^\s\"<>]+", re.IGNORECASE)
_ISBN_RE = re.compile(r"\b(?:ISBN(?:-1[03])?:?\s*)?(?=[0-9X]{10}\b|(?=(?:[0-9]+[- ]){3})[- 0-9X]{13}\b|97[89][0-9]{10}\b|(?=(?:[0-9]+[- ]){4})[- 0-9]{17}\b)(?:97[89][- ]?)?[0-9]{1,5}[- ]?[0-9]+[- ]?[0-9]+[- ]?[0-9X]\b", re.IGNORECASE)
_MEDIUM_PSEUDONYM_RE = re.compile(r"medium\.com/@[^/]+", re.IGNORECASE)
_LISTICLE_RE = re.compile(r"/(?:top|best|worst|cheapest|greatest)-\d+", re.IGNORECASE)
_WP_AGGREGATOR_HINTS = ("/wp-content/", "/wp-includes/", "/?p=")

_tiers_cache: dict[Path, dict] = {}
_graph_cache: dict[Path, dict] = {}


def _resolve_data_dir(data_dir: Path | None) -> Path:
    return data_dir if data_dir is not None else DEFAULT_DATA_DIR


def _load_tiers(data_dir: Path) -> dict:
    if data_dir in _tiers_cache:
        return _tiers_cache[data_dir]
    path = data_dir / "source-tiers.yaml"
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    domains = (raw.get("domains") or {}) if isinstance(raw, dict) else {}
    _tiers_cache[data_dir] = domains
    return domains


def _load_graph(data_dir: Path) -> dict:
    if data_dir in _graph_cache:
        return _graph_cache[data_dir]
    path = data_dir / "publisher-graph.yaml"
    with path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}
    parents = (raw.get("parents") or {}) if isinstance(raw, dict) else {}
    _graph_cache[data_dir] = parents
    return parents


def _normalise_host(url: str) -> str:
    parsed = urlparse(url if "://" in url else f"http://{url}")
    host = (parsed.hostname or "").lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _root_domain(host: str) -> str:
    parts = host.split(".")
    if len(parts) <= 2:
        return host
    return ".".join(parts[-2:])


def _registry_lookup(host: str, tiers: dict) -> str | None:
    if host in tiers:
        entry = tiers[host]
        if isinstance(entry, dict) and "tier" in entry:
            return entry["tier"]
    parts = host.split(".")
    for i in range(1, len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in tiers:
            entry = tiers[candidate]
            if isinstance(entry, dict) and "tier" in entry:
                return entry["tier"]
    return None


def _has_doi_or_isbn(text: str) -> bool:
    if not text:
        return False
    if _DOI_RE.search(text):
        return True
    if _ISBN_RE.search(text):
        return True
    return False


def _academic_suffix(host: str) -> bool:
    if host.endswith(".edu") or host.endswith(".gov"):
        return True
    if host.endswith(".ac.uk") or host.endswith(".edu.au") or host.endswith(".ac.jp"):
        return True
    if host.endswith(".org") and any(tag in host for tag in ("university", "institute", "research", "academy")):
        return True
    return False


def _suspicious_flags(url: str, title: str) -> list[str]:
    flags: list[str] = []
    if _MEDIUM_PSEUDONYM_RE.search(url):
        flags.append("medium_pseudonym")
    if _LISTICLE_RE.search(url):
        flags.append("listicle_no_author")
    if any(hint in url for hint in _WP_AGGREGATOR_HINTS):
        flags.append("wordpress_aggregator")
    intro_pattern = re.compile(r"\bin this article\b", re.IGNORECASE)
    if title and intro_pattern.search(title):
        flags.append("heuristic_d_ai_tells")
    return flags


def assign_tier(url: str, title: str = "", data_dir: Path | None = None) -> dict:
    data_dir = _resolve_data_dir(data_dir)
    tiers = _load_tiers(data_dir)
    host = _normalise_host(url)

    registry_tier = _registry_lookup(host, tiers)
    if registry_tier is not None:
        return {
            "url": url,
            "tier": registry_tier,
            "source": "registry",
            "unclassified": False,
            "heuristic_flags": [],
        }

    flags = _suspicious_flags(url, title)
    heuristic_d = bool(flags)

    pushed_to_b = False
    if _has_doi_or_isbn(url) or _has_doi_or_isbn(title):
        pushed_to_b = True
    elif _academic_suffix(host):
        pushed_to_b = True

    if heuristic_d and not pushed_to_b:
        tier = "D"
        source = "heuristic"
    elif pushed_to_b:
        tier = "B"
        source = "heuristic"
    else:
        tier = "Unknown"
        source = "heuristic"

    return {
        "url": url,
        "tier": tier,
        "source": source,
        "unclassified": True,
        "heuristic_flags": flags,
    }


def _years_since(pub_date: str | None) -> float | None:
    if not pub_date:
        return None
    try:
        dt = datetime.fromisoformat(pub_date.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(pub_date, "%Y-%m-%d")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    now = datetime.now(timezone.utc)
    delta_days = (now - dt).days
    return delta_days / 365.25


def _recency_bonus(years: float | None, is_historical: bool) -> float:
    if years is None:
        return 0.6
    if is_historical:
        if years > 5:
            return 1.0
        if years >= 3:
            return 0.8
        if years >= 1:
            return 0.6
        return 0.4
    if years < 1:
        return 1.0
    if years < 3:
        return 0.8
    if years < 5:
        return 0.6
    return 0.4


def score_source(
    url: str,
    tier: str,
    pub_date: str | None,
    is_historical_topic: bool = False,
    data_dir: Path | None = None,
) -> dict:
    weight = TIER_WEIGHTS.get(tier, TIER_WEIGHTS["Unknown"])
    years = _years_since(pub_date)
    recency = _recency_bonus(years, is_historical_topic)
    raw = weight * recency
    eligible = tier in ("A", "B")
    return {
        "url": url,
        "tier": tier,
        "tier_weight": weight,
        "recency_bonus": recency,
        "score_raw": raw,
        "cross_citation_bonus_eligible": eligible,
        "pub_date": pub_date,
    }


def get_publisher(domain: str, data_dir: Path | None = None) -> str:
    data_dir = _resolve_data_dir(data_dir)
    parents = _load_graph(data_dir)
    host = _normalise_host(domain)
    if host in parents:
        return parents[host]
    parts = host.split(".")
    for i in range(1, len(parts) - 1):
        candidate = ".".join(parts[i:])
        if candidate in parents:
            return parents[candidate]
    return _root_domain(host)


def apply_cross_citation_bonus(sources: list[dict], data_dir: Path | None = None) -> list[dict]:
    data_dir = _resolve_data_dir(data_dir)
    eligible_idx = [i for i, s in enumerate(sources) if s.get("cross_citation_bonus_eligible")]
    publishers: dict[int, str] = {}
    for i in eligible_idx:
        publishers[i] = get_publisher(sources[i]["url"], data_dir=data_dir)
    distinct = {publishers[i] for i in eligible_idx}
    bonus_value = 0.5 if len(distinct) >= 2 else 0.0

    out: list[dict] = []
    for i, s in enumerate(sources):
        new = dict(s)
        if i in eligible_idx and bonus_value > 0:
            new["cross_citation_bonus"] = bonus_value
            new["score"] = s["score_raw"] + bonus_value
        else:
            new["cross_citation_bonus"] = 0.0
            new["score"] = s["score_raw"]
        new["publisher"] = publishers.get(i, get_publisher(s["url"], data_dir=data_dir))
        out.append(new)
    return out


def _effective_score(s: dict) -> float:
    if "score" in s:
        return s["score"]
    return s.get("score_raw", 0.0) + s.get("cross_citation_bonus", 0.0)


def _recency_value(s: dict) -> float:
    years = _years_since(s.get("pub_date"))
    if years is None:
        return float("inf")
    return years


def compare_sources(a: dict, b: dict) -> int:
    sa, sb = _effective_score(a), _effective_score(b)
    if sa > sb:
        return -1
    if sa < sb:
        return 1

    wa, wb = a.get("tier_weight", 0), b.get("tier_weight", 0)
    if wa > wb:
        return -1
    if wa < wb:
        return 1

    ra, rb = _recency_value(a), _recency_value(b)
    if ra < rb:
        return -1
    if ra > rb:
        return 1

    claim_a = a.get("claim")
    claim_b = b.get("claim")
    if claim_a is not None and claim_b is not None and claim_a != claim_b:
        a["conflict"] = True
        b["conflict"] = True
    return 0
