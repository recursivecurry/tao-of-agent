---
name: vercel-deploy
description: Deploy a project to Vercel with the Vercel CLI, and report the deployment URL. Use when the user says "deploy", "deploy to Vercel", "ship this", "push it live", "make a preview deployment", "promote to production", or asks for a preview link.
license: MIT
metadata:
  author: recursivecurry
  version: "1.0.0"
---

# Vercel Deploy

Deploy the current project to Vercel and hand the user a URL.

**Default to a preview deployment.** Only deploy to production when the user asks for it in
so many words ("production", "prod", "live", "promote"). A preview is cheap and reversible;
a production deploy replaces what real users see.

## Step 1: Preflight

Run the preflight script once. It gathers every piece of state the decision below needs and
prints JSON to stdout:

```bash
bash scripts/preflight.sh
```

Output fields:

| Field | Meaning |
| --- | --- |
| `cli` | `installed` / `missing` |
| `auth` | Vercel username, or `null` when not logged in |
| `linked` | `project` (`.vercel/project.json`), `repo` (`.vercel/repo.json`), or `none` |
| `scope` | `orgId` from the link file, or `null` |
| `gitRemote` | `origin` URL, or `null` |
| `branch` | current branch, or `null` |
| `dirty` | `true` when the working tree has uncommitted changes |
| `teams` | team slugs available to the logged-in user |
| `framework` | detected framework, or `unknown` |

The script only runs commands that are safe in an unlinked directory. Never probe state with
`vercel link`, `vercel ls`, or `vercel project inspect` before the project is linked — without
a `.vercel/` config they prompt interactively, or silently create a link as a side effect.

## Step 2: Fix what preflight reports missing

- **`cli: missing`** — install it: `npm i -g vercel` (or run everything through `npx vercel@latest`).
- **`auth: null`** — `vercel login` opens a browser. In a non-interactive or sandboxed shell that
  cannot happen: ask the user for a token instead and pass `--token "$VERCEL_TOKEN"` on every
  command, or tell them to run `vercel login` themselves and come back. Do not print the token.
- **`teams` has more than one entry and `scope` is null** — list the slugs as bullets, ask which
  one, then pass `--scope <slug>` on every later command. One team, or `scope` already set from a
  link file: skip the question.

## Step 3: Link, if needed

Skip when `linked` is `project` or `repo`.

```bash
vercel link --repo --scope <slug>   # gitRemote is set: matches the Vercel project by repo URL
vercel link --scope <slug>          # no gitRemote: prompts to pick or create a project
```

Prefer `--repo`. Plain `vercel link` matches on directory name and picks the wrong project
whenever the local folder is named differently from the Vercel one.

Tell the user what linking does before running it — it writes `.vercel/` and can create a new
Vercel project — but once they have chosen a team, do not ask a second time.

## Step 4: Deploy

### Path A — linked with a git remote: push

This is the setup worth steering toward, because every later deploy is just a push.

**Ask before pushing. Never push on your own initiative.** Then:

```bash
git add -A
git commit -m "<what changed>"
git push
```

Vercel builds the push automatically: the production branch goes to production, every other
branch gets a preview. If the user asked for a preview but is sitting on the production branch,
say so and offer to branch first rather than shipping to production by accident.

Retrieve the URL after a few seconds:

```bash
sleep 5 && vercel ls --format json --scope <slug>
```

Take `url` from the newest entry of the `deployments` array. If the CLI is unauthenticated,
point the user at the Vercel dashboard or the commit's status checks instead.

### Path B — linked, no git remote: deploy from the CLI

```bash
vercel deploy -y --no-wait --scope <slug>            # preview
vercel deploy -y --no-wait --prod --scope <slug>     # production, only when asked
```

`--no-wait` returns the URL immediately instead of blocking for the whole build. Check on it with:

```bash
vercel inspect <deployment-url> --scope <slug>
```

### Path C — production promotion of something already built

To promote an existing preview rather than rebuild:

```bash
vercel promote <deployment-url> --scope <slug>
```

Confirm with the user first — this changes what production serves.

## Environment variables

A build that reads env vars fails on Vercel unless they exist there too. When `.env`,
`.env.local`, or `.env.production` is present and the project was just linked, tell the user
their local values are not uploaded, and offer:

```bash
vercel env add <NAME> preview --scope <slug>       # prompts for the value on stdin
vercel env pull .env.local --scope <slug>          # the reverse: fetch what Vercel already has
```

Never read secret values out of a `.env` file into the transcript, and never pass them as
command-line arguments — `vercel env add` reads from stdin for exactly this reason.

## Reporting back

Always end with the URL on its own line:

```
Preview: https://tao-abc123-acme.vercel.app
Build:   queued (vercel inspect <url> for status)
```

Report the build state honestly. `--no-wait` means the deploy was *accepted*, not that it
succeeded — say "queued"/"building", not "deployed", until `vercel inspect` shows `READY`.

Do not curl the deployed URL to verify it. Just return the link.

## Troubleshooting

Deeper diagnosis lives in [references/troubleshooting.md](references/troubleshooting.md) —
read it only when a deploy actually fails. It covers build failures, missing env vars,
wrong root directory, auth and scope errors, and sandbox network restrictions.
