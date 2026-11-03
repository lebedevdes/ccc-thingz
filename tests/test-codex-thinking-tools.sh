#!/bin/bash
# Test OpenCode consultation with fake responses; no credentials or model calls.
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
python3 "$SCRIPT_DIR/codex-thinking-tools-tests.py"
