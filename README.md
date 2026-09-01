# tao-of-agent

Agent skills following the [Vercel agent skills](https://vercel.com/docs/agent-resources/skills)
format. Each skill is a directory under `skills/` with a `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [`minimal-code`](skills/minimal-code) | Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, TDD. |

## Install

```bash
npx skills add recursivecurry/tao-of-agent --skill minimal-code
```

Add `-g` to install globally, or `-a claude-code` to target a specific agent.

Manual install for Claude Code:

```bash
cp -r skills/minimal-code ~/.claude/skills/
```

## Making `minimal-code` always apply

An agent loads a skill only when it judges the skill relevant, and it loads it at the *start*
of a task — not at the end, where the pre-flight checklist matters most. Coding principles are
meant to hold on every change, so back the skill with a pointer in your project's `CLAUDE.md`
(or `AGENTS.md`):

```markdown
Follow the minimal-code skill when writing or changing code.

Load it before adding any new abstraction, dependency, or configuration option,
and again before reporting a change as done.
```

The skill holds the detail; the pointer is what gets it consulted at the two moments that
decide whether the change stays small.
