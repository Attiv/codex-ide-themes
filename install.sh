#!/usr/bin/env bash
set -euo pipefail

repo_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
generator="$repo_dir/tools/generate_ide_themes.py"

case "${1:-}" in
  "")
    output_dir="${CODEX_HOME:-$HOME/.codex}/themes"
    exec python3 "$generator" --output "$output_dir"
    ;;
  --check)
    if (( $# != 1 )); then
      printf 'Usage: %s [--check]\n' "${0##*/}" >&2
      exit 2
    fi
    exec python3 "$generator" --check
    ;;
  *)
    printf 'Usage: %s [--check]\n' "${0##*/}" >&2
    exit 2
    ;;
esac
