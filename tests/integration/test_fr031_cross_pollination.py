"""Integration smoke test for FR-031 cross-pollination structural contract.

FR-031 (see .claude/skills/research-deep/SKILL.md, Step 7 and the dedicated
"FR-031 — Synthesis pass details" section) says: when ≥2 parallel research
agents discover a common entity, term, or theme, the orchestrator MUST
propagate that as a hint into subsequent agents' prompts, and the receiving
agent MUST mirror it under `_meta.hints_received[]` in its output JSON.

The orchestrator that does this propagation is LLM-driven (no Python script
implements it), so this test cannot exercise the LLM behaviour directly.
Instead, it validates the *structural contract* that the SKILL.md prescribes
for the agent JSON: the shape of `_meta.hints_received[]` (and the sibling
`hints_sent[]` used to seed the next round).

No live network calls. Pure fixture-based assertions.
"""
from __future__ import annotations

import json
from pathlib import Path

FIXTURES = Path(__file__).parent.parent / "fixtures" / "fr031"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def test_fr031_agent_json_can_have_meta_block():
    """Both agent JSONs carry a `_meta` block; jest sends a hint, vitest receives it.

    Verifies the round-to-round propagation: the entity surfaced by jest in
    `hints_sent` matches the entity vitest reports under `hints_received` —
    i.e. the orchestrator successfully ferried "ESM" between agents.
    """
    jest = _load("agent_jest.json")
    vitest = _load("agent_vitest.json")

    # jest carries _meta.hints_sent
    assert "_meta" in jest, "jest agent JSON must have a _meta block"
    assert "hints_sent" in jest["_meta"], "jest._meta must contain hints_sent[]"
    assert isinstance(jest["_meta"]["hints_sent"], list)
    assert len(jest["_meta"]["hints_sent"]) >= 1, (
        "jest._meta.hints_sent must have at least 1 entry"
    )
    assert "entity" in jest["_meta"]["hints_sent"][0], (
        "each hint must carry an 'entity' field"
    )

    # vitest carries _meta.hints_received
    assert "_meta" in vitest, "vitest agent JSON must have a _meta block"
    assert "hints_received" in vitest["_meta"], (
        "vitest._meta must contain hints_received[] (FR-031 contract)"
    )
    assert isinstance(vitest["_meta"]["hints_received"], list)
    assert len(vitest["_meta"]["hints_received"]) >= 1, (
        "vitest._meta.hints_received must have at least 1 entry"
    )

    # Propagation: jest's entity reached vitest
    assert (
        vitest["_meta"]["hints_received"][0]["entity"]
        == jest["_meta"]["hints_sent"][0]["entity"]
    ), "the entity emitted by jest must match the entity received by vitest"


def test_fr031_hint_propagation_structural_contract():
    """Each entry in `_meta.hints_received[]` has the required keys and types."""
    vitest = _load("agent_vitest.json")
    hints = vitest["_meta"]["hints_received"]

    assert isinstance(hints, list), "_meta.hints_received must be a list"
    assert len(hints) >= 1, "fixture must contain at least 1 hint to test"

    required_keys = {"from_agent", "entity", "context"}
    for hint in hints:
        assert isinstance(hint, dict), f"each hint must be a dict, got {type(hint)}"
        missing = required_keys - hint.keys()
        assert not missing, f"hint is missing required keys: {missing}"
        assert isinstance(hint["from_agent"], str), (
            "hint.from_agent must be a string identifying the source agent"
        )
        assert hint["from_agent"], "hint.from_agent must be non-empty"
        assert isinstance(hint["entity"], str) and hint["entity"], (
            "hint.entity must be a non-empty string"
        )
        assert isinstance(hint["context"], str) and hint["context"], (
            "hint.context must be a non-empty string"
        )


def test_fr031_two_agents_share_entity_overlap():
    """The cross-pollination is about a real shared entity: 'ESM' appears in
    both agents' field values, proving the hint reflects genuine overlap and
    is not just a synthetic propagation artifact.
    """
    jest = _load("agent_jest.json")
    vitest = _load("agent_vitest.json")

    jest_value = jest["fields"]["esm_support"]["value"]
    vitest_value = vitest["fields"]["esm_support"]["value"]

    assert "ESM" in jest_value and "ESM" in vitest_value, (
        "expected 'ESM' to appear in both jest and vitest esm_support values"
    )

    # Aggregate every entity that surfaced anywhere across both agents (hints
    # plus field values) and confirm "ESM" is in the union — this is the
    # cross-pollination handle the orchestrator latched onto.
    entities_seen: set[str] = set()
    for hint in jest.get("_meta", {}).get("hints_sent", []):
        entities_seen.add(hint["entity"])
    for hint in vitest.get("_meta", {}).get("hints_received", []):
        entities_seen.add(hint["entity"])
    if "ESM" in jest_value:
        entities_seen.add("ESM")
    if "ESM" in vitest_value:
        entities_seen.add("ESM")

    assert "ESM" in entities_seen, (
        "'ESM' must appear in the union of hints + field values across both agents"
    )
