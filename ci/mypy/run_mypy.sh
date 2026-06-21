#!/bin/bash
#
# run_mypy.sh
# ===========
# Runs mypy deterministically for CI non-regression checks
#
# Output is stable and parseable (no colors, no pretty formatting)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

# Ensure mypy is available
MYPY_CMD="mypy"
if [ -f "venv/bin/mypy" ]; then
    MYPY_CMD="venv/bin/mypy"
elif ! command -v mypy &> /dev/null; then
    echo "ERROR: mypy not found. Install with: pip install mypy" >&2
    exit 2
fi

# Run mypy with stable output format
# - --show-error-codes: include [error-code] for each error
# - --no-pretty: disable pretty formatting
# - --no-color-output: no ANSI colors
# - --no-error-summary: skip summary (we parse errors only)
exec "$MYPY_CMD" mahoun/ api/ \
    --config-file=mypy.ini \
    --show-error-codes \
    --no-pretty \
    --no-color-output \
    --no-error-summary

