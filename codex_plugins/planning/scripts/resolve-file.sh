#!/bin/bash
# Usage: resolve-file.sh <relative-path> [user-override-dir]
# Project overrides > user overrides > plugin defaults. Run from project root.
set -euo pipefail

path="${1:-}"
case "$path" in
    ""|/*|..|../*|*/../*|*/..) echo "error: expected a relative path inside references" >&2; exit 1 ;;
esac
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PLUGIN_ROOT="$(dirname "$SCRIPT_DIR")"
user_dir="${2:-${CODEX_HOME:-$HOME/.codex}/exec-plan}"

for candidate in ".codex/exec-plan/$path" "$user_dir/$path" "$PLUGIN_ROOT/references/$path"; do
    if [ -f "$candidate" ]; then
        cat "$candidate"
        exit 0
    fi
done
echo "error: file not found in override chain: $path" >&2
exit 1
