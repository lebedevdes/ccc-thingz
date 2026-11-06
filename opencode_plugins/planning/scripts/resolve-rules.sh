#!/bin/bash
# resolve custom rules file through the two-layer override chain
# usage: resolve-rules.sh <filename> [data-dir]
# e.g.: resolve-rules.sh planning-rules.md /path/to/plugin/data
#
# data-dir: plugin data directory path, passed from SKILL.md where
# passed explicitly by the orchestrator, or derived from OpenCode configuration.
# defaults to <OpenCode config directory>/planning if not provided as argument.
#
# checks in order (first-found-wins, not merged):
#   1. .opencode/<filename> (project override)
#   2. <data-dir>/<filename> (user override)
#
# outputs file content to stdout if found, empty output if not
# always exits 0

filename="${1:-}"
if [ -z "$filename" ]; then
    exit 0
fi

# use argument if provided, fall back to env var
data_dir="${2:-${OPENCODE_CONFIG_DIR:-${XDG_CONFIG_HOME:-$HOME/.config}/opencode}/planning}"

if [ -f ".opencode/$filename" ] && [ -s ".opencode/$filename" ]; then
    cat ".opencode/$filename"
elif [ -n "$data_dir" ] && [ -f "$data_dir/$filename" ] && [ -s "$data_dir/$filename" ]; then
    cat "$data_dir/$filename"
fi

exit 0
