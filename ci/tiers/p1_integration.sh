#!/bin/bash
# P1 — Core integration (target: < 10 minutes)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

export PYTHONHASHSEED=0
export MAHOUN_NO_EXTERNAL_CALLS=1
export MAHOUN_TEST_MODE=1

echo "================================================"
echo "P1 Integration Test Tier"
echo "================================================"

"${SCRIPT_DIR}/p0_critical.sh" --collect-only > /dev/null

pytest \
  tests/governance/ \
  tests/contracts/ \
  tests/determinism/ \
  tests/verification/ \
  tests/reasoning/ \
  tests/test_api_endpoints.py \
  tests/test_bootstrap_wiring.py \
  tests/test_compose_contract.py \
  tests/test_golden_path.py \
  tests/test_golden_path_failure.py \
  tests/test_proof_carrying_contracts.py \
  tests/test_integration_comprehensive.py \
  -q \
  --tb=short \
  "$@"
