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
