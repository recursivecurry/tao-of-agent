---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Write a commit message for this change. Return only the commit message.

Diff summary: In src/retry.ts, the retry helper previously retried on every error. It now retries only when the error is a network timeout (code ETIMEDOUT) or an HTTP 503, and gives up immediately on anything else. The maximum attempt count is unchanged at 3. A test was added in test/retry.test.ts covering a 400 response, which must not be retried.
