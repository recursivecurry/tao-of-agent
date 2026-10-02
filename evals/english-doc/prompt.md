---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Edit the following README paragraph so it reads naturally. Return only the edited paragraph.

Great question — how does the cache work? Let's dive in. It's not just about speed, it's about reliability. Our cache layer is fast, robust, and scalable, and it was carefully designed to handle up to 12,000 requests per second with a default TTL of 300 seconds. Experts agree that caching is essential. Entries older than the TTL are evicted lazily on the next read, not by a background sweeper, so a stale entry can survive past its TTL until something reads it. And that changes everything.
