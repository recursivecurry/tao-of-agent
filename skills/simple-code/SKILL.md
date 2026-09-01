---
name: simple-code
description: Apply KISS, YAGNI, DRY, readability, and test-driven development when writing or changing code. Use when implementing a feature, fixing a bug, refactoring, reviewing a diff, or deciding whether an abstraction is worth adding.
license: MIT
metadata:
  author: recursivecurry
  version: "1.1.0"
---

# Simple Code

Make the smallest correct, maintainable change that satisfies the request.

## Before you write

- Open the files you will change, their tests, and their callers. Never describe how code behaves
  without having read it.
- State the scope in one sentence: what the request asks for. Anything past that sentence is out.
- Search for an existing helper, constant, or pattern before adding a new one.
- Resolve ambiguity from tests, docs, adjacent code, and git history. Ask only when the answer
  would change what you build.

## Stop at the first rung that works

1. **Nothing.** The requirement is not real yet — do not build for it.
2. **Existing code** in this repo.
3. **The standard library.**
4. **A native platform feature**, rather than a hand-rolled equivalent.
5. **A dependency already installed.** Never add one for trivial functionality; when a new
   dependency is genuinely warranted, state in one sentence why it beats the maintenance,
   security, and compatibility cost.
6. **The smallest clear implementation** you can write.
7. **New code** — the minimum of it.

Add nothing that nothing calls: no config knob, parameter, interface, layer, or extension point
whose only user is hypothetical. Three similar lines beat a premature abstraction. Climbing past a
rung that would have worked is how a small change turns into a large one — if you do it, say why in
one sentence.

## Fixing bugs

- Trace the failure to its root cause. Making the symptom disappear is not a fix.
- Read every caller before changing shared behavior — the bug likely reaches places nobody reported.
- One correct fix at the source beats a guard added at each call site.

## Writing the code

**Duplication**

- Extract on the third occurrence, not the second. Two similar blocks are a coincidence.
- Before extracting, confirm the occurrences are the same *concept*, not the same *shape*. Code
  that changes for different reasons stays separate even when the lines match.
- Name any literal that appears twice. No magic numbers, no bare strings.

**Readability**

- Names state intent; a reader should not need the definition to know what a name holds.
- Split a function when it has two responsibilities — not when it crosses a line count.
- Flatten control flow with early returns and guard clauses.
- Comment *why*, never *what*: the non-obvious constraint, the reason for the odd choice, the thing
  that will look like a bug.
- Match the surrounding style and run the project's formatter and linter.

**Behavior**

- Make the default the safe, predictable thing a caller who read no docs would want.
- Handle each error where it occurs. Swallow a failure only where the codebase already does so
  deliberately, and say why in a comment.
- No hidden side effects — a function named for reading does not write.
- No hardcoded secrets, machine-specific paths, or environment assumptions.
- Use the repo's existing way of doing this kind of task. A second way costs every future reader.

**The diff**

- Touch as few files as possible, but never leave the change incomplete to keep the diff small.
- Do not refactor or reformat code the task does not require.
- Preserve public behavior and backward compatibility unless a break was requested.
- Prefer deleting code to adding it, and boring code to clever code.

## Tests

- Ship tests with every behavior change. Write the failing test first where it fits.
- Cover error paths and edge cases: empty, invalid, boundary, and ordering or concurrency where
  they apply.
- Keep tests order-independent — no shared mutable state, no reliance on execution sequence.
- Let test names and bodies document the intended behavior; keep them as readable as the code.
- Never leave an existing test broken.
- Run them, and report the exact command. If you ran only a subset, say so and say why. Never
  report a test as passing that you did not run, and separate pre-existing failures from ones your
  change caused.

## Before you report done

- [ ] Solves the request — no more, no less.
- [ ] You stopped at the lowest rung that works.
- [ ] Nothing unused was added: abstraction, dependency, config, extension point.
- [ ] A bug fix removed the root cause, and you checked the other callers.
- [ ] Tests cover the change, and you ran them.
- [ ] The diff is easy to review and revert.
- [ ] You can explain the design in a few sentences. If you cannot, simplify before adding more.

An unchecked box is work remaining, not a caveat for the summary.

## Limits

These rules constrain what you add. They never justify:

- **Removing safeguards to save lines.** Error handling, validation, tests, security, data-loss
  protection, and accessibility are the minimum, not the extras. Robust beats short.
- **Narrowing the request.** YAGNI governs your speculation, not the user's stated requirements.
  Build all of it; if part looks wrong, say so in a sentence and build it under a stated assumption.
- **Refactoring code the task never touched.**
- **Following a rule off a cliff.** When a rule would make this specific change worse, set it aside
  and say why.
