---
id: 2026-01-15-001
date: 2026-01-15
trigger: user-feedback
context: "/research \"compare cloud providers\""
type: source-classification
status: pending
---

During a cloud provider comparison, the user flagged that `cloudflare.com/blog` is not equivalent to official documentation despite being Tier B. The blog contains marketing content that overstates product capabilities compared to official pricing pages.

**Suggested rule**: Classify `cloudflare.com/blog` as Tier C (community/secondary), not Tier B. Reserve Tier B for `cloudflare.com` (non-blog paths).
