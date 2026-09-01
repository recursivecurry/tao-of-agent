# Vercel deploy troubleshooting

Read this only when a deploy actually fails.

## Getting the real error

`vercel deploy --no-wait` returns before the build runs, so its exit code says nothing about
the build. Always pull the logs:

```bash
vercel inspect <deployment-url> --logs --scope <slug>
```

Report the failing line to the user verbatim rather than paraphrasing it.

## Build fails on Vercel but succeeds locally

Ordered by how often each one is the cause:

1. **Missing environment variables.** Local `.env` files are never uploaded. Check what the
   project has with `vercel env ls --scope <slug>`, and add what is missing with
   `vercel env add <NAME> preview --scope <slug>` (reads the value from stdin).
2. **Wrong root directory.** A monorepo deploys from the repo root by default. Fix it in the
   Vercel dashboard under Settings → General → Root Directory, or deploy from the subdirectory
   with `vercel deploy ./apps/web`.
3. **Dev dependency needed at build time.** Vercel installs dev dependencies by default, but a
   `NODE_ENV=production` install skips them. Move the package into `dependencies`.
4. **Node version mismatch.** Set `"engines": { "node": "22.x" }` in `package.json`, or pick the
   version in Settings → General → Node.js Version.
5. **Case-sensitive imports.** macOS filesystems are case-insensitive; the build container is not.
   `import Button from './button'` breaks when the file is `Button.tsx`.
6. **Lockfile out of sync.** `npm ci` fails when `package-lock.json` does not match
   `package.json`. Run the install locally and commit the updated lockfile.

## `Error: No existing credentials found`

The CLI is not authenticated. `vercel login` needs a browser. Where that is impossible:

```bash
vercel deploy --token "$VERCEL_TOKEN" -y --no-wait
```

Have the user create a token at https://vercel.com/account/tokens and export it themselves —
never echo the value, and never write it into a file in the repo.

## `Error: The specified token is not valid` / scope errors

The token or account has no access to the scope being targeted. Confirm the slug with
`vercel teams list --format json`, and confirm the token belongs to an account on that team.
A personal-account token cannot deploy into a team scope.

## Linked to the wrong project

Delete the link and redo it:

```bash
rm -rf .vercel
vercel link --repo --scope <slug>
```

`.vercel/` holds only ids, no secrets, but it should still be gitignored — `vercel link` adds
it to `.gitignore` automatically.

## Deployment succeeds but the site 404s

- A static build wrote to a directory Vercel is not serving. Check the Output Directory setting
  against what the build produces (`dist`, `build`, `out`, `.next`).
- A framework preset was detected wrong. `vercel project inspect --scope <slug>` shows the
  detected framework; override it in project settings.

## Sandbox network restrictions

A sandboxed agent may be unable to reach Vercel at all — timeouts, DNS failures, or connection
resets on every command.

- **claude.ai:** the user adds `*.vercel.com` at https://claude.ai/settings/capabilities.
- **Codex:** rerun the deploy command with escalated network permissions
  (`sandbox_permissions=require_escalated`). Escalate the deploy itself, not the preflight checks.

If the network cannot be opened, say so plainly. There is no way to deploy without reaching
Vercel — hand the user the exact command to run themselves.
