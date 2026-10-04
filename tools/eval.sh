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
# shellcheck source=tools/staging.sh
source "$(dirname "${BASH_SOURCE[0]}")/staging.sh"

readonly PLUGIN_DIR="plugins/claude/tao"
readonly EVALS_DIR="evals"
readonly RESULTS_DIR="${EVALS_DIR}/results"

main() {
  local repo_root results_dir
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  cd "$repo_root"

  if ! command -v claude >/dev/null; then
    echo "eval.sh: the claude CLI is required" >&2
    exit 1
  fi

  stage_distribution
  cp -R "$EVALS_DIR" "${stage_dir}/${PLUGIN_DIR}/${EVALS_DIR}"
  rm -rf "${stage_dir:?}/${PLUGIN_DIR}/${RESULTS_DIR}"

  results_dir="${repo_root}/${RESULTS_DIR}/$(date -u +%Y-%m-%dT%H-%M-%SZ)"
  mkdir -p "$results_dir"
  claude plugin eval "$stage_dir/$PLUGIN_DIR" \
    --trust-plugin \
    --output-dir "$results_dir" \
    --report "${results_dir}/report.html" \
    "$@"
}

main "$@"
