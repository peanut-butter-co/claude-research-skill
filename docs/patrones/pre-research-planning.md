# Pattern: pre-research planning

Concept extracted from a prior project (B2B commercial research), generalized for any research task.

## The core idea

**Before executing the first query, write a structured plan and confirm it with the user.** This is not ceremony: it's the only way to keep research from falling into the "I already know this" bias and ending up covering only the most obvious path.

The plan is materialized as a set of written decisions taken in a fixed order. Most are **checklists** (mark every option that applies, not pick-one) — the agent's natural tendency is to collapse to a single choice and that has to be actively resisted.

## When to apply this pattern

- Research tasks with broad or ambiguous search space.
- Any session where "execute and see what comes out" would produce predictable bias (same sources, same terminology, same geographies).
- Before invoking tools that are expensive in tokens or time (multi-agent deep research, mass scraping, paid APIs).

DO NOT apply if: the query is factual and pinpoint ("when did X release?"), if the user already provided concrete queries, or if it's a direct follow-up of prior research in the same session.

## The 7 decisions (generic)

Each one is written into the session document BEFORE executing. Types: **CHECKLIST** (mark all that apply), **SELECTION** (pick one), **DERIVED** (computed from others), **ACTION** (produce a concrete artifact).

### 1. Information profile — CHECKLIST
What kind of surface does the information live on? Mark all that apply:
- [ ] **Web-native** — pages with good SEO, indexed, accessible via search engines.
- [ ] **Platform-dependent** — lives inside platforms (Maps, Instagram, forums, Discord, X) and needs in-platform search.
- [ ] **Directory-resident** — in databases / directories / sectoral catalogs that don't rank in Google.
- [ ] **Latent** — only findable by indirect paths (PDFs, mentions, citation chains, networks of people).

Marking 3-4 implies a single search tool isn't enough. Each profile activates different mandatory sources (decision 6).

### 2. Search dimensions — CHECKLIST
What axes will I vary my queries along? List every relevant one:
- [ ] Topic vs sub-topic (specific vs generic)
- [ ] Geography / language / culture
- [ ] Temporality (historical vs current vs predictive)
- [ ] Audience / level (technical vs popular, B2B vs B2C)
- [ ] Format (paper, blog, repo, video, thread)
- [ ] Terminology and synonyms (field jargon, translations, abbreviations)

Each relevant combination = one block of queries.

### 3. Indirect paths — CHECKLIST
How do I find what I'm looking for WITHOUT naming it directly? Activate every viable one:
- [ ] **Reverse** — start from effects/consequences and walk back to causes; start from who uses it to find who produces it.
- [ ] **Snowball** — from one piece found, follow its references / authors / "see also".
- [ ] **Dorking** — advanced operators (`filetype:pdf`, `site:`, `intitle:`, exact-match quotes) for corners that ranking hides.
- [ ] **Cross-reference** — search where X is mentioned alongside Y to find their relationships.

### 4. Biases to compensate — CHECKLIST
What will I miss unless I actively compensate?
- [ ] **Recency** — algorithms reward new; the important thing may be old.
- [ ] **Language/culture** — searching only in English biases; add the topic's local language.
- [ ] **Source** — require N unique domains (e.g. >15) instead of harvesting the same portal.
- [ ] **Terminology** — do an explicit round with synonyms and antonyms.
- [ ] **Authority** — top 10 results are not truth; force yourself to pages 2-5 or filter for low-authority.
- [ ] **Size** — only the big ones are visible; separate rounds for small/niche players.

### 5. Stop criterion — SELECTION
When is the search complete? Default: **saturation + matrix coverage**, operationalized with numeric thresholds (tunable to the rigor the case demands).

**Default thresholds**:
- **Saturation**: <1 new finding per query for 5 consecutive queries on the same path → path exhausted.
- **Source diversity**: ≥15 unique domains (standard) or ≥25 (rigorous).
- **Minimum quality**: ≥70% of sources at Tier B+ when scoring is active (see SPECS §Source scoring of the project using this pattern).
- **Matrix coverage**: matrix of relevant cells (e.g. dimension × dimension from decision 2). No relevant empty cells → coverage complete.

Stop rule: **matrix coverage complete** AND **(saturation reached OR minimum diversity reached)**.

Note at end of each round: "X new findings in Y queries, Z unique domains accumulated" + revisit matrix.

### 6. Mandatory sources — DERIVED
Computed automatically from the profile in decision 1. Not freely chosen: they are what the profile **demands**.

| Source type | Web-native | Platform-dep. | Directory-res. | Latent |
|---|:-:|:-:|:-:|:-:|
| General WebSearch | ✓ | ✓ | ✓ | ✓ |
| In-platform search (Maps, X, Reddit, etc.) | — | ✓ | — | — |
| Sectoral directories / databases | — | — | ✓ | ✓ |
| People search (LinkedIn, profiles) | — | — | ✓ | ✓ |
| Dorking (filetype, site:) | — | — | — | ✓ |
| Reverse / snowball from known results | — | — | — | ✓ |

(The table adapts to the domain: in academic research, swap "directories" for "Semantic Scholar / arXiv"; in social research, `/last30days` already covers it; etc.)

### 7. Written query plan — ACTION
Produce the concrete artifact: the actual queries grouped by block, written BEFORE executing the first one. Minimum 5 per relevant block.

This is what breaks the "I already know this" feeling and forces diversification. If queries aren't written, no searching happens.

## Confirmation before executing

After writing the 7 decisions, present them to the user via AskUserQuestion (or equivalent) and ask: execute, adjust, or change approach? **Do not execute anything until confirmation.**

## Path A vs Path B

When prior research sessions on the same topic exist (search log/registry):

- **Path A — new research** (no log or empty): take the 7 decisions, present, execute.
- **Path B — continuation**: read the log as HISTORICAL CONTEXT, not active plan. Present the user with three options:
  - **A)** continue the same line
  - **B)** try a new line the agent suggests (informed by what worked/failed)
  - **C)** the user defines the line

  Only then take the 7 decisions for THIS session, informed by the choice.

Rule: prior-session decisions are context, not plan. Each session decides for itself. If a prior session left gaps, that doesn't mean this one has to fill them — the right strategy may be different.

## Revision during execution

The 7-decision plan is agreed at the start, but **it is not immutable**. If during execution accumulated evidence contradicts an assumption of the plan, pause and revisit the affected decisions before continuing.

Concrete triggers for re-planning:
- **Finding invalidates scope**: a piece found reveals the actual topic is different from what was framed (e.g. "X" turns out to be two different products with the same name).
- **Mandatory path runs dry**: a source derived from decision 6 produces nothing useful after 5+ queries → revisit profile (decision 1).
- **Unanticipated bias emerges**: during execution a bias not marked in decision 4 surfaces (e.g. the topic is only discussed in a specific language not previously planned).
- **Canonical terminology revealed**: a canonical term of the field appears that wasn't in decision 2 → expand dimensions and queries.

When triggered: pause, log the trigger in the search-log, adjust affected decisions, present the delta to the user, and resume. **Never revise the plan silently.**

This is the conceptual equivalent of "Phase 4.5: Outline Refinement" in [199-biotechnologies/claude-deep-research-skill](https://github.com/199-biotechnologies/claude-deep-research-skill): the plan is a starting point, not a closed contract.

## Anti-patterns

- **Skipping decisions because "it's obvious"** — the sense of obviousness is exactly the bias this prevents.
- **Turning checklists into selections** — marking 1 when 3 apply produces shallow research.
- **Inheriting the prior session's plan** — see Path B.
- **Starting to search before presenting to the user** — loses the chance for cheap correction.

## Continuous learning system (optional but recommended)

Maintain a `learnings.md` (or `learnings/` directory) where, at the close of each session, you record:
- Queries that worked better than expected
- Queries that produced nothing useful
- Explicit user feedback
- Tools with unexpected behavior
- Domain findings that would change future decisions

Consolidate back into CLAUDE.md / the pattern doc when 10+ mature entries exist or the user asks.

## Open validations of this pattern

- [`learnings/2026-05-06-001-pre-research-mid-weight-friction.md`](../learnings/2026-05-06-001-pre-research-mid-weight-friction.md) — unvalidated hypothesis that decisions 2/3/5 produce friction on mid-weight tasks. When closing sessions that exercise this pattern, observe and log there.
