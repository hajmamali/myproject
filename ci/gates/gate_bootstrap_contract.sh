#!/usr/bin/env bash
# ============================================================================
# Bootstrap Architecture Contract Validation Gate
# ============================================================================
# Purpose: Validate bootstrap implementation complies with frozen contract
# Status: MANDATORY - Must pass before any bootstrap changes
# Documentation: mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "════════════════════════════════════════════════════════════════════════"
echo "GATE: Bootstrap Architecture Contract Validation"
echo "════════════════════════════════════════════════════════════════════════"
echo ""
echo "Contract File: mahoun/bootstrap/bootstrap_contract.yaml"
echo "Validator: mahoun/bootstrap/contract_validator.py"
echo ""

# Change to project root
cd "$PROJECT_ROOT"

# Check contract file exists
if [[ ! -f "mahoun/bootstrap/bootstrap_contract.yaml" ]]; then
    echo "❌ FAIL: Contract file not found"
    echo ""
    echo "Expected: mahoun/bootstrap/bootstrap_contract.yaml"
    echo ""
    echo "This file defines the frozen bootstrap architecture contract."
    echo "It must exist for validation to proceed."
    exit 1
fi

# Check validator exists
if [[ ! -f "mahoun/bootstrap/contract_validator.py" ]]; then
    echo "❌ FAIL: Contract validator not found"
    echo ""
    echo "Expected: mahoun/bootstrap/contract_validator.py"
    exit 1
fi

# Run contract validation
echo "Running bootstrap contract validation..."
echo ""

if python3 -m mahoun.bootstrap.contract_validator; then
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo "✅ GATE PASSED: Bootstrap contract compliance verified"
    echo "════════════════════════════════════════════════════════════════════════"
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo "════════════════════════════════════════════════════════════════════════"
    echo "❌ GATE FAILED: Bootstrap contract violations detected"
    echo "════════════════════════════════════════════════════════════════════════"
    echo ""
    echo "CONTRACT VIOLATIONS MUST BE FIXED BEFORE PROCEEDING"
    echo ""
    echo "The bootstrap architecture contract is FROZEN."
    echo "Any deviation requires:"
    echo "  1. Explicit architectural justification"
    echo "  2. ADR documentation"
    echo "  3. Constitutional approval"
    echo ""
    echo "See: mahoun/bootstrap/BEHAVIOR_SNAPSHOT.md"
    echo ""
    exit $EXIT_CODE
fi
