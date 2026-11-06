#!/bin/bash
# Resolve brainstorm rules: project first, then user; never merge.
# Usage: resolve-rules.sh <filename> [user-rules-dir]
# Run from the project root. The optional directory overrides CODEX_HOME.

set -euo pipefail

filename="${1:-}"
if [ -z "$filename" ]; then
    exit 0
fi

user_dir="${2:-${CODEX_HOME:-$HOME/.codex}}"
project_rules=".codex/$filename"
user_rules="$user_dir/$filename"

if [ -f "$project_rules" ] && [ -s "$project_rules" ]; then
    cat "$project_rules"
elif [ -f "$user_rules" ] && [ -s "$user_rules" ]; then
    cat "$user_rules"
fi
