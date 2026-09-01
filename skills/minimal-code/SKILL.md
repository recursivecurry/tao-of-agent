---
name: minimal-code
description: Write the smallest correct, readable, maintainable change. Use whenever writing, modifying, refactoring, fixing, or reviewing code, especially when deciding whether to add abstractions, dependencies, configuration, helpers, tests, or broader refactors.
license: MIT
metadata:
  author: recursivecurry
  version: 2.0.0
---

# Minimal Code

Make the smallest correct change that fully satisfies the request.

"Smallest" means minimum justified complexity, not minimum characters or lines. Never sacrifice correctness, safety, validation, clarity, or required behavior merely to reduce the diff.

## Core Principles

Apply KISS, YAGNI, and DRY pragmatically:

- **KISS:** Prefer the simplest solution that is correct and clear.
- **YAGNI:** Do not add behavior, abstraction, configuration, or extensibility without a current need.
- **DRY:** Reuse shared concepts and remove meaningful duplication, but do not abstract merely because code looks similar.

Treat programming proverbs as heuristics, not laws. Prefer repository evidence, current requirements, and maintainability over mechanical rules.

## 1. Understand Before Editing

Before changing code:

1. Understand the requested behavior and scope.
2. Inspect the affected code, callers, tests, configuration, and relevant docs.
3. Trace the real execution or data flow when behavior is not obvious.
4. Search for existing helpers, types, constants, utilities, and project conventions.
5. Resolve ambiguity from repository evidence when possible.

Do not guess about behavior that can be verified from the repository.

Ask a clarification question only when unresolved ambiguity would materially change the implementation.

## 2. Use the Simplest Sufficient Solution

Prefer, in order:

1. No change when the requested behavior already exists.
2. Existing project code or patterns.
3. Standard-library functionality.
4. Native language, platform, framework, database, or browser features.
5. Already-installed dependencies.
6. A small direct implementation.
7. A new abstraction or dependency only when simpler options are insufficient.

Stop at the first option that correctly solves the problem.

Prefer boring, explicit code over clever code.

Do not add:

- speculative functionality,
- extension points for hypothetical callers,
- configuration without a current need,
- wrappers that merely mirror another API,
- unnecessary indirection,
- boilerplate or scaffolding without a concrete purpose.

Complexity must be justified by a current requirement.

## 3. Reuse Without Premature Abstraction

Reuse existing code when it already represents the same concept.

Remove duplication when doing so creates a clearer single source of truth.

Do not merge code merely because it looks similar. Similar-looking code may represent different concepts or evolve independently.

Extract a helper or abstraction when it makes the current code meaningfully clearer, safer, or easier to maintain — not merely because repetition exists.

Prefer concrete implementations until an abstraction has a real purpose.

## 4. Keep Behavior Explicit

Code should make its behavior easy to understand.

- Prefer clear names and straightforward control flow.
- Avoid hidden state and surprising side effects.
- Keep responsibilities focused.
- Use comments for non-obvious reasons or constraints, not to restate the code.
- Follow established project conventions unless correctness or clarity requires otherwise.
- Avoid unrelated formatting or cleanup.

Do not refactor unrelated code as part of a feature or bug fix.

## 5. Handle Failure Deliberately

Do not silently ignore errors unless that behavior is explicitly intended.

For relevant failure modes:

- handle the error,
- propagate it,
- or preserve the project's established failure behavior.

Consider boundary cases that plausibly affect the requested change, including invalid or empty inputs, compatibility, ordering or concurrency, security, data loss, and operational failures.

Do not add defensive code for purely hypothetical scenarios.

## 6. Fix Causes, Not Symptoms

For bug fixes:

1. Reproduce or establish the failure when practical.
2. Identify the root cause.
3. Inspect other callers or shared paths affected by that cause.
4. Fix the cause at the narrowest correct location.
5. Add regression coverage when the repository supports it.

Prefer one correct shared fix over repeated local workarounds.

Do not weaken validation, security, accessibility, or data-integrity checks to make a bug disappear.

## 7. Dependencies and Configuration

Before adding a dependency, confirm that existing project code, the standard library, native platform features, or installed dependencies cannot reasonably solve the problem.

Add a dependency only when its concrete benefit outweighs its maintenance, security, compatibility, and operational cost.

Do not add configuration options merely to make implementation choices configurable. Add configuration when users, environments, or existing architecture actually require variation.

## 8. Test the Changed Behavior

Changes that affect behavior should be verified.

Use the repository's existing testing conventions when available.

Prefer tests that cover:

- the changed behavior,
- relevant regression cases,
- meaningful failure or boundary cases.

Writing the failing test first is useful when practical, but correctness and regression coverage matter more than ceremony.

If the repository has no applicable test structure, use the narrowest meaningful alternative validation and state what you did.

Run the relevant tests or checks.

Never claim a test passed unless you actually ran it.

If only a subset was run, say which subset and why.

When failures occur, distinguish failures caused by the change from pre-existing or unrelated failures when possible.

## 9. Keep the Diff Focused

Every changed file and line should have a reason connected to the request.

Prefer local, reversible changes.

Avoid:

- unrelated refactors,
- broad renaming,
- drive-by cleanup,
- unnecessary formatting changes,
- behavior changes outside the requested scope.

Minimize diff size only after correctness and maintainability are satisfied.

## 10. Before Reporting Done

Verify that:

- the requested problem is actually solved;
- the implementation is no more complex than necessary;
- existing code was reused where appropriate;
- no speculative abstraction, dependency, configuration, or feature was added;
- errors and relevant edge cases are handled appropriately;
- a bug fix addresses the root cause rather than only the symptom;
- relevant tests or checks were run;
- the diff contains no unrelated changes;
- the resulting code is understandable and consistent with the project.

If one of these checks reveals required work, fix it before reporting completion.

Then report:

- what changed,
- which files changed,
- which tests or checks actually ran,
- and any material assumptions, limitations, or unresolved risks.
