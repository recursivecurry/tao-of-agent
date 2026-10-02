---
type: llm
weight: 1
---

The response is a commit message only: a subject line under about 72 characters, optionally followed by a blank line and a body. No preamble, explanation, or Markdown decoration such as headers or emoji.

It describes the actual change: retries are now limited to ETIMEDOUT and HTTP 503, other errors fail immediately, the attempt limit of 3 is unchanged, and a test covers the non-retried 400 case.

It contains no promotional or inflated language such as "greatly improves", "robust", or "ensures", and no invented motivation that the summary did not state.
