#!/bin/bash
# Temporary fixtures only: no model calls or writes to real OpenCode settings.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/opencode-planning-tests.py"
