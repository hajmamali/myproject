#!/bin/bash
#
# Safe CI/CD Execution Script
# ===========================
# Runs all tests in a resource-safe manner.
#
# Usage:
#   bash first_step_ci_cd/run_safe_ci.sh
#

set -e  # Exit on error

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Project root
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_DIR="${PROJECT_ROOT}/first_step_ci_cd"

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  First Step CI/CD – Reality Check${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Project Root: ${PROJECT_ROOT}"
echo "Test Directory: ${TEST_DIR}"
echo ""

# Check pytest is available
if ! command -v pytest &> /dev/null; then
    echo -e "${RED}ERROR: pytest not found!${NC}"
    echo "Install with: pip install pytest pytest-asyncio"
    exit 1
fi

echo -e "${YELLOW}✓ pytest found${NC}"
echo ""

# Function to run a test file
run_test() {
    local test_file=$1
    local test_name=$2
    
    echo -e "${YELLOW}Running: ${test_name}${NC}"
    
    if pytest "${test_file}" -v --tb=short --color=yes; then
        echo -e "${GREEN}✓ ${test_name} PASSED${NC}"
        echo ""
        return 0
    else
        echo -e "${RED}✗ ${test_name} FAILED${NC}"
        echo ""
        return 1
    fi
}

# Track results
PASSED=0
FAILED=0

# Run each test suite
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Phase 1: Import Tests${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if run_test "${TEST_DIR}/test_1_imports.py" "Import Integrity Tests"; then
    ((PASSED++))
else
    ((FAILED++))
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Phase 2: Structure Tests${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if run_test "${TEST_DIR}/test_2_structure.py" "Structure Tests"; then
    ((PASSED++))
else
    ((FAILED++))
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Phase 3: Contract Tests${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if run_test "${TEST_DIR}/test_3_contracts.py" "Contract Tests"; then
    ((PASSED++))
else
    ((FAILED++))
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Phase 4: Light Logic Tests${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if run_test "${TEST_DIR}/test_4_logic_light.py" "Light Logic Tests"; then
    ((PASSED++))
else
    ((FAILED++))
fi

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Phase 5: Anti-Mock Tests${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

if run_test "${TEST_DIR}/test_5_anti_mock.py" "Anti-Mock Tests"; then
    ((PASSED++))
else
    ((FAILED++))
fi

# Final summary
echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  FINAL SUMMARY${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Total Test Suites: $((PASSED + FAILED))"
echo -e "${GREEN}Passed: ${PASSED}${NC}"
echo -e "${RED}Failed: ${FAILED}${NC}"
echo ""

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}✓✓✓ ALL TESTS PASSED ✓✓✓${NC}"
    echo ""
    echo -e "${GREEN}Reality Statement:${NC}"
    echo "All tests passed successfully, proving that:"
    echo "  1. Modules import without errors"
    echo "  2. Classes have expected structure"
    echo "  3. Method contracts are correct"
    echo "  4. Basic logic flows work"
    echo "  5. Implementations are REAL (not placeholders)"
    echo ""
    echo "This provides confidence that recent work is authentic"
    echo "and ready for further integration testing."
    echo ""
    exit 0
else
    echo -e "${RED}✗✗✗ SOME TESTS FAILED ✗✗✗${NC}"
    echo ""
    echo "Please review the failures above."
    echo "Common issues:"
    echo "  - Missing dependencies (check requirements.txt)"
    echo "  - Import errors (check module paths)"
    echo "  - Incomplete implementations (placeholders detected)"
    echo ""
    exit 1
fi

