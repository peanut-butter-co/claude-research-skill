"""SC-005: mode-detection accuracy integration test.

Loads 10 hand-curated topics from the fixture file, runs detect_mode_fast on
each one, and asserts that at least 9/10 detections are correct.

Correctness rules:
  - expected=comparative  => returned mode == "comparative"
  - expected=narrative    => returned mode != "comparative"  (None or "narrative")

A parametrized test per topic surfaces exactly which topic failed.
"""

from pathlib import Path

import pytest
import yaml

from scripts.mode_detect import detect_mode_fast

REPO_ROOT = Path(__file__).parent.parent.parent.parent
FIXTURE_PATH = REPO_ROOT / "tests" / "fixtures" / "sc" / "mode_detection_topics.yaml"
DATA_DIR = REPO_ROOT / ".claude" / "skills" / "_lib" / "data"


def _load_topics():
    with FIXTURE_PATH.open() as f:
        data = yaml.safe_load(f)
    return [(item["topic"], item["expected_mode"]) for item in data["topics"]]


TOPICS = _load_topics()


def _is_correct(result: dict, expected_mode: str) -> bool:
    detected = result.get("mode")
    if expected_mode == "comparative":
        return detected == "comparative"
    # narrative: any non-comparative result is correct (None = falls through to LLM)
    return detected != "comparative"


# ---------------------------------------------------------------------------
# Parametrized per-topic test — shows exactly which topic failed
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("topic,expected_mode", TOPICS, ids=[t[0][:60] for t in TOPICS])
def test_single_topic_mode_detection(topic: str, expected_mode: str):
    result = detect_mode_fast(topic, data_dir=DATA_DIR)
    assert _is_correct(result, expected_mode), (
        f"Topic: {topic!r}\n"
        f"  expected_mode : {expected_mode}\n"
        f"  detected mode : {result.get('mode')}\n"
        f"  confidence    : {result.get('confidence')}\n"
        f"  matched_pattern: {result.get('matched_pattern')}"
    )


# ---------------------------------------------------------------------------
# Aggregate test — asserts >=9/10 correct (tolerance for one miss)
# ---------------------------------------------------------------------------

def test_mode_accuracy_at_least_9_of_10():
    results = []
    for topic, expected_mode in TOPICS:
        result = detect_mode_fast(topic, data_dir=DATA_DIR)
        correct = _is_correct(result, expected_mode)
        results.append(
            {
                "topic": topic,
                "expected_mode": expected_mode,
                "detected_mode": result.get("mode"),
                "correct": correct,
            }
        )

    correct_count = sum(r["correct"] for r in results)
    failures = [r for r in results if not r["correct"]]

    failure_details = "\n".join(
        f"  [{i+1}] topic={r['topic']!r}  expected={r['expected_mode']}  "
        f"detected={r['detected_mode']}"
        for i, r in enumerate(failures)
    )

    assert correct_count >= 9, (
        f"Mode accuracy {correct_count}/10 is below threshold 9/10.\n"
        f"Failed topics:\n{failure_details}"
    )
