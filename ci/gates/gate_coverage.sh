#!/bin/bash
# Coverage gate — fail CI when coverage regresses or critical modules fall below threshold.
#
# Requires:
#   - coverage.json from current pytest run
#   - ci/coverage_baseline.json from measured baseline (scripts/generate_coverage_baseline.py)

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

cd "$PROJECT_ROOT"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

BASELINE="${PROJECT_ROOT}/ci/coverage_baseline.json"
CURRENT="${PROJECT_ROOT}/coverage.json"

if [[ ! -f "$CURRENT" ]]; then
  echo -e "${RED}❌ coverage.json not found. Run pytest with --cov-report=json first.${NC}"
  exit 1
fi

if [[ ! -f "$BASELINE" ]]; then
  echo -e "${YELLOW}⚠️  No baseline at ci/coverage_baseline.json — seeding from current run${NC}"
  python3 "${PROJECT_ROOT}/scripts/generate_coverage_baseline.py" --input "$CURRENT" --output "$BASELINE"
  echo -e "${GREEN}✓ Baseline seeded${NC}"
  exit 0
fi

python3 - <<'PY'
import json
import sys
from pathlib import Path

baseline_path = Path("ci/coverage_baseline.json")
current_path = Path("coverage.json")

baseline = json.loads(baseline_path.read_text())
current = json.loads(current_path.read_text())

def overall(data):
    t = data.get("totals", {})
    stmts = t.get("num_statements", 0)
    covered = t.get("covered_lines", 0)
    return round((covered / stmts) * 100, 2) if stmts else 0.0

def module_cov(data, module_name):
    files = data.get("files", {})
    stmts = missed = 0
    prefix = f"mahoun/{module_name}/"
    for path, fd in files.items():
        if not path.startswith(prefix):
            continue
        s = fd.get("summary", {})
        n = s.get("num_statements", 0)
        m = s.get("missing_lines", 0)
        if isinstance(m, list):
            m = len(m)
        stmts += n
        missed += m
    return round(((stmts - missed) / stmts) * 100, 2) if stmts else None

baseline_overall = baseline.get("overall_coverage", overall(baseline))
current_overall = overall(current)

errors = []

if current_overall < baseline_overall:
    errors.append(
        f"Overall coverage regressed: {current_overall}% < baseline {baseline_overall}%"
    )

thresholds = {"governance": 80.0, "ledger": 75.0, "reasoning": 70.0, "fortress": 80.0}
for mod, threshold in thresholds.items():
    cov = module_cov(current, mod)
    if cov is None:
        continue
    if cov < threshold:
        errors.append(f"Critical module '{mod}' below threshold: {cov}% < {threshold}%")

# Detect new mahoun/*.py files with zero test coverage contribution (statements > 0, 0% covered)
baseline_files = set(baseline.get("files", {}).keys()) if "files" in baseline else set()
current_files = current.get("files", {})
new_untested = []
for path, fd in current_files.items():
    if not path.startswith("mahoun/") or not path.endswith(".py"):
        continue
    if path in baseline_files:
        continue
    s = fd.get("summary", {})
    n = s.get("num_statements", 0)
    m = s.get("missing_lines", 0)
    if isinstance(m, list):
        m = len(m)
    if n > 0 and m == n:
        new_untested.append(path)

if new_untested:
    errors.append(
        "New code with no test coverage: " + ", ".join(new_untested[:10])
        + (" ..." if len(new_untested) > 10 else "")
    )

if errors:
    print("COVERAGE GATE FAILED")
    for e in errors:
        print(f"  - {e}")
    sys.exit(1)

print(f"COVERAGE GATE PASSED (overall={current_overall}%, baseline={baseline_overall}%)")
PY

echo -e "${GREEN}✓ Coverage gate passed${NC}"
