# plan — technical implementation plan generator

> Adapted from `templates/commands/plan.md` and `templates/plan-template.md` of [github/spec-kit](https://github.com/github/spec-kit). The artifact this produces (`PLAN.md`) is the load-bearing bridge between SPECS (the WHAT) and TASKS (the executable HOW).

## Critical concept

**`plan` is not optional.** Skipping it forces TASKS to invent stack/architecture decisions per task, producing inconsistency. SPECS describes WHAT and WHY; PLAN describes HOW at the architectural level (libraries, code layout, patterns, gates). TASKS is the breakdown of PLAN into atomic units of work.

`plan` is **READ-ONLY against SPECS**. If `plan` finds the spec is ambiguous on something it needs (e.g. scale assumptions for picking storage), it stops and points the user back to `clarify`, not to spec-edit on the fly.

## When to invoke

- After SPECS is stable (clarify done, no `[NEEDS CLARIFICATION]` markers, all CRITICAL/HIGH analyze findings resolved).
- Before TASKS.md exists.
- Re-run when SPECS materially changes (new FRs, new external dependencies, scope shift).

NOT for: small spec edits that don't touch architecture; incremental task addition mid-implementation.

## Operating constraints

**STRICTLY tech-focused, no product decisions**. PLAN must not introduce or modify FRs, SCs, or User Stories. If you find yourself wanting to, that's a signal SPECS needs another pass.

**No code in PLAN**. PLAN describes structure and choices. Code samples or detailed algorithms belong in `implementation-details/` files (or in the implementation phase). Per spec-kit: *"Plan template should remain high-level and readable. Any code samples, detailed algorithms, or extensive technical specifications must be placed in the appropriate `implementation-details/` file."*

**Constitution gate, run twice**. CLAUDE.md (or whatever stands as project principles) is the constitution-lite. Before producing PLAN content (Phase 0) AND after design decisions are made (post-Phase 1), check that nothing violates it. ERROR on violations unless explicitly justified in `## Complexity Tracking`.

## Procedure

### 1. Load context (read-only)

- SPECS.md — full read.
- CLAUDE.md / project-rules — full read.
- patrones/*.md — read what's referenced by SPECS.
- Existing learnings/ if any architectural decisions were captured there.

If SPECS has unresolved `[NEEDS CLARIFICATION]` or open analyze CRITICAL/HIGH: **stop**, instruct user to run `clarify`/`analyze` first.

### 2. Phase 0 — Outline & Research (resolve unknowns)

Goal: enter Phase 1 with zero `NEEDS CLARIFICATION` in tech context.

For each technical unknown that PLAN must decide (storage format, library choice, integration pattern, performance budget), produce a **decision record** in `research.md` (or appended PLAN section) with:

```
- Decision: <what was chosen>
- Rationale: <why this fits SPECS + constraints>
- Alternatives considered: <2-3 alternatives, why rejected>
```

If a decision requires user input (e.g. "do we want pytest or unittest"), ask via AskUserQuestion. Do not invent answers silently.

**Constitution check (gate 1)**: review CLAUDE.md / project rules. If any decision under consideration would violate a MUST principle, mark it CRITICAL — must be resolved before proceeding (either revise the decision or add a justified exception in `## Complexity Tracking`).

### 3. Phase 1 — Design & Contracts

Produce the following sections in `PLAN.md`:

#### Summary
1-3 sentences. Goal: what is being implemented and the headline tech approach.

#### Technical Context
A bullet list with these fields. Mark `NEEDS CLARIFICATION` if unresolved (must not exit Phase 0 with these):
- **Language / Version** (e.g. Python 3.10+)
- **Primary Dependencies** (libraries, frameworks, services)
- **Storage** (file-based / DB / format)
- **Testing** (framework, coverage target)
- **Target Platform** (CLI / web / desktop / Claude skill / etc.)
- **Project Type** (library / app / skill / plugin)
- **Performance Goals** (concrete numbers; cite SC-### if applicable)
- **Constraints** (offline, single-user, network, OS)
- **Scale / Scope** (rough volumes — N items, N sources per item, etc.)

#### Constitution / Project-Rules Check (gate)
List each MUST principle from CLAUDE.md / project rules. For each: ✅ aligned / ⚠ partial / ❌ violated. ❌ rows go to `## Complexity Tracking` with justification.

#### Project Structure
Directory tree of expected layout. **Pick one tree, no "Option A vs B"**. Annotate folders with their purpose.

```
research-skill/
├── .claude/skills/<name>/SKILL.md
├── data/
│   ├── source-tiers.yaml
│   ├── ...
├── scripts/
│   ├── score_source.py
│   ├── ...
├── tests/
│   ├── unit/
│   ├── integration/
├── learnings/        # runtime
├── tasks/            # runtime
└── ...
```

#### Architectural Patterns
The cross-cutting choices that bind multiple components:
- Where lives logic — in SKILL.md prompts vs in `scripts/`?
- Error handling style (exceptions / Result / status flags).
- Logging / observability format (structured / plain text / JSON events).
- How orchestrator coordinates with parallel agents (env vars / files / prompt-only / etc.).
- External-service abstraction (per-service adapters or a unified wrapper).
- Data validation (schema library / hand-rolled / pydantic / etc.).

Each pattern: 1-3 sentences + rationale + 1-line on alternative rejected.

#### Data Model
For each Key Entity in SPECS, give:
- Storage format (YAML / JSON / Markdown).
- File path or directory pattern.
- Schema fields (concrete types).
- Validation rules.
- Lifecycle (created by / read by / updated by / deleted by).

If SPECS' Key Entities already cover this fully, write "see SPECS §Key Entities; no additions needed".

#### Contracts (only if external interfaces exist)
For each external API the project consumes or exposes: contract spec (request / response / errors / auth). Skip if purely internal.

#### Quickstart
1-page "how to run from a clean clone": setup commands, env vars, smoke test. This bridges PLAN to first implementation task.

#### Complexity Tracking
Table populated only if Constitution gate violations exist:

| Violated principle | Why needed | Simpler alternative rejected (and why) |
|---|---|---|

Empty section is fine — means the gate cleanly passed.

### 4. Constitution check (gate 2 — post-design)

Re-run the gate against the now-concrete Architectural Patterns + Data Model + Project Structure. Any new violations? Either revise or add to Complexity Tracking with justification. Stop if unresolvable.

### 5. Output

Write `PLAN.md` to project root (or a designated path). Format:

```markdown
# Implementation Plan: <feature>

**Created**: YYYY-MM-DD
**Spec**: SPECS.md (commit / version)
**Status**: Draft | Approved

## Summary
...

## Technical Context
...

## Constitution / Project-Rules Check
...

## Project Structure
...

## Architectural Patterns
...

## Data Model
...

## Contracts
...

## Quickstart
...

## Complexity Tracking
...

## Research Decisions
(append from Phase 0; format Decision/Rationale/Alternatives)
```

### 6. Stop. Do NOT generate tasks.

`plan` ends here. Tasks are produced by the `tasks` procedure ([`tasks.md`](./tasks.md)) using PLAN as input.

## Operating principles

### Read SPECS, write PLAN — never modify SPECS during plan
If SPECS is ambiguous → stop, point to `clarify`. If SPECS is wrong → stop, point to `analyze`. The plan procedure does not patch the spec.

### One tree, one stack, one pattern per concern
PLAN forces decisions. "We could use X or Y" is not a plan — it's deferred work. If a decision genuinely depends on TBD info, mark it `NEEDS CLARIFICATION` and resolve in Phase 0 before proceeding.

### Cite SPECS at every decision
Every Technical Context entry, every Architectural Pattern, every Data Model field should be traceable to a FR-### / SC-### / Edge Case it serves. Untraceable decisions are speculative scope.

### Constitution gate is non-negotiable
A MUST violation either becomes a justified exception in `## Complexity Tracking` or the decision is revised. Silent violation is forbidden.

### Determinism
Same SPECS + same project rules → same PLAN. If a re-run produces a different plan, the difference is either a new decision (must be flagged) or noise (must be resolved).

## Anti-patterns

- **Putting code in PLAN** → belongs in implementation-details or in actual implementation.
- **Skipping the gate to "save time"** → analyze finds the violation later anyway, costs more.
- **Multiple options unresolved** → "we'll decide during implementation" defeats the purpose; resolve now.
- **Re-litigating SPECS in PLAN** → if you want to change WHAT, run `analyze` + `clarify` first.
- **Auto-generating TASKS from PLAN in the same session** → TASKS is its own pass with its own gates; keep them separate.

## Reporting

After producing PLAN:
- Path to `PLAN.md`.
- Section count + size.
- Constitution gate status (passed / passed with N exceptions in Complexity Tracking).
- Any `NEEDS CLARIFICATION` that emerged (should be 0 if Phase 0 was complete).
- Suggested next step: typically `tasks` ([`tasks.md`](./tasks.md)) or another `analyze` round if PLAN raised cross-artifact concerns.
