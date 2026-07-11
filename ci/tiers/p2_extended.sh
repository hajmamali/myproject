#!/bin/bash
# P2 — Extended validation (target: < 30 minutes)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

export PYTHONHASHSEED=0
export MAHOUN_NO_EXTERNAL_CALLS=1
export MAHOUN_TEST_MODE=1

echo "================================================"
echo "P2 Extended Validation Tier"
echo "================================================"

pytest \
  tests/governance/ \
  tests/contracts/ \
  tests/determinism/ \
  tests/verification/ \
  tests/reasoning/ \
  tests/graph/ \
  tests/rag/ \
  tests/core/ \
  tests/test_*comprehensive*.py \
  tests/test_*integration*.py \
  tests/test_*properties*.py \
  -q \
  --tb=line \
  --ignore=tests/test_e2e_manual.py \
  --ignore=tests/test_finetuning_manual.py \
  "$@"
