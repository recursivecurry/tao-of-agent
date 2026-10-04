#!/bin/bash
set -euo pipefail

stage_dir=""

remove_stage_dir() {
  if [[ -n "$stage_dir" ]]; then
    rm -rf "$stage_dir"
  fi
}

stage_distribution() {
  local repo_root
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
  stage_dir="$(mktemp -d)"
  trap remove_stage_dir EXIT
  python3 "$repo_root/tools/build.py" stage "$stage_dir" >/dev/null
}
