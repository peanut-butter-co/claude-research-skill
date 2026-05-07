# specify — natural-language → SPECS.md generator

> Adapted from `templates/commands/specify.md` and `templates/spec-template.md` of [github/spec-kit](https://github.com/github/spec-kit).

## Concept

Turn a natural-language feature description into a structured SPECS.md (the WHAT/WHY artifact). Strict separation: SPECS does NOT decide the HOW (no tech stack, no frameworks, no library choices, no architectural patterns). Those live in PLAN.

This is the entry point for new features. For an existing SPECS being refined, use `clarify` / `analyze` instead.

## When to invoke

- New project: turn the initial product brief into the first SPECS.md.
- New feature added to an existing project: produce a new spec section or a feature-specific spec.

NOT for: editing existing FRs (just edit them); refactoring SPECS shape (manual rewrite); resolving ambiguity (use `clarify`).

## Operating constraints

**WHAT and WHY only.** No tech stack, library names, architectural decisions, code structure, or implementation details in user-visible sections.

**Bounded clarification.** Maximum 3 inline `[NEEDS CLARIFICATION]` markers in the produced SPECS. If more than 3 ambiguities exist, route the user to `clarify` after generating the spec.

**Prioritization rubric for clarifications** (top to bottom; ask higher categories first):
1. **Scope** — what is included / excluded.
2. **Security & compliance** — auth, privacy, data handling.
3. **UX / interaction** — user flow, error states, accessibility.
4. **Technical** — anything that bleeds tech context. Defer to PLAN if possible.

**Informed guesses + Assumptions section.** When a detail is non-blocking and reasonable defaults exist, take an informed guess and document it under §Assumptions. Don't over-clarify.

## Procedure

### 1. Load context

- Existing CLAUDE.md / project rules.
- Existing SPECS.md if this is a feature addition (read structure to match conventions).
- patrones/*.md if any apply.

### 2. Parse the feature description

From the user's prose, extract:
- **Core user goal** — one sentence.
- **Implicit user roles / personas** — even if not named.
- **Success conditions** — what would "done" look like?
- **Constraints** mentioned (perf, scale, deadlines, rules).
- **Out-of-scope hints** — what the user said they don't want.

### 3. Generate User Stories (priority-ordered)

Each user story:
- 1-2 sentence "as a / I want / so that" statement.
- **Why this priority**: 1-3 sentences justifying P1/P2/P3.
- **Independent Test**: 1-3 sentences describing how to verify this story alone end-to-end.
- **Acceptance Scenarios**: 2-5 Given/When/Then scenarios covering primary + error flows.

P1 must be the MVP — the smallest slice that delivers user value alone. P2/P3+ are independently shippable additions.

### 4. Edge Cases

List concrete edge cases the spec must handle. At minimum consider:
- Empty / zero-state input.
- All-failure case (all sources fail, all paths broken, etc.).
- Ambiguous input.
- Partial completion / interruption.
- Concurrent access (if relevant).
- Resource exhaustion (if relevant).

### 5. Functional Requirements

Number sequentially `FR-###`. Each is one MUST/SHOULD statement, testable, unambiguous. Group by area (Planning / Execution / Output / etc.) if the surface is large.

If a requirement requires a TBD detail: insert `[NEEDS CLARIFICATION: <specific question>]` inline. Cap at 3 markers total. If you'd hit 4, decide which can be resolved with an Assumption and which is genuinely blocking.

### 6. Key Entities (if data is involved)

For each major data shape: name, fields (high-level — types belong in PLAN's data-model), lifecycle (created by / read by / updated by). Skip implementation-level details (storage format, serialization).

### 7. Success Criteria

Numbered `SC-###`. Each must be:
- **Measurable** — concrete thresholds, observable outcomes.
- **Technology-agnostic** — no framework / library / language references.
- **Testable** — describes a verification scenario, not an aspiration.

✅ Good: "A user can complete a 5-item comparative research in under 15 minutes."
❌ Bad: "The system uses fast async I/O." (tech detail)
❌ Bad: "Users are happy with the output." (not measurable)
❌ Bad: "The scoring algorithm uses Bayesian weighting." (tech detail)

Filter post-launch outcome metrics (e.g. "reduce support tickets by 50%") to a separate "Outcome metrics" subsection — they're not buildable here.

### 8. Assumptions

List all defaults you took to avoid over-clarifying. Each: 1 sentence + reason. Examples:
- "User has Claude Code installed and skill is loaded."
- "Skill operates per-user, per-machine; multi-user collab deferred."

### 9. Out of Scope

Explicitly enumerate what is intentionally deferred. Items here aren't bugs — they're known absences. Helpful for downstream `analyze` and to avoid scope creep.

### 10. Output

Write `SPECS.md` (or feature-specific spec file) using the template structure. Include a header:

```markdown
# Feature Specification: <feature>

**Feature**: `<short-name>`
**Created**: YYYY-MM-DD
**Status**: Draft
**Input**: <one-line summary of the prose this was generated from>

## Context
...
```

### 11. Self-validation via spec-quality

Run [`spec-quality.md`](./spec-quality.md) against the generated SPECS. Report any failures. Critical fails block; partials surface to user.

### 12. Reporting

- Path to SPECS.md.
- User Story count + priorities.
- FR count.
- SC count.
- `[NEEDS CLARIFICATION]` count (must be ≤3; if at the cap, recommend `clarify`).
- spec-quality result.
- Suggested next step: typically `clarify` if markers remain, else `plan`.

## Operating principles

### Spec is product language, not tech language
A reader who has never coded should understand WHAT and WHY. Tech context belongs in PLAN.

### Bounded clarification, prioritized
Three markers max. If you'd add a fourth, it means the prose was too underspecified — push back to the user with the prioritization rubric.

### Informed guess > clarification fatigue
Reasonable defaults documented in Assumptions are better than over-prompting the user. Save clarification budget for genuinely consequential ambiguity.

### Independent stories = MVP discipline
Every user story must be testable alone. If story 2 cannot be verified without story 3 also being built, they should be merged or re-prioritized.

### Determinism within bounds
Same prose + same rules → similar specs (ID assignment may shift if re-run; that's expected). Material differences across runs indicate the prose itself is ambiguous.

## Anti-patterns

- **Naming libraries / frameworks in FRs** — that's PLAN territory.
- **Vague Success Criteria** ("fast", "intuitive", "secure" without metrics).
- **Stories with co-dependencies** — story 3 only works if story 2 is also built. Either merge or re-priority.
- **Hidden Out-of-Scope** — features deferred but not declared. Always enumerate.
- **Over-clarification** — burning the 3-marker budget on cosmetic decisions instead of scope/security/UX.
