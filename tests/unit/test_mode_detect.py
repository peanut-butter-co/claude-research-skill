import textwrap
from pathlib import Path

import pytest

from scripts.mode_detect import detect_mode_fast


MINIMAL_YAML = textwrap.dedent("""\
    threshold: 0.75
    keywords:
      comparative:
        - "(?i)\\\\bcompare\\\\b"
        - "(?i)\\\\bvs\\\\.?\\\\b"
        - "(?i)\\\\b(?:best|top)\\\\s+\\\\d+\\\\b"
        - "(?i)\\\\balternatives?\\\\s+to\\\\b"
        - "(?i)(?:[\\\\w.+-]+(?:\\\\s*,\\\\s*[\\\\w.+-]+)+\\\\s*(?:,?\\\\s*(?:and|or)\\\\s+[\\\\w.+-]+)?)"
      narrative:
        - "(?i)\\\\bhow\\\\s+does\\\\b"
        - "(?i)\\\\bwhat\\\\s+(?:is|are|was|were)\\\\b"
    classification_prompt: "classify: {topic}"
""")


@pytest.fixture()
def data_dir(tmp_path):
    (tmp_path / "mode-detection.yaml").write_text(MINIMAL_YAML)
    return tmp_path


def test_compare_keyword(data_dir):
    result = detect_mode_fast("compare React and Vue", data_dir=data_dir)
    assert result["mode"] == "comparative"
    assert result["confidence"] == 1.0


def test_vs_keyword(data_dir):
    result = detect_mode_fast("Jest vs Vitest for unit tests", data_dir=data_dir)
    assert result["mode"] == "comparative"
    assert result["confidence"] == 1.0


def test_best_n_pattern(data_dir):
    result = detect_mode_fast("best 5 vector databases for RAG", data_dir=data_dir)
    assert result["mode"] == "comparative"
    assert result["confidence"] == 1.0


def test_alternatives_to(data_dir):
    result = detect_mode_fast("alternatives to Redis for caching", data_dir=data_dir)
    assert result["mode"] == "comparative"
    assert result["confidence"] == 1.0


def test_enumerated_list(data_dir):
    result = detect_mode_fast("jest, vitest, and playwright", data_dir=data_dir)
    assert result["mode"] == "comparative"
    assert result["confidence"] == 1.0


def test_open_ended_how(data_dir):
    result = detect_mode_fast("how does transformer attention work", data_dir=data_dir)
    assert result["mode"] is None


def test_narrative_impact(data_dir):
    result = detect_mode_fast("what is the impact of climate change on agriculture", data_dir=data_dir)
    assert result["mode"] is None


def test_empty_string(data_dir):
    result = detect_mode_fast("", data_dir=data_dir)
    assert result["mode"] is None
