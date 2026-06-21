#!/usr/bin/env bash

# =========================================================
# MAHOUN REPOSITORY CONTAMINATION AUDIT
# Governance / Archive / Backup Isolation Scanner
# =========================================================

set -euo pipefail

ROOT_DIR="$(pwd)"
OUTPUT_FILE="governance_repo_audit_report.txt"

echo "==================================================" > "$OUTPUT_FILE"
echo "MAHOUN GOVERNANCE REPOSITORY AUDIT REPORT" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"
echo "Generated: $(date -Iseconds)" >> "$OUTPUT_FILE"
echo "Root: $ROOT_DIR" >> "$OUTPUT_FILE"
echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 1 - DETECT ARCHIVE / BACKUP DIRECTORIES
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[1] ARCHIVE / BACKUP / SNAPSHOT DIRECTORIES" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

find . -type d \( \
-name "*backup*" -o \
-name "*archive*" -o \
-name "*snapshot*" -o \
-name "Mahoun_v2*" -o \
-name "kingmahoun*" \
\) >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 2 - SEARCH FOR DANGEROUS REFERENCES
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[2] DANGEROUS REFERENCE SCAN" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

grep -RInE \
"(backup|archive|snapshot|Mahoun_v2|kingmahoun)" \
mahoun/ api/ tests/ scripts/ \
--include="*.py" >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 3 - IMPORT/PATH MANIPULATION
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[3] IMPORT PATH MANIPULATION SCAN" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

grep -RInE \
"(sys\.path|PYTHONPATH|append\(|insert\()" \
mahoun/ api/ tests/ \
--include="*.py" >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 4 - HARDCODED ABSOLUTE PATHS
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[4] HARDCODED PATH SCAN" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

grep -RInE \
"(/home/haji|Desktop|Documents|backup|archive|snapshot)" \
mahoun/ api/ tests/ \
--include="*.py" >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 5 - RAW NEO4J ACCESS
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[5] RAW NEO4J ACCESS SCAN" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

grep -RInE \
"(session\.run\(|driver\.session\(|\.run\()" \
mahoun/ api/ tests/ \
--include="*.py" >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 6 - GOVERNANCE CONTEXT BYPASS
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[6] GOVERNANCE CONTEXT BYPASS SCAN" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

grep -RInE \
"(GovernanceContextManager\._local_context|bypass|disable_governance|skip_validation)" \
mahoun/ api/ tests/ \
--include="*.py" >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 7 - GIT STATUS
# =========================================================

echo "==================================================" >> "$OUTPUT_FILE"
echo "[7] GIT STATUS" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

git status >> "$OUTPUT_FILE" 2>&1 || true

echo "" >> "$OUTPUT_FILE"

# =========================================================
# SECTION 8 - SUMMARY + SEVERITY
# =========================================================

echo "" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"
echo "[8] SUMMARY" >> "$OUTPUT_FILE"
echo "==================================================" >> "$OUTPUT_FILE"

TOTAL_BACKUP_REFS=$(grep -ciE "(backup|archive|snapshot|Mahoun_v2|kingmahoun)" "$OUTPUT_FILE" || true)
TOTAL_PATH_MANIPS=$(grep -ciE "(sys\.path|PYTHONPATH|append\(|insert\()" "$OUTPUT_FILE" || true)
TOTAL_HARDCODED=$(grep -ciE "(/home/haji|Desktop|Documents)" "$OUTPUT_FILE" || true)
TOTAL_RAW_NEO4J=$(grep -ciE "(session\.run|driver\.session)" "$OUTPUT_FILE" || true)
TOTAL_BYPASS=$(grep -ciE "(bypass|disable_governance|skip_validation)" "$OUTPUT_FILE" || true)

echo "Backup/Archive References : $TOTAL_BACKUP_REFS" >> "$OUTPUT_FILE"
echo "Path Manipulations        : $TOTAL_PATH_MANIPS" >> "$OUTPUT_FILE"
echo "Hardcoded Paths           : $TOTAL_HARDCODED" >> "$OUTPUT_FILE"
echo "Raw Neo4j Access          : $TOTAL_RAW_NEO4J" >> "$OUTPUT_FILE"
echo "Governance Bypass Hints   : $TOTAL_BYPASS" >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"

# Severity scoring
RISK_SCORE=$((TOTAL_RAW_NEO4J + TOTAL_BYPASS * 2 + TOTAL_PATH_MANIPS))

echo "Governance Risk Score     : $RISK_SCORE" >> "$OUTPUT_FILE"

if [ "$RISK_SCORE" -eq 0 ]; then
    SEVERITY="CLEAN"
elif [ "$RISK_SCORE" -lt 10 ]; then
    SEVERITY="LOW"
elif [ "$RISK_SCORE" -lt 25 ]; then
    SEVERITY="MEDIUM"
else
    SEVERITY="CRITICAL"
fi

echo "Severity Level            : $SEVERITY" >> "$OUTPUT_FILE"

echo "" >> "$OUTPUT_FILE"
echo "Audit completed at: $(date -Iseconds)" >> "$OUTPUT_FILE"

# =========================================================
# CONSOLE SUMMARY
# =========================================================

echo ""
echo "=================================================="
echo "MAHOUN GOVERNANCE AUDIT SUMMARY"
echo "=================================================="
echo "Backup refs      : $TOTAL_BACKUP_REFS"
echo "Path manip       : $TOTAL_PATH_MANIPS"
echo "Hardcoded paths  : $TOTAL_HARDCODED"
echo "Raw Neo4j        : $TOTAL_RAW_NEO4J"
echo "Bypass hints     : $TOTAL_BYPASS"
echo "--------------------------------------------------"
echo "RISK SCORE       : $RISK_SCORE"
echo "SEVERITY         : $SEVERITY"
echo "=================================================="
echo "Full report:"
echo "$OUTPUT_FILE"
echo "=================================================="

# =========================================================
# TOP OFFENDERS
# =========================================================

echo ""
echo "TOP MATCHES:"
echo "=================================================="

grep -Ein \
"(backup|archive|snapshot|sys\.path|session\.run|driver\.session|skip_validation|disable_governance)" \
"$OUTPUT_FILE" | head -20 || true

echo "=================================================="

