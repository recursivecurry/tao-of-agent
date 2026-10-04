#!/bin/bash
# Check that the skills CLI lists each skill in src/skills exactly once.
#
# The CLI also scans plugins/claude/tao/skills/ and removes duplicates by name. That
# is observed behavior, not a documented contract, so this catches a change.
set -euo pipefail

readonly SKILLS_SRC="src/skills"

strip_ansi() {
  sed $'s/\x1b\\[[0-9;?]*[a-zA-Z]//g'
}

main() {
  local expected listed
  cd "$(dirname "${BASH_SOURCE[0]}")/.."

  python3 tools/build.py build

  expected="$(find "$SKILLS_SRC" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)"
  # `--list` has no JSON output, so read the skill names from the text listing.
  listed="$(npx --yes skills add . --list </dev/null | strip_ansi | sed -n 's/^│    \([a-z0-9-]*\)$/\1/p' | sort)"

  if [[ "$listed" != "$expected" ]]; then
    echo "check_skills_cli.sh: the skills CLI listing does not match ${SKILLS_SRC}" >&2
    diff <(echo "$expected") <(echo "$listed") >&2 || true
    exit 1
  fi
  echo "The skills CLI lists each skill once:"
  echo "$listed"
}

main "$@"
