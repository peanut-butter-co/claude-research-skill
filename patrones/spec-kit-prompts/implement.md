# implement — gate-on-checklists pre-flight pattern

> Adapted from `templates/commands/implement.md` of [github/spec-kit](https://github.com/github/spec-kit). We don't auto-execute tasks here; this prompt captures the **pre-flight gate pattern** worth keeping even when implementation is manual.

## Concept

Before any task in TASKS.md is executed (manually or by an agent), run a pre-flight check that:
1. **Scans `checklists/`** for pending items relevant to the upcoming task's scope.
2. **Halts implementation** if any blocking checklist is incomplete.
3. **Reports** what's complete vs incomplete so the operator can decide.

This is not about gating every commit — it's about gating the start of a phase or a critical task. Used as a sanity check before crossing checkpoints (Phase 2 → Phase 3, Phase 3 → Phase 4, etc.).

## When to invoke

- Before starting a new phase (Setup → Foundational → US1 → US2 → ...).
- Before crossing a Checkpoint defined in TASKS.md.
- Optionally: before any critical task that touches multiple components.

NOT for: every single task; documentation tasks; trivial commits.

## Operating constraints

**Read-only pre-flight.** This procedure does not implement anything; it checks state and reports.

**Halt on incomplete blocking checklists.** A blocking checklist is one explicitly marked as a gate for the upcoming work. Other checklists may be informational only — those don't halt.

**Skip on missing checklists.** If `checklists/` is empty or absent, skip the pre-flight (no false halts). Log that no checklists were found.

## Procedure

### 1. Identify upcoming scope

What is the operator about to do? Common cases:
- Start of Phase N.
- Cross a Checkpoint in TASKS.md.
- Begin a specific T### task.

The scope determines which checklists are relevant.

### 2. Scan checklists/

For each `.md` file in `checklists/`:
- Read the YAML frontmatter (if any) for `gate` / `applies_to` / `blocking` tags.
- Count `[ ]` (incomplete) vs `[X]` (complete) items.
- Determine if it's relevant to the upcoming scope:
  - If frontmatter `applies_to: phase-2` and we're starting Phase 3 — relevant.
  - If frontmatter `applies_to: scoring` and the upcoming task touches scoring — relevant.
  - If no frontmatter — assume general; informational unless explicitly marked blocking.

### 3. Build pre-flight report

```markdown
## Pre-flight check — <upcoming scope>

| Checklist | Items | Complete | Status |
|---|---|---|---|
| checklists/scoring.md | 18 | 18/18 | ✅ |
| checklists/last30days-integration.md | 12 | 7/12 | ⚠ blocking |
| checklists/learning-system.md | 8 | 4/8 | informational |

### Halts
- checklists/last30days-integration.md is blocking and has 5 incomplete items. The upcoming Phase 4 (US2 — Narrative) requires last30days integration to be ready.

### Recommended action
Resolve the 5 incomplete items in checklists/last30days-integration.md before proceeding.
```

### 4. Halt or proceed

- If any blocking checklist incomplete → **halt**. Operator must complete or explicitly waive.
- If only informational items incomplete → proceed with caveat.
- If all clear → proceed.

### 5. Optional: task progress integration

If TASKS.md is being updated as work progresses, the pre-flight can also report:
- Tasks in current phase: complete / total.
- Whether the prior phase's Checkpoint has been crossed (all Phase N tasks `[X]`).

## Operating principles

### Gate at phase boundaries, not every commit
Friction discipline: pre-flight every commit makes it a tax. Pre-flight at phase boundaries makes it a check.

### Blocking vs informational is explicit
Don't infer — let the checklist itself declare its status via frontmatter (`blocking: true` / `applies_to: <phase or scope>`). If unclear, default to informational.

### The point is awareness, not obstruction
Pre-flight surfaces gaps the operator may have forgotten. The decision to override is theirs — but it should be conscious.

## Reporting

After pre-flight:
- Scope checked.
- Checklists scanned (count + status table).
- Halts (if any) with specifics.
- Suggested action.
- If halted: what would unblock.
