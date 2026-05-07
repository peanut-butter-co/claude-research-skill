---
id: 2026-01-15-003
date: 2026-01-15
trigger: self-detection
context: "/research-deep \"EU AI Act compliance\""
type: tool-behavior
status: pending
---

Jina AI Reader consistently failed on EUR-Lex URLs (https://eur-lex.europa.eu/*) with a 503 response, while Wayback Machine snapshots were current enough (within 30 days) and reliably accessible. Skip Jina for eur-lex.europa.eu and go directly to Wayback.

**Suggested rule**: For `eur-lex.europa.eu` URLs, skip Jina (Tier 1a) and use Wayback Machine (Tier 1c) as the first fallback.
