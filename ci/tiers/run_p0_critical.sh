#!/bin/bash
# Phase 5: P0 Critical Path Tests
# Run only P0_CRITICAL tests (governance, security, determinism)
# Fail-fast on first failure

set -e

echo "================================================================================"
echo "🔴 RUNNING P0 CRITICAL PATH TESTS (Fail-Fast)"
echo "================================================================================"
echo ""

/home/haji/Desktop/KingMahouN/venv/bin/pytest \
    -m "p0_critical" \
    --tb=short \
    -v \
    tests/

echo ""
echo "================================================================================"
echo "✅ P0 CRITICAL TESTS PASSED"
echo "================================================================================"
