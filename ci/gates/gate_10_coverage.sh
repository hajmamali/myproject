#!/bin/bash
#
# Gate 10: Coverage Enforcement
# ==============================
#
# Purpose: Prevent coverage regressions by enforcing baseline thresholds
#
# This gate:
# 1. Runs full test suite with coverage measurement
# 2. Compares current coverage against baseline (ci/coverage_baseline.json)
# 3. Fails if coverage drops below threshold (default: 2% tolerance)
# 4. Generates detailed diff report on failures
#
# Requirements: R6 (Coverage Gate with Regression Prevention)
# Task: 2.4 Create ci/gates/gate_10_coverage.sh
#
# Exit Codes:
#   0 - Coverage gate passed (no regression)
#   1 - Coverage regression detected (fails CI)
#   2 - Missing baseline or current coverage data
#   3 - Configuration error
#

set -e
set -o pipefail

# ============================================================================
# CONFIGURATION
# ============================================================================

BASELINE_FILE="ci/coverage_baseline.json"
CURRENT_COVERAGE="coverage.json"
THRESHOLD_TOLERANCE=2.0  # Allow 2% degradation before failing
COMPARISON_SCRIPT="ci/scripts/compare_coverage.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# ============================================================================
# FUNCTIONS
# ============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo ""
    echo "================================================================================"
    echo "  GATE 10: COVERAGE ENFORCEMENT"
    echo "================================================================================"
    echo ""
}

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if baseline exists
    if [ ! -f "$BASELINE_FILE" ]; then
        log_error "Coverage baseline not found: $BASELINE_FILE"
        log_info "Run: python3 scripts/generate_coverage_baseline.py"
        return 2
    fi
    
    # Check if comparison script exists
    if [ ! -f "$COMPARISON_SCRIPT" ]; then
        log_error "Coverage comparison script not found: $COMPARISON_SCRIPT"
        return 2
    fi
    
    # Check if pytest is available
    if ! command -v pytest &> /dev/null; then
        log_error "pytest not found. Please install: pip install pytest pytest-cov"
        return 3
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

run_coverage_measurement() {
    log_info "Running test suite with coverage measurement..."
    
    # Remove old coverage data
    rm -f "$CURRENT_COVERAGE" .coverage
    
    # Run tests with coverage (quiet mode for cleaner output)
    # We run with -q to reduce noise, but capture failures
    if pytest tests/ \
        --cov=mahoun \
        --cov=api \
        --cov-report=json:"$CURRENT_COVERAGE" \
        --cov-report=term \
        -q \
        --tb=no \
        2>&1 | tee coverage_gate_run.log; then
        log_success "Test suite completed"
    else
        log_warning "Some tests failed, but continuing with coverage analysis"
    fi
    
    # Verify coverage data was generated
    if [ ! -f "$CURRENT_COVERAGE" ]; then
        log_error "Coverage data not generated: $CURRENT_COVERAGE"
        return 2
    fi
    
    log_success "Coverage data generated: $CURRENT_COVERAGE"
    return 0
}

compare_coverage() {
    log_info "Comparing current coverage against baseline..."
    
    # Run comparison script
    if python3 "$COMPARISON_SCRIPT" \
        --baseline "$BASELINE_FILE" \
        --current "$CURRENT_COVERAGE" \
        --tolerance "$THRESHOLD_TOLERANCE" \
        --fail-on-regression; then
        log_success "Coverage comparison passed - no regressions detected"
        return 0
    else
        local exit_code=$?
        log_error "Coverage regression detected (exit code: $exit_code)"
        return 1
    fi
}

print_summary() {
    local exit_code=$1
    
    echo ""
    echo "================================================================================"
    echo "  COVERAGE GATE SUMMARY"
    echo "================================================================================"
    
    if [ $exit_code -eq 0 ]; then
        log_success "✅ Coverage gate PASSED"
        echo ""
        echo "  - No coverage regressions detected"
        echo "  - All modules meet baseline thresholds"
        echo "  - Safe to merge"
    else
        log_error "❌ Coverage gate FAILED"
        echo ""
        echo "  - Coverage regression detected"
        echo "  - Review diff above for details"
        echo "  - Options:"
        echo "    1. Add tests to restore coverage"
        echo "    2. Update baseline if intentional (requires justification)"
    fi
    
    echo "================================================================================"
    echo ""
}

# ============================================================================
# MAIN EXECUTION
# ============================================================================

main() {
    print_header
    
    # Step 1: Prerequisites check
    if ! check_prerequisites; then
        exit_code=$?
        print_summary $exit_code
        exit $exit_code
    fi
    
    # Step 2: Run coverage measurement
    if ! run_coverage_measurement; then
        exit_code=$?
        log_error "Coverage measurement failed"
        print_summary $exit_code
        exit $exit_code
    fi
    
    # Step 3: Compare against baseline
    if ! compare_coverage; then
        exit_code=$?
        print_summary $exit_code
        exit $exit_code
    fi
    
    # Success!
    print_summary 0
    exit 0
}

# Run main function
main "$@"
