#!/usr/bin/env python3
"""
check_mypy_non_regression.py
============================
Compares current mypy output against a baseline to detect NEW errors.

Exit codes:
  0 - No new errors (pass)
  1 - New errors detected (fail)
  2 - Configuration/runtime error

Usage:
  python check_mypy_non_regression.py [--update-baseline]

Comparison logic:
- Parse mypy output lines matching: "path:line:col: error: ... [code]"
- Normalize paths, sort errors
- New error = appears in current but not in baseline
- Ignores summary lines like "Found X errors in Y files"
"""

import re
import sys
import subprocess
from pathlib import Path
from typing import Set, List, Tuple


SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR / "../.."
BASELINE_FILE = SCRIPT_DIR / "baseline.txt"
RUN_MYPY_SCRIPT = SCRIPT_DIR / "run_mypy.sh"


def parse_mypy_errors(output: str) -> Set[str]:
    """
    Extract and normalize mypy error lines from output.
    
    Mypy error format:
      path/to/file.py:123:45: error: Message here  [error-code]
      path/to/file.py:123: note: Note here
    
    We normalize to:
      file.py:123: error: Message [error-code]
    (strip col, use basename for stability across systems)
    """
    errors = set()
    # Match lines with "error:" or "note:" - captures file:line: prefix
    # Example: mahoun/core/foo.py:123:45: error: Xyz  [code]
    pattern = re.compile(
        r'^(.+?):(\d+)(?::\d+)?: (error|note): (.+)$',
        re.MULTILINE
    )
    
    for match in pattern.finditer(output):
        filepath, line, severity, message = match.groups()
        # Normalize path to basename for stability
        filename = Path(filepath).name
        # Reconstruct: "filename:line: severity: message"
        normalized = f"{filename}:{line}: {severity}: {message}"
        errors.add(normalized)
    
    return errors


def run_mypy() -> Tuple[str, int]:
    """Run mypy via run_mypy.sh and capture output."""
    try:
        result = subprocess.run(
            ["bash", str(RUN_MYPY_SCRIPT)],
            capture_output=True,
            text=True,
            cwd=PROJECT_ROOT,
        )
        # Combine stdout and stderr (mypy writes to stderr by default)
        output = result.stdout + result.stderr
        return output, result.returncode
    except Exception as e:
        print(f"ERROR: Failed to run mypy: {e}", file=sys.stderr)
        sys.exit(2)


def load_baseline() -> Set[str]:
    """Load baseline errors from file."""
    if not BASELINE_FILE.exists():
        print(f"WARNING: Baseline file not found: {BASELINE_FILE}", file=sys.stderr)
        print("Assuming baseline is empty (all errors are new).", file=sys.stderr)
        return set()
    
    try:
        content = BASELINE_FILE.read_text()
        return parse_mypy_errors(content)
    except Exception as e:
        print(f"ERROR: Failed to read baseline: {e}", file=sys.stderr)
        sys.exit(2)


def save_baseline(errors: Set[str]) -> None:
    """Save current errors as new baseline."""
    # Reconstruct full mypy output format for human readability
    # Sort for determinism
    sorted_errors = sorted(errors)
    content = "\n".join(sorted_errors) + "\n"
    
    try:
        BASELINE_FILE.write_text(content)
        print(f"✅ Baseline updated: {BASELINE_FILE}")
        print(f"   Total errors: {len(errors)}")
    except Exception as e:
        print(f"ERROR: Failed to write baseline: {e}", file=sys.stderr)
        sys.exit(2)


def main():
    """Main entry point."""
    update_baseline = "--update-baseline" in sys.argv
    
    print("=" * 60)
    print("🔍 Mypy Non-Regression Check")
    print("=" * 60)
    
    # Run mypy
    print("\n📊 Running mypy...")
    mypy_output, mypy_exit_code = run_mypy()
    current_errors = parse_mypy_errors(mypy_output)
    
    print(f"   Current errors: {len(current_errors)}")
    
    if update_baseline:
        print("\n🔄 Updating baseline...")
        save_baseline(current_errors)
        return 0
    
    # Load baseline
    print("\n📂 Loading baseline...")
    baseline_errors = load_baseline()
    print(f"   Baseline errors: {len(baseline_errors)}")
    
    # Compare
    new_errors = current_errors - baseline_errors
    fixed_errors = baseline_errors - current_errors
    
    print("\n" + "=" * 60)
    
    if fixed_errors:
        print(f"✅ Fixed errors: {len(fixed_errors)}")
        print("\nSample fixed:")
        for err in sorted(fixed_errors)[:5]:
            print(f"  - {err}")
        if len(fixed_errors) > 5:
            print(f"  ... and {len(fixed_errors) - 5} more")
    
    if new_errors:
        print(f"\n❌ NEW ERRORS DETECTED: {len(new_errors)}")
        print("\nNew errors:")
        for err in sorted(new_errors):
            print(f"  {err}")
        
        print("\n" + "=" * 60)
        print("❌ FAILED: New mypy errors introduced!")
        print("\nTo fix:")
        print("  1. Run: mypy mahoun/ api/")
        print("  2. Fix the errors listed above")
        print("  3. Re-run this check")
        print("\nOr, if errors are intentional:")
        print("  python ci/mypy/check_mypy_non_regression.py --update-baseline")
        return 1
    
    print("\n✅ PASSED: No new mypy errors!")
    
    if len(current_errors) > 0:
        print(f"\n⚠️  Note: {len(current_errors)} existing errors in baseline")
        print("   (These are tracked and will not fail CI)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

