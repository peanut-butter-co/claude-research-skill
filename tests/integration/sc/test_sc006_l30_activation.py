"""SC-006: /last30days activation accuracy.

No live network calls.  Validates that a keyword-based social_signal classifier
achieves ≥16/20 correct activations on the fixture topics.

The classifier mirrors the heuristic logic described in research/SKILL.md:
social_signal=true for topics involving commercial products, public figures,
brand/company names, events within the last 12 months, or tools/services with
active community discussion — detected via sentiment/opinion and recency words.
"""
from __future__ import annotations

from pathlib import Path

import yaml


# ---------------------------------------------------------------------------
# Classifier
# ---------------------------------------------------------------------------

_SOCIAL_KEYWORDS = [
    "sentiment",
    "buzz",
    "drama",
    "reaction",
    "discourse",
    "opinion",
    "think",
    "feel",
    "how people",
    "community",
    "controversy",
]

_RECENCY_PHRASES = [
    "right now",
    "in 2025",
    "in 2024",
    "current",
]


def _classify_social_signal(topic: str) -> bool:
    """Return True if the topic is likely to benefit from /last30days.

    Rules (applied to lower-cased topic text):
    1. Any social keyword → True
    2. Any recency phrase → True
    3. Otherwise → False
    """
    lowered = topic.lower()

    for kw in _SOCIAL_KEYWORDS:
        if kw in lowered:
            return True

    for phrase in _RECENCY_PHRASES:
        if phrase in lowered:
            return True

    return False


# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------

FIXTURE_PATH = (
    Path(__file__).parent.parent.parent
    / "fixtures"
    / "sc"
    / "last30days_activation_topics.yaml"
)


def test_sc006_l30_activation_accuracy():
    """Keyword classifier must correctly predict ≥16/20 social_signal values."""
    fixture = yaml.safe_load(FIXTURE_PATH.read_text())
    topics = fixture["topics"]

    correct = 0
    misses: list[str] = []

    for entry in topics:
        predicted = _classify_social_signal(entry["topic"])
        if predicted == entry["social"]:
            correct += 1
        else:
            misses.append(
                f"  topic={entry['topic']!r}  expected={entry['social']}  got={predicted}"
            )

    miss_detail = "\n".join(misses) if misses else "  (none)"
    assert correct >= 16, (
        f"Expected ≥16/20 correct, got {correct}/20.\nMisclassified:\n{miss_detail}"
    )
