# constitution — project principles & gate

> Adapted from `templates/commands/constitution.md` and `templates/constitution-template.md` of [github/spec-kit](https://github.com/github/spec-kit).

## Concept

The **constitution** is the project's set of immutable (or semi-immutable) principles that bind all later artifacts. It is the single source of truth for "MUST" rules that override individual specs and plans. `analyze` and `plan` both gate on it — a SPECS or PLAN that violates a MUST principle is automatically CRITICAL.

In our project we use **`CLAUDE.md` as the constitution-lite**: a single file at project root containing principles and project-rules. We don't run a separate `constitution.md` artifact — but the **discipline** matters:
1. Versioned (semver-style) and dated.
2. Sync-impact reports when changed (which other artifacts need to update).
3. Phrased declaratively (MUST / SHOULD / MAY / MUST NOT).
4. Small (5-10 principles). If it grows, it loses force.

## When to invoke

- Project init: write the first set of principles before any feature work.
- Material change in project direction (e.g. shift from solo-built to team-shared, or new compliance mandate).
- Periodic review (every N months or when violations recur).

NOT for: tactical decisions (those live in PLAN); UX preferences (those live in SPECS).

## Operating constraints

**Principles are MUSTs, not aspirations.** Use declarative imperative language. "We try to ship fast" is not a principle. "Every PR MUST be deployable independently" is.

**Each principle should constrain choice.** A principle that doesn't rule anything out isn't a principle.

**Versioning is non-negotiable.** Even informal projects benefit. Semver: MAJOR for backward-incompatible changes (a principle is added/removed/redefined incompatibly), MINOR for additions, PATCH for clarifications.

## Procedure

### 1. Load context

- Existing CLAUDE.md or constitution.md (if any).
- The project's working memory: recurring frustrations, past mistakes that motivated rules.
- Recent learnings/ entries marked `process-improvement`.

### 2. Articulate principles

Each principle:
- **Name** (short, memorable).
- **Statement** (1-2 sentences, declarative, MUST / MUST NOT).
- **Why** (1-2 sentences justifying why this is principle-level vs convention-level).
- **How to apply** (1-2 sentences explaining where it bites — which artifacts / actions).

Example:
> **III. Test-First**
>
> All non-trivial code MUST have a test written before the implementation lands in main. Tests MUST fail first, then pass after the implementation.
>
> Why: shifts pressure to designable interfaces and prevents post-hoc justifications.
>
> How to apply: PRs without a corresponding test are blocked at code review. Spec writers are advised to think of test scenarios while writing acceptance criteria.

Aim for 5-10 principles. Beyond 10 they collide.

### 3. Add Additional Constraints (optional)

Below the principles, a section for non-principle rules: tech stack pins, version requirements, compliance notes. These are project-specific constraints that aren't elevated to MUST principles.

### 4. Add Governance section

- **How are violations handled?** (Block at review / require justification in Complexity Tracking / etc.)
- **How are amendments proposed?** (PR / RFC / discussion).
- **Versioning policy** (semver MAJOR / MINOR / PATCH).
- **Sync impact**: when a principle changes, what artifacts need updating? (typically: SPECS Out-of-Scope review; PLAN Constitution Check; existing TASKS may need new gates).

### 5. Stamp version + dates

```markdown
**Version**: X.Y.Z
**Ratified**: YYYY-MM-DD
**Last Amended**: YYYY-MM-DD
```

### 6. Sync impact report (on every change)

When the constitution is updated, produce a brief report:

```markdown
## Sync Impact — vX.Y.Z (YYYY-MM-DD)

**Changes**:
- Added: <new principle>
- Modified: <changed principle> (was: <old>; now: <new>)
- Removed: <removed principle> + reason

**Artifacts to update**:
- [ ] SPECS.md — review Out-of-Scope; <principle> may force <change>.
- [ ] PLAN.md — re-run Constitution Check gate.
- [ ] CLAUDE.md / project docs — propagate.
- [ ] (optional) Existing tasks — add gates if implementation discipline changed.
```

### 7. Output

For our project: the constitution lives in `CLAUDE.md`. Add or update a `## Principles` section at the top, with the structure above. Don't fork into a separate `constitution.md` unless the project grows to need it.

## Operating principles (meta — for this prompt itself)

### Light touch
A constitution that's never read is dead weight. Keep it short, surface it in onboarding, reference it in commits / PRs / spec edits.

### Empirical, not aspirational
Each principle should trace to a concrete past pain or risk. "Don't break the build" earns its place. "Be excellent" doesn't.

### Audit-friendly
Future you / future contributors will read this file. Make principles machine-checkable where possible (e.g. "PRs MUST have ≥1 test" can be enforced; "code MUST be readable" cannot).

### Updates trigger sync
A constitution change without a sync impact report is incomplete. Propagation is the principle's whole point.

## Reporting

After producing or amending the constitution:
- Path to file (`CLAUDE.md` or dedicated).
- Version stamp.
- Principle count.
- Any artifacts that now require re-validation (sync impact list).
- Suggested next step: re-run `plan` Constitution Check if PLAN exists; re-run `analyze` if SPECS exists.
