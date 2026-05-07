---
description: Synthesis and report generation for research-skill. Validates URLs, calls build_report.py, writes report.md + report.csv, and closes the session with an end-of-session learning prompt.
tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - Glob
---

# /research-report

You are the synthesis stage of the `research-skill` pipeline. The user has already run `/research "<topic>"` (which produced `tasks/<case>/outline.yaml` and optionally `fields.yaml`) and `/research-deep` (which produced one `tasks/<case>/output/<agent_id>.json` per item or subquery). Your job is to read that state, validate every source URL, call `scripts/build_report.py` to produce a markdown report (and CSV in comparative mode), write the artifacts to disk, append to the session log, and close the loop with a one-question learning prompt.

This skill takes **no arguments**. It auto-discovers the active case from `tasks/`. It is purely synthesis — you do not run any new searches or extractions, and you do not modify the agent JSON files.

---

## Tooling note

All Python helpers live in `scripts/` at the repo root. Invoke them with the project venv:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from scripts.<module> import <fn>; ..."
```

You will mostly call:
- `scripts.validate_urls.validate_urls(urls, timeout=10) -> list[dict]`
- `scripts.build_report.build_report(outline, item_jsons, fields_yaml=None, url_validation=None) -> dict`
- `scripts.status.orchestrator(msg)`, `scripts.status.milestone(event, msg)` — for status output
- `scripts.learnings_write.write_learning(...)` — for FR-022 logging

When you need to pass non-trivial Python values (lists of URLs, parsed YAML dicts, the full `item_jsons` list), write a small driver script to a temp file and run it with the venv Python rather than trying to cram it onto a `-c` one-liner. Print results as JSON on stdout and parse them back. Keep these driver scripts small and self-contained; do not commit them.

For YAML parsing, use `yaml` (PyYAML) inside Python — do not try to parse YAML in shell.

---

## Pending-learnings check (FR-025)

Run this check **before anything else**. It can short-circuit the skill if too much un-consolidated feedback has piled up.

```
.venv/bin/python <<'PY'
import sys
sys.path.insert(0, '.')
from pathlib import Path
from scripts.learnings_index import read_all, count_pending_older_than, filter_pending

learnings_dir = Path('learnings')
if not learnings_dir.exists():
    print('PENDING_TOTAL=0')
    print('PENDING_OLDER_7=0')
else:
    entries = read_all(learnings_dir)
    pending = filter_pending(entries)
    older = count_pending_older_than(entries, 7)
    print(f'PENDING_TOTAL={len(pending)}')
    print(f'PENDING_OLDER_7={older}')
PY
```

Parse the two integers from stdout.

To check 24h freshness:

```
.venv/bin/python <<'PY'
import sys, time
from pathlib import Path
sys.path.insert(0, '.')
tasks_dir = Path('tasks')
cutoff = time.time() - 86400
recent = False
if tasks_dir.exists():
    for log in tasks_dir.glob('*/search-log.md'):
        if log.stat().st_mtime > cutoff:
            recent = True
            break
print(f'RECENT_24H={int(recent)}')
PY
```

**Decision logic:**

- **If `PENDING_TOTAL >= 10`:** present an `AskUserQuestion`:
  - Question: "There are <N> pending learnings waiting to be consolidated. Run `/research-consolidate` first?"
  - Options:
    - `Consolidate first` (Recommended) — exit this skill cleanly with `[orchestrator] paused: run /research-consolidate then re-invoke /research-report`. Stop.
    - `Continue anyway` — proceed with the rest of the skill.
- **Else if `PENDING_OLDER_7 > 0`** AND `RECENT_24H=0`: present an `AskUserQuestion`:
  - Question: "<N> pending learnings are older than 7 days. Consolidate before running report?"
  - Options:
    - `Consolidate first` (Recommended) — exit cleanly with `[orchestrator] paused: run /research-consolidate then re-invoke /research-report`. Stop.
    - `Continue anyway` — proceed.

If `RECENT_24H=1`, do NOT prompt about the 7-day-old entries; the user is mid-flow.

If the user chose to consolidate, return immediately. Otherwise continue to Step 1.

---

## Step 1 — Find the active case

The active case is the most recently modified `tasks/*/outline.yaml`. Use `Glob` to enumerate them:

```
pattern: tasks/*/outline.yaml
```

Behavior:
- **Zero matches** → fail with: `No planning artifacts found. Run /research "<topic>" first.` Stop.
- **Exactly one match** → that's the active case. Extract `<case>` from the path (the directory name between `tasks/` and `/outline.yaml`).
- **Multiple matches** → pick the most recently modified by `mtime`. If two are within 60 seconds of each other, list all candidates with their mtimes and ask the user which one to report on via `AskUserQuestion` (one option per case slug, plus a "Cancel" option). If the user cancels, stop.

Emit: `[orchestrator] Active case: <case>`.

---

## Step 2 — Pre-flight checks

1. Confirm `tasks/<case>/outline.yaml` exists (it does, by construction of Step 1). Read it.
2. Confirm at least one file matches `tasks/<case>/output/*.json`. If zero matches, fail with: `No agent outputs found. Run /research-deep first.` Stop.
3. Read every `tasks/<case>/output/*.json` into memory as a list of dicts. Sort them in a stable order — prefer the order of items/subqueries in `outline.yaml` (match by `agent_id` or `item` field), and append any leftovers alphabetically by filename. For narrative mode, match agent JSONs to `outline.yaml` subqueries by the JSON's `subquery` field; for comparative mode, match by the `item` field.
4. Read `tasks/<case>/fields.yaml` if it exists (comparative mode only). If the file is missing in narrative mode, that's fine; pass `fields_yaml=None` later.

Compute a quick summary:
- `N` = total item JSONs loaded
- `M` = count where `budget_exhausted` is falsy AND `pruned` is falsy
- `K` = count where `budget_exhausted` is truthy
- `J` = count where `pruned` is truthy

Emit:
```
[orchestrator] Found N item JSONs — M complete, K budget-exhausted, J pruned.
```

---

## Step 3 — Surface budget-exhausted and pruned items

For each item JSON with `budget_exhausted: true`, emit:
```
[orchestrator] Agent <item> exhausted its query budget. Fields [<comma-separated list of uncertain field names>] are marked [uncertain]. Proceeding with partial data.
```
The "uncertain field names" come from any field in the JSON whose value is missing, empty, or explicitly `null`/`"[uncertain]"`. If you cannot determine which fields are uncertain, just say `Some fields are marked [uncertain]`.

For each item JSON with `pruned: true`, emit:
```
[orchestrator] Agent <item> was pruned (reason: <prune_reason or "not provided">). No evidence found for this item.
```

If `K + J > 0`, ask the user via `AskUserQuestion`:
- Question: `Some agents have partial or pruned outputs. Proceed with report generation?`
- Options: `Proceed` (default), `Cancel — I'll re-run /research-deep first`

If the user picks `Cancel`, emit `[orchestrator] Cancelled by user.` and stop. Otherwise continue.

If `K + J == 0`, do not prompt — proceed silently.

---

## Step 4 — Collect and validate all source URLs (FR-011)

Walk every item JSON and collect every source URL. URLs typically live in fields like `sources`, `evidence`, `citations`, or inline inside field values as JSON arrays of `{title, url, tier}` records. Be liberal — gather any string that looks like an `http(s)://` URL nested anywhere in the JSON, then de-duplicate.

Pass the de-duplicated list to `validate_urls`:

```python
from scripts.validate_urls import validate_urls
results = validate_urls(all_urls)  # list of {url, ok, status_code, method_used, error}
url_validation = {r["url"]: r for r in results}
broken = [r for r in results if not r["ok"]]
```

Emit:
```
[milestone:url-validation] Validated <N> URLs — <len(broken)> broken.
```

If `len(all_urls) == 0`, skip validation entirely and pass `url_validation = {}` to `build_report`. Emit: `[milestone:url-validation] No URLs to validate.`

URL validation can be slow if there are many sources. Set a soft cap: if there are more than 200 unique URLs, emit a heads-up before starting (`Validating 247 URLs — this may take ~1–2 minutes.`) and proceed. Do not parallelise on your own; the helper handles its own pacing.

---

## Step 5 — Generate the report (FR-017/018/019/020)

Call `build_report` with the parsed outline, the list of item JSONs (in stable order from Step 2), the parsed `fields_yaml` (or `None` for narrative mode), and the `url_validation` mapping from Step 4:

```python
from scripts.build_report import build_report
result = build_report(outline, item_jsons, fields_yaml, url_validation)
report_md = result["report_md"]
report_csv = result["report_csv"]
gap_count = result["gap_count"]
broken_url_count = result["broken_url_count"]
```

`build_report` already handles, for both modes:
- Table of contents
- Inline citations `[Title • Tier B](url)`
- A `## Disagreements` section (≥2 Tier A sources disagreeing on a claim)
- A `## Gaps` section (uncertain fields with cause: insufficient evidence, pruned, budget exhausted)
- A `## Sources note` section grouped by Tier A/B/C/D/Unclassified, with sub-sections `### Extraction failures` and `### Broken URLs`

Comparative mode adds a comparison table at the top (rows = items, columns = fields) and produces `report.csv` (one row per item, columns from `fields.yaml`).

Narrative mode produces:
- `## <subquery>` sections (one per subquery, in outline order), each containing the agent's `summary` value with inline citations
- Any additional fields the agent produced (beyond `summary`) appear as sub-sections
- `## Cross-cutting findings` at the end, collecting proposed sub-questions and cross-cutting observations from `proposed_extensions[]` entries (those with `type: "subquery"`)
- `## Sources note` grouped by tier (same as comparative)
- No CSV (`report_csv` will be an empty string)

You do not implement any of this logic yourself — you only orchestrate the call.

---

## Step 6 — Claim-citation validation (FR-020)

After `build_report` returns, scan `report_md` for any field value that is non-empty AND not already marked `[uncertain]` AND has no inline citation (no `[...](http...)` link on the same line or in the immediately following lines belonging to that field).

This is a defensive double-check on top of `build_report` — `build_report` is supposed to enforce this, but if a field slips through, you must mark it `[uncertain]` post-hoc and add it to the Gaps section.

Concretely:
1. Parse the report with a small Python helper (regex over each line, looking for field rows in tables and bullet items inside per-item sections).
2. For each field value with no citation, replace the value with `[uncertain]` and append a line to the `## Gaps` section: `- <item> / <field>: no inline citation produced — marked [uncertain]`.
3. Increment `gap_count` accordingly.

For narrative mode, skip the table-row scan. Instead, check that each `## <subquery>` section contains at least one inline citation (`[...](http...)` link). If a subquery section has no inline citation at all, append to `## Gaps`: `- <subquery>: no inline citation — marked [uncertain]`.

Skip this step if `report_md` is empty or `build_report` raised an error. Never silently drop a value: if you cannot tell whether a citation exists, leave the value as-is and continue.

---

## Step 7 — Write outputs

Write `tasks/<case>/report.md` using the (possibly mutated) `report_md`.

If `report_csv` is non-empty (comparative mode), also write `tasks/<case>/report.csv`.

Emit:
```
[milestone:report-written] Report written to tasks/<case>/report.md (<gap_count> gaps, <broken_url_count> broken URLs).
```

If a CSV was written, also emit: `[milestone:report-written] CSV written to tasks/<case>/report.csv.`

---

## Step 8 — Append to search-log.md

Append a block to `tasks/<case>/search-log.md` (create the file if missing). Use the current local date and time (`YYYY-MM-DD HH:MM`, 24-hour). Tier counts come from grouping the validated sources by their tier as recorded in the item JSONs; an unclassified source counts toward `Unknown`.

Block to append:

```markdown
### Report generated YYYY-MM-DD HH:MM
- Items in report: <N>
- Total sources: <total> (Tier A: <a>, B: <b>, C: <c>, D: <d>, Unknown: <u>)
- Broken URLs: <broken_url_count>
- Gaps: <gap_count>
- CSV: <yes|no>
```

Append (do not overwrite). Ensure there is exactly one blank line between the previous content and this new block.

---

## Step 9 — End-of-session learning prompt (FR-022)

After the report is on disk and the log is updated, ask the user **one** question via `AskUserQuestion`:

- Question: `Anything from this session worth logging?`
- Options:
  - `Yes — I'll type it`
  - `No / skip`

If the user picks `Yes`, ask a follow-up free-text question via `AskUserQuestion`:
- Question: `One-line description of the learning?`
- Provide two options as scaffolds: `Type my answer` (free text) and `Cancel`.

If they provide a description, write it via `learnings_write.write_learning`:

```python
from datetime import date
from pathlib import Path
from scripts.learnings_write import write_learning

write_learning(
    trigger="session-close",
    context=f"/research-report {topic}",  # topic from outline.yaml
    type_="process-improvement",
    body=description,
    learnings_dir=Path("learnings"),
    today=date.today().isoformat(),
)
```

If the user picks `No / skip` or cancels the follow-up, do nothing.

---

## Step 10 — FR-021: Feedback signal detection

While the user is responding to the Step 9 prompt and the follow-up, watch their phrasing for two signals:

1. **Explicit log request** — phrases like "log this", "remember this", "save as a learning", "write this down". If they ask to log something but you've already moved past Step 9, offer one more `AskUserQuestion` to capture it. Use `type_="process-improvement"` unless context clearly suggests another type.

2. **"This result is wrong" flags** — phrases like "this is wrong", "the report got X wrong", "the score for Y is incorrect", "tier B should be tier A". Offer to log as a learning entry. Use:
   - `type_="domain-fact"` if it's a factual correction about the topic (e.g. "X actually launched in 2024, not 2023")
   - `type_="scoring-rule"` if it's about source-tier scoring or prioritisation

Casual unrelated comments ("nice", "ok thanks", "looks good") do **not** trigger this. When in doubt, do not prompt — over-eager logging is worse than missing a signal.

---

## Step 11 — Final status

Emit a concise final line so the parent stage knows you are done:

```
[orchestrator] /research-report complete for <case>.
```

Stop. Do not run any further tools.

---

## Edge cases & failure modes

- **`outline.yaml` is malformed YAML** → emit `[orchestrator] outline.yaml could not be parsed: <error>. Aborting.` and stop. Do not attempt to write any report.
- **One or more `output/*.json` is malformed** → skip that file with a warning (`[orchestrator] Skipping malformed output/<file>: <error>`) and continue with the rest. If zero remain, fail as in Step 2.
- **`build_report` raises** → emit `[orchestrator] build_report failed: <error>. No report written.` and stop. Do not partial-write `report.md`.
- **Disk write fails** → emit the error verbatim and stop. Do not retry.
- **`fields.yaml` missing in comparative mode** → emit `[orchestrator] fields.yaml missing in comparative mode — falling back to narrative-style sections.` Pass `fields_yaml=None` and let `build_report` handle it.
- **All URLs broken** → still write the report. The broken URL section will list everything. Do not block on this.
- **No sources at all in any item JSON** → still write the report; the Gaps section will dominate. Do not block.
- **User cancels at Step 3** → exit cleanly without writing anything. Do not append to `search-log.md`.

---

## Invariants

- Never modify `outline.yaml`, `fields.yaml`, or any `output/*.json`. They are read-only inputs.
- Never run searches or extractions. That is `/research-deep`'s job.
- Never silently drop a field value. If a value lacks a citation, mark it `[uncertain]` and surface it in `## Gaps`.
- Always write `report.md` last (after all in-memory mutations from Step 6 are applied), so a partial run leaves no half-written report on disk.
- Keep status output on `stderr`-style channels (the `scripts.status` helpers handle this) so the report content itself is clean.
