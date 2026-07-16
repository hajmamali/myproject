#!/bin/bash
# Phase 5: Full Test Suite (P0 + P1 + P2 + P3)
# Run all tests with standard reporting

set -e

echo "================================================================================"
echo "🟢 RUNNING FULL TEST SUITE (P0 + P1 + P2 + P3)"
echo "================================================================================"
echo ""

/home/haji/Desktop/KingMahouN/venv/bin/pytest \
    --tb=short \
    -v \
    --cov=mahoun \
    --cov-report=term-missing \
    tests/

echo ""
echo "================================================================================"
echo "✅ FULL TEST SUITE PASSED"
echo "================================================================================"
