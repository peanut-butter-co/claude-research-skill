# research-skill

## Goal

Build a custom Claude skill for research. Starting point: [Weizhena/Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills).

## State

- Landscape research: done — [`RESEARCH.md`](./RESEARCH.md) (categories + top 2).
- Pre-research planning pattern: done — [`patrones/pre-research-planning.md`](./patrones/pre-research-planning.md).
- Tools for defining specs: done — [`patrones/spec-kit-prompts/`](./patrones/spec-kit-prompts/) (full SDD chain: constitution / specify / spec-quality / clarify / plan / tasks / analyze / implement / checklist).
- Specs v1: done — [`SPECS.md`](./SPECS.md) refactored to spec-template format; analyze pass complete; clarify pending.
- Implementation: pending — do not start until agreed.

## Context

- `/last30days` is already installed system-wide and covers social research (Reddit + X + YouTube + TikTok + HN + Polymarket). The new skill must be complementary, not redundant.
- Project language: English. Skill output (commands, prompts, reports), specs, and project meta-docs are all in English. Existing files still in Spanish migrate file-by-file when touched.

## How to work here

- When the current step is research, deliver only research — do not design architecture or propose implementation until explicitly asked.

## Principles

**I. Network-free tests**
All tests MUST run to completion without live network calls (fixture-based).
Why: CI reproducibility; prevents test flakiness from external APIs.

**II. Deterministic scripts**
`scripts/` MUST contain only deterministic logic; judgment and orchestration live in SKILL.md prompts.
Why: separates testable code from LLM-driven behavior.

**III. Never silence**
Broken URLs and uncertain field values MUST appear in output; silent omission is never acceptable.
Why: downstream readers need to know what evidence is missing.

**IV. Incremental persistence**
Every parallel agent MUST write its partial output to disk before returning.
Why: supports resume after interruption (FR-010/FR-033a).

**V. English-first**
All new files and edits MUST be in English. Existing Spanish files migrate on next touch.
Why: skill output (reports, logs) is consumed in English by the LLM layers.

## References

- [SPECS.md](./SPECS.md) — functional requirements (28 FRs + 8 SCs)
- [PLAN.md](./PLAN.md) — architecture and operator quickstart
- [TASKS.md](./TASKS.md) — implementation task list and coverage map
