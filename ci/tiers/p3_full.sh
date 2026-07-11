#!/bin/bash
# P3 — Full suite (nightly)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

export PYTHONHASHSEED=0
export MAHOUN_NO_EXTERNAL_CALLS=1
export MAHOUN_TEST_MODE=1

echo "================================================"
echo "P3 Full Test Suite (Nightly)"
echo "================================================"

pytest tests/ -q --tb=line "$@"
