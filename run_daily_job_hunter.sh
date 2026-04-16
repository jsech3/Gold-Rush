#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$HOME/2026Projects/Job Searching"

mkdir -p "$PROJECT_DIR/logs"
mkdir -p "$PROJECT_DIR/outputs"

cd "$PROJECT_DIR"

PYTHON_BIN="/opt/homebrew/bin/python3"
if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="/usr/bin/python3"
fi

"$PYTHON_BIN" tpm_job_hunter.py
