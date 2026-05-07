"""SC-003: URL validation completeness.

Every URL in a report MUST either pass validation (ok=True) or produce an
explicit BROKEN_URL_MARKER in the report.  Zero silent drops.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_report import BROKEN_URL_MARKER, build_report

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
OUTLINES = FIXTURES / "outlines"
ITEM_JSONS = FIXTURES / "item_jsons"


def _load_json(path: Path) -> dict:
    with open(path) as fh:
        return json.load(fh)


def _load_yaml(path: Path) -> dict:
    import yaml  # pyyaml; already a project dep

    with open(path) as fh:
        return yaml.safe_load(fh)


def _collect_source_urls(item_jsons: list[dict]) -> list[str]:
    """Return every unique non-empty URL found in fields[*].sources."""
    seen: set[str] = set()
    urls: list[str] = []
    for j in item_jsons:
        for fdata in (j.get("fields") or {}).values():
            if not isinstance(fdata, dict):
                continue
            for src in fdata.get("sources") or []:
                url = src.get("url", "")
                if url and url not in seen:
                    seen.add(url)
                    urls.append(url)
    return urls


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def outline() -> dict:
    return _load_yaml(OUTLINES / "jest_vitest_playwright.yaml")


@pytest.fixture()
def fields_yaml() -> dict:
    return _load_yaml(OUTLINES / "jest_vitest_playwright_fields.yaml")


@pytest.fixture()
def jest_broken_item() -> dict:
    return _load_json(ITEM_JSONS / "us1_jest_broken_url.json")


@pytest.fixture()
def all_items() -> list[dict]:
    names = ["us1_jest_broken_url", "us1_vitest", "us1_playwright", "us1_mocha", "us1_jasmine"]
    return [_load_json(ITEM_JSONS / f"{name}.json") for name in names]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_sc003_broken_url_produces_marker(outline, fields_yaml, jest_broken_item):
    """A single broken URL must produce BROKEN_URL_MARKER in report_md."""
    broken_url = "https://broken.example.com/jest-perf"

    url_validation = {
        broken_url: {"url": broken_url, "ok": False, "status_code": 404},
    }

    result = build_report(
        outline,
        [jest_broken_item],
        fields_yaml=fields_yaml,
        url_validation=url_validation,
    )

    assert BROKEN_URL_MARKER in result["report_md"], (
        "report_md must contain BROKEN_URL_MARKER when a source URL is broken"
    )
    assert result["broken_url_count"] >= 1, (
        f"broken_url_count must be >= 1, got {result['broken_url_count']}"
    )


def test_sc003_zero_silent_drops(outline, fields_yaml, all_items):
    """When every source URL is marked broken, broken_url_count must equal the
    number of unique source URLs — no URL may be silently dropped."""
    all_urls = _collect_source_urls(all_items)
    assert all_urls, "Fixture item_jsons must contain at least one source URL"

    url_validation = {
        url: {"url": url, "ok": False, "status_code": 404}
        for url in all_urls
    }

    result = build_report(
        outline,
        all_items,
        fields_yaml=fields_yaml,
        url_validation=url_validation,
    )

    assert result["broken_url_count"] >= len(all_urls), (
        f"broken_url_count ({result['broken_url_count']}) must be >= "
        f"total unique source URLs ({len(all_urls)}); "
        "some URLs were silently dropped"
    )
