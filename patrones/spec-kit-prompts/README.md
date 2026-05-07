# Spec-kit prompts

Generalized prompts adapted from [github/spec-kit](https://github.com/github/spec-kit), so we can do Spec-Driven Development on our own projects without installing the CLI or adopting the full `.specify/` infrastructure.

These are **tools for defining the project**, not skills of the final product. Invoked manually when we need a critical pass.

## The full SDD chain

The order matters: each artifact gates the next. Skipping a step usually means the next one invents what was missing.

```
constitution → specify → spec-quality → clarify → plan → tasks → analyze → implement
                                                                  ↑
                                                                  └── (also runs after spec-quality, after plan, etc.)
checklist (any time)
```

| Prompt | Type | Output / effect | When |
|---|---|---|---|
| [`constitution.md`](./constitution.md) | Principles & gate | `CLAUDE.md` `## Principles` section (or dedicated file) | Project init; principle changes |
| [`specify.md`](./specify.md) | Spec generator | `SPECS.md` (the WHAT/WHY) | New project; new feature |
| [`spec-quality.md`](./spec-quality.md) | Static checklist | Pass/fail report on SPECS shape | After every spec edit; before `plan` |
| [`clarify.md`](./clarify.md) | Proactive critic | Updated SPECS with `## Clarifications` log | Before closing a spec section; before `plan` |
| [`plan.md`](./plan.md) | Tech plan generator | `PLAN.md` (the HOW: stack, structure, patterns, gates) | After SPECS stable, before TASKS |
| [`tasks.md`](./tasks.md) | Task list generator | `TASKS.md` (phased, story-grouped, file-pathed) | After PLAN approved, before implementation |
| [`analyze.md`](./analyze.md) | Retrospective critic | Markdown report (read-only) | After TASKS exists; before implementation; after major changes |
| [`checklist.md`](./checklist.md) | Custom critic | `checklists/<domain>.md` ("unit tests for English") | Validating specific dimensions (scoring, learning, etc.) |
| [`implement.md`](./implement.md) | Pre-flight gate | Halt/proceed report | Before phase boundaries / Checkpoints in TASKS |

## The three artifacts

The chain produces three durable artifacts at project root:

1. **`SPECS.md`** — WHAT and WHY. Product / user / scope. No tech stack.
2. **`PLAN.md`** — HOW. Tech stack, libraries, project structure, architectural patterns, data model. Cites SPECS at every decision.
3. **`TASKS.md`** — Executable breakdown of PLAN, dependency-ordered, story-grouped. Cites both SPECS (for stories/FRs) and PLAN (for stack/structure).

`CLAUDE.md` (or a dedicated `constitution.md`) is the **constitution-lite** — principles that bind all three artifacts.

`learnings/` is **runtime** — accumulated as the skill is used; consolidated back into the artifacts via `/research-consolidate` (in our project) or manual review elsewhere.

## How to invoke

Tell the assistant, e.g.:
- "Run specify on this brief"
- "Run spec-quality over SPECS.md"
- "Run clarify over SPECS"
- "Run plan over the current SPECS"
- "Generate TASKS.md from SPECS + PLAN"
- "Run analyze cross-checking SPECS / PLAN / TASKS"
- "Generate a checklist for the scoring system"

The assistant reads the corresponding prompt and applies the procedure.

## Why this matters (anti-cherry-pick note)

The original temptation is to use only the critic prompts (`clarify`, `analyze`, `checklist`) because they feel like the "valuable" parts. **That's the cherry-pick trap.** Without `specify` you have no shape; without `spec-quality` no static gate; without `plan` you skip from WHAT directly to TASKS and force task-level invention of architecture; without `constitution` no principles bind anything. The chain works because each step gates the next. Skipping any one degrades all the downstream ones.

We are using all eight in this project.

## Differences from spec-kit original

- No `.specify/` directory or `specify` CLI required.
- No `/memory/constitution.md` path — we use `CLAUDE.md` as constitution-lite.
- No agent-context auto-update files (Claude Code's project memory replaces them).
- No GitHub-issues integration (`taskstoissues` dropped — not relevant here).
- No `extensions.yml` machinery — single-user file-based workflow.
- Originally these were in Spanish (matching the project's prior language); migrated to English alongside the project's English-policy rollout. Some legacy Spanish files remain under lazy migration.
