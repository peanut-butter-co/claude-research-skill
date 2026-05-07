---
id: 2026-01-15-006
date: 2026-01-15
trigger: session-close
context: "/research-report \"compare JS testing frameworks\""
type: process-improvement
status: pending
---

After generating the comparative report, the user noted that the comparison table would be more useful if fields were sorted with the most differentiating fields first (those with the most variance across items), rather than in the order they appear in fields.yaml. This would make the key tradeoffs immediately visible without scrolling.

**Suggested rule**: In comparative reports, sort the comparison table columns so highest-variance fields appear first. Add a variance sort pass to build_report.py or document it as a recommendation in /research-report.
