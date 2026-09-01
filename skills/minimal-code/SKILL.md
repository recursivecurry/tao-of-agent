---
name: minimal-code
description: Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, and test-driven development. Use whenever writing, modifying, refactoring, or fixing code, and when reviewing a change for unnecessary complexity, speculative abstraction, or missing tests.
license: MIT
metadata:
  author: recursivecurry
  version: "1.1.0"
---

# Minimal Code

Produce the smallest correct, maintainable change that satisfies the request — smallest, not
shortest: a change that is fragile, swallows an error, or drops a validation loses to a longer
one that does not.

**The Core Principles below are the authority.** Everything above them is either a step the
principles do not spell out, or a trigger for noticing that one is about to be broken. Where
this section and a principle appear to disagree, the principle wins.

## Before you start

- Restate what is actually being asked. The requested scope is the deliverable — do not narrow it.
- Inspect the affected code, its call sites, and its tests. Trace the real flow rather than
  assuming how it works.
- Search for existing helpers, constants, and conventions before inventing new ones.
- Resolve ambiguity from the repository — tests, docs, adjacent code, git history. Ask only when
  the answer would change what you build.

## Tests

Principle V governs. Two things it leaves open:

- **Red-green-refactor is a SHOULD, not a MUST.** Write the failing test first where it fits.
  What is required is that the change ends up tested, not the order you got there.
- **If the repository has no test structure**, say so and state how you verified the change
  instead. Never silently skip verification.

Run the tests and report the exact command. If you ran only a subset, say so and say why.
Separate pre-existing failures from ones your change caused. Never report a test as passing
that you did not run.

## Stop signals

These mean a principle is about to break. When one shows up, delete what you were about to
write and take the simpler path. The last column cites the principle at stake.

| Signal | Do instead | Principle |
| --- | --- | --- |
| "This will be useful later" / "just in case" | Write it when the need is real | I |
| "Let's make this configurable" with one caller | Hardcode it; parameterize at the second caller | I |
| An interface, base class, or factory with one implementation | Use the concrete type | I, III.5 |
| A wrapper around a library "for flexibility" | Call the library directly | III.5 |
| "I'll extract a helper" after seeing it twice | Wait for the third occurrence | II.1 |
| "These two look similar, I'll merge them" | Merge only if they are the same *concept* and will change together | II.4 |
| A new boolean parameter that selects between two behaviors | Two functions with honest names | III.2 |
| `except: pass`, an ignored error return, an empty catch | Handle it, or let it propagate | III.8 |
| "I'll clean up this other file while I'm here" | Separate change | VI |
| "It works, I'm not sure why" | Trace it until you can explain it | III.9 |
| A comment restating the line below it | Delete the comment, or fix the name | IV |
| Deleting a validation or check to make the diff smaller | Keep the check | VI |

## Before you report done

- [ ] Solves the stated problem, and only that problem.
- [ ] You stopped at the lowest ladder rung that works.
- [ ] Nothing unused was added: abstraction, dependency, config knob, parameter, extension point.
- [ ] A bug fix removed the root cause, and you checked the other callers.
- [ ] Where the repository has tests, the change is covered — failure paths included — and you
      ran them.
- [ ] The project's formatter and linter ran clean.
- [ ] The diff is easy to review and revert.
- [ ] You can explain the design in a few plain sentences.

An unchecked box is remaining work, not a footnote for the summary.

Then report: what changed, which files, which checks actually ran, and any assumption you made.

---

# Core Principles

## I. Simplicity First (KISS & YAGNI)

Write simple code that solves current requirements. Do NOT anticipate hypothetical future needs.

- **MUST** choose direct and clear implementations over complex patterns
- **MUST NOT** create features, abstractions, or extension points not currently needed
- **MUST NOT** add code "just in case it might be needed later"
- **MUST** refactor only when a real need arises
- **MUST** justify any complexity beyond the minimum required for the current task

**Rationale**: Three similar lines of code is better than a premature abstraction.
Complexity is a cost that must be paid continuously; simplicity pays dividends.

## II. Don't Repeat Yourself (DRY)

Eliminate duplication by maintaining a single source of truth.

- **MUST** extract repeated logic into functions or modules when the same concept appears three times (Rule of Three)
- **MUST** use constants or configuration for repeated values
- **MUST** apply inheritance or composition to share behavior across classes when appropriate
- **MUST** distinguish between true duplication (same concept) and coincidental similarity (different concepts that happen to look alike)
- **MUST** balance DRY with readability; premature abstraction creates unnecessary complexity

**Rationale**: Duplication leads to inconsistency and maintenance burden. A single source
of truth ensures changes propagate correctly throughout the codebase.

## III. Programming Proverbs

1. **MUST** choose clear, straightforward code over clever or overly sophisticated solutions.
2. **MUST** make behavior explicit; avoid hidden, implicit, or surprising behavior.
3. **MUST** prefer the simplest solution that satisfies the current requirements; allow complexity only when necessary.
4. **MUST** optimize for readability; prefer flat, easy-to-follow control flow over deep nesting.
5. **MUST NOT** introduce unnecessary abstractions, indirection, or dependencies when a direct implementation is sufficient.
6. **MUST** keep abstractions small, focused, and easy to understand.
7. **MUST** make default behavior safe, useful, and predictable.
8. **MUST** handle errors explicitly; do not silently ignore failures unless explicitly required.
9. **MUST NOT** guess when requirements or behavior are ambiguous; use available context and evidence to resolve ambiguity.
10. **SHOULD** prefer one obvious and consistent way to perform the same kind of task across the codebase.
11. **SHOULD** follow established rules and conventions consistently, but prioritize practical correctness over rigid purity.
12. **MUST** keep responsibilities clear across modules and components, and express intent through meaningful names and concise documentation.
13. **MUST** prefer implementations that can be explained simply; if a design is difficult to explain, simplify it before adding more complexity.

**Rationale**: Clear, simple, and explicit code reduces cognitive load and improves maintainability. Prefer predictable, practical, and explainable solutions over cleverness, hidden behavior, or unnecessary complexity.

## IV. Human-Readable Code

Code MUST be easy for humans to read and understand. Code is read far more often than written.

- **MUST** use variable, function, and class names that clearly reveal intent
- **MUST** break down complex logic into small functions with descriptive names
- **MUST** write comments that explain "why" while the code expresses "what"
- **MUST** maintain consistent code style (use language-appropriate linters/formatters)
- **MUST NOT** use magic numbers or hardcoded strings; define them as named constants
- **MUST** keep functions short and focused on a single responsibility

**Rationale**: Code that is easy to read is easy to maintain, debug, and extend.
Self-documenting code reduces cognitive load and onboarding time.

## V. Test-Driven Development

Every implementation MUST be accompanied by tests that verify its correctness.

- **MUST** write tests for all new functionality
- **SHOULD** follow Red-Green-Refactor cycle: write failing test → implement → refactor
- **MUST** ensure tests are independent and can run in any order
- **MUST** test edge cases and error conditions, not just the happy path
- **MUST** keep tests readable and maintainable—tests are documentation
- **MUST NOT** commit code that breaks existing tests

**Rationale**: Tests provide confidence in code correctness, enable safe refactoring,
serve as living documentation, and catch regressions early.

## VI. Minimal Implementation Ladder

Before coding, read the task, inspect the affected code, and trace the real flow. Then stop at the first rung that works:

1. **MUST NOT** build anything not required now. *(YAGNI)*
2. **MUST** reuse existing code before writing new code.
3. **MUST** use the standard library when suitable.
4. **MUST** prefer native platform features over custom code.
5. **MUST** reuse installed dependencies; **MUST NOT** add one for trivial functionality.
6. **MUST** choose the smallest clear implementation.
7. **MUST** write only the minimum new code needed.

For bug fixes:

- **MUST** fix the root cause, not just the reported symptom.
- **MUST** inspect shared callers before patching shared behavior.
- **MUST** prefer one correct shared fix over repeated local guards.

General rules:

- **MUST NOT** add speculative abstractions, boilerplate, scaffolding, or extension points.
- **SHOULD** prefer deletion over addition and boring code over clever code.
- **MUST** minimize files changed and diff size, but never at the cost of correctness.
- **MUST** choose robust edge-case behavior over shorter but fragile code.
- **MUST NOT** weaken security, validation, data-loss protection, or accessibility for simplicity.

**Rationale**: Prefer the smallest correct change, reuse proven solutions first, and reduce complexity without sacrificing correctness or safety.
