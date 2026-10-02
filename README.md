# tao-of-agent

Agent skills following the [Vercel agent skills](https://vercel.com/docs/agent-resources/skills)
format. Each skill is a directory under `skills/` with a `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [`minimal-code`](skills/minimal-code) | Write the smallest correct, readable, tested change — KISS, YAGNI, DRY, explicit errors, TDD. |
| [`git-hygiene`](skills/git-hygiene) | Keep Git history easy to review during development and meaningful after merge. |

## Install

### As a Claude Code plugin

The repository is a plugin marketplace that ships one plugin, `tao`, containing every
skill above. Inside Claude Code:

```text
/plugin marketplace add recursivecurry/tao-of-agent
/plugin install tao@tao-of-agent
```

Plugin skills are namespaced, so they appear as `tao:minimal-code` and
`tao:git-hygiene`.

### With the skills CLI

The [skills CLI](https://vercel.com/docs/agent-resources/skills) installs skills into any
supported agent, Claude Code included. Install every skill in the repository:

```bash
npx skills add recursivecurry/tao-of-agent
```

Or pick one:

```bash
npx skills add recursivecurry/tao-of-agent --skill minimal-code
npx skills add recursivecurry/tao-of-agent --skill git-hygiene
```

Add `-g` to install globally, or `-a claude-code` to target a specific agent. Skills installed
this way keep their plain names (`minimal-code`, `git-hygiene`).

### Manually

For Claude Code:

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

Load it before making code changes. Before reporting a change as done, read
references/done-checklist.md from the skill directory and work through it.
```

The skill holds the detail; the pointer is what gets it consulted at the two moments that
decide whether the change stays small. The completion checklist lives in its own file so the
second moment costs a short read, not a reload of the whole skill.
