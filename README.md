# tao-of-agent

Agent skills following the [Vercel agent skills](https://vercel.com/docs/agent-resources/skills)
format. Each skill is a directory under `skills/` with a `SKILL.md`.

## Skills

| Skill | Description |
| --- | --- |
| [`simple-code`](skills/simple-code) | Apply KISS, YAGNI, DRY, readability, and TDD when writing or reviewing code. |
| [`vercel-deploy`](skills/vercel-deploy) | Deploy a project to Vercel with the Vercel CLI and report the deployment URL. |

## Install

```bash
npx skills add recursivecurry/tao-of-agent --skill simple-code
npx skills add recursivecurry/tao-of-agent --skill vercel-deploy
```

Add `-g` to install globally, or `-a claude-code` to target a specific agent.

Manual install for Claude Code:

```bash
cp -r skills/simple-code skills/vercel-deploy ~/.claude/skills/
```
