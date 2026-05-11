# Feature Specification: research-skill v1

**Feature**: `research-skill`
**Created**: 2026-05-06
**Status**: Draft (post-refactor to spec-template format)
**Input**: A Claude Code skill for rigorous, multi-source research with credibility scoring, complementary to `/last30days`.

## Context

Project: a Claude skill for investigation. Reference: [Weizhena/Deep-Research-skills](https://github.com/Weizhena/Deep-Research-skills); landscape in [`RESEARCH.md`](./RESEARCH.md). Must complement `/last30days` (already installed). Applies the pre-research planning pattern from [`patrones/pre-research-planning.md`](./patrones/pre-research-planning.md).

**Decisions locked with user (carried over):**
- Skill output language: English. Project meta-docs: English.
- 1 mode with always-on minimum source scoring (middle ground between standard and rigorous).
- Pre-research planning is mandatory before execution (the 7 decisions).
- Sources: `/last30days` (Reddit/X/YouTube/HN free; IG/TikTok via user-provided `SCRAPECREATORS_API_KEY`); WebSearch + WebFetch always; optional integrations system-suggested.
- Output: Markdown always + CSV when comparative.
- Commands: 3 classic (`/research` → `/research-deep` → `/research-report`) + `/research-consolidate` for self-learning.

---

## Clarifications

### Session 2026-05-07

- Q: How should the system decide between comparative and narrative mode? → A: Hybrid — keyword fast-path for obvious signals + LLM classification with 0.75 confidence threshold; below threshold ask the user.
- Q: What counts as "independent" for the cross-citation bonus? → A: Differ by parent publisher. Two sources are independent iff they belong to different parent publishers; publisher mapping lives in `data/publisher-graph.yaml`.
- Q: How aggressively does the skill detect user feedback worth logging? → A: Moderate — log explicit log requests, rejected AskUserQuestion options, tier corrections, source classification disputes, and explicit "this is wrong" flags against the skill's recent output. Casual unrelated comments do not trigger.
- Q: How is `<case>` identified, and what happens if `/research-deep` is invoked twice on the same case? → A: Hybrid — auto-slug from topic; if directory exists, ask user (resume existing vs new with timestamp suffix). Concurrent runs blocked via `tasks/<case>/.lock`.
- Q: How does the user see progress during a long `/research-deep` run? → A: Both — incremental JSON persistence to `output/` (durable) + orchestrator status messages to stdout at each milestone (ephemeral).

---

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Comparative research with scored sources (Priority: P1) — MVP

As a user investigating multiple options on the same dimensions (frameworks, tools, providers, products), I want a guided process that produces a comparison table backed by credibility-scored sources, so I can choose with confidence.

**Why this priority**: This is the core comparative use case the skill exists for. Delivers the most concrete value (a usable artifact: table + CSV) and exercises every subsystem (planning, scoring, multi-source, persistence, report).

**Independent Test**: From scratch, run `/research "compare 5 JS testing frameworks"`. The session must produce, end-to-end, a `report.md` with comparison table, a `report.csv` with one row per item, and inline citations tagged with their tier.

**Acceptance Scenarios**:

1. **Given** the user types `/research "compare X, Y, Z on price and quality"`, **When** the planning phase completes, **Then** the system writes `outline.yaml` (mode=comparative, items list, fields list) and `search-log.md` with the 7 pre-research decisions, and asks the user to confirm before executing.
2. **Given** the user has approved the outline, **When** the user runs `/research-deep`, **Then** the system launches one parallel agent per item, each returning a JSON with claim/evidence/source records where every source has a tier (A/B/C/D) assigned.
3. **Given** all item JSONs exist, **When** the user runs `/research-report`, **Then** the system produces `report.md` (TOC + comparison table + per-item sections + tiered inline citations + Sources note) and `report.csv` (one row per item, columns from `fields.yaml`).
4. **Given** any source URL fails post-hoc validation, **When** the report is generated, **Then** the affected fields show a visible gap marker rather than silently dropping the citation.

---

### User Story 2 — Narrative research on an open question (Priority: P2)

As a user investigating an open-ended question (impact analysis, "how does X work", domain explainer), I want a structured essay with cited evidence, so I get a defensible answer rather than a list.

**Why this priority**: Second-most-common research mode. Reuses 90% of US1 plumbing (planning, scoring, sources, persistence) but with a different output shape. Validates that the architecture supports both modes.

**Independent Test**: Run `/research "what impact does the EU AI Act have on SaaS startups under 50 employees"`. Must produce a `report.md` with sub-essays per subquery and a "Cross-cutting findings" section, with inline citations.

**Acceptance Scenarios**:

1. **Given** the user types an open-ended question, **When** planning runs, **Then** the system produces an `outline.yaml` with `mode: narrative` and a `subqueries` list (3-5 sub-questions) instead of items+fields.
2. **Given** an approved narrative outline, **When** `/research-deep` runs, **Then** it launches one agent per subquery, each producing evidence-backed JSON with scored sources.
3. **Given** the JSONs exist, **When** `/research-report` runs, **Then** it produces a `report.md` structured as essay-by-subquery + a "Cross-cutting findings" section synthesizing across subqueries, with inline tiered citations and a "Sources note" at end.

---

### User Story 3 — Self-learning capture and consolidation (Priority: P3)

As a recurring user, I want the skill to capture corrections and self-detected anomalies during research, and let me consolidate them into project knowledge over time, so the system improves with use rather than repeating the same mistakes.

**Why this priority**: Compound value over time. Not needed for the first runs to be useful (US1/US2 work without it), but unlocks improvement loops once the skill has usage history.

**Independent Test**: During a research session, the user corrects a tier classification ("that source isn't Tier A, it's a paid press release"). Skill must offer to log it, and `/research-consolidate` must later propose promoting that learning to `data/source-tiers.yaml`.

**Acceptance Scenarios**:

1. **Given** the user issues a correction during a session, **When** the skill detects the correction signal, **Then** it offers to log a structured learning entry under `learnings/` with frontmatter (id, date, trigger, type, status: pending).
2. **Given** an agent in `/research-deep` detects a self-identifiable anomaly (contradictory Tier A sources, query returning zero results after retries, repeatedly broken domain), **When** the anomaly is detected, **Then** a learning entry is logged automatically with `trigger: self-detection`.
3. **Given** ≥1 pending learning exists, **When** the user runs `/research-consolidate`, **Then** the skill groups them by type, proposes promotions (to `data/source-tiers.yaml`, `CLAUDE.md`, `SKILL.md`, etc.) or discards, and updates statuses on user approval.

---

### User Story 4 — Optional integration suggestions (Priority: P4)

As a user researching a topic that has a strong fit with a specialized tool (Google Places API for businesses, GitHub API for repos, Semantic Scholar for papers), I want the skill to suggest the integration during planning, so I can opt-in for higher-quality data without managing the catalog myself.

**Why this priority**: Quality-of-life multiplier. Skill works without it, but integrations dramatically improve specific topic types. Lowest priority because the catalog can grow incrementally.

**Independent Test**: Run `/research "best cheese shops in Madrid"`. Skill must detect the location/business signal and suggest Google Places API setup, with an offer to skip / configure now / never-suggest-for-similar.

**Acceptance Scenarios**:

1. **Given** the topic involves entities that match an entry in `data/topic-integrations.yaml`, **When** planning runs, **Then** the skill lists matching tools with one-line "what it adds + how to set up", and a 3-option choice (configure now / skip for this run / never suggest for similar).
2. **Given** the user picks "configure now" and provides credentials, **When** the user proceeds, **Then** credentials are written to `.config/research-skill/.env` (gitignored) and the integration is used by the relevant agents.
3. **Given** the user picks "never suggest for similar", **When** a future similar topic is researched, **Then** the suggestion is skipped silently.

---

### Edge Cases

- **Zero results across all sources**: every agent returns empty. Report must show "no evidence found" rather than blank fields.
- **All URLs broken**: post-hoc validator fails on every source. Report shows gaps with summary "all sources failed validation"; never silenced.
- **All Tier D**: the topic genuinely lives on low-quality sites (e.g. consumer SEO content). Skill must ask the user whether to include Tier D for this run.
- **Topic mode ambiguous**: cannot decide comparative vs narrative from the prompt. Skill prompts user with two options + topic-specific examples.
- **Contradictory Tier A sources**: two high-tier sources disagree on a fact. Report disagreement explicitly; log as learning candidate.
- **Resume after interruption**: `/research-deep` is killed mid-batch. Re-running must skip already-completed item JSONs and resume from last incomplete.
- **Optional integration declined repeatedly**: if user picks "never suggest" for a tool, future similar-topic runs honor that without re-asking.
- **`/last30days` not configured**: if user declined social setup, skill proceeds with WebSearch+WebFetch only and notes the missing source in the report.
- **Mid-flight scope invalidation**: during `/research-deep`, evidence reveals the topic is materially different than planned (e.g. ambiguous entity name resolves to two different products). System pauses, presents the delta, awaits user choice (continue with original / switch to revised / abort).
- **WebFetch fails on a candidate source**: 403, JS-only rendering, paywall, or other extraction failure. System attempts Tier 1 fallbacks (Jina reader → Exa contents → Wayback) and only escalates to Tier 2 browser control (Claude extension → chrome-devtools MCP → Playwright MCP) when Tier 1 is exhausted. Source declared failed only after all paths.
- **Emergent comparison dimension or new entity**: during execution an agent surfaces a comparison dimension or entity that wasn't planned. Orchestrator collects all proposals after the first round (FR-030) and presents to the user; accepted proposals trigger re-runs of affected agents on the new dimension/item.
- **Agent budget exhausted**: an agent reaches its `query_budget` cap (FR-032) before completing all fields. Hard-stops with partial JSON; remaining fields marked `[uncertain]`; report flags the gap and identifies budget exhaustion as the cause.
- **Systemic tool failure**: a Tier 1 or Tier 2 component (e.g. Jina, Exa, browser MCP) fails on >3 consecutive calls. FR-026 triggers; user chooses to degrade to next tier or proceed without that tool.
- **Agent fails to call `assign_tier()`**: an agent ships an `output/*.json` whose sources have missing tiers or hand-asserted tiers (prose judgment, not registry-backed). The orchestrator's FR-013a sweep MUST overwrite all tier fields deterministically; no `[uncertain]` is triggered for tier alone. A learning entry with `trigger: self-detection`, `type: process-improvement` MUST be logged when the sweep finds ≥1 corrected tier, so consolidation can track agent-prompt drift.

---

## Requirements *(mandatory)*

### Functional Requirements

#### Planning phase

- **FR-001**: System MUST require the user to run `/research <topic>` before `/research-deep` or `/research-report` can execute. Direct invocation of `/research-deep` without prior planning MUST return a clear instruction to plan first.
- **FR-002**: System MUST take the 7 pre-research decisions from [`patrones/pre-research-planning.md`](./patrones/pre-research-planning.md) and persist them to `tasks/<case>/search-log.md` before `/research-deep` is invoked.
- **FR-002a** *(case identity & concurrency)*: `<case>` MUST be an auto-generated slug derived from the topic by this rule: lowercase → strip punctuation → split on whitespace → drop English stop words (`a, an, the, of, in, on, to, vs, and, or, with, for`) → join with hyphens → truncate to 60 chars without splitting words (ASCII only). Worked example: `"Compare jest, vitest, and playwright on speed"` → `compare-jest-vitest-playwright-speed`. On `/research`: if `tasks/<case>/` does NOT exist, create it; if it exists, ask the user via AskUserQuestion with two options: (a) resume the existing case (treat prior plan as historical context per FR-003); (b) create a new case with timestamp suffix `<case>-YYYYMMDD-HHMM/` (the suffix is excluded from the 60-char cap). Concurrent runs on the same `<case>` MUST be blocked via lockfile `tasks/<case>/.lock` (containing PID + start timestamp); a second invocation MUST fail-fast with the lockfile contents. Stale-lock detection: if lock age > 1 hour AND no live process matches the recorded PID, the lockfile is stale and MUST be removed automatically with a warning to the user. PID is best-effort — implementation MAY substitute the Claude Code session ID or invocation timestamp if a stable PID is not available in the runtime. Note: the stop-word list is English; topics in other languages may produce sub-optimal slugs (acceptable for v1 since skill output is English).
- **FR-003**: After the user has chosen "resume existing case" in FR-002a, system MUST detect previous sessions in that case's `search-log.md` and present three continuation options (same line / new line proposed / user-defined line) before taking the 7 decisions for the current session. Behavior follows the "Camino A vs Camino B" rule from [`patrones/pre-research-planning.md`](./patrones/pre-research-planning.md): prior decisions are historical context, not active plan.
- **FR-004**: System MUST detect research mode (comparative vs narrative) using a hybrid algorithm: (a) **keyword fast-path** — if the topic contains explicit comparative signals (`compare`, `vs`, `best N`, `alternatives to`, `differences between`, `evaluate`, or an explicit enumerated list of N≥2 named items), classify as `comparative`; (b) **LLM classification fallback** — if no fast-path keyword matches, classify via LLM and emit a confidence score in [0, 1]; (c) **threshold**: if confidence ≥ 0.75 accept the classification, else ask the user via AskUserQuestion with two options and topic-specific examples. Keyword list and threshold MUST live in `data/mode-detection.yaml` so they can be tuned without code changes.
- **FR-005**: System MUST suggest matching topic-driven integrations from `data/topic-integrations.yaml` (a separate file from `data/fallback-extractors.yaml`, which serves FR-028). Each entry in `topic-integrations.yaml` MUST declare a `triggers[]` list (keyword regexes and/or entity-type tags). A topic matches an integration if any trigger matches the topic prompt OR the inferred entity type from the prompt. The system MUST present matches with a 3-option choice (configure / skip / never-suggest-for-similar). The "never" preference MUST persist in `.config/research-skill/preferences.yaml` keyed by **topic-type signature**, defined as the sorted tuple of (matched `topic-integrations.yaml` ids ∪ inferred entity-type tags) for the topic; two topics share a signature iff their tuples are equal.
- **FR-006**: System MUST present the full plan (7 decisions + outline + suggested integrations) to the user via AskUserQuestion and wait for explicit confirmation before persisting and ending the planning phase. No searches occur in this phase. During planning the system MUST also set `outline.yaml config.social_signal: true` when the topic involves any of: commercial products, public figures, brand or company names, events within the last 12 months, tools or services with active community discussion. Otherwise `false`. The user MAY override `social_signal` and `rigor` (see FR-032 / Key Entities) at the confirmation step.

#### Execution phase

**Concepts used in this section**:
- **Orchestrator** = the top-level execution context invoked by `/research-deep`. Owns agent lifecycle, intermediate synthesis (FR-031), status streaming (FR-033), strategic re-planning (FR-026), and user-facing pauses.
- **Round** = one batch of queries an agent executes between orchestrator checkpoints. Round 1 = the initial planned queries from the 7th pre-research decision. Round N>1 = follow-up queries informed by FR-031 hints, emergent threads, or strategic re-planning.

- **FR-007**: System MUST launch parallel Task agents to process items (comparative) or subqueries (narrative). For comparative mode, `outline.yaml config.items_per_batch` (default 1 = max parallelism; higher values batch items into fewer agents) controls how many items each agent handles. For narrative mode, each agent always handles exactly one subquery.
- **FR-008**: Each agent MUST use WebSearch and WebFetch as base sources. If `outline.yaml config.social_signal: true`, each agent MUST also invoke `/last30days <subquery_or_item>` via the slash-command runner (Bash `claude /last30days "<topic>"` if available in the runtime; otherwise a runtime-equivalent skill invocation). Output is parsed back as text and incorporated as Tier C sources per FR-013/FR-014. If `/last30days` is unreachable or errors out, the agent logs the failure and proceeds without it (per Edge Case "`/last30days` not configured").
- **FR-009**: Each agent MUST apply source scoring (FR-013 through FR-016) to every cited source and return a JSON of shape `{item_or_subquery, fields_or_evidence, sources: [{url, title, tier, date}], uncertain: [...], _meta: {...}}`.
- **FR-010**: System MUST resume from prior partial runs by skipping items/subqueries whose JSON in `tasks/<case>/output/` is **complete**. Complete = (all `fields[]` filled) OR `pruned: true` (FR-029d) OR `budget_exhausted: true` (FR-032). All other JSONs (missing or partial without these flags) MUST be re-run from where they stopped.
- **FR-011**: System MUST run a post-hoc URL validator on every source URL across all JSONs: HEAD request first; if HEAD returns non-2xx, fall back to a single GET request (some servers reject HEAD but allow GET). Only after both fail is the URL marked as broken. Marking as broken triggers the FR-028 fallback chain at report-generation time so the source content can still be recovered if possible.
- **FR-012**: Each agent MUST log self-detected anomalies as learning entries with `trigger: self-detection`. Specifically: (a) two or more Tier A sources contradicting on a claim with no third source resolving it; (b) a query returning zero results after 3 reformulations (synonym swap, broader term, narrower term); (c) any domain failing URL validation in ≥2 distinct sessions cumulatively across the project.
- **FR-026** *(Level 2 — strategic; pause and confirm)*: When a strategic mid-flight trigger fires during `/research-deep`, the system MUST pause execution, append the trigger and proposed delta to `search-log.md`, re-present the revised plan to the user via AskUserQuestion, and resume only after explicit confirmation. Silent strategic revision is forbidden.

    **Mid-round triggers** (can fire at any time within a round):
    - Scope-invalidating finding (e.g. ambiguous entity resolves to two distinct products).
    - Unanticipated bias requiring plan changes (per [`patrones/pre-research-planning.md` §Revision during execution](./patrones/pre-research-planning.md)).
    - Canonical terminology shift requiring query rewrites.
    - Systemic tool failure: an entire **tier** of FR-028 is exhausted (all Tier 1 components OR all Tier 2 components fail consecutively, ≥3 attempts each). Per-component failure inside a tier is normal fallback (FR-028) and does NOT trigger FR-026 on its own.

    **End-of-round triggers** (fire only at round boundaries, after FR-031 synthesis):
    - Accumulated emergent extensions (surfacing logic owned by FR-030).

    Tactical adaptation (query reformulation, fallback fetching, single-thread chasing within budget, pruning) is governed by FR-029 and does NOT pause execution.
- **FR-027**: Each agent (and orchestrator across agents) MUST track per-round metrics: new findings count per query, unique domains accumulated, tier distribution. Execution stops when matrix coverage is complete AND (saturation: <1 new finding per query for 5 consecutive queries OR diversity: ≥15 unique domains for standard rigor, ≥25 for rigorous). Thresholds defined in [`patrones/pre-research-planning.md` §Stop criterion (Decision 5)](./patrones/pre-research-planning.md).
- **FR-028**: When WebFetch OR WebSearch fails (WebFetch: 403/anti-bot, JS-only rendering, paywall, redirect loop, network timeout, or any other extraction failure; WebSearch: empty results, error, quota exhausted), the system MUST attempt alternatives in order before declaring the operation unrecoverable.

    **For WebSearch failures**: try Brave Search API (if `BRAVE_API_KEY` configured) → Exa search (if `EXA_API_KEY` configured) → DuckDuckGo HTML scraping. On success, log `search_method` in agent metadata.

    **For WebFetch failures**:

    **Tier 1 — text-extraction alternatives** (try until one succeeds before falling through to Tier 2):
      a. Jina AI Reader (`https://r.jina.ai/<url>`, free, no key required).
      b. Exa.ai `/contents` endpoint (if `EXA_API_KEY` configured).
      c. archive.org Wayback Machine (most recent snapshot).

    **Tier 2 — browser control** (last resort; try in priority order):
      1. Claude Chrome Extension (if available in environment).
      2. `chrome-devtools` MCP server (if configured).
      3. Playwright MCP server (if configured).

    On success, the agent JSON MUST record the recovery method (`fetch_method: "webfetch" | "jina" | "exa" | "wayback" | "browser-ext" | "chrome-mcp" | "playwright-mcp"`). The system MUST NOT skip Tier 1 to go directly to Tier 2 — browser control is reserved for cases where pure text extraction cannot work (heavily JS-rendered SPAs with no SSR, signed/ephemeral content, interactive walls).

    If all paths fail, the source MUST be logged with `extraction_failed: true` in the agent JSON and surfaced in `report.md` under "Sources note > Extraction failures" with the original URL, methods attempted, and failure modes. NEVER silently drop a source.
- **FR-029** *(Level 1 — auto-adapt within agent budget; no pause)*: Each agent MAY adapt tactically within its allocated `query_budget` (FR-032):
    a. **Query reformulation** up to 3 attempts per dry query (per FR-012).
    b. **Fallback fetching** through the FR-028 chain.
    c. **Emergent thread chasing**: when a lateral citation or cross-reference shows **high signal** for the current item/subquery — defined as: the candidate appears in ≥2 currently-collected sources OR scores Tier B+ on initial inspection — the agent MAY spend up to 2 extra queries chasing it, charged against budget. Capped at **`outline.yaml config.max_emergent_threads` per agent per round (default 2)**; beyond that, additional threads are logged as `proposed_extensions[]` (FR-030) instead of chased inline. Each chase MUST be logged in the agent JSON under `emergent_threads_chased[]: [{trigger, queries_spent, outcome}]`, where `outcome` ∈ {`useful`, `dead-end`, `partial`}.
    d. **Pruning**: if an item or subquery yields 0 useful results after triple reformulation, the agent MAY mark it `pruned: true` in its JSON, log the reason, and stop spending budget on it; sibling agents continue normally.

    Tactical adaptation MUST NOT (i) introduce new items/subqueries to the outline, (ii) modify `fields.yaml`, or (iii) exceed budget. Those changes are strategic and require FR-026 / FR-030 paths.
- **FR-030** *(Level 2 — emergent strategic findings; surfaced after first round)*: When an agent detects (a) a new comparison dimension applicable to multiple items beyond the current one, (b) a new item/competitor/entity that should join the comparison, or (c) a new subquery that materially extends a narrative (where "materially extends" = the new subquery's answer would meaningfully alter ≥1 planned cross-cutting finding; agent judgment, logged as a `proposed_extensions[]` entry for user verdict), the agent MUST log it as a `proposed_extensions[]` entry in its JSON without acting on it. After all agents complete their first round, the orchestrator MUST surface accumulated proposals to the user via AskUserQuestion with three options per proposal: (1) **accept** — affected agents add the new dimension/item to their `fields[]` and run additional queries to fill it (existing fields preserved; budget extension of +5 standard / +10 rigorous granted, configurable via `outline.yaml config.extension_budget`); (2) **note** — record in "Cross-cutting findings" only, no re-running; (3) **discard**. User decisions MUST be persisted in `search-log.md`.
- **FR-031** *(intermediate synthesis + cross-pollination)*: At the end of every round that does NOT hit the FR-027 stop criterion, the orchestrator MUST run an intermediate synthesis pass extracting emergent dimensions, newly canonical terms, and entity references discovered by each agent. A signal is **cross-relevant** iff (a) it appears in ≥2 agents' first-round outputs, OR (b) it appears in any single agent's output AND syntactically relates to another agent's item/subquery (overlap = case-insensitive substring match on canonical entity name, OR shared noun-phrase token after stop-word filter). Cross-relevant signals MUST be propagated to other agents as **hints** for their next round (e.g. "agent-vitest found 'bundler-aware testing' as a key differentiator — verify whether this dimension applies to your item"). Hints are non-binding suggestions, not scope changes; the receiving agent decides whether to spend budget exploring them and MUST log received hints under `_meta.hints_received[]`. This pass operates within Level 1 autonomy and does not pause execution. If FR-027 stop conditions are met, no further synthesis pass is performed and execution proceeds to report generation.
- **FR-032** *(budget caps; Level 3 hard-stop)*: Each agent MUST receive a `query_budget` derived from `outline.yaml config.rigor` (`rigor: standard` → default 15 queries; `rigor: rigorous` → default 25 queries). `query_budget` MAY also be set explicitly in `outline.yaml config` to override the rigor-derived default. `rigor` defaults to `standard` and is set during planning by the user (FR-006) or by topic-complexity heuristic. The budget covers all queries: initial planned, reformulations (FR-012), fallback fetches (FR-028), emergent-thread chasing (FR-029c). At 80% consumption the agent MUST emit a budget warning in its JSON and prioritize closing remaining `fields[]` over chasing new threads. At 100% the agent MUST hard-stop, persist current JSON state with `budget_exhausted: true`, and report which fields remain `[uncertain]`. The orchestrator MUST surface budget-exhausted agents to the user before generating the final report.
- **FR-033** *(observability during execution)*: During `/research-deep` the system MUST provide both durable and ephemeral progress signals:
    a. **Incremental persistence** — each agent's JSON output MUST be written to `tasks/<case>/output/` as soon as the agent completes; partial JSONs MUST also be flushed at each round boundary so a user tailing the directory sees progress.
    b. **Streaming status** — the orchestrator MUST emit status messages to stdout at each milestone: agent start, round complete (with new-findings count), intermediate synthesis triggered (FR-031), emergent extension proposed (FR-030), strategic re-planning triggered (FR-026), agent done (payload: items completed, fields filled, fields uncertain, sources count by tier, budget consumed, pruned/exhausted flags), agent budget warning (80%) and exhaustion (100%). Each status message MUST identify the agent (item or subquery) and the milestone.

#### Source scoring

- **FR-013**: System MUST assign a tier (A / B / C / D / Unknown) to every cited source. Lookup happens first against `data/source-tiers.yaml`. Unknown defaults to C; the source MUST also be (a) listed under "Sources note > Unclassified domains" in the report, and (b) emitted as a learning entry with `type: source-classification, status: pending` for later consolidation via `/research-consolidate`.
- **FR-013a** *(tier determinism enforcement)*: System MUST treat tier assignment as deterministic: tiers are produced exclusively by `assign_tier()` over the registry + heuristics defined in FR-013/FR-014. Agents MUST NOT invent or assert tiers from prose judgment. The orchestrator MUST run a **tier-determinism sweep** at every round boundary in `/research-deep` (and again as defense-in-depth in `/research-report` before report generation): for every source in every agent JSON, re-invoke `assign_tier()` and overwrite the source's `tier`, `score_raw`, `unclassified`, and `heuristic_flags` fields with the deterministic result. Pre-existing agent-supplied tier values MUST be discarded if they disagree with the registry. The sweep MUST persist its result back to the agent JSON (per FR-033a). When a source's URL is missing or malformed (cannot be parsed by `urlparse`), the sweep MUST mark it `extraction_failed: true` rather than silently fail. When the sweep corrects ≥1 tier within an agent JSON, the orchestrator MUST log a learning entry with `trigger: self-detection`, `type: process-improvement`, body referencing the agent_id and correction count, so consolidation can track agent-prompt drift.
- **FR-014**: For Unknown sources, system MUST apply heuristics: DOI/ISBN present (+1 tier); domain suffix `.edu`/`.gov`/academic `.org` (push toward A/B); suspicious URL patterns push toward D, including but not limited to: `medium.com/@<pseudonym>` without verified About page; generic-WordPress aggregators with no attributed author; AI-content tells (boilerplate "in this article" intros, no specific examples or dates); listicles with no attributed author; domains registered <6 months ago (when WHOIS data accessible).
- **FR-015**: System MUST compute a numeric score per source: `tier_weight × recency_bonus × cross_citation_bonus`, where tier_weight is A=4, B=3, C=2, D=0.5; recency bonus decays with age (1.0 if <1y, 0.8 if 1-3y, 0.6 if 3-5y, 0.4 if >5y; inverted for historical/academic topics); cross-citation bonus is +0.5 if N≥2 **independent** Tier ≥B sources agree on the claim. Two sources count as independent iff they belong to different parent publishers (e.g. `cnn.com` and `cnnespanol.cnn.com` share a parent and do NOT count; `nytimes.com` and `ft.com` do). Publisher mapping lives in `data/publisher-graph.yaml` (domain → parent publisher); domains without an entry default to their own root domain as parent. **Synthesis tie-break across all tiers**: (a) higher score wins; (b) on numeric tie, higher `tier_weight` wins; (c) on further tie, more recent wins; (d) if still tied AND claims contradict, both MUST be reported under the report's "Disagreements" subsection (extends FR-017a beyond Tier A).
- **FR-016**: Tier D sources MUST be excluded from the final report by default. They MAY be included only if the user explicitly approved Tier D during planning.
- **FR-016a**: During planning, if topic detection signals the topic likely lives predominantly on Tier C/D surfaces (consumer reviews, hobbyist communities, leaks/rumors, niche fan forums), the system MUST prompt the user with explicit yes/no: "This topic is likely discussed mostly on community/low-quality sources. Include Tier D in the report? [yes/no]". The decision MUST be persisted in `outline.yaml config.include_tier_d: bool` (default `false`).

#### Output

- **FR-017**: System MUST generate `report.md` with: TOC, comparison table at top (comparative mode) OR essay-per-subquery (narrative mode), inline citations tagged `[Source • Tier B]`, and a "Sources note" section at end listing sources grouped by tier.
- **FR-017a**: When ≥2 Tier A sources disagree on a claim, the report MUST surface the disagreement under a "Disagreements" subsection. Each entry: claim phrasing, sources on each side with citations, brief 1-line note if resolution is possible. Silent omission of the conflict is forbidden.
- **FR-018**: For comparative mode, system MUST also generate `report.csv` with one row per item and columns standardized from `fields.yaml`.
- **FR-019**: System MUST mark fields with insufficient evidence as `[uncertain]` rather than fabricating a value. The end of the report MUST list all gaps explicitly.
- **FR-020**: System MUST validate that every claim in the report has at least one citation and no broken URLs (URL validation per FR-011, uncertain fields per FR-019, FR-028 fallback chain attempted before declaring a URL broken). On failure, the report is delivered with gaps visibly marked, never silently dropped.

#### Self-learning

- **FR-021**: System MUST detect user feedback signals at **moderate** aggressiveness: (a) explicit log requests ("remember this", "log this"); (b) rejected AskUserQuestion options (defined as: user picked a custom answer, OR picked an option flagged in opposition to the skill's Recommended choice); (c) tier corrections (e.g. "that source isn't Tier A"); (d) source classification disputes; (e) explicit "this result is wrong" flags against the skill's most recent output. On detection, the skill MUST offer to log the feedback as a learning entry with `trigger: user-feedback` via a one-line confirmation prompt. Casual comments unrelated to a recent skill output MUST NOT trigger the prompt, to avoid interruption fatigue.
- **FR-022**: System MUST end every `/research-report` invocation with a one-line prompt: "Anything from this session worth logging?" The user can answer in one line or skip.
- **FR-023**: Each learning entry MUST be a `.md` file under `learnings/` with frontmatter (id, date, trigger, context, type, status: pending), filename pattern `YYYY-MM-DD-NNN-short-slug.md`. Allowed `type` values: `source-classification`, `query-strategy`, `tool-behavior`, `domain-fact`, `scoring-rule`, `process-improvement` (meta-learning about the skill's own process), `pattern-validation` (open hypothesis to validate via observation across N sessions).
- **FR-024**: `/research-consolidate` MUST read learnings filtered by `status: pending`, group by type, and propose for each group: promote to `data/source-tiers.yaml` / `data/topic-integrations.yaml` / `data/publisher-graph.yaml` / `data/mode-detection.yaml` / `data/fallback-extractors.yaml` / `CLAUDE.md` or `SKILL.md` / discard. On user approval, the command MUST (a) write the promoted content to its target file and (b) update the source learning's `status` frontmatter to `consolidated` or `discarded` directly in-place.
- **FR-025**: Consolidation MUST be triggered: (a) by explicit user invocation of `/research-consolidate`; OR (b) automatically prompted when ≥10 pending entries exist on any `/research-*` invocation; OR (c) prompted by `/research` at start of a new session — defined as either the first `/research` invocation for a `<case>` not previously seen, OR any `/research-*` invocation when the most recent prior invocation was >24h ago — if pending entries older than 7 days exist. Auto-triggers (b)(c) prompt the user; never run silently.

---

## Key Entities

The skill defines five primary data shapes that act as contracts between phases.

### `outline.yaml` (comparative)
Fields: `mode: comparative`, `topic`, `items[]`, `fields_file`, `config{items_per_batch, social_signal, rigor, query_budget?, max_emergent_threads, extension_budget?, topic_integrations[]}`. `items_per_batch` (default 1) — items each parallel agent handles. `rigor` ∈ {standard, rigorous} (default standard) — drives default `query_budget` (15 / 25 per FR-032) and diversity threshold (15 / 25 unique domains per FR-027). `query_budget` overrides the rigor-derived default if set. `max_emergent_threads` (default 2 per FR-029c). `extension_budget` (default +5 / +10 per FR-030). `topic_integrations[]` lists user-confirmed integrations from `data/topic-integrations.yaml` (per FR-005). Lifecycle: created by `/research`, read by `/research-deep` and `/research-report`.

### `outline.yaml` (narrative)
Fields: `mode: narrative`, `topic`, `subqueries[]`, `config{social_signal, rigor, query_budget?, max_emergent_threads, extension_budget?, topic_integrations[]}`. Same semantics as comparative `config`. Same lifecycle.

### `fields.yaml` (comparative only)
Fields: `categories{name: [field, ...]}`, `detail: brief|moderate|detailed`. Defines what each item agent must fill.

### Item JSON (per-item or per-subquery output)
Fields:
- `item` or `subquery` key
- `fields{}` — each field has `value` + `sources[{url, tier, date, fetch_method, extraction_failed?}]`
- `uncertain[]`
- `pruned?: bool` — set true if agent abandoned this item/subquery per FR-029d
- `emergent_threads_chased[]: [{trigger, queries_spent, outcome}]` — per FR-029c
- `proposed_extensions[]: [{type: dimension|item|subquery, description, rationale}]` — per FR-030
- `budget_consumed: int`
- `budget_exhausted?: bool` — set true if agent hard-stopped per FR-032
- `_meta{agent_run, hints_received[]}` — `hints_received[]` per FR-031

`fetch_method` ∈ {webfetch, jina, exa, wayback, browser-ext, chrome-mcp, playwright-mcp} per FR-028. One file per item/subquery in `tasks/<case>/output/`.

### Learning entry
Fields: frontmatter (id, date, trigger, context, type, status), body (1-3 sentences + suggested rule). One file per entry in `learnings/`.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user can complete a 5-item comparative research (planning → execution → report) and produce both `report.md` and `report.csv` in under 15 minutes from invocation. Measured assuming WebSearch p95 latency ≤3s and WebFetch p95 ≤8s; user-pause time (FR-026 / FR-030 confirmations) excluded from wall-clock.
- **SC-002**: At least 70% of cited sources in any output report are Tier A or B. When Tier D is excluded by default (FR-016), 0% of cited sources are Tier D; when the user has approved Tier D inclusion (FR-016a), <5% of cited sources are Tier D. Measurable only after **SC-002a** holds; if SC-002a fails, SC-002 is reported as `n/a — tier coverage incomplete`.
- **SC-002a** *(tier coverage)*: 100% of cited sources in any `output/*.json` carry a tier value produced by `assign_tier()` — i.e. a non-null `tier` ∈ {A,B,C,D,Unknown} accompanied by a corresponding `unclassified` boolean and (for non-registry sources) `heuristic_flags` array. Sources whose registry lookup falls through to "Unknown" with `unclassified: true` are honest gaps and DO NOT fail this SC; what this SC forbids is (a) agent-asserted tiers without registry/heuristic backing and (b) missing tier fields. Measured by static check across every `output/*.json` after the FR-013a sweep.
- **SC-003**: 100% of URLs reaching the final report pass post-hoc validation, OR the affected fields are explicitly marked as gaps. Zero silent drops.
- **SC-004**: A user can resume an interrupted `/research-deep` run by re-invoking it; the session continues without re-doing completed items.
- **SC-005**: For a hand-curated set of 10 unambiguous topics (5 obviously comparative, 5 obviously narrative), automatic mode detection (FR-004) picks correctly in ≥9 of 10 cases.
- **SC-006**: Against a hand-curated test set of 20 topics — 10 with explicit social signal (consumer products / public figures / events within last 12 months) and 10 without (historical / pure-academic / abstract concepts) — the system activates `/last30days` correctly in ≥16 of 20 (≥80%).
- **SC-007**: After 5+ research sessions with at least 3 user corrections, `/research-consolidate` proposes ≥1 promotable rule that the user approves.
- **SC-008**: A first-time user, given only `CLAUDE.md` and `SPECS.md`, can run a comparative research that passes the US1 Independent Test (`report.md` + `report.csv` with tiered citations) without consulting external docs.

---

## Assumptions

- The user has Claude Code installed and the skill is loaded.
- The user has at least the free-tier `/last30days` configured (Reddit + X via browser cookies + YouTube via yt-dlp + HN). IG/TikTok require user-provided `SCRAPECREATORS_API_KEY` and are opt-in.
- The user is comfortable reading skill output in English.
- A Python 3.10+ environment is available for the helper scripts (URL validation, scoring, consolidation).
- Network access is available; offline operation is out of scope.
- Skill operates per-user, per-machine; multi-user collaboration on the same `tasks/` directory is out of scope for v1.
- `data/source-tiers.yaml` ships with a curated initial list (~50-100 entries covering common academic, press, and aggregator domains); growth happens via consolidation. Seed list MUST cover at minimum: top 20 academic publishers (Nature, Science, Springer, Elsevier, etc.); top 20 reference press (NYT, FT, Bloomberg, Economist, etc.); top 10 known low-quality aggregators / SEO farms.
- `data/mode-detection.yaml` ships with the keyword fast-path list and the LLM-confidence threshold (per FR-004), tunable without code changes.
- `data/publisher-graph.yaml` ships with parent-publisher mappings for the seed `source-tiers.yaml` domains (per FR-015); domains without an entry default to their root domain as parent.
- `data/topic-integrations.yaml` ships with topic-driven integration suggestions (Google Places, GitHub, Semantic Scholar, etc.) keyed by `triggers[]` (per FR-005).
- `data/fallback-extractors.yaml` ships with the FR-028 chain config: Tier 1 (Jina, Exa, Wayback) and Tier 2 (browser controllers in priority order).

---

## Out of Scope (deferred to post-v1)

- Depth modes (quick / deep / exhaustive).
- HTML / PDF outputs.
- Hallucinated-quote detection (verifying citation matches source content beyond URL existence).
- Critique loop / multi-persona red-teaming.
- Multi-language report output (currently English only).
- Automatic consolidation cadence beyond manual or threshold trigger.
- Cross-project learning sharing.
- Extra agent platforms (OpenCode, Codex).
- Production-grade conflict-of-interest detection.

---

<!-- Clarifications log removed — all entries (CL-001/CL-002/CL-003) are recorded in §Clarifications above with full Q→A bullets. No open clarifications remain. -->
