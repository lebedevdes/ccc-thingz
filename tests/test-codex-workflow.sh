#!/bin/bash
# Exercise clipboard behavior with fake backends; never touch the real clipboard.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/codex-workflow-tests.py"
