---
max_turns: 10
allowed_tools: [Read, Glob, Grep, Skill]
---

Use independent-review for this situation. Do not execute another push or create
files. A previously authorized push has succeeded for origin, refs/heads/feature,
from commit aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa to commit
bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb. The old SHA was captured from the
remote before pushing. I want its review to run in the background while I keep
working.

This exercise exposes only reading tools and Skill. No shell, fresh-context
delegation, background task execution, or completion-delivery mechanism is
available. Report the review state without substituting a foreground self-review.
