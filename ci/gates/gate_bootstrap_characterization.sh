#!/bin/bash

# 🔧 CI Gate: Bootstrap Characterization Tests
# 
# This gate ensures behavioral baseline is preserved during refactoring.
# Runs before and after P0 refactoring to detect regressions.
#
# Usage:
#   ./gate_bootstrap_characterization.sh --mode baseline    # Create golden master
#   ./gate_bootstrap_characterization.sh --mode regression  # Check for regressions
#   ./gate_bootstrap_characterization.sh --mode validate    # Validate test suite

set -euo pipefail

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
CHARACTERIZATION_DIR="$REPO_ROOT/tests/bootstrap/characterization"
SNAPSHOTS_DIR="$CHARACTERIZATION_DIR/golden_master/snapshots"
CURRENT_SNAPSHOTS_DIR="$CHARACTERIZATION_DIR/current_run/snapshots"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Print usage
usage() {
    echo "Bootstrap Characterization Test Gate"
    echo ""
    echo "Usage:"
    echo "  $0 --mode baseline     Create golden master snapshots (before refactoring)"
    echo "  $0 --mode regression   Check for behavioral regressions (after refactoring)"  
    echo "  $0 --mode validate     Validate characterization test suite"
    echo ""
    echo "Examples:"
    echo "  # Before P0 refactoring - establish baseline"
    echo "  $0 --mode baseline"
    echo ""
    echo "  # After P0 refactoring - detect regressions"
    echo "  $0 --mode regression"
    echo ""
    exit 1
}

# Validate environment
validate_environment() {
    log_info "Validating test environment..."
    
    # Check Python environment
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 not found"
        exit 1
    fi
    
    # Check test directory structure
    if [[ ! -d "$CHARACTERIZATION_DIR" ]]; then
        log_error "Characterization test directory not found: $CHARACTERIZATION_DIR"
        exit 1
    fi
    
    # Check test files exist
    required_files=(
        "$CHARACTERIZATION_DIR/test_embedding_executor_behavior.py"
        "$CHARACTERIZATION_DIR/scenarios/embedding_success_easy.py"
        "$CHARACTERIZATION_DIR/scenarios/embedding_neo4j_missing_medium.py"
        "$CHARACTERIZATION_DIR/scenarios/embedding_rollback_race_hard.py"
        "$CHARACTERIZATION_DIR/scenarios/embedding_adversarial_ultra_hard.py"
        "$CHARACTERIZATION_DIR/detect_regressions.py"
    )
    
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            log_error "Required test file missing: $file"
            exit 1
        fi
    done
    
    log_success "Environment validation passed"
}

# Run characterization tests and create snapshots
run_baseline_tests() {
    log_info "Running baseline characterization tests..."
    
    # Create snapshots directory
    mkdir -p "$SNAPSHOTS_DIR"
    
    # Change to repo root for test execution
    cd "$REPO_ROOT"
    
    # Run characterization test suite
    log_info "Executing complete behavioral characterization suite..."
    
    if python3 -m pytest -xvs tests/bootstrap/characterization/test_embedding_executor_behavior.py::test_complete_embedding_executor_characterization; then
        log_success "Characterization tests completed successfully"
    else
        log_error "Characterization tests failed"
        exit 1
    fi
    
    # Verify snapshots were created
    expected_snapshots=(
        "embedding_easy_success.json"
        "embedding_missing_neo4j.json" 
        "embedding_rollback_race.json"
        "embedding_adversarial_ultra.json"
        "behavioral_characterization_report.json"
    )
    
    missing_snapshots=()
    for snapshot in "${expected_snapshots[@]}"; do
        if [[ ! -f "$SNAPSHOTS_DIR/$snapshot" ]]; then
            missing_snapshots+=("$snapshot")
        fi
    done
    
    if [[ ${#missing_snapshots[@]} -gt 0 ]]; then
        log_error "Missing snapshot files: ${missing_snapshots[*]}"
        exit 1
    fi
    
    log_success "Golden master snapshots created: ${#expected_snapshots[@]} files"
    log_info "Snapshots location: $SNAPSHOTS_DIR"
    
    # Show snapshot summary
    for snapshot in "${expected_snapshots[@]}"; do
        if [[ -f "$SNAPSHOTS_DIR/$snapshot" ]]; then
            size=$(stat -c%s "$SNAPSHOTS_DIR/$snapshot" 2>/dev/null || stat -f%z "$SNAPSHOTS_DIR/$snapshot" 2>/dev/null || echo "unknown")
            log_info "  ✓ $snapshot (${size} bytes)"
        fi
    done
}

# Check for behavioral regressions
check_regressions() {
    log_info "Checking for behavioral regressions..."
    
    # Verify baseline exists
    if [[ ! -d "$SNAPSHOTS_DIR" ]] || [[ ! -f "$SNAPSHOTS_DIR/behavioral_characterization_report.json" ]]; then
        log_error "Golden master baseline not found. Run with --mode baseline first."
        exit 1
    fi
    
    # Create current snapshots directory
    mkdir -p "$CURRENT_SNAPSHOTS_DIR"
    
    # Run current characterization tests
    cd "$REPO_ROOT"
    
    log_info "Running current characterization tests..."
    
    # Temporarily redirect snapshots to current directory
    export CHARACTERIZATION_SNAPSHOTS_DIR="$CURRENT_SNAPSHOTS_DIR"
    
    if python3 -m pytest -xvs tests/bootstrap/characterization/test_embedding_executor_behavior.py::test_complete_embedding_executor_characterization; then
        log_success "Current characterization tests completed"
    else
        log_error "Current characterization tests failed"
        exit 1
    fi
    
    # Run regression detection
    log_info "Analyzing behavioral differences..."
    
    cd "$CHARACTERIZATION_DIR"
    
    if python3 detect_regressions.py "$SNAPSHOTS_DIR" "$CURRENT_SNAPSHOTS_DIR"; then
        log_success "🔒 NO BEHAVIORAL REGRESSIONS DETECTED"
        log_success "Refactoring preserved all observable behavior"
        
        # Show regression report summary
        if [[ -f "$CURRENT_SNAPSHOTS_DIR/regression_report.json" ]]; then
            regression_status=$(python3 -c "
import json
with open('$CURRENT_SNAPSHOTS_DIR/regression_report.json') as f:
    report = json.load(f)
    print(report['regression_summary']['status'])
            ")
            
            log_info "Regression Status: $regression_status"
        fi
        
    else
        log_error "🚨 BEHAVIORAL REGRESSIONS DETECTED"
        log_error "Refactoring changed observable behavior"
        
        # Show regression details
        if [[ -f "$CURRENT_SNAPSHOTS_DIR/regression_report.json" ]]; then
            log_error "Regression report: $CURRENT_SNAPSHOTS_DIR/regression_report.json"
            
            # Extract critical findings
            critical_count=$(python3 -c "
import json
with open('$CURRENT_SNAPSHOTS_DIR/regression_report.json') as f:
    report = json.load(f)
    print(report['regression_summary']['critical_count'])
            " 2>/dev/null || echo "0")
            
            high_count=$(python3 -c "
import json
with open('$CURRENT_SNAPSHOTS_DIR/regression_report.json') as f:
    report = json.load(f)
    print(report['regression_summary']['high_count'])
            " 2>/dev/null || echo "0")
            
            log_error "Critical regressions: $critical_count"
            log_error "High severity regressions: $high_count"
        fi
        
        exit 1
    fi
}

# Validate characterization test suite
validate_test_suite() {
    log_info "Validating characterization test suite..."
    
    cd "$REPO_ROOT"
    
    # Check test syntax
    log_info "Checking Python syntax..."
    if ! python3 -m py_compile tests/bootstrap/characterization/test_embedding_executor_behavior.py; then
        log_error "Syntax error in main test orchestrator"
        exit 1
    fi
    
    scenario_files=(
        "tests/bootstrap/characterization/scenarios/embedding_success_easy.py"
        "tests/bootstrap/characterization/scenarios/embedding_neo4j_missing_medium.py"
        "tests/bootstrap/characterization/scenarios/embedding_rollback_race_hard.py"
        "tests/bootstrap/characterization/scenarios/embedding_adversarial_ultra_hard.py"
    )
    
    for file in "${scenario_files[@]}"; do
        if ! python3 -m py_compile "$file"; then
            log_error "Syntax error in $file"
            exit 1
        fi
    done
    
    # Check imports
    log_info "Validating imports..."
    if ! python3 -c "
import sys
sys.path.append('.')
from tests.bootstrap.characterization.test_embedding_executor_behavior import CharacterizationTestOrchestrator
print('✓ Imports validated')
    "; then
        log_error "Import validation failed"
        exit 1
    fi
    
    # Check behavioral recorder
    log_info "Validating behavioral recorder..."
    if ! python3 -c "
import sys
sys.path.append('.')
from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralRecorder, BehavioralSnapshot
recorder = BehavioralRecorder('TestExecutor')
print('✓ Behavioral recorder validated')
    "; then
        log_error "Behavioral recorder validation failed"
        exit 1
    fi
    
    log_success "Test suite validation completed"
    log_info "Ready for characterization testing"
}

# Main execution
main() {
    local mode=""
    
    # Parse arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --mode)
                mode="$2"
                shift 2
                ;;
            -h|--help)
                usage
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                ;;
        esac
    done
    
    # Validate mode
    if [[ -z "$mode" ]]; then
        log_error "Mode required"
        usage
    fi
    
    case "$mode" in
        baseline|regression|validate)
            ;;
        *)
            log_error "Invalid mode: $mode"
            usage
            ;;
    esac
    
    # Header
    echo "🔧 Bootstrap Characterization Test Gate"
    echo "Mode: $mode"
    echo "Repository: $REPO_ROOT"
    echo "Timestamp: $(date)"
    echo ""
    
    # Always validate environment first
    validate_environment
    
    # Execute based on mode
    case "$mode" in
        baseline)
            log_info "Creating golden master behavioral baseline..."
            run_baseline_tests
            log_success "✅ Golden master baseline established"
            log_info "🔒 Ready for P0 refactoring with behavioral protection"
            ;;
        regression)
            log_info "Checking for behavioral regressions..."
            check_regressions
            log_success "✅ Behavioral regression check completed"
            ;;
        validate)
            log_info "Validating characterization test suite..."
            validate_test_suite
            log_success "✅ Test suite validation completed"
            ;;
    esac
}

# Execute main function with all arguments
main "$@"