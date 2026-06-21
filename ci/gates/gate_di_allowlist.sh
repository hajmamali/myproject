#!/usr/bin/env bash
# Gate: Neo4j DI Allowlist Enforcement
# Blocks any file outside the Neo4j allowlist from importing or constructing:
#   - GraphDatabase.driver()
#   - AsyncGraphDatabase.driver()
#   - Neo4jConnection(...) direct instantiation
#
# Allowlist (only these files may create Neo4j drivers/connections):
#   - mahoun/graph/neo4j/connection.py
#   - mahoun/graph/neo4j/schema.py
#   - api/database.py
#
# Exit 0 = clean. Exit 1 = violation found.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
cd "$PROJECT_ROOT"

ALLOWLIST_FILES=(
  "mahoun/graph/neo4j/connection.py"
  "mahoun/graph/neo4j/schema.py"
  "api/database.py"
)

VIOLATIONS=0

echo "=========================================="
echo "Gate: Neo4j DI Allowlist Enforcement"
echo "=========================================="
echo ""
echo "Allowlist (authorized files):"
for f in "${ALLOWLIST_FILES[@]}"; do
  echo "  - $f"
done
echo ""

# Pattern 1: GraphDatabase.driver() outside allowlist
echo "→ Checking for GraphDatabase.driver() outside allowlist..."
MATCHES=$(grep -rn 'GraphDatabase\.driver(' mahoun/ api/ \
  --include="*.py" \
  --exclude-dir="__pycache__" \
  --exclude-dir=".git" \
  --exclude-dir=".pytest_cache" \
  2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  # Filter out allowlist files
  FILTERED=""
  while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    is_allowed=false
    for allowed in "${ALLOWLIST_FILES[@]}"; do
      if [[ "$file" == "$allowed" ]]; then
        is_allowed=true
        break
      fi
    done
    if [ "$is_allowed" = false ]; then
      FILTERED="${FILTERED}${line}\n"
    fi
  done <<< "$MATCHES"
  
  if [ -n "$FILTERED" ]; then
    echo "❌ VIOLATION: GraphDatabase.driver() found outside allowlist:"
    echo -e "$FILTERED"
    VIOLATIONS=$((VIOLATIONS + 1))
  else
    echo "✓ Clean (all matches are in allowlist files)"
  fi
else
  echo "✓ Clean (no matches)"
fi
echo ""

# Pattern 2: AsyncGraphDatabase.driver() outside allowlist
echo "→ Checking for AsyncGraphDatabase.driver() outside allowlist..."
MATCHES=$(grep -rn 'AsyncGraphDatabase\.driver(' mahoun/ api/ \
  --include="*.py" \
  --exclude-dir="__pycache__" \
  --exclude-dir=".git" \
  --exclude-dir=".pytest_cache" \
  2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  # Filter out allowlist files
  FILTERED=""
  while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    is_allowed=false
    for allowed in "${ALLOWLIST_FILES[@]}"; do
      if [[ "$file" == "$allowed" ]]; then
        is_allowed=true
        break
      fi
    done
    if [ "$is_allowed" = false ]; then
      FILTERED="${FILTERED}${line}\n"
    fi
  done <<< "$MATCHES"
  
  if [ -n "$FILTERED" ]; then
    echo "❌ VIOLATION: AsyncGraphDatabase.driver() found outside allowlist:"
    echo -e "$FILTERED"
    VIOLATIONS=$((VIOLATIONS + 1))
  else
    echo "✓ Clean (all matches are in allowlist files)"
  fi
else
  echo "✓ Clean (no matches)"
fi
echo ""

# Pattern 3: Neo4jConnection(...) direct instantiation
# Allowed usage: get_connection() or within connection.py itself
echo "→ Checking for Neo4jConnection(...) direct instantiation outside connection.py..."
MATCHES=$(grep -rn 'Neo4jConnection(' mahoun/ api/ \
  --include="*.py" \
  --exclude-dir="__pycache__" \
  --exclude-dir=".git" \
  --exclude-dir=".pytest_cache" \
  2>/dev/null || true)

if [ -n "$MATCHES" ]; then
  # Filter: exclude connection.py, get_connection() calls, type hints, imports, comments
  FILTERED=""
  while IFS= read -r line; do
    file=$(echo "$line" | cut -d: -f1)
    content=$(echo "$line" | cut -d: -f3-)
    
    # Skip if in connection.py (allowlist)
    if [[ "$file" == "mahoun/graph/neo4j/connection.py" ]]; then
      continue
    fi
    
    # Skip comments (lines starting with # after stripping whitespace)
    content_trimmed=$(echo "$content" | sed 's/^[[:space:]]*//')
    if [[ "$content_trimmed" == \#* ]]; then
      continue
    fi
    
    # Skip if it's get_connection() call (authorized pattern)
    if [[ "$content" == *"get_connection()"* ]]; then
      continue
    fi
    
    # Skip type hints like ": Neo4jConnection" or "-> Neo4jConnection"
    if [[ "$content" =~ :[[:space:]]*Neo4jConnection || "$content" =~ -\>[[:space:]]*Neo4jConnection ]]; then
      continue
    fi
    
    # Skip imports like "from ... import Neo4jConnection"
    if [[ "$content" =~ ^[[:space:]]*from.*import.*Neo4jConnection || "$content" =~ ^[[:space:]]*import.*Neo4jConnection ]]; then
      continue
    fi
    
    # If we get here, it's a direct instantiation violation
    FILTERED="${FILTERED}${line}\n"
  done <<< "$MATCHES"
  
  if [ -n "$FILTERED" ]; then
    echo "❌ VIOLATION: Direct Neo4jConnection(...) instantiation found (use get_connection() instead):"
    echo -e "$FILTERED"
    VIOLATIONS=$((VIOLATIONS + 1))
  else
    echo "✓ Clean (all matches are authorized patterns)"
  fi
else
  echo "✓ Clean (no matches)"
fi
echo ""

# Summary
echo "=========================================="
if [ $VIOLATIONS -eq 0 ]; then
  echo "✅ PASS: Neo4j DI Allowlist Gate"
  echo "=========================================="
  exit 0
else
  echo "❌ FAIL: Found $VIOLATIONS violation(s)"
  echo ""
  echo "Fix: Neo4j driver/connection creation is restricted to:"
  echo "  - mahoun/graph/neo4j/connection.py"
  echo "  - mahoun/graph/neo4j/schema.py"
  echo "  - api/database.py"
  echo ""
  echo "All other code must use:"
  echo "  - get_connection() to obtain the Neo4j singleton"
  echo "  - connection.governed_session() for queries"
  echo "=========================================="
  exit 1
fi
