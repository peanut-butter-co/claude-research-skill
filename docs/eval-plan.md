# Eval plan for research-skill

A layered approach for evaluating changes to the four skills (`/research`, `/research-deep`, `/research-report`, `/research-consolidate`). Cheapest layers run on every PR; expensive layers gate releases.

## Layer 1 — Unit tests for `scripts/` (network-free)

Per CLAUDE.md Principles I & II, scripts are deterministic and tests must run without live network. Coverage targets:

- **`assign_tier()`** — curated dataset of ~200 URLs with ground-truth tier labels (A/B/C/D). Track misclassification rate. **Concrete signal:** the Fever Originals run (2026-05-08) produced 97/106 sources tier=Unknown — clear regression target for this eval.
- **`score_source()` + `apply_cross_citation_bonus()`** — fixture-based tests with known scoring expectations (date decay, publisher graph, cross-citation matrix).
- **`mode_detect_fast()`** — curated topics with ground-truth `comparative|narrative` labels; track regex precision/recall.
- **`slug`, `validate_urls`, `lockfile`, `learnings_index`, `preferences`** — trivial unit tests for edge cases (collisions, stale TTLs, malformed YAML, never-suggest signatures).

**Cost:** ~free, runs in seconds. **Cadence:** every PR.

## Layer 2 — Frozen-fixture component evals

For the LLM-driven parts where ground truth is hard, snapshot real cases as committed fixtures:

- `evals/fixtures/<case>/` — committed `outline.yaml`, `output/*.json`, `search-log.md` from real runs (PII scrubbed).
- Re-run `/research-report` against each fixture and diff the output: report length, citation count, gap count, structural sections present, broken-URL count.
- Catches regressions in `build_report.py` synthesis logic without touching the network or spawning agents.

**Cost:** seconds per fixture, no LLM tokens. **Cadence:** every PR.
**Maintenance cost:** fixtures need refresh when report format intentionally changes (accept the cost — the diff is the point).

## Layer 3 — LLM-as-judge on end-to-end quality

The only layer that detects *research quality* regressions (not just code regressions). For 5–10 curated topics with hand-built answer keys (known event series, known cities, known competitors, etc.):

1. Run the full pipeline (`/research` → `/research-deep` → `/research-report`).
2. Grade with an Opus-based judge using structured rubrics:
   - **Coverage** — of N items in the answer key, how many appear in the report?
   - **Citation faithfulness** — sample 10 claims, fetch each cited URL, ask judge "does this source support this claim?". Track support rate.
   - **Tier accuracy** — judge re-tiers sources independently; compare with skill output.
   - **Subquery quality** — judge grades whether the 3–5 subqueries cover the topic surface area.
   - **Comprehensiveness** — judge identifies missing major angles.

**Cost:** ~430K tokens per topic × N topics × judge tokens. **Cadence:** weekly or per-release.
**Risk:** judge variance — average over 3 runs per metric to reduce noise.

## Layer 4 — A/B harness for prompt changes

Most edits to this skill change SKILL.md prompts, not Python code. A/B runner:

1. Takes two skill versions (git refs or copies).
2. Runs both on the same fixture topic with **record/replay HTTP cache** for WebSearch + WebFetch responses.
3. Outputs a structured diff: 7 decisions, subqueries, agent JSONs, final report.
4. Side-by-side LLM judge: "which version produced a better report? cite specific differences."

**Critical:** without HTTP record/replay, randomness from live search makes A/B comparison meaningless. Use a tool like `vcrpy` or a custom cassette layer keyed on (query, url).

**Cost:** moderate (cached responses + 2 runs + judge). **Cadence:** when iterating on a prompt change.

## Where to start

Build **Layer 1 tier-classification eval** first:

- Bounded dataset (~200 URLs is enough).
- Unambiguous metric (precision/recall per tier).
- Clear signal already exists (97/106 Unknown in last run).
- Pattern reuses for mode-detection and source-scoring evals.

Once Layer 1 is in place, add Layer 2 fixtures from real cases. Defer Layer 3/4 until the skill is stable enough that quality gating matters more than rapid iteration.

## Suggested directory structure

```
evals/
  datasets/
    tier_urls.yaml          # ground-truth URL → tier mappings
    mode_topics.yaml        # ground-truth topic → mode mappings
    answer_keys/
      fever_originals.yaml  # known events, cities, partnerships
      <other_topic>.yaml
  fixtures/
    <case_slug>/            # snapshots of real runs
      outline.yaml
      output/*.json
      search-log.md
  runners/
    run_tier_eval.py        # Layer 1
    run_fixture_eval.py     # Layer 2
    run_e2e_eval.py         # Layer 3
    run_ab_eval.py          # Layer 4
  judges/
    coverage_rubric.md
    faithfulness_rubric.md
    tier_rubric.md
  results/
    YYYY-MM-DD/             # historical runs for tracking regressions
      tier_eval.json
      fixture_eval.json
      e2e_eval.json
```

## Open questions

- **HTTP record/replay tool**: vcrpy vs. custom cassettes vs. mitmproxy?
- **Judge model**: Opus 4.7 for quality, but cost adds up — Sonnet 4.6 for cheaper iterations?
- **Answer key maintenance**: who curates them, and how often do they need updating as topics evolve?
- **Eval-as-code vs. eval-as-data**: do rubrics live in markdown or in structured YAML?
- **Token budget tracking**: should evals themselves track token consumption to detect prompt bloat regressions?
