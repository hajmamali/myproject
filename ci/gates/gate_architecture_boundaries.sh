#!/bin/bash
# Gate: Architecture Boundary Enforcement
# Ensures RAG services respect architectural boundaries and don't become "God Objects"
# 
# CRITICAL CHECKS:
# 1. RAG services must NOT create GovernanceContext (must receive it)
# 2. RAG services must NOT call ReasoningEngine/VerdictEngine
# 3. RAG services must NOT make policy decisions (PolicyResolver)
# 4. Router must remain orchestrator-only (no business logic)
#
# Part of: Phase 5 - Architecture Integration Mission
# Prevents: God Object anti-pattern, boundary violations

set -euo pipefail

echo "🏛️  ARCHITECTURE BOUNDARY ENFORCEMENT GATE"
echo "========================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Violation accumulator
VIOL_FILE=$(mktemp)
trap 'rm -f "$VIOL_FILE"' EXIT

add_violation() {
    echo "$1" >> "$VIOL_FILE"
}

count_violations() {
    wc -l < "$VIOL_FILE" 2>/dev/null || echo 0
}

# ---------------------------------------------------------------------------
# Check 1: RAG services must NOT create GovernanceContext
# ---------------------------------------------------------------------------
echo "🚫 Check 1: RAG services creating GovernanceContext..."

CONTEXT_CREATION_IN_RAG=$(
    grep -rn "GovernanceContextManager\.create_context" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "\.pyc" \
    || true
)

if [ -n "$CONTEXT_CREATION_IN_RAG" ]; then
    echo -e "${RED}❌ VIOLATION: RAG service creating GovernanceContext${NC}"
    echo "$CONTEXT_CREATION_IN_RAG"
    while IFS= read -r line; do
        add_violation "RAG creates context: $line"
    done <<< "$CONTEXT_CREATION_IN_RAG"
else
    echo -e "${GREEN}✅ PASS: No context creation in RAG services${NC}"
fi

# ---------------------------------------------------------------------------
# Check 2: RAG services must NOT call ReasoningEngine/VerdictEngine
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 2: RAG services calling reasoning engines..."

REASONING_CALLS_IN_RAG=$(
    grep -rn \
        -e "ReasoningEngine" \
        -e "VerdictEngine" \
        -e "EvidenceLinkedVerdictEngine" \
        -e "UnifiedReasoningService" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "from.*import" \
    | grep -v "\.pyc" \
    || true
)

if [ -n "$REASONING_CALLS_IN_RAG" ]; then
    echo -e "${RED}❌ VIOLATION: RAG service calling reasoning engines${NC}"
    echo "$REASONING_CALLS_IN_RAG"
    while IFS= read -r line; do
        add_violation "RAG calls reasoning: $line"
    done <<< "$REASONING_CALLS_IN_RAG"
else
    echo -e "${GREEN}✅ PASS: No reasoning engine calls in RAG services${NC}"
fi

# ---------------------------------------------------------------------------
# Check 3: RAG services must NOT make policy decisions
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 3: RAG services making policy decisions..."

POLICY_DECISIONS_IN_RAG=$(
    grep -rn \
        -e "PolicyResolver\.resolve" \
        -e "PolicyResolver\.decide" \
        -e "def decide_" \
        -e "def authorize_" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "_apply_policy_filter" \
    | grep -v "\.pyc" \
    || true
)

if [ -n "$POLICY_DECISIONS_IN_RAG" ]; then
    echo -e "${RED}❌ VIOLATION: RAG service making policy decisions${NC}"
    echo "$POLICY_DECISIONS_IN_RAG"
    while IFS= read -r line; do
        add_violation "RAG decides policy: $line"
    done <<< "$POLICY_DECISIONS_IN_RAG"
else
    echo -e "${GREEN}✅ PASS: No policy decisions in RAG services${NC}"
fi

# ---------------------------------------------------------------------------
# Check 4: RAG services must NOT orchestrate workflows
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 4: RAG services orchestrating workflows..."

ORCHESTRATION_IN_RAG=$(
    grep -rn \
        -e "def orchestrate" \
        -e "def execute_workflow" \
        -e "WorkflowOrchestrator" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "\.pyc" \
    || true
)

if [ -n "$ORCHESTRATION_IN_RAG" ]; then
    echo -e "${RED}❌ VIOLATION: RAG service orchestrating workflows${NC}"
    echo "$ORCHESTRATION_IN_RAG"
    while IFS= read -r line; do
        add_violation "RAG orchestrates: $line"
    done <<< "$ORCHESTRATION_IN_RAG"
else
    echo -e "${GREEN}✅ PASS: No orchestration in RAG services${NC}"
fi

# ---------------------------------------------------------------------------
# Check 5: Router must remain orchestrator (no business logic)
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 5: Router containing business logic..."

# Check for complex business logic in routers
BUSINESS_LOGIC_IN_ROUTER=$(
    grep -rn \
        -e "def.*filter.*(" \
        -e "def.*calculate.*(" \
        -e "def.*process.*(" \
        -e "def.*transform.*(" \
        --include="*.py" \
        api/routers/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "process_request" \
    | grep -v "\.pyc" \
    | head -20 \
    || true
)

if [ -n "$BUSINESS_LOGIC_IN_ROUTER" ]; then
    echo -e "${YELLOW}⚠️  WARNING: Potential business logic in router${NC}"
    echo "$BUSINESS_LOGIC_IN_ROUTER"
    echo -e "${YELLOW}   (Review manually - may be false positive)${NC}"
fi

# ---------------------------------------------------------------------------
# Check 6: No duplicate RAG service implementations
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 6: Duplicate RAG service implementations..."

RAG_SERVICE_CLASSES=$(
    grep -rn "^class.*RAGService" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "\.pyc" \
    || true
)

RAG_CLASS_COUNT=$(echo "$RAG_SERVICE_CLASSES" | grep -c "class" || echo 0)

if [ "$RAG_CLASS_COUNT" -gt 3 ]; then
    echo -e "${YELLOW}⚠️  WARNING: $RAG_CLASS_COUNT RAG service classes found${NC}"
    echo "$RAG_SERVICE_CLASSES"
    echo -e "${YELLOW}   Expected: HybridRAGService, PolicyAwareRAGService, Base classes${NC}"
    echo -e "${YELLOW}   Review for potential duplicates (AGENTS.md Part 3)${NC}"
else
    echo -e "${GREEN}✅ PASS: $RAG_CLASS_COUNT RAG service classes (reasonable)${NC}"
fi

# ---------------------------------------------------------------------------
# Check 7: RAG must not bypass Container dependency injection
# ---------------------------------------------------------------------------
echo ""
echo "🚫 Check 7: RAG services bypassing DI Container..."

DI_BYPASS_IN_RAG=$(
    grep -rn \
        -e "from.*import.*Engine" \
        -e "Engine(" \
        --include="*.py" \
        mahoun/rag/ \
        2>/dev/null \
    | grep -v "^\s*#" \
    | grep -v "QueryEngine" \
    | grep -v "EmbeddingEngine" \
    | grep -v "\.pyc" \
    | grep "VerdictEngine\|ReasoningEngine" \
    || true
)

if [ -n "$DI_BYPASS_IN_RAG" ]; then
    echo -e "${RED}❌ VIOLATION: RAG service bypassing DI Container${NC}"
    echo "$DI_BYPASS_IN_RAG"
    while IFS= read -r line; do
        add_violation "RAG bypasses DI: $line"
    done <<< "$DI_BYPASS_IN_RAG"
else
    echo -e "${GREEN}✅ PASS: No DI Container bypass in RAG services${NC}"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "📊 ARCHITECTURE BOUNDARY SUMMARY"
echo "================================="

TOTAL=$(count_violations)

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS: All architecture boundaries respected${NC}"
    echo ""
    echo "   Verified:"
    echo "   ✅ RAG services receive GovernanceContext (not create)"
    echo "   ✅ RAG services don't call reasoning engines"
    echo "   ✅ RAG services don't make policy decisions"
    echo "   ✅ RAG services don't orchestrate workflows"
    echo "   ✅ No DI Container bypass"
    echo ""
    echo "   Architecture integrity maintained ✨"
    exit 0
else
    echo -e "${RED}❌ FAIL: $TOTAL architecture boundary violations${NC}"
    echo ""
    echo "ARCHITECTURAL PRINCIPLES VIOLATED:"
    echo ""
    echo "1. Separation of Concerns"
    echo "   - RAG = Data retrieval + filtering"
    echo "   - Reasoning = Logic + inference"
    echo "   - Governance = Authorization + audit"
    echo ""
    echo "2. Dependency Direction"
    echo "   - Router → Container → Services"
    echo "   - Never: Service → Router"
    echo "   - Never: RAG → ReasoningEngine"
    echo ""
    echo "3. God Object Prevention"
    echo "   - Each service has ONE responsibility"
    echo "   - No service creates its own governance"
    echo "   - No service orchestrates other services"
    echo ""
    echo "REMEDIATION:"
    echo "- Move governance creation to API middleware/router"
    echo "- Move reasoning logic to ReasoningEngine"
    echo "- Move policy decisions to PolicyResolver"
    echo "- Keep RAG focused on retrieval + filtering only"
    echo ""
    echo "See: AGENTS.md Part 1, Phase 4 Architecture Checklist"
    exit 1
fi
