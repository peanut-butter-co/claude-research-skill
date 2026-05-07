---
name: research-deep
description: Parallel-agent execution orchestrator for the research-skill pipeline. Reads planning artifacts from `tasks/<case>/` (produced by `/research`), spawns one Task sub-agent per item or sub-query, runs them concurrently with budget caps, applies tier scoring, performs intermediate cross-pollination synthesis between rounds, and surfaces emergent extensions for user confirmation. Invoked as `/research-deep` with no arguments — case is auto-detected from the most recently modified directory under `tasks/` containing an `outline.yaml`.
tools:
  - Bash
  - Read
  - Write
  - Task
  - AskUserQuestion
  - WebSearch
  - WebFetch
---

# /research-deep — Parallel research orchestrator

## Overview

This skill is the **execution stage** of the research-skill pipeline. The previous stage (`/research`) produced an `outline.yaml` (and optionally `fields.yaml`) under `tasks/<case>/`. Your job is to:

1. Locate the active case under `tasks/`.
2. Hold a lockfile so only one orchestrator runs per case.
3. For each item/sub-query, spawn a parallel `Task` agent. Each agent searches, fetches, scores sources, fills the matrix cell for its item, and writes its own JSON under `tasks/<case>/output/<agent_id>.json`.
4. Between rounds, run an intermediate synthesis pass that cross-pollinates findings between agents and surfaces emergent dimensions/items for user confirmation.
5. Apply hard budget caps and a saturation/diversity stop criterion.
6. Persist incremental progress so the user tailing `output/` sees agents flush JSON at every round boundary.
7. Release the lock and emit a completion summary listing budget-exhausted agents and any unresolved `[uncertain]` fields.

**You do NOT produce a final user-facing report.** That is the job of the downstream `/research-consolidate` and `/research-report` skills, which read the same `output/*.json` files.

This skill implements FRs **001, 002a, 007, 008, 009, 010, 011, 012, 013, 014, 015, 016, 021, 026, 027, 028, 029, 030, 031, 032, 033a, 033b** from `SPECS.md`. (FR-009 = one Task agent per item/sub-query; FR-011 = per-agent URL validation in agent step 5; FR-021 = feedback signal sweep in Step 10.5.)

---

## Invariants

- **Project root** is the current working directory (the directory containing `tasks/`, `data/`, `learnings/`, `scripts/`, `.venv/`).
- **Python is invoked via `.venv/bin/python -c "..."`** — never via `python` or `python3`. Always insert the project root onto `sys.path` first: `import sys; sys.path.insert(0, '.')`.
- **Working directory resets between `Bash` calls** for sub-agents in some Claude Code modes — agents must always use absolute paths or `cd $(pwd)`-equivalents. The orchestrator itself uses paths relative to the project root.
- **Never skip Tier 1 fetch fallbacks to go directly to Tier 2 (browser)** — see FR-028 below.
- **Never invent a tier**: only `assign_tier()` decides A/B/C/D/Unknown. Unknown sources MUST log a learning entry.
- **Never overwrite a completed agent JSON on resume.**
- **Never proceed past a Level 2/3 trigger without user confirmation** (Level 1 is auto-adapt, no pause; Level 2 pauses; Level 3 is hard-stop).

---

## Step 1 — Detect the case (FR-001)

The skill takes no arguments. Detect the active case:

```bash
.venv/bin/python -c "
import sys, os
from pathlib import Path
sys.path.insert(0, '.')
tasks = Path('tasks')
if not tasks.exists():
    print('NO_TASKS')
    raise SystemExit(0)
candidates = []
for p in tasks.iterdir():
    if p.is_dir() and (p / 'outline.yaml').exists():
        candidates.append((p.stat().st_mtime, p.name))
candidates.sort(reverse=True)
for _, name in candidates:
    print(name)
"
```

Logic:

- If output is `NO_TASKS` or empty: **fail** with the exact message:
  > `No planning artifacts found. Run /research "<topic>" first.`
- If exactly one candidate: use it as `<case>`.
- If multiple candidates: list them (most recent first) and call `AskUserQuestion` asking the user to pick which case to operate on. Each option is a case name.

Persist `<case>` in your working memory. From here on, all paths are `tasks/<case>/...`.

If the user passes an explicit case name as `$ARGUMENTS`, use that instead — but still verify `tasks/<case>/outline.yaml` exists. If it does not, fail with:
> `Case '<case>' has no outline.yaml. Run /research first or pick a different case.`

Emit:
```
[orchestrator] Starting /research-deep for case <case>
```

---

## Step 2 — Lockfile (FR-002a)

Run this Python in one Bash call, before doing any work in `tasks/<case>/`:

```bash
.venv/bin/python -c "
import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from scripts.lockfile import acquire, check_stale, read_lock
case = Path('tasks/<case>')
# Try to GC stale lock first
check_stale(case, ttl_seconds=3600)
existing = read_lock(case)
if existing is not None:
    print('LOCKED', json.dumps(existing))
    raise SystemExit(2)
acquire(case)
print('OK')
"
```

If exit code is 2 (LOCKED), **fail-fast**: print the lockfile contents and refuse to run. Exact message:
> `Another /research-deep run is in progress for case <case> (pid=<pid>, started=<start>). Aborting.`

If lock acquisition succeeds, continue. **Always release the lock** in the final step (and on any error path) via:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; from scripts.lockfile import release; release(Path('tasks/<case>'))"
```

---

## Step 3 — Load outline + fields

Read `tasks/<case>/outline.yaml`. Its top-level shape is:

```yaml
mode: comparative | narrative
items: [...]            # comparative mode
subqueries: [...]       # narrative mode
config:
  items_per_batch: 1
  social_signal: true | false
  rigor: standard | rigorous
  query_budget: 15           # default 15 standard, 25 rigorous
  max_emergent_threads: 2
  extension_budget: 5
  include_tier_d: false
```

If `mode: comparative`, also read `tasks/<case>/fields.yaml`:

```yaml
categories:
  <category_name>:
    - <field_name_1>
    - <field_name_2>
```

If a key is missing, fall back to the documented defaults above. Persist all of these as `<config_*>` in your working memory; you will pass them into agent prompts.

The list of **work units** is:
- `outline.items` (comparative) — one agent per item, agent_id = `make_slug(item)`.
- `outline.subqueries` (narrative) — one agent per sub-query, agent_id = `make_slug(subquery)`. The agent writes its JSON with the `"subquery"` top-level key (see Agent Prompt Template below).

Compute `agent_id` for each unit:

```bash
.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from scripts.slug import make_slug
print(make_slug('<unit_name>'))
"
```

---

## Step 4 — Resume logic (FR-010)

Ensure `tasks/<case>/output/` exists (`mkdir -p`). For each work unit, check if `tasks/<case>/output/<agent_id>.json` exists.

A unit is **complete** if any of the following:
- `pruned: true`
- `budget_exhausted: true`
- (Comparative mode) All listed `fields` have a non-empty `value` AND the field is not in `uncertain[]`.
- (Narrative mode) The `summary` field is filled (non-empty `value` AND not in `uncertain[]`).

(Read each candidate JSON via `Read`. If the file is malformed JSON, treat it as incomplete — log it and re-queue it.)

Build:
- `to_run` — units that need work this run.
- `skipped` — units already complete.

Emit:
```
[milestone:resume] <len(to_run)> items to process, <len(skipped)> items already complete (skipped).
```

If `to_run` is empty, jump to **Step 12 — Final summary**.

---

## Step 5 — Round 1: parallel Task spawn (FR-007, FR-033b)

For each unit in `to_run`, build the agent prompt using the **Agent Prompt Template** below. Then call the `Task` tool **once per unit** in a single message — these calls run concurrently. (If `config.items_per_batch > 1`, batch that many items into a single agent prompt and have the agent write one JSON per item.)

Before spawning:
```
[orchestrator] Round 1: spawning <N> agents in parallel — rigor: <rigor>, query_budget: <budget>/agent
```

For each agent, also emit:
```
[milestone:agent_start] Item: <item_or_subquery>
```

After all `Task` calls return, read every `tasks/<case>/output/<agent_id>.json` that the agents produced. For each:
```
[agent:<agent_id>] Done — fields: <N_filled>/<N_total>, uncertain: <N_uncertain>, sources: <N_total> (A:<a> B:<b> C:<c> D:<d>), budget: <consumed>/<budget>
```

If any agent set `budget_exhausted: true`:
```
[milestone:budget_exhausted] Agent <agent_id> exhausted budget
```
If any agent's `budget_consumed >= 0.8 * query_budget` and `< query_budget`:
```
[milestone:budget_warning] Agent <agent_id> at 80% budget
```

---

## Step 6 — Cross-citation bonus + tier-D filtering (FR-014, FR-016)

After every round, before deciding whether to continue:

1. Aggregate all `sources[]` from all agent JSONs into a single list.
2. Apply cross-citation bonus:
```bash
.venv/bin/python -c "
import sys, json
sys.path.insert(0, '.')
from scripts.score_source import apply_cross_citation_bonus
sources = json.loads(<JSON_BLOB>)
out = apply_cross_citation_bonus(sources, data_dir='data')
print(json.dumps(out))
"
```
3. Apply Tier D filtering. If `config.include_tier_d` is **false** (the default), strip all sources with `tier == 'D'` from each field's `sources[]`. If, after stripping, a field has zero sources, mark the field as `uncertain` (add to `uncertain[]`) and set its `value` to `[uncertain]`.

These updates are written **back into the agent JSONs** by the orchestrator. (The agent itself does not know what other agents found, so cross-citation bonus is computed centrally.)

---

## Step 7 — Intermediate synthesis + cross-pollination (FR-031)

If the FR-027 stop criterion **does not** fire (see Step 9), do an intermediate synthesis pass before the next round.

Emit:
```
[milestone:synthesis_triggered] Intermediate synthesis running
```

1. **Gather**: read all `tasks/<case>/output/<agent_id>.json` produced this round.
2. **Extract** (LLM pass — you do this in your own thinking, no extra tool needed):
   - Emergent dimensions: features/properties that >=2 agents independently surfaced and were not in the original `fields.yaml`.
   - Newly canonical terms: terminology that became consistent across agents (e.g. an entity now consistently called by one specific name).
   - Entity references: when one agent's output references the item of another agent (case-insensitive substring match, or shared noun phrase after stop-word filter).
3. **Cross-relevance test** for each candidate signal `s`:
   - `s` is cross-relevant if it appears in **≥2 agents' outputs**, OR
   - `s` appears in **one agent's output AND syntactically relates to another agent's item** (case-insensitive substring of the other agent's item name, or shared noun phrase after stop-word filter).
4. **Hint generation** per receiving agent:
   ```
   agent-<source_item> found '<finding>' as a key differentiator — verify whether this dimension applies to your item.
   ```
   Each agent gets only the hints that target it. Cap at **5 hints per agent per round** to avoid prompt bloat — keep the highest-confidence ones.
5. **Propagate**: when you build the next round's agent prompt, include the hints under `_meta.hints_received[]`. The agent must record them in its output JSON under `_meta.hints_received[]` as well.
6. Append a synthesis block to `tasks/<case>/search-log.md` under `### Cross-pollination`:
   ```
   ## Round <N> synthesis (UTC <timestamp>)
   - <N_dimensions> emergent dimensions across <N_agents> agents
   - <N_terms> canonical terms aligned
   - Hints dispatched: <map of agent_id → count>
   ```

This is **Level 1** — no user pause.

---

## Step 8 — Emergent extension surfacing (FR-030)

After Round 1's FR-031 pass, also handle **proposed_extensions** (Level 2):

1. Collect every `proposed_extensions[]` entry from every agent JSON.
2. Deduplicate by `(type, description)`.
3. If the list is non-empty:
   ```
   [milestone:extension_proposed] <N> extensions proposed after round 1
   ```
4. **Pause** and call `AskUserQuestion`. Use one question with multi-select options, OR (if >5 extensions) one `AskUserQuestion` per extension. For each extension present three options:
   - `accept` — agent will add this dimension/item to its plan and gets `extension_budget` extra queries.
   - `note` — record in "Cross-cutting findings" only; do not re-run.
   - `discard` — ignore.
5. Apply user decisions:
   - For each `accept`: locate the affected agent(s). On the next round, their prompt receives:
     - The new field/dimension/sub-query.
     - `+config.extension_budget` added to their `query_budget`.
     - A `_meta.hints_received[]` entry: `Extension accepted: <description>. Investigate this dimension.`
   - For each `note`: append to `search-log.md` under `### Cross-cutting findings`.
   - For each `discard`: append a single line to `search-log.md` under `### Strategic adaptations`: `Round <N>: discarded extension '<description>'`.
6. Always record the full decision set in `search-log.md` under `### Strategic adaptations`:
   ```
   ## Round <N> extension decisions
   - accept: <description> → agents [<a>, <b>], +<extension_budget> queries each
   - note: <description>
   - discard: <description>
   ```

---

## Step 9 — Stop criterion (FR-027)

Compute after each round:

- **Saturation**: for the most recent 5 queries on a path (per agent's `_meta` or by inspecting `search-log.md`), if total new findings (new fields filled or new sources added) is `<5`, that path is exhausted. If **every** active path is saturated, the saturation condition is met.
- **Diversity**: count unique domains across all `sources[]` in all agent JSONs. Threshold:
  - `rigor == 'standard'` → 15
  - `rigor == 'rigorous'` → 25
- **Matrix coverage**: every (item × field) cell has either a non-empty `value` or is in `uncertain[]` or its agent has `pruned: true` / `budget_exhausted: true`.

**Stop** when:
> matrix coverage complete **AND** (saturation **OR** diversity threshold reached).

If stop fires, emit:
```
[milestone:stop_criterion_met] Matrix complete + (saturation=<bool>, diversity=<count>/<threshold>)
```
…and proceed to Step 12.

Otherwise, run Step 7 and Step 8, then go to Step 10.

---

## Step 10 — Strategic mid-flight triggers (FR-026, Level 2)

You evaluate these triggers **continuously** (mid-round, the agent itself flags them; end-of-round, you compute them after Step 7).

**Mid-round triggers** (an agent can interrupt and bubble up to the orchestrator via its JSON `_meta.strategic_trigger`):
- Scope-invalidating finding — e.g. an entity name resolves to two distinct products.
- Unanticipated bias requiring plan changes.
- Canonical terminology shift requiring query rewrites across all agents.
- Systemic tool failure — the entire Tier 1 fetch chain OR all configured search providers have failed ≥3 attempts each.

**End-of-round triggers**:
- Accumulated emergent extensions (handled in Step 8).

On any Level 2 trigger:

1. Emit:
   ```
   [milestone:strategic_replan_triggered] <trigger_type>
   ```
2. Append to `tasks/<case>/search-log.md`:
   ```
   ## Strategic adaptation — <UTC timestamp>
   Trigger: <trigger_type>
   Detail: <description>
   Proposed change: <proposed change>
   ```
3. **Pause**: call `AskUserQuestion`. Present the trigger, the proposed plan revision, and ask the user to confirm/modify/cancel.
4. Resume only after the user confirms. Update the in-memory plan accordingly. (e.g., rewrite the canonical terminology in queries, drop a sub-query, split an item into two.)
5. If the user cancels, gracefully stop the run, persist all current JSONs, release the lock, and emit a final summary noting the cancellation.

**Do not** trigger a Level 2 pause for things that Level 1 already handles (single dry query, single 403, etc.).

---

## Step 10.5 — FR-021 Feedback signal sweep (orchestrator)

Run this sweep **immediately after each `AskUserQuestion` call in Steps 8 and 10** (and again briefly in Step 12 — see below). Its job is to detect user-feedback signals at moderate aggressiveness and offer to log them as learning entries with `trigger='user-feedback'`.

Signals to detect in the user's response (or any free-text the user typed):

- (a) Explicit log requests — phrases like "log this", "remember this", "for next time", "save this".
- (b) Rejected recommendation — the user picked a custom answer (anything not in the pre-defined options) OR picked an option that was NOT the one marked Recommended (e.g. picked `discard` when `accept` was Recommended in Step 8; picked `cancel` or modified the plan in Step 10).
- (c) Tier corrections — "that source isn't Tier A", "this should be Tier B", etc.
- (d) Source-classification disputes — "this is the wrong category", "don't classify <domain> as <X>".
- (e) Explicit "this is wrong" flags against the skill's most recent output — phrases like "this is wrong", "incorrect", "that's not right", "wrong result".

Casual responses ("ok", "yes", "sounds good", "next", "go ahead") DO NOT trigger. Casual comments unrelated to a recent skill output DO NOT trigger.

If a signal fires, present **one** `AskUserQuestion` per distinct signal:

- Question: "Log this as a learning entry for future runs? — <one-line summary of the signal>"
- Options:
  - `Yes, log it` — call `write_learning` (next snippet).
  - `No, skip` (Recommended) — discard.

If the user confirms `Yes`:

```
TRIGGER='user-feedback' CTX='<one-line summary>' TYPE='<workflow|integration|tier|source|domain-fact|scoring-rule|process-improvement|other>' BODY='<2-4 sentence body capturing what to remember>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.')
from pathlib import Path
from scripts.learnings_write import write_learning
path = write_learning(
    trigger=os.environ['TRIGGER'],
    context=os.environ['CTX'],
    type_=os.environ['TYPE'],
    body=os.environ['BODY'],
    learnings_dir=Path('learnings'),
)
print(f'WROTE {path}')
PY
```

`type_` mapping (same as `/research` Phase 9):
- `integration` for integration-suggestion signals.
- `tier` for tier corrections (signal c).
- `source` for source-classification disputes (signal d).
- `workflow` for AskUserQuestion rejections / cancellations (signal b).
- `domain-fact` for signal (e) when correcting a factual claim.
- `scoring-rule` for signal (e) when correcting a tier/scoring rule for future runs.
- `process-improvement` for signal (e) when correcting how the orchestrator behaves.
- `other` only when nothing else fits.

After this sweep, return to whatever step came next (Step 11 for subsequent rounds, or Step 12 if the run is ending).

---

## Step 11 — Subsequent rounds (Round 2, 3, …)

If you reach this point, stop criterion has not fired. Repeat the spawn-collect-synthesize-decide loop:

1. Recompute `to_run` — any agent that is **not** complete (see FR-010 definition) and **not** budget-exhausted. Include accepted-extension agents (Step 8).
2. For each, build a fresh agent prompt that includes the new `_meta.hints_received[]` and (if applicable) the extension's added field/dimension and `+extension_budget` queries.
3. Spawn all agents in parallel via `Task` (Step 5).
4. Run Step 6, 7, 8, 9 again.
5. Repeat until stop criterion fires, **or** every active agent is `pruned`/`budget_exhausted`/complete, **or** you hit a hard guard of 5 rounds (defensive cap — emit `[milestone:round_cap_reached]` and stop).

Each round emits:
```
[milestone:round_complete] Round <N> complete — <X> new findings, <Y> unique domains
```

---

## Step 12 — Final summary + lock release

1. Read all `tasks/<case>/output/<agent_id>.json` one last time.
2. Compute summary stats:
   - Total items, fields, filled fields, uncertain fields.
   - Total sources by tier (A/B/C/D/Unknown).
   - Agents with `pruned: true` or `budget_exhausted: true`.
   - Total queries consumed across agents.
3. Append to `tasks/<case>/search-log.md`:
   ```
   ## /research-deep run complete — <UTC timestamp>
   - Rounds: <N>
   - Agents: <total> (complete: <c>, pruned: <p>, budget-exhausted: <b>)
   - Sources: A=<a>, B=<b>, C=<c>, D=<d>, Unknown=<u>
   - Uncertain fields: <count> (see per-agent JSONs)
   - Diversity: <unique_domains> unique domains
   ```
4. Emit:
   ```
   [orchestrator] Run complete. <N> agents, <R> rounds, <S> sources collected.
   [orchestrator] Budget-exhausted agents: <list or 'none'>
   [orchestrator] Uncertain fields: <count> (next step: /research-consolidate)
   ```
4a. **FR-021 final sweep**: if the user responds to the final summary with feedback signals (per the rules in Step 10.5), run one last Step 10.5 sweep before releasing the lock. Keep it light — only fire if a signal is unambiguous; do not prompt on silence or casual acknowledgements.
5. **Release the lock** (always — even on error paths, wrap the whole flow accordingly):
   ```bash
   .venv/bin/python -c "import sys; sys.path.insert(0, '.'); from pathlib import Path; from scripts.lockfile import release; release(Path('tasks/<case>'))"
   ```

The orchestrator is done. Downstream skills (`/research-consolidate`, `/research-report`) will read `tasks/<case>/output/*.json` and `search-log.md`.

---

## Agent prompt template (FR-007)

When spawning each `Task` agent, pass this prompt, with `<placeholders>` replaced by orchestrator-known values. The agent runs in its own context window.

```
You are a research agent for the research-skill orchestrator.

# Identity
- agent_id: <agent_id>
- item: <item_or_subquery>
- case: <case>
- output file: tasks/<case>/output/<agent_id>.json

# Mode
mode: <comparative|narrative>

# Task
For **comparative mode**: Fill the matrix cell for your item. Fill every field listed below.

For **narrative mode**: Answer your sub-query as a well-sourced essay. Your JSON uses `subquery` as the identifier key (not `item`). Produce one field called `summary` — a concise, evidence-backed answer to your sub-question (3–6 sentences). Cite every claim. If you find important tangential sub-angles, also add additional fields named descriptively (e.g. `compliance_timeline`, `enforcement_mechanism`), but `summary` is always required. If you cannot find reliable evidence, set the field value to `[uncertain]` and add the field name to `uncertain[]`.

Fields to fill (from fields.yaml — comparative mode only):
<categories_yaml_block>

# Sub-question (narrative mode only)
subquery: <subquery_text>

# Configuration
- query_budget: <query_budget>          # hard cap on WebSearch calls
- rigor: <standard|rigorous>
- social_signal: <true|false>
- include_tier_d: <true|false>
- max_emergent_threads: <max_emergent_threads>
- extension_budget: <extension_budget>   # extra queries if user accepted an extension

# Hints from prior round (cross-pollination — FR-031)
<bulleted list of _meta.hints_received[]; empty for round 1>

# Project root
You are running with the project root as cwd. Use absolute or `.`-relative paths. Python helpers go through `.venv/bin/python -c "..."` with `sys.path.insert(0, '.')`.

# Procedure (per field — repeat until budget exhausted or all fields filled)

1. **Plan the query**. Pick the next un-resolved field. Compose 1 WebSearch query that targets it. Prefer narrow, evidence-seeking queries. Account for hints (canonical terminology, suggested dimensions).

2. **Search**. Use the `WebSearch` tool. If WebSearch fails or returns nothing useful:
   - Reformulate up to 3 times (synonym swap, broader, narrower).
   - If still nothing: fall back through the search providers (FR-028):
     - Brave (via `scripts.search.brave.search`, requires BRAVE_API_KEY)
     - Exa (via `scripts.search.exa.search`, requires EXA_API_KEY)
     - DuckDuckGo (via `scripts.search.duckduckgo.search`)
   - If 3 reformulations + all fallback providers return zero useful results: log a learning entry (trigger='self-detection', type='search-dry') via `scripts.learnings_write.write_learning`, mark the field as `[uncertain]`.

3. **Fetch**. For each promising URL, use `WebFetch`. If it fails (403, JS-only, paywall, timeout, empty body), follow FR-028 fallback chain in this order — DO NOT skip Tier 1:
   - **Tier 1 (always try first):**
     a. Jina AI Reader: `scripts.extractors.jina.fetch(url)`
     b. Exa /contents: `scripts.extractors.exa.fetch(url, env=load_env())` (requires EXA_API_KEY)
     c. Wayback Machine: `scripts.extractors.wayback.fetch(url)`
   - **Tier 2 (only if all Tier 1 failed):** detect via `scripts.extractors.browser.detect_available()` and use the first available:
     1. Claude Chrome Extension
     2. chrome-devtools MCP
     3. Playwright MCP
   - Record the successful tool name in `source.fetch_method`. If ALL fail, set `extraction_failed: true` on the source and note in agent JSON.

4. **Score the source** (FR-013/014/015):
   ```
   .venv/bin/python -c "
   import sys, json
   sys.path.insert(0, '.')
   from scripts.score_source import assign_tier, score_source
   t = assign_tier('<url>', title='<title>', data_dir='data')
   s = score_source('<url>', t['tier'], '<pub_date>', data_dir='data')
   print(json.dumps({**t, **s}))
   "
   ```
   - If `unclassified: true`, emit a learning entry: `write_learning(trigger='self-detection', context='<domain>', type_='source-classification', body='<details>', learnings_dir=Path('learnings'), today=<today>)`.
   - Persist `tier` and `score_raw` on the source object.

5. **Validate URLs** that you actually quote in `value` via `scripts.validate_urls.validate_urls([...])` and drop dead ones. If a domain fails ≥2 sessions cumulative (check `learnings/`), log a learning entry.

6. **Tier D filter**: if `include_tier_d == false`, do not use Tier D sources as primary evidence. They may be referenced as `note` only.

7. **Extract value**. Read the fetched content; pull out the field's value with citation(s). Aim for 1–3 high-quality sources per field. Mark as `[uncertain]` if evidence is weak.

8. **Social signal (FR-008)**. If `social_signal == true`, run once per item (early in the round):
   ```bash
   claude /last30days "<item>" 2>&1 || true
   ```
   Parse stdout. Tag every URL it returns as Tier C, then continue normal scoring. If the command fails (nonzero or unavailable), log via `write_learning(trigger='self-detection', type_='tool-failure', ...)` and continue without it.

9. **Emergent thread chasing (FR-029c)**. If during a fetch you find a lateral citation that:
   - Appears in ≥2 sources OR
   - Scores Tier B+
   …spend up to 2 extra queries chasing it. Cap at `max_emergent_threads` extra threads per round per agent. Beyond that cap, log it in `proposed_extensions[]` with `type: dimension|item|subquery`, a description, and a rationale. The orchestrator will surface these to the user.

10. **Pruning (FR-029d)**. If after triple reformulation + fallbacks you have 0 useful results for a field, mark it `[uncertain]` and stop spending budget on it. If **every** field is unworkable for this item, set `pruned: true`, log the reason, and write the JSON.

11. **Self-detected anomaly logging (FR-012)**. Emit a learning entry via `scripts.learnings_write.write_learning(trigger='self-detection', ...)` for:
    a. Two+ Tier A sources contradicting on a claim with no third source resolving it. type='contradiction'.
    b. Query returning zero results after 3 reformulations. type='search-dry'.
    c. Domain failing URL validation in ≥2 distinct sessions cumulative (cross-check `learnings/` history). type='domain-failure'.

12. **Budget tracking (FR-032)**. Increment `budget_consumed` for every WebSearch (and every fallback search-provider call). Do NOT count fetches.
    - At `budget_consumed >= 0.8 * query_budget`: print `[agent:<id>] Budget warning: <consumed>/<budget>`. Stop chasing emergent threads and stop opening new fields; close out fields you've already started.
    - At `budget_consumed >= query_budget`: HARD-STOP. Set `budget_exhausted: true`, write the JSON, exit.

13. **Strategic mid-flight triggers (FR-026, you escalate to orchestrator)**. If you detect a scope-invalidating finding (e.g. ambiguous entity resolving to two distinct products), an unanticipated bias, a canonical terminology shift, or systemic tool failure (Tier 1 fully exhausted ≥3 attempts), set `_meta.strategic_trigger = {type, detail}` in your JSON, write the JSON immediately, and exit. The orchestrator will pause the run and consult the user.

14. **Incremental persistence (FR-033a)**. Write the JSON at every "round boundary". For a single-round agent, that means: after every 3–5 fields finished, flush the JSON in its current state. For multi-round agents, always flush at the end of the round before exiting.

# Output JSON shape (write to tasks/<case>/output/<agent_id>.json)

For comparative mode:

```json
{
  "item": "<item>",
  "fields": {
    "<field_name>": {
      "value": "<value or [uncertain]>",
      "sources": [
        {
          "url": "https://...",
          "title": "...",
          "tier": "A|B|C|D|Unknown",
          "date": "YYYY-MM-DD",
          "fetch_method": "webfetch|jina|exa|wayback|browser-ext|chrome-mcp|playwright-mcp",
          "extraction_failed": false
        }
      ]
    }
  },
  "uncertain": ["<field_name>", "..."],
  "pruned": false,
  "emergent_threads_chased": [
    {"trigger": "...", "queries_spent": 1, "outcome": "useful|dead-end|partial"}
  ],
  "proposed_extensions": [
    {"type": "dimension|item|subquery", "description": "...", "rationale": "..."}
  ],
  "budget_consumed": 0,
  "budget_exhausted": false,
  "_meta": {
    "agent_run": "<ISO8601 UTC>",
    "hints_received": [<orchestrator-supplied hints>],
    "strategic_trigger": null
  }
}
```

For narrative mode:

```json
{
  "subquery": "<subquery_text>",
  "fields": {
    "summary": {
      "value": "<3–6 sentence evidence-backed answer, or [uncertain]>",
      "sources": [
        {
          "url": "https://...",
          "title": "...",
          "tier": "A|B|C|D|Unknown",
          "date": "YYYY-MM-DD",
          "fetch_method": "webfetch|jina|exa|wayback|browser-ext|chrome-mcp|playwright-mcp",
          "extraction_failed": false
        }
      ]
    },
    "<optional_descriptive_field>": {
      "value": "...",
      "sources": [ ... ]
    }
  },
  "uncertain": ["<field_name>", "..."],
  "pruned": false,
  "emergent_threads_chased": [
    {"trigger": "...", "queries_spent": 1, "outcome": "useful|dead-end|partial"}
  ],
  "proposed_extensions": [
    {"type": "subquery", "description": "<new sub-question>", "rationale": "..."}
  ],
  "budget_consumed": 0,
  "budget_exhausted": false,
  "_meta": {
    "agent_run": "<ISO8601 UTC>",
    "hints_received": [<orchestrator-supplied hints>],
    "strategic_trigger": null
  }
}
```

Notes for narrative mode:
- Top-level identifier is `"subquery"` (not `"item"`).
- `fields` are free-form (not driven by `fields.yaml`), but `"summary"` is **always** present.
- `proposed_extensions` entries use `type: "subquery"` (a new sub-question to investigate).

# Status streaming (FR-033b)
Use `scripts.status.agent('<agent_id>', '<msg>')` to print progress. Emit at minimum:
- one line per field finished
- one line on budget warning
- one line on budget exhaustion
- one line on prune
- one line on completion with the summary stats described above

# Final
When done (all fields filled, OR budget exhausted, OR pruned, OR strategic_trigger set):
1. Run `apply_cross_citation_bonus` over your own sources to flag eligible ones (orchestrator will redo this globally — it's safe).
2. Write the JSON to tasks/<case>/output/<agent_id>.json.
3. Emit `[agent:<agent_id>] Done — fields: <N_filled>/<N_total>, uncertain: <N_uncertain>, sources: <N> (A:<a> B:<b> C:<c> D:<d>), budget: <consumed>/<budget>`.
4. Return.
```

---

## FR-028 — Fallback chain reference (orchestrator + agents)

**Search fallback** (`WebSearch` returns nothing or errors):

1. WebSearch (built-in)
2. `scripts.search.brave.search(query, env, count=10)` — needs `BRAVE_API_KEY` in `.config/research-skill/.env`.
3. `scripts.search.exa.search(query, env, count=10)` — needs `EXA_API_KEY`.
4. `scripts.search.duckduckgo.search(query, count=10)` — no key required.

If a provider's key is missing, skip it silently. If **all** configured providers return zero, treat the query as dry → reformulate (Level 1, up to 3) → if still dry, prune (FR-029d) and log via `write_learning`.

**Fetch fallback** (`WebFetch` returns 403/empty/timeout/paywall):

Tier 1 (try in order — never skip):
1. `scripts.extractors.jina.fetch(url, timeout=15)` → `{ok, content, fetch_method}`
2. `scripts.extractors.exa.fetch(url, env, timeout=15)` (needs `EXA_API_KEY`)
3. `scripts.extractors.wayback.fetch(url, timeout=15)`

Tier 2 (only after Tier 1 fully failed):
- `detect = scripts.extractors.browser.detect_available()` → `{available: bool, method: 'browser-ext'|'chrome-mcp'|'playwright-mcp', fetch_method: ...}`
- Pick first available:
  1. Claude Chrome Extension (`browser-ext`)
  2. chrome-devtools MCP (`chrome-mcp`)
  3. Playwright MCP (`playwright-mcp`)

Record the successful method on the source as `fetch_method`. If **everything** fails: `extraction_failed: true` on the source, drop it from primary evidence, log via `write_learning(trigger='self-detection', type_='fetch-total-failure', ...)`. **Never silently lose** a fetch failure.

---

## FR-029 — Level 1 auto-adapt (in agent context)

Each agent may, **without pausing** the orchestrator:

a. **Query reformulation**: up to 3 attempts per dry query (synonym swap → broader term → narrower term).
b. **Fallback fetching**: full FR-028 chain.
c. **Emergent thread chasing**: when a lateral citation appears in ≥2 sources OR scores Tier B+, spend up to 2 extra queries on it. Hard cap of `max_emergent_threads` per agent per round. Beyond the cap, log to `proposed_extensions[]` (do not chase).
d. **Pruning**: if 0 useful results after triple reformulation, mark the field `[uncertain]`. If every field is dry, set `pruned: true` and stop.

Level 1 actions are recorded in the agent JSON (`emergent_threads_chased[]`, `proposed_extensions[]`, `uncertain[]`, `pruned`) and visible to the orchestrator post-round, but they never trigger a user pause.

---

## FR-031 — Synthesis pass details (orchestrator)

Each round end, after agents return JSONs and before deciding to spawn another round:

1. **Collect** all per-agent outputs.
2. **Extract candidate signals** (you do this in your own reasoning):
   - Emergent dimensions: properties surfaced by ≥2 agents that aren't in `fields.yaml`.
   - Canonical terminology: a term that ≥2 agents now use consistently.
   - Entity references: agent A's text mentions agent B's item (case-insensitive substring or shared noun phrase).
3. **Cross-relevance test**: a signal qualifies if `count(agents) >= 2` OR `(count(agents) == 1 AND syntactic_match_to_other_agent_item)`.
4. **Hint generation** (per receiving agent):
   - Format: `agent-<source> found '<finding>' as a key differentiator — verify whether this dimension applies to your item.`
   - Cap at 5 per receiving agent per round.
5. **Propagate** by inserting hints into the next-round agent prompt under the "Hints from prior round" block, and require the agent to mirror them under `_meta.hints_received[]`.
6. **Log** the synthesis in `search-log.md` under `### Cross-pollination`.

This is **always Level 1** (no user pause).

---

## FR-030 — Extension surfacing (orchestrator, Level 2)

Always run after FR-031 in Round 1; optional in later rounds if new `proposed_extensions[]` accumulated.

1. Aggregate `proposed_extensions[]` from all agent JSONs.
2. Deduplicate by `(type, description)`.
3. If empty, skip this step.
4. **Pause** and call `AskUserQuestion`. For each extension, options: `accept | note | discard`.
5. Apply decisions:
   - `accept` → add to affected agent's plan, grant `+extension_budget` queries, propagate as a hint.
   - `note` → record in `search-log.md → ### Cross-cutting findings` only.
   - `discard` → record in `search-log.md → ### Strategic adaptations` and ignore.
6. Always log the full decision set in `search-log.md`.

---

## FR-032 — Budget management (orchestrator + agents)

- Source of truth: `outline.yaml → config.query_budget` (default 15 standard, 25 rigorous).
- Each agent owns its budget and increments `budget_consumed` per **search** call (not per fetch).
- 80% threshold → **warn** (agent emits `[milestone:budget_warning]`-equivalent and stops chasing emergent threads / opening new fields).
- 100% → **hard-stop**, set `budget_exhausted: true`, persist JSON, exit.
- The orchestrator may grant `+extension_budget` to specific agents after Step 8 user-accepts an extension. This is the only legal way to extend a budget.

The orchestrator surfaces all budget-exhausted agents in the final summary (Step 12) and in `[milestone:budget_exhausted]` events.

---

## FR-027 — Stop criterion (orchestrator)

After every round, evaluate (in this order — short-circuit allowed):

1. **Matrix coverage complete**: every (item, field) cell has a non-empty `value` OR is in `uncertain[]` OR its agent is `pruned`/`budget_exhausted`. If false → continue.
2. **Saturation OR Diversity**:
   - Saturation: across the most recent 5 queries on each active path, total new findings `< 5` per path → all paths saturated.
   - Diversity: unique domains across all sources `>= 15` (standard) or `>= 25` (rigorous).
   - If at least one is true → STOP.

If both conditions met → emit `[milestone:stop_criterion_met]` and proceed to Step 12.

If only matrix coverage is complete but neither saturation nor diversity → still continue one more round (you have headroom; let the agents probe more). If matrix coverage is incomplete and budget remains → continue.

Defensive cap: a maximum of 5 rounds, regardless. If you hit it, emit `[milestone:round_cap_reached]` and stop.

---

## FR-013/014/015 — Tier assignment + scoring reference

For every URL the agents collect:

```bash
.venv/bin/python -c "
import sys, json
sys.path.insert(0, '.')
from scripts.score_source import assign_tier, score_source, apply_cross_citation_bonus
t = assign_tier('<url>', title='<title>', data_dir='data')
s = score_source('<url>', t['tier'], '<pub_date>', is_historical_topic=False, data_dir='data')
print(json.dumps({**t, **s}))
"
```

The orchestrator runs `apply_cross_citation_bonus(sources, data_dir='data')` once per round over the **full** aggregated source list (Step 6) and writes the bonus back into agent JSONs.

If `assign_tier` returns `unclassified: true`, the orchestrator (or the agent that produced it) MUST:
```bash
.venv/bin/python -c "
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, '.')
from scripts.learnings_write import write_learning
write_learning(
    trigger='self-detection',
    context='<domain or topic>',
    type_='source-classification',
    body='URL <url> could not be classified. Heuristic flags: <flags>.',
    learnings_dir=Path('learnings'),
    today=date.today().isoformat(),
)
"
```

---

## FR-016 — Tier D filtering reference

- Default: `config.include_tier_d == false`. The orchestrator strips Tier D sources from per-field `sources[]` after each round (Step 6).
- If `include_tier_d == true`: Tier D sources stay in but their `score_raw` is unchanged (already reflected by tier weight 0.5).
- If stripping leaves a field with zero sources, mark it `[uncertain]`.

---

## FR-008 — Social signal (orchestrator policy)

The orchestrator does NOT call `/last30days` itself; each agent does, once per round, if `config.social_signal == true`. The orchestrator only:

- Confirms `social_signal` is wired into the agent prompt.
- If an agent reports `last30days_failed: true` in `_meta`, surface the failure in the final summary but do not retry centrally.

---

## FR-033a — Incremental persistence reference

- Agents flush their JSON at every round boundary, AND mid-round every 3–5 fields.
- The orchestrator flushes `search-log.md` after each round + after each Level 2 user decision.
- Lockfile holds for the entire run; release in Step 12 (or in any error path via the catch-all release call).

---

## Status streaming reference (FR-033b — full event list)

| Event | When |
|---|---|
| `[orchestrator] Starting /research-deep for case <case> — <N> items, rigor: <rigor>` | Step 1 |
| `[milestone:resume] X items to process, Y items already complete (skipped)` | Step 4 |
| `[milestone:agent_start] Item: <item>` | Step 5, per agent |
| `[agent:<id>] Done — fields: …` | After each agent returns |
| `[milestone:budget_warning] Agent <id> at 80% budget` | Per agent crossing 80% |
| `[milestone:budget_exhausted] Agent <id> exhausted budget` | Per agent at 100% |
| `[milestone:round_complete] Round <N> complete — X new findings, Y unique domains` | End of each round |
| `[milestone:synthesis_triggered] Intermediate synthesis running` | Step 7 |
| `[milestone:extension_proposed] <N> extensions proposed after round 1` | Step 8 |
| `[milestone:strategic_replan_triggered] <trigger_type>` | Step 10 |
| `[milestone:stop_criterion_met] Matrix complete + (saturation=…, diversity=…)` | Step 9 stop |
| `[milestone:round_cap_reached]` | Defensive 5-round cap |
| `[orchestrator] Run complete. <N> agents, <R> rounds, <S> sources collected.` | Step 12 |

Use the helpers:
```bash
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from scripts.status import orchestrator, milestone, agent; orchestrator('<msg>')"
```

---

## Error handling

- **Lock acquired but error mid-flight**: catch the error, persist whatever JSONs exist, append `## Aborted run — <reason>` to `search-log.md`, release the lock, re-raise.
- **Agent fails entirely (Task tool errors)**: log via `write_learning(trigger='tool-failure', type_='agent-crash', ...)`, mark the unit incomplete, continue with other agents. On next `/research-deep` invocation it will resume.
- **All agents fail in a single round**: emit `[milestone:strategic_replan_triggered] systemic_tool_failure`, pause, ask the user.
- **No `.venv/bin/python`**: this skill cannot run. Fail with: `Project venv not found. Run \`uv venv && uv pip install -e .\` from the project root.`

---

## Quick reference — invoking the skill

```
/research-deep
```

Or, with an explicit case (advanced):
```
/research-deep <case-name>
```

The skill expects:
- `tasks/<case>/outline.yaml` — required.
- `tasks/<case>/fields.yaml` — required if `outline.mode == 'comparative'`.
- `data/` — for tier classification.
- `learnings/` — for cumulative anomaly logs.
- `.config/research-skill/.env` — optional; for `BRAVE_API_KEY` / `EXA_API_KEY`.
- `.venv/` — required.

When this skill returns, the next step in the pipeline is `/research-consolidate`.
