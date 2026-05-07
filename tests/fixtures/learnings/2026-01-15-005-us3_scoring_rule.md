---
id: 2026-01-15-005
date: 2026-01-15
trigger: self-detection
context: "/research-deep \"best practices cloud security\""
type: scoring-rule
status: pending
---

Cloud security documentation published by cloud vendors (AWS, GCP, Azure) about their own products was initially scored as potentially biased (Tier C heuristic). However, official vendor docs are the authoritative primary source for their own products — their tier should be A for platform-specific claims and B for general best practices.

**Suggested rule**: For official vendor documentation about vendor's own product (`docs.aws.amazon.com`, `cloud.google.com/docs`, `docs.microsoft.com/azure`), use Tier A for product-specific claims, not Tier B.
