---
# Generated from src/skills/git-hygiene/SKILL.md.tmpl. Edit the source, not this file.
name: git-hygiene
description: Keep Git history easy to review during development and meaningful after merge. Use whenever committing, amending, rebasing, squashing, preparing a branch for review, applying review feedback, or cleaning history before merge.
license: MIT
metadata:
  author: recursivecurry
  version: 1.0.0
---

# Git Review Hygiene

Keep Git history easy to review during development and meaningful after merge.

## Rules

1. **Inspect minimally**
   - Follow repository-specific Git/PR conventions first.
   - Start with `git status`, the relevant diff, and recent commits.
   - Expand history or diff inspection only when needed.

2. **Before review: clean history**
   - Keep each commit a coherent logical change.
   - Separate unrelated changes.
   - Amend/squash WIP, debug, typo-only, and trivial correction commits.
   - Ensure commit messages describe the actual change.

3. **During review: preserve the delta**
   - Do not rewrite commits reviewers have already seen just to clean history.
   - Apply review feedback as focused new commits, preferably `git commit --fixup=<target>` when appropriate.
   - Make changes since the last review easy to identify.

4. **Before merge: clean final history**
   - Squash fixup and review-only commits into their targets.
   - Preserve independently meaningful commits.
   - Verify the final diff and relevant tests.

## Guardrails

- Prefer amend/rebase/squash for **unreviewed** commits when it improves clarity.
- Avoid rewriting **reviewed or shared** history unless repository policy or the workflow requires it.
- Never force-push solely for cosmetic cleanup.
- Do not repeatedly inspect unchanged history or diffs.
- After changes, verify only the affected diff/history and relevant tests.

## Objective

At each stage, optimize for the relevant question:

```text
During review: What changed since the last review?
After merge:   What meaningful change was made?
```

Choose the smallest Git operation that keeps the relevant answer clear.
