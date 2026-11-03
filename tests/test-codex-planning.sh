#!/bin/bash
# CI entry point: all checks use temporary fixtures, no model calls or credentials.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/codex-planning-tests.py"
