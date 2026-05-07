"""SC-004: Resume-after-interruption test.

No live network calls. Validates two properties of the resumable-session design:

1. After an interrupted session (acquire + partial writes + release), the lock
   is gone so a re-invocation can proceed, and the already-written output files
   are preserved.

2. The set of completed items is correctly computable from the output directory,
   so the orchestrator can skip them on re-invocation.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.lockfile import acquire, release


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def get_completed_items(output_dir: Path) -> set[str]:
    completed = set()
    for f in output_dir.glob("*.json"):
        data = json.loads(f.read_text())
        if "item" in data:
            completed.add(data["item"])
    return completed


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_sc004_lockfile_released_after_interruption(tmp_path):
    """Interrupted session: lock is released, partial outputs are preserved.

    Simulates a session that acquired the lock, wrote 2 of 5 output JSONs,
    then called release() (e.g. via a finally block or signal handler).
    A re-invocation must be able to acquire the lock again, and must find
    the partial outputs intact.
    """
    case_dir = tmp_path / "tasks" / "my_case"
    output_dir = case_dir / "output"
    output_dir.mkdir(parents=True)

    # --- Phase 1: simulated interrupted session ---
    acquire(case_dir)

    # Write 2 of 5 output files (the "completed" agents)
    all_items = ["jest", "vitest", "playwright", "mocha", "jasmine"]
    completed_items = all_items[:2]
    for item in completed_items:
        (output_dir / f"{item}.json").write_text(json.dumps({"item": item}))

    # Simulate cleanup on interruption
    release(case_dir)

    # --- Assertions ---
    # Lock must be gone so a re-invocation can acquire it
    lock_file = case_dir / ".lock"
    assert not lock_file.exists(), "Lock file must be absent after release"

    # Partial outputs must still exist (not cleaned up by release)
    written = list(output_dir.glob("*.json"))
    assert len(written) == 2, (
        f"Expected 2 output files to survive lock release, got {len(written)}"
    )


def test_sc004_completed_items_detectable(tmp_path):
    """Orchestrator can compute the remaining items from the output directory.

    Simulates an output directory with 3 of 5 items already written.
    Verifies that the set difference yields exactly the 2 remaining items,
    which is what the orchestrator uses to build the next dispatch batch.
    """
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    all_items = {"jest", "vitest", "playwright", "mocha", "jasmine"}
    already_done = ["jest", "vitest", "playwright"]

    for item in already_done:
        (output_dir / f"{item}.json").write_text(json.dumps({"item": item}))

    completed = get_completed_items(output_dir)
    remaining = all_items - completed

    assert remaining == {"mocha", "jasmine"}, (
        f"Expected remaining={{'mocha', 'jasmine'}}, got {remaining}"
    )
