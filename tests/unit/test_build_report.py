from __future__ import annotations

import csv
import io

import pytest

from scripts.build_report import (
    BROKEN_URL_MARKER,
    UNCERTAIN_MARKER,
    build_report,
)


def _comparative_outline() -> dict:
    return {
        "mode": "comparative",
        "topic": "Compare Jest, Vitest",
        "items": ["jest", "vitest"],
        "fields_file": "fields.yaml",
        "config": {"items_per_batch": 1, "social_signal": False, "rigor": "standard"},
    }


def _fields_yaml() -> dict:
    return {
        "categories": {
            "performance": ["startup_ms"],
            "ergonomics": ["dx"],
        },
        "detail": "moderate",
    }


def _src(url: str, tier: str = "B", title: str = "Doc", **extra) -> dict:
    base = {"url": url, "tier": tier, "title": title, "date": "2025-01-01"}
    base.update(extra)
    return base


def _comparative_jsons() -> list[dict]:
    return [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {
                    "value": "850ms",
                    "sources": [_src("https://jestjs.io/docs", tier="A", title="Jest docs")],
                },
                "dx": {
                    "value": "mature, slower",
                    "sources": [_src("https://blog.example.com/jest-dx", tier="B", title="Jest DX")],
                },
            },
            "uncertain": [],
            "budget_consumed": 8,
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {
                    "value": "120ms",
                    "sources": [_src("https://vitest.dev/guide", tier="A", title="Vitest guide")],
                },
                "dx": {
                    "value": "modern, fast HMR",
                    "sources": [_src("https://news.example.com/vitest", tier="B", title="Vitest review")],
                },
            },
            "uncertain": [],
            "budget_consumed": 10,
        },
    ]


def test_comparative_md_basic_structure():
    out = build_report(_comparative_outline(), _comparative_jsons(), fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "# Compare Jest, Vitest" in md
    assert "## Table of contents" in md
    assert "## Comparison" in md
    assert "| Item | startup_ms | dx |" in md
    assert "| jest |" in md
    assert "| vitest |" in md
    assert "## jest" in md
    assert "## vitest" in md
    assert "## Sources note" in md
    assert "### Tier A" in md
    assert "### Tier B" in md


def test_comparative_csv_header_and_rows():
    out = build_report(_comparative_outline(), _comparative_jsons(), fields_yaml=_fields_yaml())
    rows = list(csv.reader(io.StringIO(out["report_csv"])))
    assert rows[0] == ["item", "startup_ms", "dx"]
    assert rows[1] == ["jest", "850ms", "mature, slower"]
    assert rows[2] == ["vitest", "120ms", "modern, fast HMR"]


def test_narrative_md_essay_and_cross_cutting():
    outline = {
        "mode": "narrative",
        "topic": "Impact of EU AI Act",
        "subqueries": ["scope of obligations", "compliance costs"],
        "config": {"social_signal": False, "rigor": "standard"},
    }
    jsons = [
        {
            "subquery": "scope of obligations",
            "fields": {
                "summary": {
                    "value": "covers high-risk AI systems",
                    "sources": [_src("https://eur-lex.europa.eu/x", tier="A", title="EUR-Lex")],
                }
            },
            "uncertain": [],
            "proposed_extensions": [{"type": "subquery", "description": "SME exemptions"}],
        },
        {
            "subquery": "compliance costs",
            "fields": {
                "summary": {
                    "value": "estimated 5-10% of revenue",
                    "sources": [_src("https://example-think-tank.org/x", tier="B", title="Think tank")],
                }
            },
            "uncertain": [],
        },
    ]
    out = build_report(outline, jsons)
    md = out["report_md"]
    assert "# Impact of EU AI Act" in md
    assert "## scope of obligations" in md
    assert "## compliance costs" in md
    assert "## Cross-cutting findings" in md
    assert "SME exemptions" in md
    assert out["report_csv"] == ""


def test_inline_citation_format():
    out = build_report(_comparative_outline(), _comparative_jsons(), fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "[Jest docs • Tier A](https://jestjs.io/docs)" in md
    assert "[Vitest guide • Tier A](https://vitest.dev/guide)" in md


def test_uncertain_field_propagates_to_table_and_gaps():
    jsons = [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {"value": UNCERTAIN_MARKER, "sources": []},
                "dx": {"value": "mature", "sources": [_src("https://j.example", tier="B")]},
            },
            "uncertain": ["startup_ms"],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "## Gaps" in md
    assert "jest: startup_ms" in md
    assert out["gap_count"] >= 1
    rows = list(csv.reader(io.StringIO(out["report_csv"])))
    jest_row = next(r for r in rows if r[0] == "jest")
    assert UNCERTAIN_MARKER in jest_row


def test_broken_url_marker_and_in_sources_note():
    jsons = [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {
                    "value": "850ms",
                    "sources": [_src("https://broken.example/x", tier="B", title="Broken")],
                },
                "dx": {"value": "mature", "sources": [_src("https://ok.example/x", tier="B", title="OK")]},
            },
            "uncertain": [],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    url_validation = {
        "https://broken.example/x": {"url": "https://broken.example/x", "ok": False, "status_code": 404},
        "https://ok.example/x": {"url": "https://ok.example/x", "ok": True, "status_code": 200},
        "https://v.example": {"url": "https://v.example", "ok": True, "status_code": 200},
        "https://v.example/dx": {"url": "https://v.example/dx", "ok": True, "status_code": 200},
    }
    out = build_report(
        _comparative_outline(), jsons, fields_yaml=_fields_yaml(), url_validation=url_validation
    )
    md = out["report_md"]
    assert BROKEN_URL_MARKER in md
    assert "### Broken URLs" in md
    assert "https://broken.example/x" in md
    assert out["broken_url_count"] == 1


def test_extraction_failure_listed_in_sources_note():
    jsons = [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {
                    "value": "850ms",
                    "sources": [
                        _src("https://failed.example/x", tier="B", title="Failed",
                             extraction_failed=True, methods_attempted=["webfetch", "jina", "exa"],
                             failure_mode="403 anti-bot"),
                    ],
                },
                "dx": {"value": "mature", "sources": [_src("https://ok.example", tier="B")]},
            },
            "uncertain": [],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "### Extraction failures" in md
    assert "https://failed.example/x" in md
    assert "403 anti-bot" in md
    assert "webfetch" in md


def test_disagreements_subsection_with_two_tier_a_conflicting():
    jsons = [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {
                    "value": "around 800ms",
                    "sources": [
                        _src("https://a1.example", tier="A", title="A1", claim="Jest takes 850ms"),
                        _src("https://a2.example", tier="A", title="A2", claim="Jest takes 1200ms"),
                    ],
                },
                "dx": {"value": "mature", "sources": [_src("https://ok.example", tier="B")]},
            },
            "uncertain": [],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "## Disagreements" in md
    assert "Jest takes 850ms" in md
    assert "Jest takes 1200ms" in md
    assert "jest — startup_ms" in md


def test_sources_note_groups_by_tier_and_unclassified():
    jsons = [
        {
            "item": "jest",
            "fields": {
                "startup_ms": {
                    "value": "850ms",
                    "sources": [
                        _src("https://a.example", tier="A", title="A doc"),
                        _src("https://u.example", tier="Unknown", title="Unclassified blog"),
                    ],
                },
                "dx": {"value": "mature", "sources": [_src("https://b.example", tier="B", title="B doc")]},
            },
            "uncertain": [],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://c.example", tier="C", title="C doc")]},
                "dx": {"value": "fast", "sources": [_src("https://b2.example", tier="B", title="B2 doc")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    sources_note = md.split("## Sources note", 1)[1]
    assert "### Tier A" in sources_note
    assert "A doc" in sources_note
    assert "### Tier B" in sources_note
    assert "### Tier C" in sources_note
    assert "### Unclassified domains" in sources_note
    assert "Unclassified blog" in sources_note


def test_pruned_item_shows_no_evidence():
    jsons = [
        {
            "item": "jest",
            "pruned": True,
            "prune_reason": "zero useful results after triple reformulation",
            "fields": {},
            "uncertain": [],
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "## jest" in md
    jest_section = md.split("## jest", 1)[1].split("## vitest", 1)[0]
    assert "No evidence found" in jest_section
    assert "triple reformulation" in jest_section
    rows = list(csv.reader(io.StringIO(out["report_csv"])))
    jest_row = next(r for r in rows if r[0] == "jest")
    assert jest_row[1] == UNCERTAIN_MARKER
    assert jest_row[2] == UNCERTAIN_MARKER


def test_budget_exhausted_annotates_gaps():
    jsons = [
        {
            "item": "jest",
            "budget_exhausted": True,
            "fields": {
                "startup_ms": {"value": "850ms", "sources": [_src("https://j.example", tier="A")]},
                "dx": {"value": UNCERTAIN_MARKER, "sources": []},
            },
            "uncertain": ["dx"],
            "budget_consumed": 25,
        },
        {
            "item": "vitest",
            "fields": {
                "startup_ms": {"value": "120ms", "sources": [_src("https://v.example", tier="A")]},
                "dx": {"value": "fast", "sources": [_src("https://v.example/dx", tier="A")]},
            },
            "uncertain": [],
        },
    ]
    out = build_report(_comparative_outline(), jsons, fields_yaml=_fields_yaml())
    md = out["report_md"]
    assert "## Gaps" in md
    gaps_section = md.split("## Gaps", 1)[1]
    assert "jest: dx" in gaps_section
    assert "[budget exhausted]" in gaps_section


def test_empty_item_jsons_global_no_evidence():
    out = build_report(_comparative_outline(), [], fields_yaml=_fields_yaml())
    assert "No evidence found." in out["report_md"]
    assert out["gap_count"] == 0
    assert out["broken_url_count"] == 0
    rows = list(csv.reader(io.StringIO(out["report_csv"])))
    assert rows[0] == ["item", "startup_ms", "dx"]
    for row in rows[1:]:
        assert all(cell == UNCERTAIN_MARKER for cell in row[1:])


def test_url_validation_none_skips_gracefully():
    out = build_report(_comparative_outline(), _comparative_jsons(), fields_yaml=_fields_yaml(), url_validation=None)
    assert out["broken_url_count"] == 0
    assert BROKEN_URL_MARKER not in out["report_md"]
