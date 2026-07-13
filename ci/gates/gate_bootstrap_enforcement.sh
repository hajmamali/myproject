#!/bin/bash
#
# Gate: Bootstrap Runtime Enforcement
# ====================================
#
# CRITICAL (P0): This gate enforces that bootstrap_runtime() is called
# in api/main.py during app startup. Without this call, SERVICE_REGISTRY
# remains empty and graph-enhanced retrieval silently fails.
#
# This gate was created to prevent regression of B1+B8 bug where
# bootstrap was never called, breaking RAG chain.
#
# Exit codes:
#   0 = Pass (bootstrap call present)
#   1 = Fail (bootstrap call missing or incorrect)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo "========================================"
echo "Gate: Bootstrap Runtime Enforcement"
echo "========================================"
echo ""

cd "$REPO_ROOT"

# ============================================================================
# CHECK 1: bootstrap_runtime import exists in api/main.py
# ============================================================================

echo "Check 1: Verifying bootstrap_runtime import..."

if ! grep -q "from mahoun.bootstrap.runtime import bootstrap_runtime" api/main.py; then
    echo "❌ FAIL: bootstrap_runtime not imported in api/main.py"
    echo ""
    echo "CRITICAL: The bootstrap module must be imported to initialize services."
    echo "Without this import, SERVICE_REGISTRY will be empty and graph-enhanced"
    echo "RAG will silently fail."
    echo ""
    echo "Required line:"
    echo "  from mahoun.bootstrap.runtime import bootstrap_runtime"
    echo ""
    exit 1
fi

echo "✓ bootstrap_runtime import found"

# ============================================================================
# CHECK 2: bootstrap_runtime() is actually called
# ============================================================================

echo "Check 2: Verifying bootstrap_runtime() is called..."

if ! grep -q "bootstrap_runtime()" api/main.py; then
    echo "❌ FAIL: bootstrap_runtime() not called in api/main.py"
    echo ""
    echo "CRITICAL: Importing bootstrap_runtime is not enough — it must be called"
    echo "during app lifespan startup to populate SERVICE_REGISTRY."
    echo ""
    echo "Required pattern in lifespan function:"
    echo "  registry = bootstrap_runtime()"
    echo ""
    exit 1
fi

echo "✓ bootstrap_runtime() call found"

# ============================================================================
# CHECK 3: Registry stored in app.state for health checks
# ============================================================================

echo "Check 3: Verifying registry stored in app.state..."

if ! grep -q "app.state.service_registry" api/main.py; then
    echo "❌ FAIL: Bootstrap registry not stored in app.state"
    echo ""
    echo "CRITICAL: The SERVICE_REGISTRY must be stored in app.state for"
    echo "health checks and observability."
    echo ""
    echo "Required pattern:"
    echo "  app.state.service_registry = registry"
    echo ""
    exit 1
fi

echo "✓ Registry storage found"

# ============================================================================
# CHECK 4: Critical services verification exists
# ============================================================================

echo "Check 4: Verifying critical services check..."

if ! grep -q "critical_services.*graph_retriever" api/main.py; then
    echo "❌ FAIL: Critical services verification missing"
    echo ""
    echo "CRITICAL: The bootstrap must verify that critical services"
    echo "(especially graph_retriever) are present in the registry."
    echo ""
    echo "Required pattern:"
    echo "  critical_services = ['query', 'gnn', 'graph_retriever']"
    echo "  missing_services = [s for s in critical_services if s not in registry]"
    echo ""
    exit 1
fi

echo "✓ Critical services verification found"

# ============================================================================
# CHECK 5: Fail-fast on bootstrap failure
# ============================================================================

echo "Check 5: Verifying fail-fast behavior..."

# Count RuntimeError occurrences in bootstrap section
bootstrap_errors=$(grep -A2 "raise RuntimeError" api/main.py | grep -i -E "bootstrap|SERVICE|MAHOUN|system cannot start" | wc -l)

if [ "$bootstrap_errors" -lt 1 ]; then
    echo "❌ FAIL: No fail-fast behavior on bootstrap failure"
    echo ""
    echo "CRITICAL: If bootstrap fails, the app MUST NOT start."
    echo "Silent degradation is not acceptable for P0 services."
    echo ""
    echo "Required pattern (multi-line RuntimeError with bootstrap/SERVICE/MAHOUN):"
    echo "  raise RuntimeError("
    echo "      'MAHOUN bootstrap failed...'"
    echo "  )"
    echo ""
    exit 1
fi

echo "✓ Fail-fast behavior verified ($bootstrap_errors error handlers found)"

# ============================================================================
# SUMMARY
# ============================================================================

echo ""
echo "========================================"
echo "✅ PASS: Bootstrap enforcement verified"
echo "========================================"
echo ""
echo "All checks passed:"
echo "  ✓ bootstrap_runtime imported"
echo "  ✓ bootstrap_runtime() called"
echo "  ✓ Registry stored in app.state"
echo "  ✓ Critical services verified"
echo "  ✓ Fail-fast behavior present"
echo ""

exit 0
