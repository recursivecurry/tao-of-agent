---
name: minimal-code
description: Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, and test-driven development. Use whenever writing, modifying, refactoring, or fixing code, and when reviewing a change for unnecessary complexity, speculative abstraction, or missing tests.
license: MIT
metadata:
  author: recursivecurry
  version: "1.0.0"
---

# Minimal Code

Produce the smallest correct, maintainable change that satisfies the request. The full
principles are at the bottom of this file and are authoritative; the workflow and stop signals
above them are how to apply the principles in practice.

Smallest does not mean shortest. A shorter change that is fragile, silently swallows an error,
or drops a validation loses to a longer one that does not — see Ladder rule "MUST choose robust
edge-case behavior over shorter but fragile code."

## Workflow

### 1. Understand before typing

- Read the task and restate what is actually being asked. The requested scope is the deliverable.
- Inspect the affected code, its call sites, and its tests. Trace the real flow rather than
  assuming how it works.
- Search for existing helpers, constants, and conventions before inventing new ones.
- When behavior is ambiguous, resolve it from the repository — tests, docs, neighboring code.
  Ask only when the ambiguity blocks a correct implementation. Never guess.

### 2. Stop at the first rung that works

Walk the Minimal Implementation Ladder (Principle VI) top to bottom and stop at the first rung
that solves the problem: build nothing not required now → reuse existing code → standard library
→ native platform features → installed dependencies → smallest clear implementation → minimum
new code. Adding a dependency for trivial functionality is a violation, not a shortcut.

For a bug fix, find the root cause first. If the broken behavior is shared, fix it once at the
shared site after checking the other callers — do not scatter local guards at each symptom.

### 3. Write the test first

Red → green → refactor. Write a test that fails for the right reason, make it pass, then clean
up. Cover the error conditions and edge cases, not just the happy path: empty input, invalid
input, boundary values. Tests must be independent of each other and of execution order.

If the repository has no test structure, say so and describe how the change was verified
instead — do not silently skip verification.

### 4. Write the code

- Name things so the intent is obvious; no magic numbers or inline literals.
- Keep control flow flat. Prefer an early return to another nesting level.
- Handle every error explicitly. A swallowed exception is a defect unless the codebase
  swallows it deliberately and you can point to why.
- Match the surrounding conventions in style, naming, and structure.
- Comment the *why*. The code already states the *what*.
- Change as few files as possible, and touch nothing unrelated to the task.

### 5. Self-review before finishing

Answer each of these honestly. Any "no" means go back:

- Does the change solve the stated problem, and only that problem?
- Is there a simpler implementation that is equally correct?
- Can every abstraction, parameter, and file added be justified by a *current* requirement?
- Is every new behavior covered by a test, including its failure paths?
- Do the existing tests still pass? (Run them. Report the command.)
- Could a reviewer understand the diff without asking what it is for?
- Can the design be explained in a few plain sentences? If not, simplify it before adding more.

Then report: what changed, which files, which checks were actually run, and any assumption you
made. Never claim a test passed that was not executed.

## Stop signals

These phrases, in your own reasoning, mean a principle is about to be broken. When one shows
up, delete the code you were about to write and take the simpler path.

| Signal | Violation | Do instead |
| --- | --- | --- |
| "This will be useful later" / "just in case" | YAGNI | Write it when the need is real |
| "Let's make this configurable" with one caller | YAGNI | Hardcode it; parameterize at the second caller |
| An interface, base class, or factory with one implementation | YAGNI | Use the concrete type |
| A wrapper around a library "for flexibility" | Speculative indirection | Call the library directly |
| "I'll extract a helper" after seeing it twice | Premature abstraction | Rule of Three — wait for the third |
| "These two look similar, I'll merge them" | Coincidental similarity | Merge only if they are the same *concept* and will change together |
| A boolean parameter that switches what the function does | Hidden behavior | Two functions with honest names |
| `except: pass`, an ignored error return, an empty catch | Silent failure | Handle it, or let it propagate |
| "I'll clean up this other file while I'm here" | Scope creep | Separate change |
| "It works, I'm not sure why" | Guessing | Trace it until you can explain it |
| A comment restating the line below it | Noise | Delete the comment, or fix the name |
| Deleting a validation or check to make the diff smaller | Fragility for brevity | Keep the check |

## Trade-offs the principles do not settle

Two principles collide often enough to name the tiebreakers:

- **DRY vs. YAGNI.** Rule of Three decides. Two occurrences stay duplicated; the third earns the
  abstraction. Three similar lines beat a premature abstraction.
- **DRY vs. readability.** If the shared abstraction is harder to follow than the duplication it
  removes, keep the duplication.
- **Small diff vs. correctness.** Correctness wins, always.
- **Simplicity vs. safety.** Never trade away security, validation, data-loss protection, or
  accessibility for a simpler-looking implementation.
- **Existing convention vs. these principles.** Follow the codebase, unless its convention is
  actually wrong on correctness, safety, or clarity. Do not launch a cleanup crusade from inside
  an unrelated task.

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
