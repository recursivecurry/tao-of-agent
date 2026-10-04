#!/bin/bash
# Print session-context.md as SessionStart hook output.
#
# Claude Code and Codex both add hookSpecificOutput.additionalContext to the
# session. The context file is found next to this script, so the script does
# not depend on either agent's plugin path variable.
set -euo pipefail

CONTEXT_FILE="$(dirname "${BASH_SOURCE[0]}")/session-context.md"
readonly CONTEXT_FILE

json_escape() {
  local text="$1"
  text="${text//\\/\\\\}"
  text="${text//\"/\\\"}"
  text="${text//$'\t'/\\t}"
  text="${text//$'\r'/}"
  text="${text//$'\n'/\\n}"
  printf '%s' "$text"
}

main() {
  local context
  context="$(<"$CONTEXT_FILE")"
  printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
    "$(json_escape "$context")"
}

main
