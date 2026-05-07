"""Edge cases batch 1: zero-results, all-broken-URLs, all-Tier-D, ambiguous mode.

Covers four resilience scenarios for the build_report + mode_detect pipeline:

1. Zero results across all sources (every item JSON has empty `fields`)
2. All URLs broken (every source URL marked ok=False in url_validation)
3. All Tier D sources (FR-016a path: low-tier-only evidence surfaces as a gap
   or uncertainty, not a silent pass)
4. Mode detection on a genuinely ambiguous topic (no fast-path match → mode=None,
   consistent with confidence < 0.75 → AskUserQuestion behavior)

No live network calls; all fixture URLs are fake/example domains. Does NOT
invoke SKILL.md or Claude Code.
"""

from __future__ import annotations

import json
from pathlib import Path

import yaml

from scripts.build_report import BROKEN_URL_MARKER, build_report
from scripts.mode_detect import detect_mode_fast

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = REPO_ROOT / "data"
ITEMS = ["jest", "vitest", "playwright", "mocha", "jasmine"]


def _load_outline_and_fields() -> tuple[dict, dict]:
    outline = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright.yaml").read_text()
    )
    fields = yaml.safe_load(
        (FIXTURES / "outlines" / "jest_vitest_playwright_fields.yaml").read_text()
    )
    return outline, fields


def _load_standard_item_jsons() -> list[dict]:
    return [
        json.loads((FIXTURES / "item_jsons" / f"us1_{item}.json").read_text())
        for item in ITEMS
    ]


def _flat_field_names(fields_yaml: dict) -> list[str]:
    out: list[str] = []
    for category_fields in fields_yaml.get("categories", {}).values():
        out.extend(category_fields or [])
    return out


# ---------------------------------------------------------------------------
# Edge case 1: zero results across all sources
# ---------------------------------------------------------------------------


def test_edge_zero_results_produces_all_uncertain():
    """Every item JSON has empty `fields` → all cells [uncertain], report still written."""
    outline, fields = _load_outline_and_fields()
    field_names = _flat_field_names(fields)
    n_items = len(outline["items"])
    expected_min_gaps = n_items * len(field_names)

    # Build item JSONs with empty fields (no values, no sources)
    item_jsons = [
        {
            "item": item,
            "fields": {},
            "uncertain": [],
            "pruned": False,
            "emergent_threads_chased": [],
            "proposed_extensions": [],
            "budget_consumed": 0,
            "budget_exhausted": False,
        }
        for item in outline["items"]
    ]

    result = build_report(outline, item_jsons, fields_yaml=fields)
    md = result["report_md"]

    # Report is still written (not blocked by zero results)
    assert md, "report_md must be non-empty even with zero results"
    assert outline["topic"] in md, "Report must include topic header"
    assert "## Comparison" in md, "Report must include comparison section"

    # Every item × every field is uncertain → marker appears
    assert "[uncertain]" in md, "Report must contain [uncertain] marker for missing fields"

    # Gap count covers at least every missing field across every item
    assert result["gap_count"] >= expected_min_gaps, (
        f"Expected gap_count ≥ {expected_min_gaps} "
        f"(n_items={n_items} × n_fields={len(field_names)}), "
        f"got {result['gap_count']}"
    )


# ---------------------------------------------------------------------------
# Edge case 2: all URLs broken
# ---------------------------------------------------------------------------


def test_edge_all_urls_broken_report_still_written():
    """Every URL in every item is broken (404) → report written, broken count matches."""
    outline, fields = _load_outline_and_fields()
    item_jsons = _load_standard_item_jsons()

    # Collect every unique URL across all items
    all_urls: set[str] = set()
    for j in item_jsons:
        for fdata in j.get("fields", {}).values():
            for src in fdata.get("sources") or []:
                url = src.get("url")
                if url:
                    all_urls.add(url)

    assert all_urls, "Standard fixture JSONs must contain at least one URL"

    url_validation = {
        url: {
            "url": url,
            "ok": False,
            "status_code": 404,
            "method_used": "GET",
            "error": "404 Not Found",
        }
        for url in all_urls
    }

    result = build_report(
        outline, item_jsons, fields_yaml=fields, url_validation=url_validation
    )
    md = result["report_md"]

    # Report is non-empty (still written despite all URLs broken)
    assert md, "report_md must be non-empty even when all URLs are broken"

    # Broken-URL marker appears in the body
    assert BROKEN_URL_MARKER in md, (
        f"Expected BROKEN_URL_MARKER ({BROKEN_URL_MARKER!r}) to appear in report"
    )

    # Broken URLs section exists
    assert "### Broken URLs" in md, "Expected '### Broken URLs' section in report"

    # Broken URL count equals all unique URLs
    assert result["broken_url_count"] == len(all_urls), (
        f"Expected broken_url_count == {len(all_urls)}, "
        f"got {result['broken_url_count']}"
    )


# ---------------------------------------------------------------------------
# Edge case 3: all Tier D sources (FR-016a)
# ---------------------------------------------------------------------------


def test_edge_all_tier_d_gap_shown():
    """Field with only Tier D sources → gap or uncertain marker, never silent pass.

    FR-016a: when `include_tier_d` is false (the default in the standard outline),
    a field that has only Tier D sources is effectively unsupported. The agent
    should leave its value empty/uncertain, and the report must surface that —
    either as a gap or via [uncertain] in the rendered markdown.
    """
    # Outline contains a single synthetic item to keep the test scoped
    outline = {
        "mode": "comparative",
        "topic": "All-Tier-D edge case",
        "items": ["lonely-item"],
        "config": {"include_tier_d": False},
    }
    fields_yaml = {
        "categories": {
            "performance": ["startup_time"],
        },
        "detail": "moderate",
    }

    # Synthetic item: every source is Tier D, value left empty because no
    # trustworthy evidence is available under include_tier_d=False semantics.
    item_jsons = [
        {
            "item": "lonely-item",
            "fields": {
                "startup_time": {
                    "value": None,
                    "sources": [
                        {
                            "url": "https://random-blog.example.com/post-a",
                            "title": "Random blog post A",
                            "tier": "D",
                            "date": "2024-01-01",
                        },
                        {
                            "url": "https://random-blog.example.com/post-b",
                            "title": "Random blog post B",
                            "tier": "D",
                            "date": "2024-02-02",
                        },
                    ],
                }
            },
            "uncertain": [],
            "pruned": False,
            "budget_consumed": 1,
            "budget_exhausted": False,
        }
    ]

    result = build_report(outline, item_jsons, fields_yaml=fields_yaml)
    md = result["report_md"]

    # FR-016a: surface the gap, not a silent pass
    assert result["gap_count"] >= 1 or "[uncertain]" in md, (
        "All-Tier-D field must produce a gap or [uncertain] marker in the report; "
        f"got gap_count={result['gap_count']} and "
        f"[uncertain]-in-md={'[uncertain]' in md}"
    )


# ---------------------------------------------------------------------------
# Edge case 4: mode-detection ambiguous threshold
# ---------------------------------------------------------------------------


def test_edge_mode_ambiguous_threshold():
    """Genuinely ambiguous topic → mode=None (falls through to LLM / AskUserQuestion).

    Per data/mode-detection.yaml, threshold=0.75. A topic that matches no fast-path
    regex returns {"mode": None, "confidence": 0.0}, which downstream is treated as
    confidence < threshold → AskUserQuestion. This test pins both branches:
      - ambiguous topic → mode is None
      - clearly-comparative topic → mode is "comparative" with high confidence
    """
    # Ambiguous: no comparative keyword, no comma list, no "vs" / "compare"
    ambiguous_topic = "trade-offs of serverless architectures"
    result_ambiguous = detect_mode_fast(ambiguous_topic, data_dir=DATA_DIR)
    assert result_ambiguous["mode"] is None, (
        f"Ambiguous topic {ambiguous_topic!r} should fall through to LLM "
        f"(mode=None), got mode={result_ambiguous['mode']!r}"
    )
    assert result_ambiguous["confidence"] < 0.75, (
        f"Ambiguous fast-path confidence must be < threshold 0.75, "
        f"got {result_ambiguous['confidence']}"
    )

    # Comparative fast-path: "compare" keyword → high-confidence comparative
    comparative_topic = "Compare Vite, Webpack, and esbuild for a React monorepo"
    result_comparative = detect_mode_fast(comparative_topic, data_dir=DATA_DIR)
    assert result_comparative["mode"] == "comparative", (
        f"Comparative topic {comparative_topic!r} should match fast-path, "
        f"got mode={result_comparative['mode']!r}"
    )
    assert result_comparative["confidence"] >= 0.75, (
        f"Comparative fast-path confidence must be ≥ threshold 0.75, "
        f"got {result_comparative['confidence']}"
    )
