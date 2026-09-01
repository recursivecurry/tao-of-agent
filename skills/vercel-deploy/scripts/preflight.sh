#!/bin/bash
# Gather Vercel deploy state as JSON on stdout. Status messages go to stderr.
# Only runs commands that are safe in an unlinked directory.
set -euo pipefail

cd "${1:-.}"

json_string() {
  # Emit a JSON string, or null for empty input.
  if [ -z "${1:-}" ]; then
    printf 'null'
  else
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/^/"/' -e 's/$/"/'
  fi
}

echo "preflight: checking vercel cli..." >&2
if command -v vercel >/dev/null 2>&1; then
  cli=installed
  auth=$(vercel whoami 2>/dev/null | tail -n1 | tr -d '[:space:]' || true)
else
  cli=missing
  auth=""
fi

echo "preflight: checking link state..." >&2
if [ -f .vercel/project.json ]; then
  linked=project
  scope=$(sed -n 's/.*"orgId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .vercel/project.json | head -n1)
elif [ -f .vercel/repo.json ]; then
  linked=repo
  scope=$(sed -n 's/.*"orgId"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' .vercel/repo.json | head -n1)
else
  linked=none
  scope=""
fi

echo "preflight: checking git..." >&2
git_remote=$(git remote get-url origin 2>/dev/null || true)
branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || true)
if git rev-parse --git-dir >/dev/null 2>&1 && [ -n "$(git status --porcelain 2>/dev/null)" ]; then
  dirty=true
else
  dirty=false
fi

teams="[]"
if [ -n "$auth" ]; then
  echo "preflight: listing teams..." >&2
  slugs=$(vercel teams list --format json 2>/dev/null \
    | tr ',' '\n' \
    | sed -n 's/.*"slug"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/"\1"/p' \
    | paste -sd, - || true)
  teams="[${slugs}]"
fi

framework=unknown
if [ -f package.json ]; then
  for f in next astro nuxt @sveltejs/kit remix @remix-run/dev vite react-scripts; do
    if grep -q "\"$f\"" package.json; then framework=$f; break; fi
  done
  [ "$framework" = unknown ] && framework=node
elif [ -f index.html ]; then
  framework=static
fi

cat <<EOF
{
  "cli": "$cli",
  "auth": $(json_string "$auth"),
  "linked": "$linked",
  "scope": $(json_string "$scope"),
  "gitRemote": $(json_string "$git_remote"),
  "branch": $(json_string "$branch"),
  "dirty": $dirty,
  "teams": $teams,
  "framework": "$framework"
}
EOF
