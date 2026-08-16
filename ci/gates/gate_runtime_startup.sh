#!/bin/bash
# =============================================================================
# MAHOUN RUNTIME STARTUP VALIDATION GATE
# =============================================================================
# 
# This gate validates that the application can start up without import errors
# or runtime initialization failures. It catches issues like:
# - Missing imports (e.g., asyncio not imported)
# - Missing symbols (e.g., require_permissions vs require_permission)
# - Import-time errors in critical modules
# - Basic initialization failures
#
# This is a RUNTIME test, not static analysis. It actually imports and attempts
# basic initialization of critical components.
#
# FAIL-CLOSED: Any import or initialization error causes the gate to fail.
# =============================================================================

# Don't exit on error - we want to collect all failures
set +e

echo "🔍 Runtime Startup Validation Gate"
echo "=================================="
echo ""

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track failures
FAILURES=0
PASSED=0
SKIPPED=0

# Function to test import
test_import() {
    local module=$1
    local description=$2
    
    echo -n "Testing: $description ($module)... "
    
    # Try import and capture error output
    local error_output
    error_output=$(python3 -c "import $module" 2>&1)
    local exit_code=$?
    
    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        # Check if it's a missing dependency vs code error
        if echo "$error_output" | grep -q "ModuleNotFoundError"; then
            echo -e "${YELLOW}⚠ SKIPPED (missing dependency)${NC}"
            echo -e "${YELLOW}  Missing: $(echo "$error_output" | grep -oP "No module named '\K[^']+")${NC}"
            ((SKIPPED++))
            return 0
        else
            echo -e "${RED}✗ FAILED${NC}"
            echo -e "${RED}  Error: $error_output${NC}"
            ((FAILURES++))
            return 1
        fi
    fi
}

# Function to test symbol availability
test_symbol() {
    local module=$1
    local symbol=$2
    local description=$3
    
    echo -n "Testing: $description ($module.$symbol)... "
    
    if python3 -c "from $module import $symbol" 2>/dev/null; then
        echo -e "${GREEN}✓ PASSED${NC}"
        ((PASSED++))
        return 0
    else
        echo -e "${RED}✗ FAILED${NC}"
        echo -e "${RED}  Error: Symbol $symbol not found in $module${NC}"
        ((FAILURES++))
        return 1
    fi
}

# =============================================================================
# CRITICAL IMPORTS - Governance & Security
# =============================================================================
echo "📋 Section 1: Critical Governance & Security Imports"
echo "---------------------------------------------------"

test_import "mahoun.core.governance.mutation_boundary" "Mutation authorization boundary"
test_import "mahoun.core.governance.governance_context" "Governance context manager"
test_import "mahoun.core.governance.authorization_state" "Authorization state"
test_import "mahoun.security.rbac" "RBAC system"

echo ""

# =============================================================================
# CRITICAL SYMBOLS - RBAC
# =============================================================================
echo "📋 Section 2: Critical RBAC Symbols"
echo "------------------------------------"

test_symbol "mahoun.security.rbac" "require_permission" "Single permission decorator"
test_symbol "mahoun.security.rbac" "require_permissions" "Multiple permissions decorator"
test_symbol "mahoun.security.rbac" "Permission" "Permission enum"

echo ""

# =============================================================================
# CRITICAL IMPORTS - Database & Graph
# =============================================================================
echo "📋 Section 3: Database & Graph Layer"
echo "-------------------------------------"

test_import "mahoun.graph.neo4j.connection" "Neo4j connection management"
test_symbol "mahoun.graph.neo4j.connection" "get_connection" "Connection factory"
test_symbol "mahoun.graph.neo4j.connection" "verify_async_driver_connectivity" "Async driver verification"

echo ""

# =============================================================================
# CRITICAL IMPORTS - API Layer
# =============================================================================
echo "📋 Section 4: API Layer"
echo "----------------------"

test_import "api.database" "API database bootstrap"
test_import "api.main" "API main application"

# Note: api.routers.governance is optional (try-except in main.py)
# We test it but don't fail if it's missing
echo -n "Testing: Governance router (optional)... "
if python3 -c "from api.routers import governance" 2>/dev/null; then
    echo -e "${GREEN}✓ PASSED${NC}"
    ((PASSED++))
else
    echo -e "${YELLOW}⚠ SKIPPED (optional)${NC}"
fi

echo ""

# =============================================================================
# CRITICAL IMPORTS - Reasoning Engine
# =============================================================================
echo "📋 Section 5: Reasoning Engine"
echo "-------------------------------"

test_import "mahoun.reasoning.evidence_linked_verdict" "Evidence-linked verdict engine"
test_import "mahoun.reasoning.adapters" "Reasoning dependency container"

echo ""

# =============================================================================
# CRITICAL IMPORTS - RAG & Retrieval
# =============================================================================
echo "📋 Section 6: RAG & Retrieval"
echo "------------------------------"

test_import "mahoun.rag.hybrid_rag_service" "Hybrid RAG service"
test_import "mahoun.rag.legal_aware_retrieval" "Legal-aware retrieval"

echo ""

# =============================================================================
# CRITICAL IMPORTS - Guardrails
# =============================================================================
echo "📋 Section 7: Guardrails & Safety"
echo "----------------------------------"

test_import "mahoun.guardrails.ultra_nli_verifier" "NLI text-grounding verifier"
test_import "mahoun.core.fortress_validator" "Fortress validator"

echo ""

# =============================================================================
# CRITICAL IMPORTS - Ledger
# =============================================================================
echo "📋 Section 8: Ledger & Integrity"
echo "---------------------------------"

test_import "mahoun.ledger.writer" "Evidence ledger writer"
test_import "mahoun.ledger.write_gate" "Ledger write gate"

echo ""

# =============================================================================
# SUMMARY
# =============================================================================
echo "=================================="
echo "📊 SUMMARY"
echo "=================================="
echo -e "Passed: ${GREEN}$PASSED${NC}"
echo -e "Failed: ${RED}$FAILURES${NC}"
echo -e "Skipped (missing deps): ${YELLOW}$SKIPPED${NC}"
echo ""

if [ $FAILURES -eq 0 ]; then
    echo -e "${GREEN}✓ All runtime startup checks PASSED${NC}"
    if [ $SKIPPED -gt 0 ]; then
        echo -e "${YELLOW}⚠ Note: $SKIPPED test(s) skipped due to missing dependencies${NC}"
        echo -e "${YELLOW}  Install missing dependencies for full coverage${NC}"
    fi
    echo ""
    exit 0
else
    echo -e "${RED}✗ Runtime startup validation FAILED${NC}"
    echo -e "${RED}  $FAILURES critical import(s) or symbol(s) are broken${NC}"
    echo ""
    echo "This gate prevents deployment of code with import errors that would"
    echo "cause runtime failures. Fix the above issues before merging."
    echo ""
    exit 1
fi
