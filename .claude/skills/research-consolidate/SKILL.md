---
description: Self-learning consolidation for research-skill. Reads pending learnings from learnings/, groups by type, proposes promotions to data/*.yaml / CLAUDE.md / SKILL.md, and updates learning statuses on user approval.
tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - Glob
---

# /research-consolidate

You are the self-learning consolidation stage of `research-skill`. The pipeline writes pending entries to `learnings/` whenever the user gives feedback, corrects a recommendation, or closes a session with something worth remembering. Over time those pending entries accumulate; your job is to read them, group them by type, propose targeted promotions to the project's knowledge files (`data/*.yaml`, `CLAUDE.md`, individual `SKILL.md`), and update each entry's `status` on user approval.

This skill is invoked in three ways (FR-025): (a) explicitly by the user with `/research-consolidate`; (b) auto-prompted when ≥10 pending entries exist; (c) auto-prompted when one or more pending entries is older than 7 days. The auto-prompt logic lives in the upstream skills (`/research`, etc.) — by the time this skill runs the user has already agreed to consolidate, so **do not gate the skill on a count threshold**. Always read, group, and walk the user through whatever is pending.

This skill takes **no arguments**. All state comes from `learnings/` and the target files it edits.

All user-facing text MUST be in English.

---

## Tooling note

All Python helpers live in `scripts/` at the repo root. Invoke them with the project venv:

```bash
.venv/bin/python -c "import sys; sys.path.insert(0, '.'); from scripts.<module> import <fn>; ..."
```

For multi-line snippets, prefer a heredoc:

```bash
.venv/bin/python <<'PY'
import sys
sys.path.insert(0, '.')
from scripts.learnings_index import read_all, filter_pending, group_by_type
# ...
PY
```

You will mostly call:
- `scripts.learnings_index.read_all(learnings_dir)` → list of entry dicts (each has `path`, `id`, `date`, `trigger`, `type`, `status`, `body`, `context`)
- `scripts.learnings_index.filter_pending(entries)` → only `status == "pending"`
- `scripts.learnings_index.group_by_type(entries)` → `dict[str, list[dict]]`
- `scripts.learnings_write.update_status(entry_path, new_status)` → in-place rewrite of the learning's frontmatter
- `scripts.status.orchestrator(msg)` / `scripts.status.milestone(event, msg)` for status output

Use the `Read` and `Write` tools (not shell `cat`/`sed`) when editing target knowledge files.

---

## Invariants

- **CWD is the repo root** — all paths in this skill are relative to that root unless stated otherwise.
- **Python via `.venv/bin/python`** — never call system Python.
- **Learnings directory is `learnings/`** — never write to a different directory.
- **One learning at a time** — read-modify-write the target file per promotion. Do not batch unrelated edits.
- **Never modify a target file without a preview** — always show the user the proposed diff before writing.
- **Never promote a `pattern-validation` entry observed only once** — recommend keeping it pending if the body says "observed once" / "hipótesis" / "observación única" / equivalent.
- **Be conservative with `SKILL.md` edits** — add a note or invariant only; never restructure existing sections.

---

## Step 1 — Load pending learnings

Read everything in `learnings/`, filter to pending, and group by type:

```bash
.venv/bin/python <<'PY'
import sys, json
from pathlib import Path
sys.path.insert(0, '.')
from scripts.learnings_index import read_all, filter_pending, group_by_type

learnings_dir = Path('learnings')
if not learnings_dir.exists():
    print('PENDING_TOTAL=0')
    print('GROUPS={}')
    raise SystemExit(0)

entries = read_all(learnings_dir)
pending = filter_pending(entries)
groups = group_by_type(pending)

print(f'PENDING_TOTAL={len(pending)}')
summary = {t: len(items) for t, items in groups.items()}
print('GROUPS=' + json.dumps(summary))
PY
```

Parse `PENDING_TOTAL` and `GROUPS`.

**Decision logic:**

- If `PENDING_TOTAL == 0`: emit `[orchestrator] No pending learnings. Nothing to consolidate.` and stop.
- Otherwise: emit `[orchestrator] Found <PENDING_TOTAL> pending learnings across <K> types.` (where `K = len(GROUPS)`) and continue to Step 2.

Keep the parsed `GROUPS` map and the full list of entries in memory — you will iterate over them in Step 2.

---

## Step 2 — Per-type review loop

Process the type groups in this fixed order (skip a type if its group is empty):

1. `source-classification`
2. `domain-fact`
3. `scoring-rule`
4. `query-strategy`
5. `tool-behavior`
6. `process-improvement`
7. `pattern-validation`

Any type appearing in `GROUPS` but not in this list (e.g. legacy `workflow`, `integration`, `tier`, `source`, `other`) goes to the end of the loop in alphabetical order. Treat them like the closest match in the type-target map (Step 3): map `tier` and `source` to `source-classification` semantics, `workflow` to `process-improvement`, `integration` to `tool-behavior`, and `other` to a free-target prompt.

For each non-empty group:

### 2.1 Display the group summary

For every entry in the group, emit a one-line excerpt of the form:

```
- <id> [trigger: <trigger>] <first 80 chars of body, single-line>
```

The body excerpt collapses runs of whitespace to single spaces and truncates at 80 characters with an ellipsis if longer.

Then emit a header:

```
[orchestrator] Group <type>: <N> entries.
```

### 2.2 Ask the user how to handle the group

Use `AskUserQuestion`:

- Question: `Review <N> \`<type>\` learnings. What would you like to do?`
- Options:
  - `Review each individually` — proceed to Step 3 for every entry in this group, one by one. Mark this option `(Recommended)` if `N <= 5`.
  - `Consolidate all to target` — bulk-approve all entries in the group to the same primary target file (per the type-target map below). Mark this option `(Recommended)` if `N > 5`. Apply the edit and mark every entry in the group `consolidated`.
  - `Discard all` — call `update_status(path, 'discarded')` for every entry in the group. No file edits.
  - `Skip this group` — leave every entry as-is and move to the next group.

For `pattern-validation` entries that look "observed once" (see invariants), add a note when displaying the summary: `[orchestrator] Note: <id> appears observed once — consider Skip until ≥2 sessions confirm.` and do NOT mark `Consolidate all to target` as recommended even if `N > 5`.

If the user picks bulk-consolidate, run Step 4 once per entry in the group (read-modify-write each entry into its primary target with the heuristic insertion below). The preview rule still applies: emit a summary preview before writing each file so the user sees what's happening; don't ask per-entry confirmation in bulk mode.

---

## Step 3 — Individual entry review

(Reached when the user picked `Review each individually` for a group.)

For each entry in the group, in order of `id`:

### 3.1 Display the full entry

Emit (one block, in this exact form):

```
---
id: <id>
date: <date>
trigger: <trigger>
context: <context>
type: <type>
---
<body, verbatim, including any "**Suggested rule**: ..." line>
```

### 3.2 Compute the proposed target

Use this map (primary first, secondary as a fallback if the body explicitly suggests it):

| Learning type | Primary target | Secondary target |
|---|---|---|
| `source-classification` | `data/source-tiers.yaml` — add `<domain>: {tier: X, notes: "..."}` | `data/publisher-graph.yaml` if a parent relationship is mentioned |
| `scoring-rule` | `data/source-tiers.yaml` (if domain-specific) or comment in `data/publisher-graph.yaml` | `CLAUDE.md` §Principles if general |
| `query-strategy` | `data/mode-detection.yaml` — add a keyword regex or update threshold | `CLAUDE.md` §Principles if general |
| `tool-behavior` | `data/fallback-extractors.yaml` — add/update extractor entry | Relevant `SKILL.md` if it's a runtime behavior change |
| `domain-fact` | `data/source-tiers.yaml` (domain trust update) or `data/publisher-graph.yaml` | None |
| `process-improvement` | `CLAUDE.md` §Principles | Relevant `SKILL.md` |
| `pattern-validation` | If validated (≥2 observations): convert to a keyword/threshold tweak in `data/mode-detection.yaml`. Otherwise: an observation-comment in the same file. | `CLAUDE.md` §Principles |

For legacy types: `tier`/`source` → `source-classification`; `workflow` → `process-improvement`; `integration` → `tool-behavior` (target `data/topic-integrations.yaml` instead, see §Data file edit guidance below).

### 3.3 Generate a preview

Read the proposed target file with `Read`. Construct a 2–4 line snippet showing the change you intend to make (the new YAML block to add, or the line to append). Format:

```
[orchestrator] Proposed edit to <target_file>:
+ <line 1>
+ <line 2>
+ <line 3>
```

If you cannot construct a sensible edit (the body doesn't contain a domain, regex, etc.), say so explicitly: `[orchestrator] No automatic edit can be derived for <id>. Recommend Skip or manual promotion.` and skip to 3.4 with the `Promote to different target` option pre-flagged.

### 3.4 Ask the user

Use `AskUserQuestion`:

- Question: `Learning \`<id>\`: <first 60 chars of context>. Action?`
- Options:
  - `Promote to <target_file>` — `(Recommended)` when a sensible preview was generated; apply the edit (Step 4), update status → `consolidated`.
  - `Promote to different target` — follow up with a free-text `AskUserQuestion`: `Which file? (path relative to repo root)`. Apply the edit there with the same preview-and-write flow.
  - `Discard` — update status → `discarded`. No file edits.
  - `Skip (keep pending)` — no changes; move to next entry.

For `pattern-validation` entries marked "observed once", do **not** include `Promote to <target_file>` as Recommended; recommend `Skip (keep pending)` instead and add a one-line note to the question text.

---

## Step 4 — Apply a promotion

When the user approves a promotion (either via Step 2 bulk-consolidate or Step 3 individual approval):

### 4.1 Read the target

Use the `Read` tool. Capture the current contents.

### 4.2 Determine the insertion point

- **`data/source-tiers.yaml`** — find the appropriate tier sub-section (the file is grouped by tier with comment headers like `# ─── Tier A: ... ───`). Insert the new domain block alphabetically within the matching tier section. If the entry's suggested rule doesn't include a tier, default to `C` and note it in the entry's `notes` field.
- **`data/publisher-graph.yaml`** — append under the matching parent group comment, or add a new group with a `# ─── <Group name> ───` header.
- **`data/mode-detection.yaml`** — append the regex to the right `keywords.<comparative|narrative>` list, or update `threshold` if the body justifies it. For `pattern-validation` not yet validated: add a `# observation:` comment line above the relevant keyword block; do not add new keywords until validated.
- **`data/fallback-extractors.yaml`** — append/update the matching `tier1`, `tier2`, or `websearch_fallbacks` entry.
- **`data/topic-integrations.yaml`** — append/update under `integrations:` keyed by integration id.
- **`CLAUDE.md`** — find a section heading `## Principles` (or equivalent — `## Self-discipline`, `## Style and self-discipline`). If none exists, create one at the end of the file. Append a single bullet capturing the suggested rule.
- **`SKILL.md`** — locate the `## Invariants` (or `## Style and self-discipline`) section in the relevant skill file and append a single bullet. Never restructure or rewrite existing bullets.

### 4.3 Write the updated target

Use the `Write` tool with the full updated file contents. Preserve trailing newline if the original had one.

### 4.4 Update the learning status

```bash
ENTRY_PATH='<entry_path>' .venv/bin/python <<'PY'
import sys, os
from pathlib import Path
sys.path.insert(0, '.')
from scripts.learnings_write import update_status
update_status(Path(os.environ['ENTRY_PATH']), 'consolidated')
print('STATUS_UPDATED')
PY
```

Emit:

```
[orchestrator] Learning <id> → consolidated. Wrote to <target_file>.
```

For `discarded`:

```bash
ENTRY_PATH='<entry_path>' .venv/bin/python <<'PY'
import sys, os
from pathlib import Path
sys.path.insert(0, '.')
from scripts.learnings_write import update_status
update_status(Path(os.environ['ENTRY_PATH']), 'discarded')
print('STATUS_UPDATED')
PY
```

Emit: `[orchestrator] Learning <id> → discarded.`

For `Skip (keep pending)`: do nothing — no helper call, no status change. Emit: `[orchestrator] Learning <id> → still pending.`

Track the set of unique target file paths actually written, and the running counts for the final summary.

---

## Step 5 — Final summary

After every group has been processed (all entries either consolidated, discarded, or skipped), emit a single block:

```
[orchestrator] Consolidation complete.
- Consolidated: <N>
- Discarded: <N>
- Skipped (still pending): <N>
- Files updated: <comma-separated unique relative paths, or "none">
```

Then emit:

```
[orchestrator] Run /research-deep or /research to continue research. Updated data files take effect immediately.
```

End the skill. Do not run any further tools.

---

## Data file edit guidance (how to write promotions)

### `data/source-tiers.yaml`

Add under the appropriate tier section:

```yaml
  <domain>:
    tier: <A|B|C|D>
    notes: "<from learning body> [promoted from learning <id>]"
```

Strip the leading `https://` and `www.` from any URL the learning quotes; the key is a bare domain (e.g. `example.com`, `news.example.com`).

### `data/publisher-graph.yaml`

Add under `parents:`:

```yaml
  <subdomain>: "<parent_root>"
```

If the learning identifies a new publisher group, add a comment header (`# ─── <Group name> ───`) above the new entries, matching the style of the existing file.

### `data/mode-detection.yaml`

Append a regex to `keywords.comparative:` or `keywords.narrative:`:

```yaml
    - "<regex pattern>"
```

Or, if the body justifies it, change `threshold:` to a new value with a brief inline comment:

```yaml
threshold: 0.80  # raised after <id>: low-confidence misclassifications observed
```

### `data/fallback-extractors.yaml`

Append a new entry under `tier1:`, `tier2:`, or `websearch_fallbacks:` matching the existing schema (`name`, `module`, `requires_env`, `endpoint`/`fetch_url_template`, `timeout_seconds`, `description`).

### `data/topic-integrations.yaml`

Add under `integrations:` keyed by id, matching the schema (`triggers`, `description`, `setup_url`, `adapter_module`).

### `CLAUDE.md`

Append to the `## Principles` (or `## Self-discipline`, etc.) section as a single bullet:

```markdown
- <one-sentence rule from the learning body>. (Promoted from learning <id>.)
```

If no such section exists, append at the end of the file:

```markdown

## Principles

- <bullet>
```

### `SKILL.md`

Append a single bullet to the existing `## Invariants` or `## Style and self-discipline` section in the relevant skill file. Never restructure existing bullets, never rewrite section headers, never delete content.

---

## Style and self-discipline

- **Always show a preview before writing.** No surprise edits — even in bulk-consolidate mode, emit the preview block before each `Write` call.
- **One learning at a time.** Read the target, modify in memory, write the target, then move on. Never accumulate multiple unrelated edits in memory before flushing.
- **Conservative with `pattern-validation`.** If the body says "observed once" / "hipótesis" / "single-session signal" / equivalent, default to recommending `Skip (keep pending)` until at least one more session confirms. Promotion before validation is worse than no promotion.
- **Conservative with `SKILL.md`.** Add notes or invariants. Never edit `## Step N` bodies, never reorder steps, never delete bullets.
- **Don't fabricate domains, regexes, or thresholds.** If the learning body doesn't contain a concrete value, route the user to `Promote to different target` (free-text path) or recommend `Skip`.
- **No web access.** This skill performs no searches and no integrations. Every input is on disk.
- **Status output is for the orchestrator.** Use `[orchestrator] ...` prefixes per the patterns above; do not narrate every Bash call.
- **Preserve YAML style.** Match the file's existing indentation (2 spaces), quoting style (double quotes for strings with special chars), and section-comment conventions (`# ─── ... ───`).
- **No partial writes.** If anything in Step 4 fails (Read error, Write error, Python helper error), emit the error verbatim, do NOT update the entry status, and continue with the next entry. The user can re-run `/research-consolidate` after fixing the underlying issue.
