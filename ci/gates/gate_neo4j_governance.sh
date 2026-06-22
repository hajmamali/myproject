#!/bin/bash

# Gate: Neo4j Governance Compliance
# Ensures no direct Neo4j driver usage outside approved allowlist

set -e

echo "🛡️  NEO4J GOVERNANCE COMPLIANCE GATE"
echo "================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track violations
VIOLATIONS=0

echo "🔍 Scanning for direct Neo4j driver usage..."

# Define allowlist - ONLY these files may create drivers/sessions
ALLOWED_PATHS=(
    "mahoun/graph/neo4j/connection.py"
    "mahoun/graph/neo4j/schema.py"
    "tests/fixtures/seed_data.py"
)

# Check for forbidden AsyncGraphDatabase.driver() usage
echo "🚫 Checking AsyncGraphDatabase.driver() usage..."
ASYNC_VIOLATIONS=$(grep -rn "AsyncGraphDatabase.driver(" --include="*.py" . || true)
if [ -n "$ASYNC_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Direct AsyncGraphDatabase.driver() usage found:${NC}"
    echo "$ASYNC_VIOLATIONS" | while read -r line; do
        file_path=$(echo "$line" | cut -d: -f1)
        
        # Check if file is in allowlist
        ALLOWED=false
        for allowed in "${ALLOWED_PATHS[@]}"; do
            if [[ "$file_path" == *"$allowed"* ]]; then
                ALLOWED=true
                break
            fi
        done
        
        if [ "$ALLOWED" = false ]; then
            echo -e "${RED}   VIOLATION: $line${NC}"
            ((VIOLATIONS++))
        else
            echo -e "${YELLOW}   ALLOWED: $line${NC}"
        fi
    done
fi

# Check for forbidden GraphDatabase.driver() usage
echo "🚫 Checking GraphDatabase.driver() usage..."
SYNC_VIOLATIONS=$(grep -rn "GraphDatabase.driver(" --include="*.py" . || true)
if [ -n "$SYNC_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Direct GraphDatabase.driver() usage found:${NC}"
    echo "$SYNC_VIOLATIONS" | while read -r line; do
        file_path=$(echo "$line" | cut -d: -f1)
        
        # Check if file is in allowlist
        ALLOWED=false
        for allowed in "${ALLOWED_PATHS[@]}"; do
            if [[ "$file_path" == *"$allowed"* ]]; then
                ALLOWED=true
                break
            fi
        done
        
        if [ "$ALLOWED" = false ]; then
            echo -e "${RED}   VIOLATION: $line${NC}"
            ((VIOLATIONS++))
        else
            echo -e "${YELLOW}   ALLOWED: $line${NC}"
        fi
    done
fi

# Check for raw session() usage outside governed paths
echo "🚫 Checking raw session() usage outside governed paths..."
RAW_SESSION_VIOLATIONS=$(grep -rn "\.session()" --include="*.py" . \
    | grep -v "governed_session" \
    | grep -v "test_" \
    | grep -v "/tests/" \
    | grep -v "\.pyc" \
    || true)
if [ -n "$RAW_SESSION_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Raw .session() usage outside governed paths:${NC}"
    echo "$RAW_SESSION_VIOLATIONS"
    ((VIOLATIONS++))
fi

# Check for neo4j.Session direct usage
echo "🚫 Checking neo4j.Session direct instantiation..."
NEO4J_SESSION_VIOLATIONS=$(grep -rn "neo4j\.Session\b\|from neo4j import.*Session" --include="*.py" . \
    | grep -v "governed_session" \
    | grep -v "test_" \
    | grep -v "/tests/" \
    | grep -v "GovernedNeo4jSession" \
    | grep -v "\.pyc" \
    || true)
if [ -n "$NEO4J_SESSION_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Direct neo4j.Session usage found:${NC}"
    echo "$NEO4J_SESSION_VIOLATIONS"
    ((VIOLATIONS++))
fi

# Check for tx.run( outside governed paths
echo "🚫 Checking tx.run() usage..."
TX_RUN_VIOLATIONS=$(grep -rn "tx\.run(" --include="*.py" . \
    | grep -v "test_" \
    | grep -v "/tests/" \
    | grep -v "\.pyc" \
    || true)
if [ -n "$TX_RUN_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Direct tx.run() usage found:${NC}"
    echo "$TX_RUN_VIOLATIONS"
    ((VIOLATIONS++))
fi

# Check for mutation Cypher outside governed context
echo "🚫 Checking for potential mutation bypasses..."
MUTATION_PATTERNS=("CREATE " "MERGE " "DELETE " "SET " "REMOVE ")
for pattern in "${MUTATION_PATTERNS[@]}"; do
    MUTATIONS=$(grep -rn "$pattern" --include="*.py" . | grep -v "test" | grep -v "governed" || true)
    if [ -n "$MUTATIONS" ]; then
        echo -e "${YELLOW}⚠️  Potential $pattern mutations (manual review needed):${NC}"
        echo "$MUTATIONS" | head -5  # Show first 5 only
    fi
done

# Summary
echo ""
echo "📊 GOVERNANCE COMPLIANCE SUMMARY"
echo "================================"

if [ $VIOLATIONS -eq 0 ]; then
    echo -e "${GREEN}✅ PASS: No governance violations detected${NC}"
    echo "   - All Neo4j access goes through approved paths"
    echo "   - MutationAuthorizationBoundary integrity maintained"
    exit 0
else
    echo -e "${RED}❌ FAIL: $VIOLATIONS governance violations found${NC}"
    echo ""
    echo "REMEDIATION REQUIRED:"
    echo "1. Replace direct driver usage with get_connection().governed_session()"
    echo "2. Use connection.execute_query() for read-only queries"
    echo "3. All mutations must go through GovernedNeo4jSession"
    echo ""
    echo "For details, see: mahoun/core/governance/mutation_boundary.py"
    exit 1
fi