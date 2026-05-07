# Tasks: research-skill v1

**Created**: 2026-05-07
**Plan**: [`PLAN.md`](./PLAN.md)
**Spec**: [`SPECS.md`](./SPECS.md)
**Status**: Draft

> Phase ordering is strict: each phase must complete before the next can start (see Checkpoints). Tasks marked `[P]` touch files disjoint from other unblocked tasks in their phase and may run in parallel. Tasks marked `[USx]` belong to the user-story phase for User Story x.

---

## Phase 1: Setup

- [X] T001 [P] Initialize repo skeleton — directories `.claude/skills/{research,research-deep,research-report,research-consolidate}/`, `data/`, `scripts/{extractors,search,integrations}/`, `tests/{unit,integration,fixtures,smoke}/`, `learnings/`, `tasks/`, `.config/research-skill/` — touches: directory tree
- [X] T002 [P] Project metadata + dependencies (Python 3.10+, requests, PyYAML, python-frontmatter, python-slugify, pytest 8) and pytest config — touches: `pyproject.toml`
- [X] T003 [P] `.gitignore` covering runtime artifacts — `tasks/`, `learnings/*.md` (keep `.gitkeep`), `.config/research-skill/.env`, `*.lock`, `.venv/`, `__pycache__/`, `*.pyc` — touches: `.gitignore`
- [X] T004 [P] Seed `data/source-tiers.yaml` with curated 50–100 entries (top 20 academic publishers, top 20 reference press, top 10 known low-quality aggregators) per SPECS Assumptions — touches: `data/source-tiers.yaml`
- [X] T005 [P] Seed `data/publisher-graph.yaml` with parent-publisher mappings for the seed source-tiers domains (FR-015) — touches: `data/publisher-graph.yaml`
- [X] T006 [P] Seed `data/topic-integrations.yaml` catalog (Google Places, GitHub, Semantic Scholar, Apify, Crunchbase, Exa, Perplexity, etc.) keyed by `triggers[]` (FR-005) — touches: `data/topic-integrations.yaml`
- [X] T007 [P] Seed `data/mode-detection.yaml` with keyword fast-path list, LLM threshold 0.75, and classification prompt (FR-004) — touches: `data/mode-detection.yaml`
- [X] T008 [P] Seed `data/fallback-extractors.yaml` with Tier 1 (jina/exa/wayback) and Tier 2 (browser-ext/chrome-mcp/playwright-mcp) chain config (FR-028) — touches: `data/fallback-extractors.yaml`
- [X] T009 [P] `.gitkeep` stubs for runtime-populated directories — touches: `learnings/.gitkeep`, `tasks/.gitkeep`

---

## Phase 2: Foundational

> Hard gate. No User Story phase may start until every task here is `[X]`.

### Helper modules (one task per `scripts/` module)

- [X] T010 [P] `.env` loader for `.config/research-skill/.env` (FR-005 credentials path) — touches: `scripts/env.py`
- [X] T011 [P] Slug generation per FR-002a (lower → strip punctuation → drop English stop words → hyphenate → ASCII-only → 60-char cap without word splits) — touches: `scripts/slug.py`
- [X] T012 [P] Lockfile acquire/release/check_stale (FR-002a) with PID + ISO start, POSIX `os.kill(pid, 0)` stale detection, age-only fallback on Windows or missing PID — touches: `scripts/lockfile.py`
- [X] T013 [P] Post-hoc URL validator HEAD then GET fallback (FR-011) — touches: `scripts/validate_urls.py`
- [X] T014 [P] Source scoring engine: `data/source-tiers.yaml` lookup + Unknown heuristics (DOI/ISBN, suffix, suspicious patterns per FR-014) + numeric score (FR-015) + cross-citation independence by parent publisher via `data/publisher-graph.yaml` — touches: `scripts/score_source.py`
- [X] T015 [P] Mode detection keyword fast-path (FR-004 path a) reading regexes from `data/mode-detection.yaml` — touches: `scripts/mode_detect.py`
- [X] T016 [P] Status streaming emitter with `[orchestrator]` / `[agent:<id>]` / `[milestone:<event>]` prefixes (FR-033b) — touches: `scripts/status.py`
- [X] T017 [P] Tier 1 extractor: Jina AI Reader (FR-028) — touches: `scripts/extractors/jina.py`
- [X] T018 [P] Tier 1 extractor: Exa.ai `/contents` (FR-028) — touches: `scripts/extractors/exa.py`
- [X] T019 [P] Tier 1 extractor: Wayback Machine (FR-028) — touches: `scripts/extractors/wayback.py`
- [X] T020 [P] Tier 2 dispatcher: detect Claude Chrome Extension / chrome-devtools MCP / Playwright MCP availability and route per priority order from `data/fallback-extractors.yaml` (FR-028) — touches: `scripts/extractors/browser.py`
- [X] T021 [P] WebSearch fallback: Brave Search API (FR-028 search chain) — touches: `scripts/search/brave.py`
- [X] T022 [P] WebSearch fallback: DuckDuckGo HTML scraper (FR-028 search chain last resort) — touches: `scripts/search/duckduckgo.py`
- [X] T023 [P] WebSearch fallback: Exa search endpoint (FR-028 search chain) — touches: `scripts/search/exa.py`
- [X] T024 [P] Integration adapter base class with uniform `enrich(query) -> list[Source]` interface (FR-005 catalog scaffold) — touches: `scripts/integrations/base.py`
- [X] T025 [P] Learnings index: read frontmatter + group by `type` and `status` for consolidation (FR-024) — touches: `scripts/learnings_index.py`
- [X] T026 [P] Learnings writer: emit `learnings/YYYY-MM-DD-NNN-<slug>.md` with frontmatter (FR-023) — touches: `scripts/learnings_write.py`
- [X] T027 [P] Preferences read/write helper for `.config/research-skill/preferences.yaml` (FR-005 never-suggest persistence) — touches: `scripts/preferences.py`
- [X] T028 [P] Report builder: markdown TOC + comparison table + per-item sections (comparative) / essay-by-subquery + Cross-cutting findings (narrative) + tiered inline citations + Disagreements subsection + Sources note + Extraction failures + Unclassified domains; CSV emission (FR-017/017a/018/019/020) — touches: `scripts/build_report.py`

### Unit tests (one task per scripts module; all parallel with each other)

- [X] T029 [P] Unit tests for env loader — touches: `tests/unit/test_env.py`
- [X] T030 [P] Unit tests for slug generator (stop-word drop, ASCII fold, 60-char no-split, worked example from FR-002a) — touches: `tests/unit/test_slug.py`
- [X] T031 [P] Unit tests for lockfile acquire/release + stale detection + age fallback — touches: `tests/unit/test_lockfile.py`
- [X] T032 [P] Unit tests for URL validator (HEAD success, HEAD-fails-GET-succeeds, both fail) — touches: `tests/unit/test_validate_urls.py`
- [X] T033 [P] Unit tests for scoring engine (tier_weight, recency_bonus, cross-citation by parent publisher per FR-015, suspicious patterns per FR-014, tie-break order) — touches: `tests/unit/test_score_source.py`
- [X] T034 [P] Unit tests for mode-detection keyword fast-path (positive + negative + boundary cases) — touches: `tests/unit/test_mode_detect.py`
- [X] T035 [P] Unit tests for status emitter (prefix, milestone names, agent identification) — touches: `tests/unit/test_status.py`
- [X] T036 [P] Unit tests for Tier 1 extractors + Tier 2 dispatcher (mocked HTTP, fallback ordering) — touches: `tests/unit/test_extractors.py`
- [X] T037 [P] Unit tests for search fallbacks (Brave / DuckDuckGo / Exa with mocked responses) — touches: `tests/unit/test_search.py`
- [X] T038 [P] Unit tests for learnings index + writer (frontmatter round-trip, status filter, in-place update) — touches: `tests/unit/test_learnings.py`
- [X] T039 [P] Unit tests for preferences read/write (never-suggest key persistence) — touches: `tests/unit/test_preferences.py`
- [X] T040 [P] Unit tests for report builder (comparative md+csv, narrative md, gap markers, Disagreements, Sources note grouping) — touches: `tests/unit/test_build_report.py`

### Checkpoint: end of Phase 2

Gate: all of T001..T040 are `[X]`. No `[USx]`-tagged task may start until this passes. Run `pytest tests/unit -q` — must be green.

---

## Phase 3: User Story 1 — Comparative research with scored sources [US1] (MVP)

> Independent Test (from SPECS §US1): from scratch, run `/research "compare 5 JS testing frameworks"`. Must produce `report.md` with comparison table, `report.csv` with one row per item, and inline citations tagged with their tier.

- [X] T050 [P] [US1] `/research` planning skill — comparative path: 7 pre-research decisions, slug+lockfile via FR-002a, mode detect (FR-004 hybrid: keyword fast-path then LLM with 0.75 threshold), `social_signal` heuristic + override (FR-006), rigor + query_budget override (FR-006/032), Tier-D inclusion prompt when topic signals predominantly C/D (FR-016a), integration suggestion 3-option modal (FR-005), AskUserQuestion confirmation gate (FR-006), persist `outline.yaml` + `fields.yaml` + `search-log.md`, FR-021 user-feedback detection during planning Q&A — touches: `.claude/skills/research/SKILL.md`
- [X] T051 [P] [US1] `/research-deep` orchestrator + comparative agent prompts — parallel Task spawn per item per `items_per_batch` (FR-007); per-agent: WebSearch + WebFetch + `/last30days` invocation when `social_signal: true` via Bash slash-command runner (FR-008); JSON shape with sources/uncertain/_meta (FR-009); resume-skip rule for complete JSONs (FR-010); URL post-hoc validator pass (FR-011); self-detected anomalies → learnings via FR-012; tier assignment + numeric scoring application (FR-013/014/015) and Tier-D filter (FR-016); Level 2 strategic mid-flight gate (FR-026 mid-round + end-of-round triggers); FR-027 stop criterion + numeric thresholds; FR-028 fallback chain (Tier 1 then Tier 2) with `fetch_method` recorded; Level 1 auto-adapt (FR-029 a–d) with `emergent_threads_chased[]`, `proposed_extensions[]`, `pruned`; FR-030 emergent-extension surfacing after first round with extension_budget; FR-031 intermediate synthesis + cross-pollination via `_meta.hints_received[]`; FR-032 budget cap + 80% warning + hard-stop; FR-033b status streaming + FR-033a incremental persistence — touches: `.claude/skills/research-deep/SKILL.md`
- [X] T052 [P] [US1] `/research-report` synthesis — comparative path: TOC + comparison table at top, per-item sections, inline citations `[Source • Tier B]`, Disagreements subsection (FR-017a Tier-A; FR-015 tie-break extension to all tiers), Sources note grouped by tier + Unclassified domains (FR-013), Extraction failures section (FR-028), `report.csv` per `fields.yaml` columns (FR-018), `[uncertain]` field markers + gaps list (FR-019), claim-citation validation + visible gap markers (FR-020) — touches: `.claude/skills/research-report/SKILL.md`
- [X] T053 [P] [US1] Integration test — comparative end-to-end with fixtures, asserts US1 Acceptance Scenarios 1-4 (planning artifacts written; one parallel agent per item with tiered sources; report.md+report.csv with table+citations+Sources note; broken URL → visible gap, never silenced) — touches: `tests/integration/test_us1_comparative.py`
- [X] T054 [P] [US1] Test fixtures for US1 — 5-item JS testing frameworks outline + canned WebSearch + WebFetch responses + `/last30days` stub output covering Tier A/B/C distribution — touches: `tests/fixtures/outlines/jest_vitest_playwright.yaml`, `tests/fixtures/search_responses/us1_*.json`, `tests/fixtures/fetch_responses/us1_*.json`, `tests/fixtures/last30days/us1_*.txt`

### Checkpoint: end of Phase 3 (MVP)

Gate: all T050..T054 are `[X]`. The Independent Test from SPECS §US1 passes end-to-end. **This is the MVP shippable point** — phases 4–7 are additive value.

---

## Phase 4: User Story 2 — Narrative research on an open question [US2]

> Independent Test (from SPECS §US2): run `/research "what impact does the EU AI Act have on SaaS startups under 50 employees"`. Must produce `report.md` with sub-essays per subquery and a "Cross-cutting findings" section, with inline citations.

- [X] T060 [P] [US2] `/research` planning skill — narrative path: subqueries derivation (3–5), `mode: narrative` outline shape, narrative-specific Acceptance Scenario 1 (FR-006 confirmation reused) — touches: `.claude/skills/research/SKILL.md` (cross-phase sequential after T050)
- [X] T061 [P] [US2] `/research-deep` narrative agent prompts — one agent per subquery (FR-007 narrative path), evidence-backed JSON with scored sources, FR-031 cross-pollination across subqueries — touches: `.claude/skills/research-deep/SKILL.md` (cross-phase sequential after T051)
- [X] T062 [P] [US2] `/research-report` narrative path — essay-by-subquery + "Cross-cutting findings" synthesizing across subqueries, inline tiered citations + Sources note (FR-017 narrative shape) — touches: `.claude/skills/research-report/SKILL.md` (cross-phase sequential after T052)
- [X] T063 [P] [US2] Integration test — narrative end-to-end with fixtures, asserts US2 Acceptance Scenarios 1-3 — touches: `tests/integration/test_us2_narrative.py`
- [X] T064 [P] [US2] Test fixtures for US2 — EU AI Act narrative outline + canned search/fetch responses — touches: `tests/fixtures/outlines/eu_ai_act.yaml`, `tests/fixtures/search_responses/us2_*.json`, `tests/fixtures/fetch_responses/us2_*.json`

### Checkpoint: end of Phase 4

Gate: all T060..T064 are `[X]`. Independent Test from SPECS §US2 passes end-to-end.

---

## Phase 5: User Story 3 — Self-learning capture and consolidation [US3]

> Independent Test (from SPECS §US3): during a session the user corrects a tier classification; skill must offer to log it; `/research-consolidate` must later propose promoting that learning to `data/source-tiers.yaml`.

- [X] T070 [P] [US3] `/research-consolidate` skill — read pending learnings, group by type, propose promotions to `data/source-tiers.yaml` / `data/topic-integrations.yaml` / `data/publisher-graph.yaml` / `data/mode-detection.yaml` / `data/fallback-extractors.yaml` / `CLAUDE.md` / `SKILL.md` / discard, write target file + update source learning's `status` in-place (FR-024), trigger conditions (manual / 10+ pending / 24h + 7d-old) per FR-025 — touches: `.claude/skills/research-consolidate/SKILL.md`
- [X] T071 [P] [US3] Wire FR-021 user-feedback detection to learnings writer in `/research` and `/research-deep` — touches: `.claude/skills/research/SKILL.md`, `.claude/skills/research-deep/SKILL.md` (cross-phase sequential after T050/T051/T060/T061)
- [X] T072 [P] [US3] FR-022 end-of-session prompt + FR-025 auto-prompt at `/research-report` close ("Anything from this session worth logging?" + threshold-based consolidation prompt) — touches: `.claude/skills/research-report/SKILL.md` (cross-phase sequential after T052/T062)
- [X] T073 [P] [US3] Integration test — tier correction during session → learning entry written → `/research-consolidate` proposes promotion → user approves → `data/source-tiers.yaml` updated + learning `status: consolidated` (US3 Acceptance Scenarios 1-3) — touches: `tests/integration/test_us3_consolidate.py`
- [X] T074 [P] [US3] Test fixtures for US3 — pending learnings sample set covering all 7 `type` values from FR-023 — touches: `tests/fixtures/learnings/us3_*.md`

### Checkpoint: end of Phase 5

Gate: all T070..T074 are `[X]`. Independent Test from SPECS §US3 passes end-to-end.

---

## Phase 6: User Story 4 — Optional integration suggestions [US4]

> Independent Test (from SPECS §US4): run `/research "best cheese shops in Madrid"`. Skill must detect location/business signal and suggest Google Places API setup with skip / configure now / never-suggest options.

- [X] T080 [P] [US4] Wire FR-005 integration suggestion list at planning time, 3-option modal (configure / skip / never), credentials persisted to `.config/research-skill/.env`, never-suggest persisted via `scripts/preferences.py` keyed by topic-type signature — touches: `.claude/skills/research/SKILL.md` (cross-phase sequential after T050/T060)
- [X] T081 [P] [US4] Concrete first integration adapter scaffold — Google Places adapter implementing `scripts/integrations/base.py` interface (US4 Independent Test driver) — touches: `scripts/integrations/google_places.py` + `tests/unit/test_google_places.py`
- [X] T082 [P] [US4] Integration test — Madrid cheese shops topic triggers Google Places suggestion, "configure now" path writes credentials and uses adapter; "skip" falls back to base sources; "never" silences future similar topics (US4 Acceptance Scenarios 1-3) — touches: `tests/integration/test_us4_integrations.py`
- [X] T083 [P] [US4] Test fixtures for US4 — Madrid cheese shops outline + Google Places mocked response + preferences.yaml round-trip fixture — touches: `tests/fixtures/outlines/cheese_shops_madrid.yaml`, `tests/fixtures/integrations/google_places_*.json`, `tests/fixtures/preferences/us4_*.yaml`

### Checkpoint: end of Phase 6

Gate: all T080..T083 are `[X]`. Independent Test from SPECS §US4 passes end-to-end.

---

## Phase 7: Polish

### Documentation

- [X] T090 `README.md` operator quickstart synthesized from PLAN §Quickstart — touches: `README.md`
- [X] T091 `CLAUDE.md` — add `## Principles` section (constitution-lite per `patrones/spec-kit-prompts/constitution.md`), pointers to SPECS / PLAN / TASKS / RESEARCH, quickstart link — touches: `CLAUDE.md`

### Success-criteria verification

- [X] T092 [P] SC-001 wall-clock test for 5-item comparative under 15 min (assumes WebSearch p95 ≤3s, WebFetch p95 ≤8s; user-pause time excluded) — touches: `tests/integration/sc/test_sc001_walltime.py`
- [X] T093 [P] SC-002 tier distribution checker (≥70% A/B, <5% D in any output report) — touches: `tests/integration/sc/test_sc002_tier_distribution.py`
- [X] T094 [P] SC-003 URL validation 100% pass OR explicit gap marker; zero silent drops — touches: `tests/integration/sc/test_sc003_validation.py`
- [X] T095 [P] SC-004 resume after interruption — kill mid-batch, re-invoke, completed JSONs skipped — touches: `tests/integration/sc/test_sc004_resume.py`
- [X] T096 [P] SC-005 mode-detection accuracy ≥9/10 on hand-curated 10-topic set — touches: `tests/integration/sc/test_sc005_mode_accuracy.py` + `tests/fixtures/sc/mode_detection_topics.yaml`
- [X] T097 [P] SC-006 `/last30days` activation accuracy ≥16/20 on hand-curated 20-topic set (10 social + 10 non-social) — touches: `tests/integration/sc/test_sc006_l30_activation.py` + `tests/fixtures/sc/last30days_activation_topics.yaml`
- [X] T098 [P] SC-007 after 5+ sessions with 3+ corrections, `/research-consolidate` proposes ≥1 user-approved promotable rule — touches: `tests/integration/sc/test_sc007_consolidate.py` + `tests/fixtures/sc/consolidation_history.yaml`
- [X] T099 [P] SC-008 first-time user with only CLAUDE.md+SPECS.md runs successful comparative research — onboarding scenario test — touches: `tests/integration/sc/test_sc008_onboarding.py`

### Edge-case smoke tests

- [X] T100 [P] Edge cases batch 1 — zero results across all sources; all URLs broken; all Tier D (FR-016a yes/no path); topic mode ambiguous (mode-detect <0.75 → AskUserQuestion) — touches: `tests/integration/edge/test_edge_zero_and_quality.py`
- [X] T101 [P] Edge cases batch 2 — contradictory Tier A (FR-017a Disagreements); optional integration declined repeatedly (FR-005 never path); `/last30days` not configured — touches: `tests/integration/edge/test_edge_decline_and_l30.py`
- [X] T102 [P] Edge cases batch 3 — mid-flight scope invalidation (FR-026 mid-round); WebFetch fails through Tier 1 → Tier 2 (FR-028); emergent comparison dimension (FR-030 accept path); agent budget exhausted (FR-032 hard-stop); systemic tool failure (FR-026 systemic trigger) — touches: `tests/integration/edge/test_edge_adaptation.py`

### Final review

- [X] T103 Per-skill SKILL.md final review — language consistency (English), tool declarations match invocations used, FR coverage cross-checked against this file's Coverage Map, anti-pattern sweep — touches: `.claude/skills/{research,research-deep,research-report,research-consolidate}/SKILL.md`

### FR-specific verification

- [X] T104 [P] FR-031 cross-pollination smoke — two-agent fixture proves a cross-relevant signal (≥2 agents OR entity/term overlap per FR-031) is propagated as a hint into the next round's agent prompt and recorded under `_meta.hints_received[]` — touches: `tests/integration/test_fr031_cross_pollination.py`, `tests/fixtures/fr031/*.json`

### Checkpoint: end of Phase 7

Gate: all T090..T104 are `[X]`. All SC tests pass. All edge case smoke tests pass. Run `pytest -q` (unit + integration + sc + edge) — must be green.

---

## Dependencies

- **Phase gates**: Phase 2 (Foundational) blocks all Phase 3+ tasks. Phase 3 (US1 / MVP) is the first shippable surface; Phases 4–6 are independently shippable on top of MVP. Phase 7 (Polish) blocks no story phase but is required for v1 release.
- **Data files block scoring/extraction**: T004 (source-tiers) and T005 (publisher-graph) block T014 (scoring engine). T007 (mode-detection) blocks T015. T008 (fallback-extractors) blocks T020.
- **Helper tests blocked by their impl**: T029..T040 each blocked by their corresponding T010..T028 module impl (test files are parallel with each other, but each test waits on its impl).
- **Same-file sequential edits across phases**: `.claude/skills/research/SKILL.md` is edited in T050 → T060 → T080 → T071 → T091 → T103 in that order. Same pattern for `research-deep/SKILL.md` (T051 → T061 → T071 → T103) and `research-report/SKILL.md` (T052 → T062 → T072 → T103). Marked non-`[P]` in those phases.
- **US1 must complete before US2/US3/US4 integration tests**: T053 (US1 IT) blocks T063 (US2 IT), T073 (US3 IT), T082 (US4 IT) only because they share fixtures patterns; logically each phase has its own gate.
- **Integration adapter base before concrete adapters**: T024 blocks T081.
- **Learnings infrastructure before US3**: T025/T026 block T070/T071/T072.
- **Preferences before US4 never-suggest**: T027 blocks T080.
- **Report builder before US1/US2 report skills**: T028 blocks T052 and T062.

---

## MVP Strategy

The minimum shippable surface is **Phase 1 + Phase 2 + Phase 3 (US1 only)**. At that checkpoint, the Independent Test for US1 passes end-to-end: a comparative research from invocation to `report.md` + `report.csv` with tiered citations. Phases 4–6 (US2 narrative / US3 self-learning / US4 optional integrations) are sequenced by SPECS priority order and each is independently shippable on top of MVP — landing US3 without US2 is valid, etc. Phase 7 (Polish) is required for v1 release but does not gate MVP usability.

---

## Coverage Map (informative)

### FRs → Tasks
| FR | Tasks |
|----|-------|
| FR-001 | T050 |
| FR-002 | T050 |
| FR-002a | T011, T012, T050 |
| FR-003 | T050 |
| FR-004 | T015, T050 (LLM fallback) |
| FR-005 | T024, T027, T050, T080 |
| FR-006 | T050 |
| FR-007 | T051, T061 |
| FR-008 | T051 |
| FR-009 | T051 |
| FR-010 | T051 |
| FR-011 | T013, T051 |
| FR-012 | T026, T051, T071 |
| FR-013 | T014, T051, T052 |
| FR-014 | T014 |
| FR-015 | T014, T028 (Disagreements) |
| FR-016 | T014, T052 |
| FR-016a | T050 |
| FR-017 | T028, T052, T062 |
| FR-017a | T028, T052 |
| FR-018 | T028, T052 |
| FR-019 | T028, T052, T062 |
| FR-020 | T013, T028, T052 |
| FR-021 | T026, T050, T071 |
| FR-022 | T026, T072 |
| FR-023 | T026 |
| FR-024 | T025, T070 |
| FR-025 | T070, T072 |
| FR-026 | T051 |
| FR-027 | T051 |
| FR-028 | T013, T017, T018, T019, T020, T021, T022, T023, T051 |
| FR-029 | T051 |
| FR-030 | T051 |
| FR-031 | T051, T061, T104 |
| FR-032 | T051 |
| FR-033 | T016, T051 |

### User Stories → Phases
| US | Phase | Tasks |
|----|-------|-------|
| US1 (P1, MVP) | Phase 3 | T050–T054 |
| US2 (P2) | Phase 4 | T060–T064 |
| US3 (P3) | Phase 5 | T070–T074 |
| US4 (P4) | Phase 6 | T080–T083 |

### SCs → Verification Tasks
| SC | Task |
|----|------|
| SC-001 | T092 |
| SC-002 | T093 |
| SC-003 | T094 |
| SC-004 | T095 |
| SC-005 | T096 |
| SC-006 | T097 |
| SC-007 | T098 |
| SC-008 | T099 |

### Key Entities → Foundational Tasks
| Entity | Tasks |
|--------|-------|
| `outline.yaml` (comparative + narrative) | T050, T060 (creation), T051, T061 (read), T052, T062 (read) |
| `fields.yaml` | T050 (creation), T051, T052 (read) |
| Item JSON (per-item or per-subquery) | T051, T061 (creation), T052, T062 (read) |
| `search-log.md` | T050, T051, T052, T060, T061, T062 |
| Learning entry | T026, T050, T051, T070, T071, T072 |
| Registry files (`data/*.yaml`) | T004–T008 (seed), T014/T020/T024/T025 (read), T070 (write via consolidation) |

### Edge Cases → Polish Tasks
| Edge case | Task |
|-----------|------|
| Zero results across all sources | T100 |
| All URLs broken | T100 |
| All Tier D | T100 |
| Topic mode ambiguous | T100 |
| Contradictory Tier A | T101 |
| Resume after interruption | T095 |
| Optional integration declined repeatedly | T101 |
| `/last30days` not configured | T101 |
| Mid-flight scope invalidation | T102 |
| WebFetch fails (Tier 1 → Tier 2) | T102 |
| Emergent dimension/entity | T102 |
| Agent budget exhausted | T102 |
| Systemic tool failure | T102 |

### Infra tasks (no FR mapping — expected)
T001–T009 (Setup scaffolding), T090–T091 (docs), T103 (final review) serve PLAN's Project Structure and Quickstart rather than specific FRs. Annotated per analyze finding F5 so future analyze runs treat them as expected-unmapped rather than coverage gaps.
