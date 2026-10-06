#!/bin/bash
# Check that Codex installs the generated plugin and loads its skills.
#
# Codex has no validation command, so this installs the plugin from the
# staged distribution into a temporary CODEX_HOME. No login is needed: nothing here
# calls a model.
set -euo pipefail
# shellcheck source=tools/staging.sh
source "$(dirname "${BASH_SOURCE[0]}")/staging.sh"

readonly SKILLS_SRC="src/skills"
readonly PLUGIN_DIR="plugins/codex/tao"
readonly MARKETPLACE="tao-of-agent"
readonly PLUGIN="tao"

main() {
  local installed expected loaded
  cd "$(dirname "${BASH_SOURCE[0]}")/.."

  if ! command -v codex >/dev/null; then
    echo "check_codex_plugin.sh: the codex CLI is required" >&2
    exit 1
  fi

  stage_distribution
  codex_home="$stage_dir/codex-home"
  mkdir "$codex_home"
  export CODEX_HOME="$codex_home"

  codex plugin marketplace add "$stage_dir" >/dev/null
  codex plugin add "${PLUGIN}@${MARKETPLACE}" >/dev/null

  # The cache holds one directory per installed version.
  installed="$(find "${CODEX_HOME}/plugins/cache/${MARKETPLACE}/${PLUGIN}" -mindepth 1 -maxdepth 1 -type d)"
  if ! diff -r "$stage_dir/$PLUGIN_DIR" "$installed" >&2; then
    echo "check_codex_plugin.sh: the installed plugin differs from ${PLUGIN_DIR}" >&2
    exit 1
  fi

  expected="$(find "$SKILLS_SRC" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sed "s/^/${PLUGIN}:/" | sort)"
  loaded="$(codex debug prompt-input "hi" 2>/dev/null | grep -oE "${PLUGIN}:[a-z0-9-]+" | sort -u)"
  if [[ "$loaded" != "$expected" ]]; then
    echo "check_codex_plugin.sh: the skills Codex loads do not match ${SKILLS_SRC}" >&2
    diff <(echo "$expected") <(echo "$loaded") >&2 || true
    exit 1
  fi
  echo "Codex installs ${PLUGIN_DIR} and loads each skill:"
  echo "$loaded"
}

main "$@"
