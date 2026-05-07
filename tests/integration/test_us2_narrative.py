"""Integration tests for US2: narrative research (essay-style with subqueries).

Exercises the Python helper scripts end-to-end using canned fixtures.
Does NOT call SKILL.md or invoke Claude Code.
Does NOT make network calls (all fixture URLs are fake/example domains).

Fixture files consumed:
  tests/fixtures/outlines/eu_ai_act.yaml
  tests/fixtures/item_jsons/us2_scope_of_obligations.json
  tests/fixtures/item_jsons/us2_compliance_costs.json
  tests/fixtures/item_jsons/us2_sme_exemptions.json

These files are written by task T064.  Tests that load them will skip with a
clear message if T064 has not yet run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from scripts.build_report import build_report
from scripts.lockfile import acquire, release
from scripts.slug import make_slug

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

FIXTURES = Path(__file__).parent.parent / "fixtures"
REPO_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = REPO_ROOT / ".claude" / "skills" / "_lib" / "data"

_US2_ITEM_FILES = [
    "us2_scope_of_obligations.json",
    "us2_compliance_costs.json",
    "us2_sme_exemptions.json",
]

VALID_TIERS = {"A", "B", "C", "D", "Unknown"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _require_fixture(path: Path) -> None:
    """Skip the test with a descriptive message when *path* does not exist."""
    if not path.exists():
        pytest.skip(f"Fixture not yet created by T064: {path}")


def _load_outline() -> dict:
    path = FIXTURES / "outlines" / "eu_ai_act.yaml"
    _require_fixture(path)
    return yaml.safe_load(path.read_text())


def _load_item_jsons() -> list[dict]:
    jsons: list[dict] = []
    for fname in _US2_ITEM_FILES:
        path = FIXTURES / "item_jsons" / fname
        _require_fixture(path)
        jsons.append(json.loads(path.read_text()))
    return jsons


def _build_narrative_report(
    outline: dict | None = None,
    item_jsons: list[dict] | None = None,
    url_validation: dict | None = None,
) -> dict:
    if outline is None:
        outline = _load_outline()
    if item_jsons is None:
        item_jsons = _load_item_jsons()
    return build_report(outline, item_jsons, fields_yaml=None, url_validation=url_validation)


# ---------------------------------------------------------------------------
# Scenario 1: Planning artifacts — outline shape
# ---------------------------------------------------------------------------


def test_narrative_outline_shape():
    """eu_ai_act.yaml has mode=narrative, subqueries list of 3-5 items."""
    outline = _load_outline()
    assert outline.get("mode") == "narrative", (
        f"Expected mode='narrative', got {outline.get('mode')!r}"
    )
    subqueries = outline.get("subqueries")
    assert isinstance(subqueries, list), "outline.subqueries must be a list"
    assert 3 <= len(subqueries) <= 5, (
        f"Expected 3-5 subqueries, got {len(subqueries)}: {subqueries!r}"
    )


def test_narrative_outline_has_no_fields_file():
    """Narrative outline must NOT contain a fields_file key (narrative uses no fields.yaml)."""
    outline = _load_outline()
    assert "fields_file" not in outline, (
        "Narrative outline must not have a 'fields_file' key; "
        f"found: {outline.get('fields_file')!r}"
    )


def test_narrative_outline_has_no_items_key():
    """Narrative outline must NOT contain an items key (that's comparative mode)."""
    outline = _load_outline()
    assert "items" not in outline, (
        "Narrative outline must not have an 'items' key; "
        f"found: {outline.get('items')!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 1b: Slug generation
# ---------------------------------------------------------------------------


def test_narrative_slug_from_topic():
    """make_slug on a narrative topic string yields a reasonable slug."""
    topic = "Impact of EU AI Act on businesses"
    slug = make_slug(topic)
    assert len(slug) <= 60, f"Slug too long ({len(slug)} chars): {slug!r}"
    assert slug == slug.lower(), f"Slug must be lowercase: {slug!r}"
    assert " " not in slug, f"Slug must not contain spaces: {slug!r}"
    # Substantive words should survive (stop-word list drops "of", "on" etc.)
    assert "eu" in slug or "ai" in slug or "act" in slug or "impact" in slug, (
        f"Expected at least one content word in slug, got: {slug!r}"
    )


# ---------------------------------------------------------------------------
# Scenario 2: Agent JSONs — subquery key, summary field, tiered sources
# ---------------------------------------------------------------------------


def test_narrative_agent_jsons_use_subquery_key():
    """Each us2_*.json has a 'subquery' key (not 'item')."""
    item_jsons = _load_item_jsons()
    for data in item_jsons:
        assert "subquery" in data, (
            f"Expected 'subquery' key in JSON, found keys: {list(data.keys())}"
        )
        assert "item" not in data, (
            f"Narrative JSON must use 'subquery', not 'item'; "
            f"subquery={data.get('subquery')!r}"
        )


def test_narrative_agent_jsons_have_summary_field():
    """Each us2_*.json has fields['summary']['value'] that is non-empty."""
    item_jsons = _load_item_jsons()
    for data in item_jsons:
        subquery = data.get("subquery", "(unknown)")
        fields = data.get("fields", {})
        assert "summary" in fields, (
            f"subquery={subquery!r}: expected 'summary' field, got fields: {list(fields.keys())}"
        )
        summary = fields["summary"]
        assert isinstance(summary, dict), (
            f"subquery={subquery!r}: fields['summary'] must be a dict, got {type(summary)}"
        )
        value = summary.get("value")
        assert value and str(value).strip(), (
            f"subquery={subquery!r}: fields['summary']['value'] must be non-empty, got {value!r}"
        )


def test_narrative_agent_jsons_have_tiered_sources():
    """Each us2_*.json has sources with valid tier labels (A/B/C/D/Unknown)."""
    item_jsons = _load_item_jsons()
    for data in item_jsons:
        subquery = data.get("subquery", "(unknown)")
        all_sources: list[dict] = []
        for fdata in data.get("fields", {}).values():
            if isinstance(fdata, dict):
                all_sources.extend(fdata.get("sources") or [])
        assert len(all_sources) > 0, (
            f"subquery={subquery!r}: must have at least one source"
        )
        for src in all_sources:
            tier = src.get("tier")
            assert tier in VALID_TIERS, (
                f"subquery={subquery!r}: source has invalid tier {tier!r}; "
                f"url={src.get('url')!r}"
            )


# ---------------------------------------------------------------------------
# Scenario 3: build_report — narrative structure
# ---------------------------------------------------------------------------


def test_report_narrative_structure():
    """build_report produces ## <subquery> sections, ## Cross-cutting findings, ## Sources note."""
    outline = _load_outline()
    item_jsons = _load_item_jsons()
    result = _build_narrative_report(outline=outline, item_jsons=item_jsons)
    md = result["report_md"]

    assert "## Cross-cutting findings" in md, "Missing ## Cross-cutting findings section"
    assert "## Sources note" in md, "Missing ## Sources note section"

    # Every subquery from the outline must have its own ## section
    for sub in outline["subqueries"]:
        assert f"## {sub}" in md, f"Missing section for subquery {sub!r}"


def test_report_narrative_per_subquery_sections():
    """Each subquery in the outline has its own ## heading in the report."""
    outline = _load_outline()
    item_jsons = _load_item_jsons()
    result = _build_narrative_report(outline=outline, item_jsons=item_jsons)
    md = result["report_md"]

    h2_headings = re.findall(r"^## (.+)$", md, re.MULTILINE)
    for sub in outline["subqueries"]:
        assert sub in h2_headings, (
            f"Subquery {sub!r} not found as a ## heading; "
            f"found headings: {h2_headings!r}"
        )


def test_report_narrative_no_csv():
    """report_csv is empty string for narrative mode."""
    result = _build_narrative_report()
    assert result["report_csv"] == "", (
        f"Expected report_csv='' for narrative mode, got: {result['report_csv']!r}"
    )


def test_report_narrative_inline_citation_format():
    """Report contains at least one '[Title • Tier X](url)' inline citation."""
    result = _build_narrative_report()
    citation_pattern = re.compile(r"\[.+ • Tier [ABCD]\]\(https?://")
    assert citation_pattern.search(result["report_md"]) is not None, (
        "No inline citation matching '[Title • Tier X](https://…)' found in report"
    )


def test_report_narrative_cross_cutting_from_proposed_extensions():
    """proposed_extensions with type=subquery appear in ## Cross-cutting findings."""
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
                    "sources": [
                        {
                            "url": "https://eur-lex.europa.eu/x",
                            "tier": "A",
                            "title": "EUR-Lex",
                            "date": "2024-03-01",
                        }
                    ],
                }
            },
            "uncertain": [],
            "proposed_extensions": [
                {"type": "subquery", "description": "SME exemptions and thresholds"}
            ],
        },
        {
            "subquery": "compliance costs",
            "fields": {
                "summary": {
                    "value": "estimated 5-10% of annual revenue",
                    "sources": [
                        {
                            "url": "https://example-think-tank.org/ai-costs",
                            "tier": "B",
                            "title": "Think tank analysis",
                            "date": "2024-06-15",
                        }
                    ],
                }
            },
            "uncertain": [],
        },
    ]
    result = build_report(outline, jsons, fields_yaml=None, url_validation=None)
    md = result["report_md"]

    assert "## Cross-cutting findings" in md
    cross_section = md.split("## Cross-cutting findings", 1)[1]
    assert "SME exemptions and thresholds" in cross_section, (
        "proposed_extensions description must appear in ## Cross-cutting findings"
    )


# ---------------------------------------------------------------------------
# Scenario 4: Lockfile works with narrative case
# ---------------------------------------------------------------------------


def test_narrative_lockfile_works_with_narrative_case(tmp_path):
    """acquire/release lockfile on a narrative research case directory."""
    case_dir = tmp_path / "tasks" / "impact-eu-ai-act"
    case_dir.mkdir(parents=True)

    acquire(case_dir)
    assert (case_dir / ".lock").exists(), "acquire() must write a .lock file"

    release(case_dir)
    assert not (case_dir / ".lock").exists(), "release() must remove the .lock file"
