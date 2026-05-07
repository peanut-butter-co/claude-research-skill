# spec-quality — static checklist for SPECS.md

> Adapted from the auto-generated Spec Quality Checklist in [`templates/commands/specify.md`](https://github.com/github/spec-kit/blob/main/templates/commands/specify.md) (lines ~141-178).

## Concept

Distinct from the dynamic `checklist.md` (which generates domain-specific checklists for any quality concern), this is a **standing static checklist** that any SPECS.md must pass before being considered stable. Run it after every material spec edit; before promoting to PLAN.

If the dynamic checklist asks "are the requirements well-written for THIS domain?", spec-quality asks "is this a well-formed spec at all?".

## When to invoke

- After SPECS is initially drafted.
- After every batch of edits that touches FRs, SCs, User Stories, or Edge Cases.
- Before invoking `plan` (gate).
- Before promoting SPECS from Draft to Approved.

## Procedure

Walk the checklist top-to-bottom. For each item: ✅ pass / ❌ fail / ⚠ partial. Failures must be fixed before the spec is considered stable. Partials are acceptable only if explicitly justified.

Output: a brief report listing the result per category and the failures that need addressing. NOT a copy of the spec.

## The checklist

### Content quality
- [ ] No implementation details (languages, frameworks, APIs, library names) appear in user-facing sections (User Stories, Acceptance Scenarios, FRs). Tech context belongs in PLAN, not SPECS. (FRs MAY name external services that are user-visible product choices, e.g. "system MUST invoke `/last30days`" — but not internal libraries.)
- [ ] Spec is focused on user value and business needs. "Why" is present alongside "what".
- [ ] Spec is written for the team / stakeholders, not for an implementer. A non-coder should understand intent.
- [ ] All mandatory sections are present per the template: User Stories, Acceptance Scenarios, FRs, SCs, Key Entities (if data exists), Edge Cases, Assumptions, Out of Scope.

### Requirement completeness
- [ ] No `[NEEDS CLARIFICATION]` markers remain. If any do, route to `clarify` and pause.
- [ ] Each FR is testable and unambiguous (a reasonable reader cannot interpret it two materially different ways).
- [ ] Success Criteria are **measurable** (numeric thresholds, observable outcomes).
- [ ] Success Criteria are **technology-agnostic** (no framework / library / API names).
- [ ] All Acceptance Scenarios are defined for every priority-1 (MVP) User Story.
- [ ] Edge cases enumerated for at least: empty / zero state, all-failure state, ambiguous input, partial completion, concurrent access (if relevant), resource exhaustion (if relevant).
- [ ] Scope is clearly bounded — Out of Scope section exists and lists deliberately-deferred items.
- [ ] Dependencies and Assumptions identified.

### Feature readiness
- [ ] All FRs have clear acceptance criteria (either inline or via SCs that map to them).
- [ ] User scenarios cover primary flows, error flows, and recovery flows where applicable.
- [ ] Each User Story has an **Independent Test** section that describes how to verify the story alone.
- [ ] Each User Story is **independently shippable** — can be built and released without depending on later-priority stories.
- [ ] User Stories are prioritized P1/P2/P3/... with a "Why this priority" justification.

### Style and consistency
- [ ] Terminology is consistent (the same concept named the same way across all sections).
- [ ] No internal contradictions (a quick scan: do FRs contradict User Stories? Do Edge Cases contradict the happy path?).
- [ ] FR / SC / User Story IDs are stable, sequential, no gaps, no dupes.
- [ ] Inline references between sections use IDs (FR-###, SC-###, US#) not phrasing.
- [ ] Spec is in the project's declared language (CLAUDE.md / project rules).

## Failure handling

For each failed item:
- **Critical fails** (no User Stories, NEEDS CLARIFICATION present, Success Criteria not measurable): block PLAN; require fix before proceeding.
- **Partial / minor**: log as a known gap; can proceed with explicit acknowledgment from the user.

If 3+ items fail across categories, recommend a full `analyze` round before patching individually.

## Reporting

```
## Spec Quality Report (YYYY-MM-DD)

| Category | Result |
|---|---|
| Content quality | ✅ |
| Requirement completeness | ⚠ 1 partial |
| Feature readiness | ✅ |
| Style and consistency | ✅ |

### Partials / failures
- [Requirement completeness] FR-014 enumerates examples but is non-exhaustive; acceptable for v1.

### Recommendation
Spec is stable. Proceed to `plan`.
```

## Operating principles

- This is a **static** checklist — items don't change between runs. Update items only when the spec template itself evolves.
- Run before `plan`. Don't run on top of TASKS — that's a different shape (use `analyze` for cross-artifact).
- If failures recur in the same category across runs, that category needs a project-rule (CLAUDE.md) update so future specs avoid the issue.
