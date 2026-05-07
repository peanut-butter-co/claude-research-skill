# Implementation Plan: research-skill v1

**Created**: 2026-05-07
**Spec**: [`SPECS.md`](./SPECS.md) (post-clarify, post-analyze rd3, post-spec-quality)
**Status**: Draft

## Summary

Implement four Claude Code skills (`/research`, `/research-deep`, `/research-report`, `/research-consolidate`) in this repo as Markdown SKILL.md prompts that orchestrate parallel Task agents and call deterministic Python 3.10+ helper scripts for slug generation, lockfile management, URL validation, source scoring, fallback extraction, and consolidation. State is file-based on disk under `tasks/<case>/` and `learnings/`; no database, no daemon, no persistent server. The skill complements `/last30days` (invoked as a sub-tool when planning marks `social_signal: true`) rather than duplicating its sources.

## Technical Context

- **Language / Version**: Python 3.10+ for `.claude/skills/_lib/scripts/`. SKILL.md prompts are pure Markdown executed by Claude Code's runtime. (Cites SPECS Assumptions §"Python 3.10+ environment is available".)
- **Primary Dependencies**:
  - `requests` — HTTP for URL validation and Tier 1 fallback fetchers (Jina / Exa / Wayback) (FR-011, FR-028).
  - `PyYAML` — read/write all `data/*.yaml` registries and outline/fields/learnings frontmatter (FR-013, FR-015, FR-005, FR-023).
  - `python-frontmatter` — parse frontmatter inside `learnings/*.md` for FR-024 consolidation grouping.
  - `python-slugify` — ASCII-safe slug normalization step inside `scripts/slug.py` (the stop-word filter is hand-rolled per FR-002a; slugify handles unicode→ASCII and whitespace).
  - Stdlib: `csv`, `json`, `os`, `re`, `subprocess`, `pathlib`, `dataclasses`, `unicodedata`.
  - Claude Code runtime tools (no Python wrapper): WebSearch, WebFetch, Task, AskUserQuestion, Bash, Read, Write, Glob (used directly from SKILL.md prompts).
- **Storage**: file-based.
  - YAML for configuration / registries (FR-005, FR-013, FR-015, FR-024) and outlines (Key Entities §`outline.yaml`).
  - JSON for per-agent output (Key Entities §"Item JSON").
  - Markdown for SPECS / PLAN / `search-log.md` / `learnings/*.md` / `report.md`.
  - CSV for comparative reports (FR-018).
  - `.config/research-skill/.env` for credentials, gitignored (FR-005).
- **Testing**: `pytest` 8+. Pure scripts get unit tests under `tests/unit/`. Skill end-to-end flows are validated by fixture-based integration tests (recorded WebSearch/WebFetch JSON responses) under `tests/integration/`. No coverage target gate for v1; coverage measured but not enforced. Live HTTP smoke test only in `tests/smoke/` (manual).
- **Target Platform**: Claude Code (CLI + Desktop + IDE). Skill format: `.claude/skills/<name>/SKILL.md`. Per-skill dependencies declared at the top of each SKILL.md.
- **Project Type**: Claude Code multi-skill (4 sibling skills under one repo) plus shared `.claude/skills/_lib/scripts/` and `.claude/skills/_lib/data/` libraries.
- **Performance Goals**:
  - SC-001: 5-item comparative completes in <15 min wall-clock (assumes WebSearch p95 ≤3s, WebFetch p95 ≤8s, parallelism 5 agents).
  - SC-003: 100% of cited URLs validated post-hoc.
  - SC-005: ≥9/10 mode detection accuracy.
  - Helper scripts MUST complete in <2s on a 100-source case (validation, scoring, consolidation indexing).
- **Constraints**:
  - Single-user, single-machine (SPECS Assumptions §"per-user, per-machine").
  - Network access required (no offline mode in v1).
  - macOS / Linux primary; Windows untested (POSIX `os.kill(pid, 0)` for stale-lock detection — FR-002a).
  - No persistent process; all coordination via files on disk.
- **Scale / Scope**:
  - Comparative: 1–20 items per case; ~10–30 fields per item; ~20–80 sources per item.
  - Narrative: 3–5 subqueries per case; ~30–60 sources per subquery.
  - `data/source-tiers.yaml` seed: 50–100 entries (Assumptions); grows via consolidation.
  - `learnings/`: dozens to low-hundreds of entries over project lifetime.

## Constitution / Project-Rules Check

CLAUDE.md is the constitution-lite. Two binding rules extracted:

| Rule (from CLAUDE.md) | Status | Where this lands in PLAN |
|---|---|---|
| Skill output language: English | ✅ aligned | All SKILL.md prompts, status messages, error strings, report templates, helper-script stdout in English. Spanish project files migrate lazily when touched (per CLAUDE.md). |
| Skill must complement `/last30days`, not be redundant | ✅ aligned | Per FR-008 the orchestrator invokes `/last30days` as a sub-tool when `social_signal: true`. No reimplementation of Reddit/X/YouTube/HN fetching in this repo. |

Plus implicit governance from the spec-kit chain itself:

| Rule | Status | Notes |
|---|---|---|
| No code in PLAN (per `patrones/spec-kit-prompts/plan.md`) | ✅ aligned | This document describes structure and choices; concrete code lives in `.claude/skills/_lib/scripts/` and SKILL.md prompts. |
| PLAN does not modify SPECS | ✅ aligned | All FR/SC references are read-only here. |
| `/research-deep` cannot run without `/research` first (FR-001) | ✅ aligned | Enforced by lockfile + outline.yaml presence check (Architectural Patterns §"Skill orchestration"). |

No violations. **`## Complexity Tracking`** section below remains empty.

## Project Structure

```
research-skill/
├── .claude/
│   └── skills/
│       ├── research/
│       │   └── SKILL.md                  # planning phase orchestrator
│       ├── research-deep/
│       │   └── SKILL.md                  # parallel-agent execution orchestrator
│       ├── research-report/
│       │   └── SKILL.md                  # synthesis + report generator
│       ├── research-consolidate/
│       │   └── SKILL.md                  # learnings consolidation flow
│       └── _lib/                          # skill-internal shared library (not a slash command)
│           ├── data/                      # versioned config registries (travel with the skill)
│           │   ├── source-tiers.yaml      # FR-013 — domain → tier
│           │   ├── publisher-graph.yaml   # FR-015 — domain → parent publisher
│           │   ├── topic-integrations.yaml# FR-005 — topic triggers → integration suggestions
│           │   ├── mode-detection.yaml    # FR-004 — keyword fast-path + LLM threshold
│           │   └── fallback-extractors.yaml# FR-028 — Tier 1 + Tier 2 chain config
│           └── scripts/                   # deterministic Python helpers (travel with the skill)
│               ├── __init__.py
│               ├── slug.py                # FR-002a slug generation
│               ├── lockfile.py            # FR-002a lock + stale detection
│               ├── validate_urls.py       # FR-011 HEAD/GET validator
│               ├── score_source.py        # FR-013/14/15 tiering + numeric score
│               ├── extractors/
│               │   ├── __init__.py
│               │   ├── jina.py            # FR-028 Tier 1a
│               │   ├── exa.py             # FR-028 Tier 1b + WebSearch fallback
│               │   ├── wayback.py         # FR-028 Tier 1c
│               │   └── browser.py         # FR-028 Tier 2 dispatcher
│               ├── search/
│               │   ├── __init__.py
│               │   ├── brave.py           # FR-028 WebSearch fallback
│               │   └── duckduckgo.py      # FR-028 WebSearch fallback (last resort)
│               ├── integrations/          # FR-005 — per-topic integration adapters
│               │   ├── __init__.py
│               │   └── base.py            # uniform interface
│               ├── mode_detect.py         # FR-004 keyword fast-path
│               ├── status.py              # FR-033 streaming status emitter
│               ├── learnings_index.py     # FR-024 consolidation index/grouping
│               ├── build_report.py        # FR-017/18 markdown + CSV emitter
│               └── env.py                 # .config/research-skill/.env loader
├── tests/
│   ├── unit/                              # one file per scripts/* module
│   ├── integration/                       # fixture-based skill flows
│   ├── fixtures/
│   │   ├── search_responses/
│   │   ├── fetch_responses/
│   │   └── outlines/
│   └── smoke/                             # manual live-network tests
├── docs/patrones/                         # already-written process docs (read-only by skill at runtime)
│   ├── pre-research-planning.md
│   └── spec-kit-prompts/
├── learnings/                             # runtime-populated, gitignored content but path tracked
│   └── .gitkeep
├── tasks/                                 # runtime-populated, gitignored
│   └── .gitkeep
├── .config/
│   └── research-skill/
│       └── preferences.yaml               # FR-005 "never suggest" prefs (gitignored)
├── pyproject.toml                         # package metadata + pytest config + pinned deps
├── .gitignore                             # excludes tasks/, learnings/*.md, .config/.env, .lock files
├── CLAUDE.md
├── SPECS.md
├── PLAN.md                                # this file
├── RESEARCH.md
└── README.md                              # operator quickstart (regenerated from §Quickstart)
```

Annotations:
- `.claude/skills/<name>/SKILL.md` is the skill prompt; one prompt per slash command.
- `data/` is the durable, version-controlled knowledge that consolidation promotes into.
- `scripts/` is the deterministic, unit-tested code layer the SKILL.md prompts call via `Bash`.
- `tasks/` and `learnings/` are runtime artifacts; tracked via `.gitkeep` only.
- `.config/research-skill/` lives at repo root for v1 (single-user, single-machine assumption); operator may symlink to `~/.config/research-skill/` if preferred.

## Architectural Patterns

### Pattern 1: SKILL.md as the LLM-driven orchestrator; `scripts/` as the deterministic substrate
Logic that requires judgment (mode detection LLM fallback, planning Q&A, agent prompts, intermediate synthesis, hint cross-pollination, user-facing AskUserQuestion choices, learning capture decisions) lives in SKILL.md prompts. Logic that is purely mechanical (slug generation, lockfile read/write, HEAD/GET validation, tier lookup, score arithmetic, Tier 1 extractor calls, CSV emission) lives in `scripts/` as Python functions invoked from SKILL.md via `Bash`.

**Rationale**: scripts are unit-testable and deterministic; SKILL.md handles ambiguity. Split is along the determinism axis, not arbitrary.
**Alternative rejected**: putting tier lookup or slug generation inside SKILL.md as inline LLM reasoning — non-deterministic, harder to evolve `data/*.yaml` registries without prompt churn.

### Pattern 2: File-based orchestrator ↔ agent coordination
The `/research-deep` orchestrator passes per-agent prompts (containing item, fields, mandatory sources, query_budget, hints_received) and reads each agent's JSON back from `tasks/<case>/output/<agent_id>.json`. No env-var passing, no shared memory, no IPC. Round boundaries are detected by all agents having flushed their round-N JSON. FR-031 hints flow as text appended into the next-round agent prompt.

**Rationale**: Task agents are isolated by Claude Code's runtime; durable JSON satisfies FR-033a (incremental persistence) and FR-010 (resume); same artifact serves observability and resume.
**Alternative rejected**: in-memory message bus or stdout-only IPC — ephemeral, breaks resume, not visible to user tailing the directory.

### Pattern 3: Three-level mid-flight adaptation, in three different mechanisms
- **Level 1 (FR-029, auto-adapt within agent)**: pure agent autonomy inside SKILL.md prompt; budget bookkeeping in agent JSON; no orchestrator round-trip.
- **Level 2 (FR-026 / FR-030, pause-and-confirm)**: orchestrator detects strategic triggers, calls AskUserQuestion, persists decision in `search-log.md`, then resumes. Mid-round triggers (scope invalidation, terminology shift, systemic tool failure) interrupt; end-of-round triggers (FR-030 emergent extensions) are batched and surfaced after FR-031 synthesis.
- **Level 3 (FR-032, hard-stop)**: agent self-enforces budget cap; emits `budget_exhausted: true` to JSON; orchestrator surfaces before final report.

**Rationale**: aligns each adaptation level with the right place in the call graph — autonomous → in-agent prompt; collaborative → orchestrator AskUserQuestion; bounded → agent self-check.
**Alternative rejected**: a single mid-flight gate at the orchestrator level for all three — would force every reformulation through the orchestrator, killing parallelism and adding chatter.

### Pattern 4: Error handling — exceptions in `scripts/`, structured failure in agent JSON
Python `scripts/` raise exceptions for unexpected failures (missing YAML, malformed input). Expected failures (URL broken, fetch declined, integration unavailable, tool tier exhausted) return structured dicts (`{ok: bool, value?, error?}`) that agents include in their JSON output (`extraction_failed`, `fetch_method`, `pruned`, `budget_exhausted`).

**Rationale**: SKILL.md prompts are not the place to handle exception traces; clean dict contracts let prompts branch on `ok` without parsing tracebacks. Helper scripts use exceptions for real bugs.
**Alternative rejected**: a Result/Option type via a dependency (e.g. `result` lib) — gain not worth the dep; dicts are flat, JSON-serializable, and prompt-friendly.

### Pattern 5: Status streaming via prefixed stdout lines (FR-033b)
The orchestrator emits structured status lines to stdout, prefixed by `[orchestrator]`, `[agent:<id>]`, `[milestone:<event>]`. Lines are plain text, machine-parseable but human-readable. Optional `--json` flag (post-MVP) emits NDJSON for tooling. No external logger.

**Rationale**: simplest mechanism that meets FR-033 ephemeral signal; complements durable JSON output. No log aggregation infrastructure to set up.
**Alternative rejected**: Python `logging` configured globally — overkill for a CLI; mixes script-internal warnings with user-visible status.

### Pattern 6: External-service abstraction via per-service adapters with a shared interface
Each Tier 1 extractor (Jina, Exa, Wayback) and each search fallback (Brave, Exa, DuckDuckGo) and each topic integration is a Python module under `scripts/extractors/`, `scripts/search/`, or `scripts/integrations/` exposing a uniform interface (`fetch(url) -> Result` for extractors; `search(query) -> list[Result]` for search; `enrich(query) -> list[Source]` for integrations). FR-028 Tier 2 (browser MCP / Claude extension) is dispatched via `scripts/extractors/browser.py` which detects availability at runtime (env vars, MCP listing) and routes accordingly.

**Rationale**: catalog grows incrementally (FR-005, FR-024 promotion path); uniform interface lets the orchestrator try fallbacks in a flat loop without per-service branching in the prompt.
**Alternative rejected**: a single monolithic `external_apis.py` — couples unrelated services and breaks down once one needs more arguments than another.

### Pattern 7: Data validation — schema-light, hand-rolled
Each YAML registry has a documented shape (in `data/<file>.yaml` header comments). `scripts/` modules validate the fields they consume on load and raise on missing required keys. No Pydantic, no JSON Schema runtime, no Marshmallow.

**Rationale**: data files are small, evolved manually, and live in version control where review catches schema drift. Adding Pydantic for 5 small YAMLs is more abstraction than the data demands.
**Alternative rejected**: Pydantic models per registry — clean, but the cost (model code + version-coupled migrations) outweighs the value at this scale.

### Pattern 8: Lockfile concurrency control (FR-002a)
`tasks/<case>/.lock` is a plain text file with two lines: `pid=<pid>` and `start=<ISO8601>`. `scripts/lockfile.py` exposes `acquire(case_path)`, `release(case_path)`, `check_stale(case_path, ttl_seconds=3600)`. Stale detection uses POSIX `os.kill(pid, 0)`; if a stable PID is unavailable in the runtime, the lockfile substitutes the Claude Code session ID or invocation timestamp (per FR-002a) and stale detection degrades to age-only with a warning emitted via `scripts/status.py`. On Windows the same age-only fallback applies.

**Rationale**: no extra dep; readable by hand; survives orphaned processes.
**Alternative rejected**: SQLite lock or `fcntl.flock` — opaque to users, doesn't survive process death cleanly.

### Pattern 9: `/last30days` invocation via Bash slash-command runner (FR-008)
The agent prompt instructs the model to invoke `claude /last30days "<topic>"` via Bash if the runner is available; otherwise it routes through the runtime's native skill-invocation path (the agent calls the skill as a tool). Output is parsed back as text and tagged Tier C per FR-013. Failure modes are handled per FR-008 (log + proceed without).

**Rationale**: cross-skill calling without coupling to `/last30days`'s internal API; matches the heterogeneity of Claude Code runtimes.
**Alternative rejected**: importing `/last30days`'s internals — out of scope, brittle, and breaks the "complement, not duplicate" rule.

### Pattern 10: Test isolation — recorded fixtures for integration, no live HTTP in CI
Integration tests under `tests/integration/` use canned WebSearch/WebFetch responses stored as JSON under `tests/fixtures/`. Live network is exercised only by `tests/smoke/`, run manually. Unit tests under `tests/unit/` use neither network nor filesystem beyond `tmp_path`.

**Rationale**: deterministic CI; cheap to run; honest reproduction of edge cases.
**Alternative rejected**: VCR-style cassettes — usable but adds a dep and re-recording flow; flat JSON fixtures are sufficient.

## Data Model

SPECS §Key Entities defines five primary shapes. PLAN expands with concrete storage, paths, validation, and lifecycle.

### `outline.yaml`
- **Format**: YAML.
- **Path**: `tasks/<case>/outline.yaml` (one per case).
- **Schema**: see SPECS §Key Entities (comparative + narrative shapes). Required fields validated by `/research` SKILL.md before writing; missing required keys → fail with explicit message.
- **Validation rules**: `mode ∈ {comparative, narrative}`; `rigor ∈ {standard, rigorous}` default `standard`; `query_budget` integer ≥ 5 if set; `max_emergent_threads` integer ≥ 0 default 2; `extension_budget` integer ≥ 0; `topic_integrations[]` entries must reference an `id` present in `data/topic-integrations.yaml`.
- **Lifecycle**: created by `/research` (after user confirmation FR-006); read by `/research-deep` (orchestrator + each agent's prompt context); read by `/research-report`; never modified after creation (strategic FR-026/FR-030 changes are appended to `search-log.md`, not back-edited into outline.yaml — per Pattern 2).

### `fields.yaml` (comparative only)
- **Format**: YAML.
- **Path**: `tasks/<case>/fields.yaml`.
- **Schema**: see SPECS §Key Entities. `categories` is `dict[str, list[str]]`; `detail ∈ {brief, moderate, detailed}`.
- **Validation rules**: at least one category with at least one field; `detail` required.
- **Lifecycle**: created by `/research`; read by each `/research-deep` agent and by `/research-report` for CSV column ordering.

### Item JSON (per-item or per-subquery output)
- **Format**: JSON.
- **Path**: `tasks/<case>/output/<agent_id>.json`. `<agent_id>` = the slug-form of the item or subquery (same slug rule as FR-002a applied to the item/subquery string).
- **Schema**: see SPECS §Key Entities (including `pruned`, `emergent_threads_chased[]`, `proposed_extensions[]`, `budget_consumed`, `budget_exhausted`, `_meta.hints_received[]`, `fetch_method`).
- **Validation rules**: `sources[].tier ∈ {A, B, C, D, Unknown}`; `fetch_method ∈ {webfetch, jina, exa, wayback, browser-ext, chrome-mcp, playwright-mcp}`; `budget_consumed ≤ outline.config.query_budget`.
- **Lifecycle**:
  - Created by the agent at first round-end flush (per FR-033a).
  - Updated at every round boundary (incremental persistence).
  - Final-state on agent completion (`pruned: true` OR `budget_exhausted: true` OR all fields filled).
  - Read by orchestrator (FR-031 synthesis), by `/research-report` (synthesis + URL validation pass), and by `/research-deep` resume logic (FR-010).
  - Never deleted by the skill; user may rm to force re-run.

### `search-log.md`
- **Format**: Markdown with per-session sections.
- **Path**: `tasks/<case>/search-log.md`.
- **Schema** (per session block):
  ```
  ## Session YYYY-MM-DD HH:MM (<line>)
  ### 7 Pre-research decisions
  1. Information profile: ...
  2. Search dimensions: ...
  ...
  ### Suggested integrations
  ### Strategic adaptations
  - [FR-026] <trigger> @ <ts> → <user choice>
  - [FR-030] <proposal> → <accept|note|discard>
  ### Queries executed
  - <ts> <query> → <result count>
  ### Gaps detected
  ```
- **Validation rules**: human-readable; no machine validation in v1 beyond presence-of-file check by `/research-deep`.
- **Lifecycle**: created by `/research` first invocation; appended by every subsequent `/research`, `/research-deep`, `/research-report` invocation on the same case (per FR-003 continuation logic).

### Learning entry
- **Format**: Markdown with YAML frontmatter.
- **Path**: `learnings/YYYY-MM-DD-NNN-<short-slug>.md`.
- **Schema** (frontmatter):
  ```yaml
  ---
  id: 2026-05-07-001
  date: 2026-05-07
  trigger: user-feedback | self-detection | session-close
  context: "<command + topic>"
  type: source-classification | query-strategy | tool-behavior | domain-fact | scoring-rule | process-improvement | pattern-validation
  status: pending | consolidated | discarded
  ---
  ```
- **Schema** (body): 1-3 sentences narrative, then `**Suggested rule**: <rule>`.
- **Validation rules**: frontmatter keys required: id, date, trigger, type, status. `type` ∈ FR-023 enumerated values. `status` ∈ {pending, consolidated, discarded}.
- **Lifecycle**:
  - Created by agents (FR-012 self-detection), by `/research-report` (FR-022 end-of-session prompt), by detection during any `/research-*` invocation (FR-021 user-feedback signals).
  - Updated by `/research-consolidate` on user approval — sets `status` to `consolidated` or `discarded` in-place (FR-024).
  - Never deleted; discarded entries kept for history.

### Registry files (`data/*.yaml`)
- **Format**: YAML.
- **Path**: `data/`.
- **Schemas**: documented in each file's header comment.
  - `source-tiers.yaml`: `domain → tier` (`{domain: {tier: A|B|C|D, notes?: str}}`). Seed list per Assumptions.
  - `publisher-graph.yaml`: `domain → parent_publisher` (`{domain: parent_root}`). Default to root if absent.
  - `topic-integrations.yaml`: `id → {triggers: [regex|tag], description, setup_url, adapter_module}`.
  - `mode-detection.yaml`: `{keywords: [regex], threshold: float, prompt: str}`.
  - `fallback-extractors.yaml`: `{tier1: [{name, module, requires_env?}], tier2: [{name, kind: ext|mcp, detect}]}`.
- **Lifecycle**:
  - Created at project init (seed); version-controlled.
  - Read by `scripts/score_source.py`, `scripts/extractors/*`, `scripts/search/*`, `scripts/mode_detect.py`, `scripts/integrations/*`.
  - Updated by `/research-consolidate` (FR-024) on user approval — direct in-place edits with provenance comments referencing the source learning's `id`.

### `preferences.yaml`
- **Format**: YAML.
- **Path**: `.config/research-skill/preferences.yaml`.
- **Schema**: `{never_suggest: [{signature: list[str], integration_id: str, recorded_at: ISO8601}]}`. `signature` = topic-type signature per FR-005 (sorted tuple of matched `topic-integrations.yaml` ids ∪ inferred entity-type tags).
- **Validation rules**: `signature` non-empty list of strings; `integration_id` MUST reference a known entry in `data/topic-integrations.yaml`; `recorded_at` ISO 8601.
- **Lifecycle**: created on first "never suggest" selection in `/research`; appended on each subsequent never; read by `/research` planning before showing integration suggestions; never auto-deleted (operator may rm to reset).

## Contracts

The skill consumes external services but does not expose any of its own. Per FR-028 and FR-005, contracts to document for v1:

### Tier 1 extractors (FR-028)
| Service | Method | Auth | Failure modes |
|---|---|---|---|
| Jina AI Reader | `GET https://r.jina.ai/<url>` | none | non-2xx, empty body, rate limit |
| Exa.ai `/contents` | `POST https://api.exa.ai/contents` | `EXA_API_KEY` env | 401, 429, missing key → tier skipped silently |
| Wayback Machine | `GET https://archive.org/wayback/available?url=<url>` then `GET <closest_snapshot>` | none | no snapshot, 5xx |

### WebSearch fallbacks (FR-028)
| Service | Method | Auth | Failure modes |
|---|---|---|---|
| Brave Search | `GET https://api.search.brave.com/res/v1/web/search` | `BRAVE_API_KEY` env | 401, 429 |
| Exa search | `POST https://api.exa.ai/search` | `EXA_API_KEY` env | 401, 429 |
| DuckDuckGo HTML | `GET https://duckduckgo.com/html/?q=<q>` | none | layout drift, 5xx |

### `/last30days` invocation (FR-008)
- Mechanism: `claude /last30days "<topic>"` via Bash; output captured as text. Failure: nonzero exit OR Bash unavailable → log and proceed (FR-008 + Edge Case "/last30days not configured").

### Browser controllers (FR-028 Tier 2)
- Detection-only contracts. `scripts/extractors/browser.py` checks: (a) Claude Chrome Extension presence (env signal TBD by runtime), (b) `chrome-devtools` MCP listed in available MCP servers, (c) `playwright` MCP listed. Invocation is delegated to the LLM via SKILL.md tool calls; the script only returns which path is available.

### Topic integrations (FR-005)
Per-integration adapter contracts will be defined as adapters are added; v1 ships scaffold (`base.py`) + zero concrete adapters. The first concrete adapter (Google Places, per US4) lands as a follow-up.

No outbound HTTP from helper scripts crosses authenticated boundaries beyond what the user supplies via `.config/research-skill/.env`.

## Quickstart

From a clean clone:

```bash
# 1. Python environment
python3.10 -m venv .venv
source .venv/bin/activate
pip install -e .

# 2. Optional credentials (any subset; skill degrades gracefully)
mkdir -p .config/research-skill
cat > .config/research-skill/.env <<'EOF'
# EXA_API_KEY=...
# BRAVE_API_KEY=...
EOF

# 3. Install skill into Claude Code (symlink the .claude/skills/* into the user's skills dir)
# Claude Code picks up .claude/skills automatically when this repo is the working directory.

# 4. Smoke test (no live network)
pytest tests/unit -q
pytest tests/integration -q

# 5. First research run (live)
claude
> /research "compare jest, vitest, and playwright on speed and DX"
# follow the planning Q&A; confirm; then:
> /research-deep
> /research-report
```

Smoke success criteria:
- Unit tests green.
- Integration tests green using fixtures.
- A live `/research` produces `tasks/compare-jest-vitest-playwright-speed-dx/outline.yaml` and `search-log.md`.

## Complexity Tracking

| Violated principle | Why needed | Simpler alternative rejected (and why) |
|---|---|---|
| _none_ | _none_ | _none_ |

Constitution gate (both passes) is clean.

## Research Decisions

Phase 0 decisions made during PLAN drafting:

- **Decision**: Python 3.10+ with `requests` + `PyYAML` + `python-frontmatter` + `python-slugify`; no Pydantic, no async runtime.
  **Rationale**: SPECS Assumptions pin Python 3.10+. Sync HTTP is sufficient — parallelism comes from Task agents, not from intra-script async. Minimal deps reduce supply-chain surface.
  **Alternatives considered**: (a) `httpx` async client — rejected, no parallelism need at script level. (b) Pydantic for YAML schemas — rejected, scale doesn't justify dep. (c) full stdlib (no `requests`) — rejected, costs more code than it saves.

- **Decision**: SKILL.md (LLM prompt) hosts judgment logic; `scripts/` holds deterministic logic.
  **Rationale**: Per Pattern 1; aligns with FR-013/14/15 (deterministic scoring) vs FR-031 (LLM-driven synthesis with hint generation).
  **Alternatives considered**: (a) all logic in SKILL.md — non-deterministic registry lookups. (b) all logic in scripts — kills the ergonomics of LLM-driven planning Q&A.

- **Decision**: File-based coordination between orchestrator and parallel Task agents; per-agent JSON in `tasks/<case>/output/`.
  **Rationale**: Matches FR-033a (incremental persistence) and FR-010 (resume); avoids ephemeral IPC.
  **Alternatives considered**: in-memory message bus, env-var passing — both break resume and observability.

- **Decision**: Three-level adaptation lives in three different layers (agent prompt / orchestrator / agent self-check) per Pattern 3.
  **Rationale**: Each level matches the autonomy boundary; merging them would funnel everything through orchestrator and serialize parallel work.
  **Alternatives considered**: single mid-flight gate — rejected as serialization risk.

- **Decision**: Plain-text lockfile with PID + ISO timestamp; POSIX-only stale detection; Windows degrades to age-only.
  **Rationale**: Per FR-002a (PID best-effort, age fallback acceptable). Matches Pattern 8.
  **Alternatives considered**: `fcntl.flock` — Windows-incompatible. SQLite — opaque, heavier than the problem.

- **Decision**: Per-service adapter modules in `scripts/extractors/`, `scripts/search/`, `scripts/integrations/` with a uniform `fetch/search/enrich` interface.
  **Rationale**: FR-005 catalog grows by consolidation; uniform interface keeps SKILL.md fallback loop flat.
  **Alternatives considered**: monolithic `external_apis.py` — couples unrelated services.

- **Decision**: Schema-light hand-rolled YAML validation (no Pydantic / JSON Schema runtime).
  **Rationale**: Pattern 7. Five small registries; reviewed in version control.
  **Alternatives considered**: Pydantic models — overkill for current scale.

- **Decision**: pytest 8 with fixture-based integration; no live HTTP in CI; manual smoke tier only.
  **Rationale**: Determinism beats freshness in CI; live tier exists for honesty.
  **Alternatives considered**: VCR cassettes — extra dep + re-record flow.

- **Decision**: Status streaming via prefixed plain-text stdout lines (`[orchestrator]`, `[agent:<id>]`, `[milestone:<event>]`); JSON mode deferred post-MVP.
  **Rationale**: FR-033b minimum bar; lets users tail the directory + read stdout simultaneously.
  **Alternatives considered**: Python `logging` — heavier; structured JSON event log — useful but premature.

- **Decision**: `.config/research-skill/` lives at repo root for v1 (single-user, single-machine).
  **Rationale**: Matches SPECS Assumptions §"per-user, per-machine"; keeps the file under version-control's eye via `.gitignore` rules rather than home-dir invisibility.
  **Alternatives considered**: `~/.config/research-skill/` — viable; operator may symlink. Defer the system-wide path until v2.
