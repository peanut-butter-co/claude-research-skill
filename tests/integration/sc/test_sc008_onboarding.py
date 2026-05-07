"""SC-008: First-time user onboarding smoke test.

Verifies that a first-time operator who has only CLAUDE.md and SPECS.md can
follow the Quickstart steps to run a successful comparative research. Tests
that the scaffolding is in place — not that Claude executes anything live.

Checks:
  1. All required script modules are importable without ImportError.
  2. The data directory contains the required YAML configuration files.
  3. The .claude/skills directory has all four expected skill files.
  4. make_slug() works on the canonical Quickstart example query.
"""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).parent.parent.parent.parent
DATA_DIR = REPO_ROOT / ".claude" / "skills" / "_lib" / "data"
SKILLS_DIR = REPO_ROOT / ".claude" / "skills"

# ---------------------------------------------------------------------------
# 1. All script modules importable
# ---------------------------------------------------------------------------

SCRIPT_MODULES = [
    "scripts.build_report",
    "scripts.lockfile",
    "scripts.score_source",
    "scripts.slug",
    "scripts.mode_detect",
    "scripts.validate_urls",
    "scripts.learnings_write",
    "scripts.learnings_index",
    "scripts.preferences",
    "scripts.status",
]


@pytest.mark.parametrize("module_name", SCRIPT_MODULES)
def test_sc008_all_scripts_importable(module_name: str):
    """Each script module must be importable with no ImportError."""
    try:
        importlib.import_module(module_name)
    except ImportError as exc:
        pytest.fail(f"ImportError when importing {module_name!r}: {exc}")


# ---------------------------------------------------------------------------
# 2. Data directory has required YAML files
# ---------------------------------------------------------------------------

REQUIRED_DATA_FILES = [
    "mode-detection.yaml",
    "source-tiers.yaml",
    "publisher-graph.yaml",
]


def test_sc008_data_directory_has_required_files():
    """Required YAML files must be present in the data/ directory."""
    if not DATA_DIR.is_dir():
        pytest.skip(f"data/ directory not found at {DATA_DIR} — skipping onboarding data check")

    actual_files = {p.name for p in DATA_DIR.iterdir() if p.is_file()}

    missing = [f for f in REQUIRED_DATA_FILES if f not in actual_files]

    assert not missing, (
        f"Missing required data files: {missing}\n"
        f"Files actually present in data/: {sorted(actual_files)}"
    )


# ---------------------------------------------------------------------------
# 3. Skills directory has all four skill files
# ---------------------------------------------------------------------------

REQUIRED_SKILLS = [
    "research",
    "research-deep",
    "research-report",
    "research-consolidate",
]


@pytest.mark.parametrize("skill_name", REQUIRED_SKILLS)
def test_sc008_skills_directory_has_all_four_skills(skill_name: str):
    """Each expected skill must have a SKILL.md file under .claude/skills/."""
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    assert skill_path.exists(), (
        f"Missing skill file: {skill_path}\n"
        f"Expected .claude/skills/{skill_name}/SKILL.md to exist"
    )


# ---------------------------------------------------------------------------
# 4. make_slug works on the canonical Quickstart example query
# ---------------------------------------------------------------------------

def test_sc008_make_slug_works_on_example_query():
    """make_slug must return a non-empty lowercase slug for the Quickstart example."""
    from scripts.slug import make_slug

    query = "compare jest vitest playwright speed dx"
    result = make_slug(query)

    assert result, f"make_slug returned an empty string for query: {query!r}"
    assert result == result.lower(), (
        f"make_slug result is not lowercase: {result!r}"
    )
    assert " " not in result, (
        f"make_slug result contains spaces: {result!r}"
    )
