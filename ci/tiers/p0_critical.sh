#!/bin/bash
# P0 — Fast critical tests (target: < 3 minutes)
# governance, contracts, determinism, fortress, ledger integrity

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

export PYTHONHASHSEED=0
export MAHOUN_NO_EXTERNAL_CALLS=1
export MAHOUN_TEST_MODE=1

echo "================================================"
echo "P0 Critical Test Tier"
echo "================================================"

pytest \
  tests/governance/ \
  tests/contracts/ \
  tests/determinism/ \
  tests/verification/ \
  tests/test_fortress_validator.py \
  tests/test_ledger_hash_chain.py \
  tests/test_ledger_atomicity.py \
  tests/test_ledger_properties.py \
  tests/test_blockchain_ledger.py \
  tests/reasoning/test_verdict_engine_adapter_reasoning_response.py \
  -q \
  --tb=short \
  "$@"
