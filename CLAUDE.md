# research-skill

Four Claude Code skills for structured web research: `/research`, `/research-deep`, `/research-report`, `/research-consolidate`.

## Context

- `/last30days` is installed system-wide and covers social signals (Reddit, X, YouTube, HN, Polymarket). This skill is complementary — invoke it when `social_signal: true`, never duplicate its sources.
- All output (reports, logs, learnings) is in English.

## Principles

**I. Network-free tests** — All tests MUST run without live network calls. Why: CI reproducibility.

**II. Deterministic scripts** — `scripts/` MUST contain only deterministic logic; judgment lives in SKILL.md. Why: separates testable code from LLM behavior.

**III. Never silence** — Broken URLs and uncertain fields MUST appear in output. Why: readers need to know what evidence is missing.

**IV. Incremental persistence** — Every parallel agent MUST write partial output to disk before returning. Why: resume after interruption (FR-010/FR-033a).

**V. English-first** — All new files and edits MUST be in English. Why: skill output is consumed in English by the LLM layers.

## References

- [docs/SPECS.md](./docs/SPECS.md) — functional requirements (28 FRs + 8 SCs)
- [docs/PLAN.md](./docs/PLAN.md) — architecture, directory structure, quickstart
- [docs/TASKS.md](./docs/TASKS.md) — implementation task list and FR coverage map
