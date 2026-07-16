#!/bin/bash
# Phase 5: P1 Integration Tests
# Run P0 + P1 integration tests
# Fail-fast on first failure

set -e

echo "================================================================================"
echo "🟠 RUNNING P1 INTEGRATION TESTS (Fail-Fast)"
echo "================================================================================"
echo ""

/home/haji/Desktop/KingMahouN/venv/bin/pytest \
    -m "p0_critical or p1_integration" \
    --tb=short \
    -v \
    tests/

echo ""
echo "================================================================================"
echo "✅ P1 INTEGRATION TESTS PASSED"
echo "================================================================================"
