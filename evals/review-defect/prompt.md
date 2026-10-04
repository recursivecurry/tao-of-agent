---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Use independent-review's reviewer instructions to assess this supplied code and
contract. This is an offline review exercise, not a real push: do not launch an
agent, create a checkout, or claim Git/test verification. Return supported
findings, unresolved questions, and limitations.

Contract: page_size accepts an integer. Values below 1 use 1; values above 100 use
100; all other values are unchanged. Validation rejects non-integers before this
function is called, including rejecting booleans. Callers intentionally use this
clamping behavior.

Changed implementation in pagination.py, lines 1-2:

```python
def page_size(value: int) -> int:
    return min(1, max(value, 100))
```
