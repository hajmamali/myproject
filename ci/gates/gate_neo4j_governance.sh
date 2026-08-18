#!/bin/bash
# Gate: Neo4j Governance Compliance (PATCH GROUP E)
# Ensures no raw Neo4j driver/session/mutation usage outside approved governance wrappers.
# FIXES: subshell counter bug replaced with temp file accumulation; mutation patterns
#        now FAIL hard instead of just warning.

set -euo pipefail

echo "🛡️  NEO4J GOVERNANCE COMPLIANCE GATE"
echo "================================="

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Violation accumulator (file-based to avoid subshell counter bug)
VIOL_FILE=$(mktemp)
trap 'rm -f "$VIOL_FILE"' EXIT

add_violation() {
    echo "$1" >> "$VIOL_FILE"
}

count_violations() {
    wc -l < "$VIOL_FILE" 2>/dev/null || echo 0
}

# ---------------------------------------------------------------------------
# Allowlist: ONLY these production files may contain raw driver / session calls
# ---------------------------------------------------------------------------
ALLOWED_PATHS=(
    "mahoun/graph/neo4j/connection.py"
    "mahoun/graph/neo4j/schema.py"
    "mahoun/graph/neo4j/runner.py"
    "tests/"
    "ci/enforcement/"
    "archived_modules/"
    ".worktrees/"
    ".kilo/"
    "venv/"
    ".venv/"
    ".test_classification_backup/"
)

is_allowed() {
    local file_path="$1"
    for allowed in "${ALLOWED_PATHS[@]}"; do
        if [[ "$file_path" == *"$allowed"* ]]; then
            return 0
        fi
    done
    return 1
}

# ---------------------------------------------------------------------------
# 1. AsyncGraphDatabase.driver()
# ---------------------------------------------------------------------------
echo "🚫 Checking AsyncGraphDatabase.driver() ..."
while IFS= read -r line; do
    file_path=$(echo "$line" | cut -d: -f1)
    if ! is_allowed "$file_path"; then
        echo -e "${RED}   VIOLATION: $line${NC}"
        add_violation "AsyncGraphDatabase.driver: $line"
    else
        echo -e "${YELLOW}   ALLOWED: $line${NC}"
    fi
done < <(grep -rn "AsyncGraphDatabase.driver(" --include="*.py" . 2>/dev/null || true)

# ---------------------------------------------------------------------------
# 2. GraphDatabase.driver()
# ---------------------------------------------------------------------------
echo "🚫 Checking GraphDatabase.driver() ..."
while IFS= read -r line; do
    file_path=$(echo "$line" | cut -d: -f1)
    if ! is_allowed "$file_path"; then
        echo -e "${RED}   VIOLATION: $line${NC}"
        add_violation "GraphDatabase.driver: $line"
    else
        echo -e "${YELLOW}   ALLOWED: $line${NC}"
    fi
done < <(grep -rn "GraphDatabase.driver(" --include="*.py" . 2>/dev/null || true)

# ---------------------------------------------------------------------------
# 3. Raw .session() outside governed paths
# ---------------------------------------------------------------------------
echo "🚫 Checking raw .session() calls ..."
while IFS= read -r line; do
    file_path=$(echo "$line" | cut -d: -f1)
    if ! is_allowed "$file_path"; then
        echo -e "${RED}   VIOLATION: $line${NC}"
        add_violation "raw .session(): $line"
    fi
done < <(grep -rn "\.session()" --include="*.py" . 2>/dev/null \
    | grep -v "governed_session" \
    | grep -v "\.pyc" \
    || true)

# ---------------------------------------------------------------------------
# 4. tx.run() outside governed paths
# ---------------------------------------------------------------------------
echo "🚫 Checking tx.run() calls ..."
while IFS= read -r line; do
    file_path=$(echo "$line" | cut -d: -f1)
    if ! is_allowed "$file_path"; then
        echo -e "${RED}   VIOLATION: $line${NC}"
        add_violation "tx.run: $line"
    fi
done < <(grep -rn "tx\.run(" --include="*.py" . 2>/dev/null \
    | grep -v "\.pyc" \
    || true)

# ---------------------------------------------------------------------------
# 5. APOC mutation procedures outside governed paths (HARD FAIL)
# ---------------------------------------------------------------------------
echo "🚫 Checking APOC mutation procedures ..."
while IFS= read -r line; do
    file_path=$(echo "$line" | cut -d: -f1)
    if ! is_allowed "$file_path"; then
        echo -e "${RED}   VIOLATION (APOC mutation): $line${NC}"
        add_violation "APOC mutation: $line"
    fi
done < <(grep -rni \
    "apoc\.create\|apoc\.refactor\|apoc\.nodes\.delete\|apoc\.detachDeleteNodes" \
    --include="*.py" . 2>/dev/null \
    | grep -v "\.pyc" \
    || true)

# ---------------------------------------------------------------------------
# 6. Direct mutation Cypher outside approved paths (HARD FAIL)
#    Patterns: MERGE (, CREATE (, DETACH DELETE, DELETE
#    Scoped to Python string literals only (heuristic grep)
# ---------------------------------------------------------------------------
echo "🚫 Checking raw mutation Cypher in Python source ..."
MUTATION_CYPHER_VIOLATIONS=$(
    grep -rn \
        -e 'MERGE (' \
        -e 'CREATE (' \
        -e 'DETACH DELETE' \
        -e 'session\.run(' \
        --include="*.py" . 2>/dev/null \
    | grep -v '\#' \
    | grep -v 'governed_session' \
    | grep -v 'write_node\|write_relationship\|delete_node' \
    | grep -v '\.pyc' \
    | grep -v 'tests/' \
    | grep -v '.test_classification_backup/' \
    | grep -v 'mahoun/graph/neo4j/connection.py' \
    | grep -v 'mahoun/graph/neo4j/schema.py' \
    | grep -v 'mahoun/core/governance/mutation_boundary.py' \
    | grep -v 'mahoun/core/governance/' \
    || true
)
if [ -n "$MUTATION_CYPHER_VIOLATIONS" ]; then
    echo -e "${RED}❌ CRITICAL: Raw mutation Cypher outside governed paths:${NC}"
    echo "$MUTATION_CYPHER_VIOLATIONS"
    while IFS= read -r line; do
        add_violation "mutation Cypher: $line"
    done <<< "$MUTATION_CYPHER_VIOLATIONS"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "📊 GOVERNANCE COMPLIANCE SUMMARY"
echo "================================"

TOTAL=$(count_violations)

if [ "$TOTAL" -eq 0 ]; then
    echo -e "${GREEN}✅ PASS: No governance violations detected${NC}"
    echo "   - All Neo4j access goes through approved paths"
    echo "   - MutationAuthorizationBoundary integrity maintained"
    exit 0
else
    echo -e "${RED}❌ FAIL: $TOTAL governance violations found${NC}"
    echo ""
    echo "REMEDIATION:"
    echo "1. Replace direct driver usage with get_connection().governed_session()"
    echo "2. Use connection.execute_query() for read-only queries"
    echo "3. All mutations must go through GovernedNeo4jSession.write_node/write_relationship"
    echo ""
    echo "See: mahoun/core/governance/mutation_boundary.py"
    exit 1
fi
