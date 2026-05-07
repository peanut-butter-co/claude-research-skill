# research-skill

Four Claude Code skills for structured web research: planning, parallel deep retrieval, report synthesis, and learnings consolidation.

## Skills

| Skill | Purpose |
|---|---|
| `/research` | Plan a research case: ask clarifying questions, detect mode (comparative or narrative), generate an outline, and write a search plan. |
| `/research-deep` | Execute the plan: run parallel Task agents to fetch and score sources, fill item/subquery fields, and write a search log. Requires `/research` first. |
| `/research-report` | Synthesise completed deep-research output into a structured Markdown (and optional CSV) report. |
| `/research-consolidate` | Merge new learnings from a completed case into the shared `learnings/` knowledge base. |

## Setup

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

## Docs

- [`SPECS.md`](./SPECS.md) — full functional and non-functional requirements
- [`PLAN.md`](./PLAN.md) — implementation plan, project structure, architectural decisions
- [`TASKS.md`](./TASKS.md) — task breakdown and status
