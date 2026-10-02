---
type: llm
weight: 1
---

The response is a single edited paragraph with no commentary, scores, or badges.

It removes the staged opener ("Great question", "Let's dive in"), the empty contrast ("not just about speed, it's about reliability"), the forced triad ("fast, robust, and scalable"), the vague authority ("Experts agree"), and the dramatic closer ("And that changes everything").

It preserves every fact: 12,000 requests per second, a default TTL of 300 seconds, lazy eviction on the next read rather than a background sweeper, and that a stale entry can survive past its TTL until something reads it. The causal relationship between lazy eviction and stale survival is intact.

It adds no facts that were not in the source.
