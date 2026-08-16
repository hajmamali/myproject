#!/usr/bin/env bash
# ==============================================================================
# Gate: API Database Access Firewall
# ==============================================================================
# Enforces governance-compliant database access in API layer.
# Blocks direct Neo4j driver instantiation and imports outside canonical layer.
#
# Constitutional Authority:
# - AGENTS.md Section 1-A: Canonical Neo4j Connection
# - CONSTITUTION.md Section 7: Source of Truth Principle
# - docs/governance/API_DATABASE_ACCESS_AUDIT.md
#
# Exit Codes:
# - 0: All checks passed (governance compliant)
# - 1: Violations detected (CI failure)
# - 2: Script error or configuration issue

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WORKSPACE_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo -e "${BLUE}  Gate: API Database Access Firewall${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
echo ""

# ==============================================================================
# Configuration
# ==============================================================================

FIREWALL_SCRIPT="$WORKSPACE_ROOT/ci/enforcement/api_database_firewall.py"
TARGET_DIR="$WORKSPACE_ROOT/api"
FAIL_ON_SEVERITY="P0"  # Fail CI on P0 violations

# ==============================================================================
# Pre-flight Checks
# ==============================================================================

if [ ! -f "$FIREWALL_SCRIPT" ]; then
    echo -e "${RED}❌ Error: Firewall script not found: $FIREWALL_SCRIPT${NC}"
    echo -e "${YELLOW}   This gate requires ci/enforcement/api_database_firewall.py${NC}"
    exit 2
fi

if [ ! -d "$TARGET_DIR" ]; then
    echo -e "${RED}❌ Error: Target directory not found: $TARGET_DIR${NC}"
    exit 2
fi

# Ensure Python is available
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Error: python3 not found in PATH${NC}"
    exit 2
fi

# ==============================================================================
# Run Firewall
# ==============================================================================

echo -e "${BLUE}→ Running AST-based database access firewall...${NC}"
echo ""

# Run firewall with explicit failure threshold
if python3 "$FIREWALL_SCRIPT" "$TARGET_DIR" --fail-on "$FAIL_ON_SEVERITY" --no-snippets; then
    echo ""
    echo -e "${GREEN}✅ PASS: API layer is governance compliant${NC}"
    echo -e "${GREEN}   No forbidden database access patterns detected${NC}"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────${NC}"
    echo -e "${GREEN}✅ Gate Passed: API Database Access Firewall${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    exit 0
else
    EXIT_CODE=$?
    echo ""
    echo -e "${RED}❌ FAIL: Governance violations detected in API layer${NC}"
    echo ""
    echo -e "${YELLOW}Remediation Steps:${NC}"
    echo -e "${YELLOW}1. Review violation report above${NC}"
    echo -e "${YELLOW}2. Replace direct neo4j imports with canonical layer:${NC}"
    echo -e "${YELLOW}   from mahoun.graph.neo4j.connection import get_connection${NC}"
    echo ""
    echo -e "${YELLOW}3. Replace direct driver instantiation:${NC}"
    echo -e "${YELLOW}   driver = await initialize_canonical_async_driver(uri, auth, **config)${NC}"
    echo ""
    echo -e "${YELLOW}4. See: docs/governance/API_DATABASE_ACCESS_AUDIT.md${NC}"
    echo ""
    echo -e "${BLUE}───────────────────────────────────────────────────────────────────${NC}"
    echo -e "${RED}❌ Gate Failed: API Database Access Firewall${NC}"
    echo -e "${BLUE}═══════════════════════════════════════════════════════════════════${NC}"
    echo ""
    exit 1
fi
