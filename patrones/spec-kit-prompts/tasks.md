# tasks — task list generator (the executable breakdown)

> Adapted from `templates/commands/tasks.md` and `templates/tasks-template.md` of [github/spec-kit](https://github.com/github/spec-kit).

## Critical concept

**TASKS.md is the dependency-ordered, story-grouped breakdown of PLAN into atomic units of work.** It is consumed by implementation (manual or automated). Format strictness matters because `analyze` uses it to detect coverage gaps, and `implement` uses phase grouping for checkpoint gates.

TASKS reads SPECS + PLAN. It does NOT make new product or architecture decisions — both must be locked beforehand. If TASKS surfaces a decision that wasn't made, stop and route back to the right artifact (SPECS for product, PLAN for tech).

## When to invoke

- After SPECS is stable AND PLAN is approved.
- Before implementation starts.
- Re-run when PLAN materially changes (new pattern, new dependency, new component).

NOT for: small task additions (just append to TASKS.md following the existing format).

## Operating constraints

**Required inputs**:
- `PLAN.md` — tech stack, libraries, project structure, architectural patterns. **Required**.
- `SPECS.md` — user stories with priorities, FRs, SCs, edge cases, key entities. **Required**.
- Constitution / project rules (`CLAUDE.md`).

**Optional inputs** (use if present):
- `research.md` — informs Setup tasks.
- `data-model.md` (or §Data Model in PLAN) — informs Foundational tasks.
- `contracts/` — informs per-story tasks.
- `quickstart.md` — informs final verification tasks.

If PLAN is missing → **stop**, instruct user to run `plan` first.

## Procedure

### 1. Load inputs

Full read of PLAN, SPECS, project rules. Build mental models:
- **FR inventory** keyed by ID.
- **User Story inventory** keyed by USx with priority.
- **SC inventory** filtered to buildable (exclude post-launch outcome metrics).
- **Architectural pattern decisions** from PLAN.
- **Data Model entities** (storage / fields / lifecycle).
- **Project Structure** tree (target file paths).

### 2. Phase grouping (strict order)

Tasks are organized into these phases. Implementation runs phase-by-phase; phase N+1 cannot start until phase N is complete (see Checkpoints below).

**Phase 1 — Setup**: scaffolding, repo skeleton, dependency installation, seed data files, env config templates, linter / formatter / CI bootstrap. Anything that must exist before any logic is written. Tasks here usually `[P]`-parallel since they touch disjoint files.

**Phase 2 — Foundational**: cross-cutting capabilities that every User Story depends on. For our project: source scoring engine, URL validator, fallback chain, persistence layer, lockfile mechanism, slug derivation, etc. **Phase 2 is a hard gate** — no story phase can start while Foundational is incomplete.

**Phase 3+ — Per User Story**: one phase per User Story, ordered by priority (US1 first since it's MVP). Each phase contains all tasks needed to make that story functional end-to-end (per its Independent Test in SPECS). Tagged `[USx]`. **Each story phase is independently testable** — completing Phase 3 alone should produce a working US1 even if US2/3/4 are not yet done.

**Phase N (last) — Polish**: final docs (CLAUDE.md, SKILL.md per command), the SC-### verification scenarios, hardening (error messages, edge case smoke tests), perf checks if applicable.

### 3. Task derivation rules

For each phase, generate tasks by walking the inputs:

**From PLAN's Project Structure tree**: every directory and key file gets a creation task in Setup. Skip runtime-populated directories (`learnings/`, `tasks/`).

**From PLAN's Data Model + research decisions**: each entity / decision yields one or more tasks in Foundational.

**From SPECS' FRs**: each FR maps to ≥1 task. Multiple FRs may collapse into one task if they're tightly coupled (e.g. FR-013/014/015 → one "scoring engine" task). Track FR coverage so analyze can verify nothing is dropped.

**From SPECS' User Stories**: each User Story drives a per-story phase. Within the phase, derive tasks from the story's Acceptance Scenarios (each scenario step = a task or sub-task) and from the FRs the story exercises.

**From SPECS' Edge Cases**: edge case handling becomes Polish-phase tasks unless the case is foundational (e.g. lockfile concurrency = Foundational).

**From buildable SCs**: each SC that requires a verification scenario gets a Polish task.

### 4. Format (strict)

Each task is one line:

```
- [ ] T### [P?] [USx?] <description that includes the file path(s) it touches>
```

Where:
- `T###` — sequential task ID, stable, never renumber.
- `[ ]` / `[X]` — status checkbox.
- `[P]` — present iff the task touches files disjoint from other unblocked tasks (parallel-safe).
- `[USx]` — present iff the task belongs to a user story phase (US1 / US2 / etc.).
- Description must include the **file path** the task touches. Without paths, `analyze` cannot verify coverage.

Examples:

```
- [ ] T001 [P] Initialize repo skeleton with .claude/skills/, data/, scripts/, tests/ — touches: directory structure
- [ ] T012 Source scoring engine implementing FR-013/014/015 — touches: scripts/score_source.py
- [ ] T020 [P] [US1] /research command planning phase (FR-001/002/002a/004/006) — touches: .claude/skills/research/SKILL.md
- [ ] T091 SC-001 wall-clock verification for 5-item comparative — touches: tests/integration/sc001_walltime.py
```

### 5. Anti-patterns in task descriptions

❌ Wrong:
- `- [ ] T020 Implement /research` (no FR ref, no path)
- `- [ ] T012 [P] Write the scoring code and the validator and the fallback chain` (multiple components in one task — split)
- `- [ ] T030 [P] Write tests` (vague, no path)
- `- [ ] T040 Make sure FR-014 works` (testing-the-impl phrasing — see checklist.md anti-patterns)

✅ Right:
- `- [ ] T020 [P] [US1] /research command — planning phase implementation (FR-001 through FR-006) — touches: .claude/skills/research/SKILL.md`
- `- [ ] T012 Source scoring engine (FR-013/014/015) — touches: scripts/score_source.py`
- `- [ ] T013 Unit tests for scoring engine tier weights — touches: tests/unit/test_score_source.py`

### 6. Dependencies & parallel marker

After listing tasks, add a **Dependencies** section that names the blocking relationships:

```
## Dependencies
- T012 (scoring engine) blocks T020, T021, T022 (per-story phases use it).
- T011 (URL validator) blocks T091 (SC-003 verification).
- All Phase 2 (Foundational) blocks all Phase 3+ (User Stories).
```

A task is `[P]`-parallel iff no other unblocked task touches the same file(s). Two tasks both touching `scripts/score_source.py` cannot both be `[P]`.

### 7. Checkpoints

Insert **checkpoint markers** at phase boundaries:

```
## Checkpoint: end of Phase 2 (Foundational)
Gate: all T010..T019 are [X]. No US-tagged task may start until this passes.
```

```
## Checkpoint: end of Phase 3 (US1 — MVP)
Gate: all T020..T039 are [X]. Independent Test from SPECS §US1 passes end-to-end.
This is the MVP shippable point — Phases 4+ are additive value.
```

### 8. MVP Strategy section

After the task list, add a brief paragraph clarifying:

```
## MVP Strategy
The minimum shippable surface is: Phase 1 + Phase 2 + Phase 3 (US1 only). At that checkpoint, the Independent Test for US1 passes; the skill performs comparative research end-to-end. Phases 4-6 (US2/US3/US4) are sequenced by priority and independently shippable on top of the MVP.
```

### 9. Coverage self-check (before output)

Before writing TASKS.md, verify:
- Every FR-### appears in at least one task description.
- Every User Story has its own phase tagged `[USx]`.
- Every buildable SC has a Polish-phase verification task.
- Every Key Entity has a Foundational-phase creation/management task.
- No task references a file outside the PLAN's Project Structure.
- All task IDs sequential and unique. Phase-aligned numbering gaps (e.g. T041–T049 reserved between phases) are permitted to aid scannability and future expansion; track them explicitly rather than letting them accumulate ad-hoc.

If any check fails: stop, surface the gap, do not write the file.

### 10. Output

Write `TASKS.md` to project root:

```markdown
# Tasks: <feature>

**Created**: YYYY-MM-DD
**Plan**: PLAN.md
**Status**: Draft

## Phase 1: Setup
- [ ] T001 ...
...

## Phase 2: Foundational
- [ ] T010 ...
...

## Checkpoint: end of Phase 2
...

## Phase 3: User Story 1 — <title> [US1] (MVP)
- [ ] T020 [P] [US1] ...
...

## Checkpoint: end of Phase 3
...

## Phase 4: User Story 2 — <title> [US2]
...

## Phase N: Polish
...

## Dependencies
...

## MVP Strategy
...

## Coverage Map (informative)

| FR | Tasks |
|----|-------|
| FR-001 | T020 |
| FR-002 | T020 |
| ... | ... |
```

The Coverage Map is informative — it makes `analyze` cross-checking trivial.

## Operating principles

### Strict format = downstream tooling
The `T###`, `[P]`, `[USx]` markers and explicit file paths aren't aesthetic — they're load-bearing for `analyze` (coverage) and `implement` (phase gating).

### Independence > completeness
A user story phase is "done" when it's independently testable, even if other stories are not yet built. Don't merge stories to "save tasks" — that breaks the MVP discipline.

### Tasks read PLAN, not SPECS
Yes, tasks reference SPECS for stories and FRs, but architectural and tech decisions are pulled from PLAN. If a task needs a decision PLAN doesn't have, **stop** — go back to PLAN.

### Determinism
Same PLAN + same SPECS → same TASKS (modulo task IDs which are stable once assigned). If re-runs produce different tasks, capture why.

### One task = one diff
A reasonable task is something one person/agent can implement in a sitting and review as a single PR. If a task description spans 3 files and 2 components, split it.

## Reporting

After producing TASKS.md:
- Path.
- Phase counts.
- Total task count.
- `[P]` count and percentage.
- Coverage Map size.
- Any FR / Story / SC missing coverage (should be zero — abort if not).
- Suggested next step: `analyze` cross-checking SPECS ↔ PLAN ↔ TASKS, then implementation.
