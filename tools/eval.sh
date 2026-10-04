#!/bin/bash
# Run the eval cases in evals/ against the generated Claude Code plugin.
#
# `claude plugin eval` reads cases only from inside the plugin directory, and
# evals/ is not shipped with the plugin. So this stages a copy of the plugin
# with the cases next to it, and writes the results back to evals/results/.
#
# Usage: tools/eval.sh [claude plugin eval options]
#   tools/eval.sh --judge-model sonnet
set -euo pipefail

readonly PLUGIN_DIR="plugins/tao"
readonly EVALS_DIR="evals"
readonly RESULTS_DIR="${EVALS_DIR}/results"

stage_dir=""

remove_stage_dir() {
  [[ -n "$stage_dir" ]] && rm -rf "$stage_dir"
}

main() {
  local repo_root results_dir
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$repo_root"

  if ! command -v claude >/dev/null; then
    echo "eval.sh: the claude CLI is required" >&2
    exit 1
  fi

  python3 tools/build.py build

  stage_dir="$(mktemp -d)"
  trap remove_stage_dir EXIT
  cp -R "${PLUGIN_DIR}/." "$stage_dir"
  cp -R "$EVALS_DIR" "${stage_dir}/${EVALS_DIR}"
  rm -rf "${stage_dir:?}/${RESULTS_DIR}"

  results_dir="${repo_root}/${RESULTS_DIR}/$(date -u +%Y-%m-%dT%H-%M-%SZ)"
  mkdir -p "$results_dir"
  claude plugin eval "$stage_dir" \
    --trust-plugin \
    --output-dir "$results_dir" \
    --report "${results_dir}/report.html" \
    "$@"
}

main "$@"
