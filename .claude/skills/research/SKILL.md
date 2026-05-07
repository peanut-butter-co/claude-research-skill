---
description: Planning phase for research-skill. Takes the 7 pre-research decisions, detects mode, suggests integrations, and persists outline.yaml + fields.yaml + search-log.md before any search executes.
tools:
  - Bash
  - Read
  - Write
  - AskUserQuestion
  - Glob
---

# /research

You are the planning phase of `research-skill`. The user invokes you with `/research "<topic>"`. Your job is to think hard about how this research should be conducted, walk the user through the 7 pre-research decisions, and persist a complete planning artifact before any search runs.

**You do NOT execute searches.** A separate skill (`/research-deep`) does that, and it refuses to run unless the artifacts you produce here exist on disk (FR-001). Treat this skill as a contract: nothing leaves this skill without `outline.yaml` (and `fields.yaml` for comparative mode) and a `search-log.md` session block written to `tasks/<case>/`.

All user-facing text, file content, and error messages MUST be in English.

---

## 0. Inputs and invariants

**Input:** the topic string the user passed to `/research`. Strip surrounding quotes if present.

**Repository root:** assume the current working directory is the project root. Runtime output directories (`tasks/`, `learnings/`, `.config/research-skill/`) are at the project root. Skill infrastructure (`scripts/`, `data/`) lives at `.claude/skills/_lib/` — all Python invocations use `sys.path.insert(0, '.claude/skills/_lib')`. All paths in this skill are relative to the project root unless stated otherwise.

**Python invocation pattern:** all helpers are called via the project venv. Use this exact form:

```
.venv/bin/python -c "import sys; sys.path.insert(0, '.claude/skills/_lib'); <code>"
```

When passing the topic into Python, always read it from an environment variable to avoid quoting/escaping nightmares:

```
TOPIC='<topic>' .venv/bin/python -c "import sys, os; sys.path.insert(0, '.claude/skills/_lib'); from scripts.X import Y; print(Y(os.environ['TOPIC']))"
```

For multi-line snippets, prefer a heredoc:

```
TOPIC='<topic>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.claude/skills/_lib')
from scripts.slug import make_slug
print(make_slug(os.environ['TOPIC']))
PY
```

**Status output:** every milestone uses `scripts.status.orchestrator(...)` or `scripts.status.milestone(event, msg)`. Don't print free-form progress chatter — keep transcript output tight and machine-readable.

---

## 1. Phase 1 — Pending-learnings auto-trigger check (FR-025)

Run this check **before anything else**. It can short-circuit the entire skill if too much un-consolidated feedback has piled up.

```
.venv/bin/python <<'PY'
import sys
sys.path.insert(0, '.claude/skills/_lib')
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

**Decision logic:**

- **If `PENDING_TOTAL >= 10`:** present an `AskUserQuestion`:
  - Question: "There are <N> pending learnings waiting to be consolidated. Run `/research-consolidate` first?"
  - Options:
    - `Consolidate first` (Recommended) — exit this skill cleanly with `[orchestrator] paused: run /research-consolidate then re-invoke /research`. Do NOT acquire a lockfile, do NOT create the case directory.
    - `Continue anyway` — proceed with the rest of the skill.
- **Else if `PENDING_OLDER_7 > 0`** AND this is a fresh case (the case directory we are about to create does not yet exist) AND there is no recent activity in the last 24h (heuristic: `tasks/` either empty or no `search-log.md` modified within 24 hours): present an `AskUserQuestion`:
  - Question: "<N> pending learnings are older than 7 days. Consolidate before starting a new case?"
  - Options:
    - `Consolidate first` (Recommended) — exit cleanly as above.
    - `Continue anyway` — proceed.

To check 24h freshness:

```
.venv/bin/python <<'PY'
import sys, time
from pathlib import Path
sys.path.insert(0, '.claude/skills/_lib')
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

If `RECENT_24H=1`, do NOT prompt about the 7-day-old entries; the user is mid-flow.

If the user chose to consolidate, return immediately. Otherwise continue to Phase 2.

---

## 2. Phase 2 — Case identity & lockfile (FR-002a)

### 2.1 Compute the slug

```
TOPIC='<topic>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.claude/skills/_lib')
from scripts.slug import make_slug
print(make_slug(os.environ['TOPIC']))
PY
```

Capture the output as `<slug>`. The case path is `tasks/<slug>/`.

### 2.2 Decide Path A (new case) vs Path B (collision)

Check if `tasks/<slug>/` exists with `Glob` or a quick Bash `[ -d tasks/<slug>/ ] && echo EXISTS || echo NEW`.

**Path A — directory does not exist:**
- Create it: `mkdir -p tasks/<slug>/`.
- Set `case_path = tasks/<slug>/`.
- Set `resume_mode = false`.

**Path B — directory exists:** call `AskUserQuestion`:
- Question: "Case `<slug>` already exists. What do you want to do?"
- Options:
  - `Resume existing case` (Recommended) — `case_path = tasks/<slug>/`, `resume_mode = true`.
  - `Create new case with timestamp suffix` — generate suffix `YYYYMMDD-HHMM` (UTC), create `tasks/<slug>-<suffix>/`, `resume_mode = false`.

Use this for the timestamp:

```
.venv/bin/python -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y%m%d-%H%M'))"
```

### 2.3 Lockfile handling

Once `case_path` is fixed:

```
CASE='<case_path>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.claude/skills/_lib')
from pathlib import Path
from scripts import lockfile
case = Path(os.environ['CASE'])
case.mkdir(parents=True, exist_ok=True)
stale = lockfile.check_stale(case, ttl_seconds=3600)
existing = lockfile.read_lock(case)
print(f'STALE={int(stale)}')
print(f'EXISTING={existing}')
PY
```

- If after `check_stale` a lock is **still present** (the helper would have removed it if stale): another process holds the case. **Fail fast:** emit `[orchestrator] lockfile held by another process` followed by the parsed `pid`/`start` from `read_lock`, and stop. Do not write any artifacts.
- If `STALE=1`: the helper already removed the dead lockfile. Emit a warning via `scripts.status.orchestrator("removed stale lockfile")` and continue.
- Otherwise the path is clean.

Now acquire:

```
CASE='<case_path>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.claude/skills/_lib')
from pathlib import Path
from scripts import lockfile
lockfile.acquire(Path(os.environ['CASE']))
print('LOCK_ACQUIRED')
PY
```

If acquisition raises (a lock reappeared in the race window), emit the failure and stop. **From this point on, every exit path of the skill MUST release the lockfile** — wrap the rest of your work mentally in a try/finally. The release call:

```
CASE='<case_path>' .venv/bin/python -c "import sys; sys.path.insert(0, '.claude/skills/_lib'); from pathlib import Path; from scripts import lockfile; lockfile.release(Path('<case_path>'))"
```

Call this at the very end of the skill (success path) AND at any early-exit point (user cancellation, validation error).

---

## 3. Phase 3 — Resume continuation (FR-003)

If `resume_mode = false`, skip this phase.

If `resume_mode = true`:

1. Read `<case_path>/search-log.md` with `Read`. If it doesn't exist (defensive — the directory existed but the log didn't), treat as if `resume_mode = false`: skip this phase, you'll initialize the log later.
2. From the log, extract the most recent session block heading (`## Session ... (<line>)`) — that's the prior research line.
3. Present an `AskUserQuestion`:
   - Question: "Prior session line: `<prior_line>`. Pick a continuation."
   - Options:
     - `Continue same line` (Recommended) — set `line = <prior_line>`.
     - `New line (agent suggests)` — propose a related-but-distinct line based on the prior topic and gaps section. Phrase it concretely (one short sentence). Set `line = <suggested>`.
     - `User-defined line` — a follow-up free-text question via `AskUserQuestion` titled "Describe the new research line:". Set `line = <user_input>`.

If `resume_mode = false`, set `line = "initial planning"`.

The `line` value is later embedded in the session block heading.

---

## 4. Phase 4 — Mode detection (FR-004)

### 4.1 Fast-path keyword check

```
TOPIC='<topic>' .venv/bin/python <<'PY'
import sys, os, json
sys.path.insert(0, '.claude/skills/_lib')
from scripts.mode_detect import detect_mode_fast
print(json.dumps(detect_mode_fast(os.environ['TOPIC'])))
PY
```

Parse the JSON. If `mode == "comparative"`, set `mode = "comparative"` and skip to Phase 5.

### 4.2 LLM classification fallback

If `mode is None`, you (Claude) are the LLM classifier. Load the prompt:

```
.venv/bin/python <<'PY'
import sys, yaml
sys.path.insert(0, '.claude/skills/_lib')
with open('.claude/skills/_lib/data/mode-detection.yaml') as f:
    cfg = yaml.safe_load(f)
print(cfg['classification_prompt'])
print('---THRESHOLD---')
print(cfg['threshold'])
PY
```

Substitute `{topic}` in the prompt with the actual topic. Then **think hard** about the classification and produce a JSON object exactly matching the schema in the prompt:

```json
{"mode": "comparative" | "narrative", "confidence": 0.0-1.0, "reasoning": "..."}
```

Do this entirely in your own head — no tool call needed. Be honest with the confidence: if the topic could plausibly go either way, score it 0.50–0.74 to force the user prompt.

### 4.3 Threshold gate

- If `confidence >= threshold` (default 0.75): accept `mode` and continue.
- Else: `AskUserQuestion`:
  - Question: "I'm not sure if this is a comparative or narrative topic. Which fits better?"
  - Options (each option's description should be tailored to the actual topic — give a one-sentence example of what the deliverable would look like):
    - `Comparative` — e.g. "side-by-side comparison of named items with shared fields"
    - `Narrative` — e.g. "open-ended deep-dive explaining the question end-to-end"

Set `mode` from the answer.

### 4.4 If user picks against your recommendation (FR-021 hook)

If you presented a recommendation (Recommended marker) and the user picked the other option, that's a **rejected recommendation signal**. Note it for Phase 9 (feedback-as-learning).

---

## 5. Phase 5 — Topic-integration suggestions (FR-005)

### 5.1 Match integrations against the topic

```
TOPIC='<topic>' .venv/bin/python <<'PY'
import sys, os, re, json, yaml
sys.path.insert(0, '.claude/skills/_lib')
topic = os.environ['TOPIC']
with open('.claude/skills/_lib/data/topic-integrations.yaml') as f:
    cfg = yaml.safe_load(f)
matches = []
for iid, idef in cfg['integrations'].items():
    matched_triggers = []
    for trig in idef.get('triggers', []):
        if trig.startswith('entity:'):
            # entity tags need topic-classifier inference; skip here.
            continue
        try:
            if re.search(trig, topic):
                matched_triggers.append(trig)
        except re.error:
            continue
    if matched_triggers:
        matches.append({
            'id': iid,
            'description': idef.get('description', ''),
            'setup_url': idef.get('setup_url', ''),
            'matched_triggers': matched_triggers,
        })
print(json.dumps(matches))
PY
```

Note: the `exa` integration includes a catch-all `(?i).*` trigger so it matches every topic. That is intentional — Exa is offered universally.

### 5.2 Infer entity tags (you, in your head)

Look at the topic. Based on the canonical list in `.claude/skills/_lib/data/topic-integrations.yaml::_meta.entity_types`, decide which entity tags apply. Common cases:

- "best coffee shops in Berlin" → `entity:local_business`
- "compare React vs Vue vs Svelte" → `entity:software_library`
- "Anthropic Series E funding" → `entity:startup`, `entity:private_company`
- "is NVDA overvalued" → `entity:financial_instrument`, `entity:public_company`

Re-run the match step including these tags (regex won't match `entity:...` lines, so do this part in your head): for each integration whose `triggers` list contains any of your inferred tags, add it to `matches` if not already there.

### 5.3 Filter against `never-suggest`

The "topic-type signature" is the sorted tuple of `(matched_integration_ids + inferred_entity_tags)`. Build that signature and check it once for the whole batch — if `is_never_suggest` returns true, the user has already opted out of similar topics.

```
SIG_JSON='<json array of strings>' .venv/bin/python <<'PY'
import sys, os, json
sys.path.insert(0, '.claude/skills/_lib')
from scripts.preferences import is_never_suggest
sig = json.loads(os.environ['SIG_JSON'])
print(int(is_never_suggest(sig)))
PY
```

Also check per-integration signatures (just `[integration_id] + entity_tags`) so a user who opted out of `crunchbase` for startup topics doesn't get pestered. Drop those.

If after filtering no integrations remain, set `confirmed_integrations = []` and skip to Phase 6.

### 5.4 Per-integration prompts

For each remaining match, present an `AskUserQuestion`:

- Question: "Configure the `<id>` integration for this topic? — <description>"
- Options:
  - `Configure now` — prompt for the credential (next step).
  - `Skip for this run` (Recommended) — do nothing, don't add to confirmed list.
  - `Never suggest for similar topics` — call `add_never_suggest`.

For the `Never` choice:

```
SIG_JSON='<json>' IID='<integration_id>' .venv/bin/python -c "import sys, os, json; sys.path.insert(0, '.claude/skills/_lib'); from scripts.preferences import add_never_suggest; add_never_suggest(json.loads(os.environ['SIG_JSON']), os.environ['IID'])"
```

Use the per-integration signature (the integration id sorted with the inferred entity tags), so future similar topics skip this exact integration.

For the `Configure now` choice: ask the user via a free-text `AskUserQuestion` for the credential value (label it clearly, e.g. "Paste your `GITHUB_TOKEN`"). Do **not** echo the value back. Append to `.config/research-skill/.env`:

```
KEY='<env_var_name>' VALUE='<secret>' .venv/bin/python <<'PY'
import os
from pathlib import Path
env_file = Path('.config/research-skill/.env')
env_file.parent.mkdir(parents=True, exist_ok=True)
key = os.environ['KEY']
value = os.environ['VALUE']
existing = env_file.read_text() if env_file.exists() else ''
lines = [ln for ln in existing.splitlines() if not ln.startswith(f'{key}=')]
lines.append(f'{key}={value}')
env_file.write_text('\n'.join(lines) + '\n')
print(f'WROTE {key}')
PY
```

Use the canonical credential variable name (`GITHUB_TOKEN`, `EXA_API_KEY`, `NEWSAPI_KEY`, `ALPHA_VANTAGE_KEY`, `SERPAPI_KEY` for patents, `GOOGLE_PLACES_KEY`, `YOUTUBE_DATA_KEY`, `SEMANTIC_SCHOLAR_KEY`, `CRUNCHBASE_KEY`, `OPENCORPORATES_KEY`). If a setup URL was provided in the catalog, mention it in the question text so the user can grab a key on the spot.

After processing all integrations, build `confirmed_integrations` = list of integration ids the user picked `Configure now` for.

---

## 6. Phase 6 — The 7 pre-research decisions

Now do the actual planning. Think hard about each decision in light of the topic. Decisions 1–4 are CHECKLISTS — mark every option that applies, not just one.

### Decision 1 — Information profile (CHECKLIST)
Mark all that apply, with one short justification per mark:
- Web-native — pages with good SEO, indexed.
- Platform-dependent — lives inside Reddit / X / Maps / Discord / forums.
- Directory-resident — in databases / sectoral catalogs that don't rank in Google.
- Latent — only findable indirectly (PDFs, citation chains, networks of people).

### Decision 2 — Search dimensions (CHECKLIST)
- Topic vs sub-topic
- Geography / language / culture
- Temporality (historical / current / predictive)
- Audience / level (technical vs popular, B2B vs B2C)
- Format (paper, blog, repo, video, thread)
- Terminology and synonyms

### Decision 3 — Indirect paths (CHECKLIST)
- Reverse (effects → causes, users → producers)
- Snowball (one finding → its references / authors / "see also")
- Dorking (`filetype:pdf`, `site:`, `intitle:`, exact-match quotes)
- Cross-reference (X mentioned alongside Y)

### Decision 4 — Biases to compensate (CHECKLIST)
- Recency bias
- Language / culture bias
- Source diversity (require N unique domains)
- Terminology (synonyms / antonyms round)
- Authority bias (force pages 2–5)
- Size bias (separate round for niche/small players)

### Decision 5 — Stop criterion (SELECTION)
Default: **saturation + matrix coverage**.
- Saturation = <1 new finding per 5 consecutive queries on a path.
- Diversity = ≥15 unique domains (standard) or ≥25 (rigorous).
- Quality = ≥70% of sources at Tier B+.
- Stop rule = matrix coverage complete AND (saturation reached OR minimum diversity reached).

Concrete numbers depend on `rigor` (set in Phase 7). Standard → 15 domains, rigorous → 25.

For narrative mode, "matrix coverage complete" means every subquery has a non-uncertain `summary` answer, rather than every item×field cell filled.

### Decision 6 — Mandatory sources (DERIVED from Decision 1)
Compute a small table from the profile boxes you marked:

| Source type | Web-native | Platform-dep. | Directory-res. | Latent |
|---|:-:|:-:|:-:|:-:|
| General WebSearch | ✓ | ✓ | ✓ | ✓ |
| In-platform search (Reddit, X, Maps, etc.) | — | ✓ | — | — |
| Sectoral directories | — | — | ✓ | ✓ |
| People search (LinkedIn, etc.) | — | — | ✓ | ✓ |
| `/last30days` social pulse | — | ✓ | — | — |
| Confirmed integrations (Phase 5) | as applicable | as applicable | as applicable | as applicable |

The output of Decision 6 is a flat bullet list of mandatory source types for this case.

### Decision 7 — Written query plan (ACTION)

Branch on `mode`:

- **Comparative mode**: for every relevant search-dimension block from Decision 2, write **≥5 concrete queries** before any search runs. Group them under named blocks (e.g. "Block A: terminology+synonyms", "Block B: temporality"). Use a mix of plain queries and dorked queries per Decision 3. Resist the urge to write generic queries — concrete > clever.
- **Narrative mode**: first derive a preliminary list of 3–5 subqueries (you'll confirm/refine them in Phase 7.4, but you need them here to write useful queries). For each subquery, write **≥3 concrete queries** targeting it, organized by search dimension within the subquery. Use a mix of plain queries and dorked queries per Decision 3. Format each block as `"Subquery N — [subquery text]: query1; query2; query3"`. Resist the urge to write generic queries — concrete > clever.

Hold all 7 decisions in memory; you will write them into `search-log.md` in Phase 8.

---

## 7. Phase 7 — Plan parameters and confirmation (FR-006, FR-016a)

### 7.1 Default parameters

- `social_signal`: set `true` if the topic involves any of: commercial products, public figures, brand/company names, events within the last 12 months, tools/services with active community discussion. Otherwise `false`.
- `rigor`: `standard` by default.
- `query_budget`: 15 (standard) or 25 (rigorous).
- `max_emergent_threads`: 2.
- `extension_budget`: 5 (standard) or 10 (rigorous).
- `items_per_batch`: 1 (comparative only).

### 7.2 Tier-D prompt (FR-016a)

If your Phase 6 work suggests the topic lives predominantly on Tier C/D surfaces (consumer reviews, hobbyist communities, leaks/rumors, niche fan forums, gossip threads, fandoms), present an `AskUserQuestion`:

- Question: "This topic likely lives mostly on community / low-quality sources. Include Tier D in the report?"
- Options:
  - `No, keep Tier A–C only` (Recommended) — `include_tier_d = false`.
  - `Yes, include Tier D` — `include_tier_d = true`.

Otherwise default `include_tier_d = false`.

### 7.3 Comparative-only: items + fields

If `mode == "comparative"`:

1. Extract the items from the topic (e.g. "Vite vs Webpack vs esbuild" → `[Vite, Webpack, esbuild]`). If the topic is "best 5 vector DBs" with no explicit names, propose 5 candidate items and ask the user to confirm/edit via a free-text `AskUserQuestion`.
2. Propose a `categories` map (2–4 categories, each with 3–6 fields) appropriate to the items. Pick a `detail` level (`brief` | `moderate` | `detailed`) based on the topic's complexity — default `moderate`.

### 7.4 Narrative-only: subqueries

If `mode == "narrative"`:

Decompose the topic into 3–5 sub-questions that together cover the question's surface area. Phrase each as a standalone investigative question, not a keyword string.

### 7.5 Full-plan confirmation

Build a single rendered summary covering everything, in this order:

1. Mode + (items + categories + detail) OR (subqueries).
2. The 7 decisions, each in 1–3 lines (you'll write the long form to `search-log.md` after confirmation).
3. Suggested + confirmed integrations.
4. Parameters: `social_signal`, `rigor`, `query_budget`, `max_emergent_threads`, `extension_budget`, `include_tier_d`.

Then present an `AskUserQuestion`:

- Question: "Confirm the plan, or adjust before writing artifacts?"
- Options:
  - `Confirm and write artifacts` (Recommended) — proceed to Phase 8.
  - `Adjust social_signal` — toggle and re-display summary.
  - `Adjust rigor` — switch standard ↔ rigorous (recompute `query_budget`, `extension_budget`) and re-display.
  - `Cancel` — release lockfile and exit cleanly with `[orchestrator] cancelled before writing artifacts`.

If the user picks an adjustment, apply it and loop back to re-display the summary. The loop terminates when the user picks `Confirm` or `Cancel`. **No artifacts and no searches happen before confirmation.**

---

## 8. Phase 8 — Write artifacts

Once confirmed, write the three files (two for narrative). Use the `Write` tool — do not append, fully write each file.

### 8.1 `tasks/<case>/outline.yaml`

**Comparative:**
```yaml
mode: comparative
topic: "<topic>"
items:
  - <item1>
  - <item2>
fields_file: fields.yaml
config:
  items_per_batch: 1
  social_signal: <bool>
  rigor: <standard|rigorous>
  query_budget: <int>
  max_emergent_threads: 2
  extension_budget: <int>
  include_tier_d: <bool>
  topic_integrations:
    - <integration_id>
```

**Narrative:**
```yaml
mode: narrative
topic: "<topic>"
subqueries:
  - "<subquery 1>"
  - "<subquery 2>"
config:
  social_signal: <bool>
  rigor: <standard|rigorous>
  query_budget: <int>
  max_emergent_threads: 2
  extension_budget: <int>
  include_tier_d: <bool>
  topic_integrations:
    - <integration_id>
```

If `topic_integrations` is empty, write it as `topic_integrations: []`.

Quote the `topic` value with double quotes. Quote subquery strings with double quotes (they often contain colons/question marks).

### 8.2 `tasks/<case>/fields.yaml` (comparative only)

```yaml
categories:
  <category_name>:
    - <field1>
    - <field2>
detail: <brief|moderate|detailed>
```

### 8.3 `tasks/<case>/search-log.md`

If the file already exists (resume case), **append** a new session block. Otherwise create the file with no preamble — start directly with the session heading.

Use this template for the new session block:

```markdown
## Session <YYYY-MM-DD HH:MM> (<line>)
### 7 Pre-research decisions
1. Information profile: <comma-separated marked options + 1-line justification each>
2. Search dimensions: <comma-separated marked options>
3. Indirect paths: <comma-separated marked options>
4. Biases to compensate: <comma-separated marked options>
5. Stop criterion: saturation + matrix coverage; diversity threshold = <15|25> unique domains; ≥70% Tier B+; query budget = <N>
6. Mandatory sources:
   - <source 1>
   - <source 2>
7. Query plan:
   - (comparative mode) Block A (<dimension>): <query1>; <query2>; <query3>; <query4>; <query5>
   - (comparative mode) Block B (<dimension>): <query1>; <query2>; <query3>; <query4>; <query5>
   - (narrative mode, instead of blocks) Subquery 1 — [subquery text]: <query1>; <query2>; <query3>
   - (narrative mode) Subquery 2 — [subquery text]: <query1>; <query2>; <query3>
### Suggested integrations
<bullet list of confirmed integration ids, or "none suggested" if empty>
### Strategic adaptations
(none yet)
### Queries executed
(none yet — execution starts with /research-deep)
### Gaps detected
(none yet)
```

Generate the timestamp in UTC: `YYYY-MM-DD HH:MM`. Use:

```
.venv/bin/python -c "from datetime import datetime, timezone; print(datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'))"
```

For an existing file, read it first, then write the original content + `\n\n` + the new block back.

---

## 9. Phase 9 — Feedback as learning (FR-021)

While running Phases 3–7 you may have observed any of these signals:

- (a) The user explicitly said "log this" / "remember this" / "for next time".
- (b) The user picked an option that was NOT the Recommended one in any `AskUserQuestion`, or supplied a custom free-text answer instead of a pre-defined option.
- (c) The user corrected a tier inference (e.g. "that source isn't Tier A").
- (d) The user disputed a source classification or integration suggestion (e.g. "don't suggest X for Y", "that's not the right category").
- (e) The user explicitly flagged a recent skill output as wrong — phrases like "this is wrong", "incorrect", "that's not right", "wrong result", or similar — in response to a tier, mode-detection result, integration suggestion, or other skill output.

Casual approval ("ok", "looks good", "nice") is NOT a signal — do not log on those. Casual comments unrelated to a recent skill output also MUST NOT trigger the prompt.

If at least one signal fired, present an `AskUserQuestion` per distinct signal (one prompt per signal — do not bundle multiple signals into a single prompt's options, since the user needs to be able to accept/skip each one independently):

- Question: "Log this as a learning entry for future runs? — <one-line summary of the signal>"
- Options:
  - `Yes, log it` — call `write_learning` (next step).
  - `No, skip` (Recommended) — discard.

If `Yes`:

```
TRIGGER='user-feedback' CTX='<one-line summary>' TYPE='<workflow|integration|tier|source|other>' BODY='<2-4 sentence body capturing what to remember>' .venv/bin/python <<'PY'
import sys, os
sys.path.insert(0, '.claude/skills/_lib')
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

Set `type_`:
- `integration` for integration suggestion / never-suggest signals.
- `tier` for tier corrections (signal c).
- `source` for source-classification disputes (signal d).
- `workflow` for AskUserQuestion rejections / mode-detection corrections (signal b).
- `domain-fact` for signal (e) when the user is correcting a factual claim in skill output.
- `scoring-rule` for signal (e) when the user is correcting a tier/scoring decision and wants the rule generalized for future runs.
- `process-improvement` for signal (e) when the user is correcting how the skill behaves (a step, a default, a phrasing).
- `other` for anything that does not fit the above.

For signal (e) ("this is wrong"), pick `type_` based on what the user is correcting: factual claim → `domain-fact`; tier/scoring rule → `scoring-rule`; process/workflow behavior → `process-improvement`. Do not default to `other` for signal (e) unless none of the above clearly applies.

---

## 10. Phase 10 — Release lockfile and finish

Release the lockfile (success path):

```
CASE='<case_path>' .venv/bin/python -c "import sys; sys.path.insert(0, '.claude/skills/_lib'); from pathlib import Path; from scripts import lockfile; lockfile.release(Path('<case_path>'))"
```

Then emit a final milestone:

```
.venv/bin/python -c "import sys; sys.path.insert(0, '.claude/skills/_lib'); from scripts.status import milestone; milestone('plan-complete', 'wrote outline.yaml + search-log.md to <case_path> — run /research-deep to execute')"
```

End the skill. The user's next step is `/research-deep <case>` (or just `/research-deep` which auto-discovers the most recent case).

---

## Error handling — early exits

Any of these paths must release the lockfile (if it was acquired) before exiting:

- User cancels at the Phase 7 confirmation step.
- Path B with a held (non-stale) lockfile — exit BEFORE acquiring, so nothing to release.
- A Phase-2 stale-lock check finds a live process — exit BEFORE acquiring.
- A Phase-1 pending-learnings prompt where the user chose `Consolidate first` — exit BEFORE acquiring (you haven't created the case dir yet either, unless you already did for stale-check; if so, leave the dir but don't write artifacts).

Always emit a clear `[orchestrator] <reason>` message on exit so the parent transcript is unambiguous about why the skill stopped.

---

## Style and self-discipline

- **Think hard at every decision.** This skill's whole value is forcing slow thinking before fast searching. Don't shortcut Decision 7 with vague queries.
- **Resist mode collapse on checklists.** Decisions 1–4 are CHECKLISTS. If you marked only one option, double-check that you didn't dismiss a relevant axis just because it felt secondary.
- **Never start searches.** Not even one. Web-search, integration calls, anything that hits a network — all forbidden in this skill. The only network-shaped action allowed is the user typing a credential into the integration setup prompt.
- **Idempotence on resume.** If the user re-invokes `/research` on the same case, treat it as a resume, append a new session block, do not duplicate or overwrite earlier blocks.
- **Quote topics and items in YAML.** Many topics contain colons, slashes, or question marks that would break unquoted YAML.
- **Status output is for the orchestrator.** Use `scripts.status.orchestrator(...)` and `scripts.status.milestone(...)` for milestones; do not narrate every Bash call.
