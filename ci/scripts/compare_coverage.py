#!/usr/bin/env python3
"""
Coverage Comparison Script
===========================

Purpose: Compare current coverage against baseline and detect regressions

This script:
1. Loads baseline coverage from ci/coverage_baseline.json
2. Loads current coverage from coverage.json (pytest-cov output)
3. Compares module-level and overall coverage
4. Fails if any module drops below tolerance threshold
5. Generates detailed diff report

Requirements: R6 (Coverage Gate with Regression Prevention)
Task: 2.4 Create coverage comparison script

Exit Codes:
  0 - No regression detected (all modules within tolerance)
  1 - Regression detected (coverage drop exceeds tolerance)
  2 - Missing data files
  3 - Configuration error
"""

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional


@dataclass
class CoverageComparison:
    """Comparison of current vs baseline coverage for a module"""

    module: str
    baseline_percent: float
    current_percent: float
    delta: float
    is_regression: bool
    baseline_statements: int
    current_statements: int


@dataclass
class OverallComparison:
    """Overall coverage comparison statistics"""

    baseline_overall: float
    current_overall: float
    delta: float
    is_regression: bool
    modules_compared: int
    modules_regressed: int
    modules_improved: int


class CoverageComparer:
    """Compare coverage data against baseline"""

    def __init__(self, baseline_path: Path, current_path: Path, tolerance: float):
        self.baseline_path = baseline_path
        self.current_path = current_path
        self.tolerance = tolerance

    def load_baseline(self) -> dict[str, Any]:
        """Load baseline coverage data"""
        if not self.baseline_path.exists():
            raise FileNotFoundError(f"Baseline not found: {self.baseline_path}")

        with open(self.baseline_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_current(self) -> dict[str, Any]:
        """Load current coverage data (pytest-cov format)"""
        if not self.current_path.exists():
            raise FileNotFoundError(f"Current coverage not found: {self.current_path}")

        with open(self.current_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def extract_module_coverage(self, coverage_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Extract module-level coverage from pytest-cov format"""
        files = coverage_data.get("files", {})
        modules: dict[str, dict[str, Any]] = {}

        for file_path, file_data in files.items():
            # Only process mahoun/* files
            if not file_path.startswith("mahoun/"):
                continue

            # Extract module name (e.g., mahoun/core/models.py -> core)
            parts = file_path.split("/")
            if len(parts) >= 2:
                module_name = parts[1]
            else:
                continue

            summary = file_data.get("summary", {})
            statements = summary.get("num_statements", 0)
            covered = summary.get("covered_lines", statements - summary.get("missing_lines", 0))

            # Aggregate by module
            if module_name not in modules:
                modules[module_name] = {"statements": 0, "covered": 0}

            modules[module_name]["statements"] += statements
            modules[module_name]["covered"] += covered

        # Calculate percentages
        for module_name, data in modules.items():
            if data["statements"] > 0:
                data["percent"] = round((data["covered"] / data["statements"]) * 100, 2)
            else:
                data["percent"] = 0.0

        return modules

    def compare_modules(
        self, baseline: dict[str, Any], current_modules: dict[str, dict[str, Any]]
    ) -> list[CoverageComparison]:
        """Compare module-level coverage"""
        comparisons: list[CoverageComparison] = []

        baseline_modules = baseline.get("modules", {})

        # Compare modules present in baseline
        for module_name, baseline_data in baseline_modules.items():
            baseline_percent = baseline_data.get("coverage_percent", 0.0)
            baseline_statements = baseline_data.get("statements", 0)

            current_data = current_modules.get(module_name, {})
            current_percent = current_data.get("percent", 0.0)
            current_statements = current_data.get("statements", 0)

            delta = current_percent - baseline_percent
            is_regression = delta < -self.tolerance

            comparisons.append(
                CoverageComparison(
                    module=module_name,
                    baseline_percent=baseline_percent,
                    current_percent=current_percent,
                    delta=delta,
                    is_regression=is_regression,
                    baseline_statements=baseline_statements,
                    current_statements=current_statements,
                )
            )

        return comparisons

    def calculate_overall(
        self, baseline: dict[str, Any], current_modules: dict[str, dict[str, Any]]
    ) -> OverallComparison:
        """Calculate overall coverage comparison"""
        baseline_overall = baseline.get("overall_coverage", 0.0)

        # Calculate current overall
        total_statements = sum(m["statements"] for m in current_modules.values())
        total_covered = sum(m["covered"] for m in current_modules.values())

        if total_statements > 0:
            current_overall = round((total_covered / total_statements) * 100, 2)
        else:
            current_overall = 0.0

        delta = current_overall - baseline_overall
        is_regression = delta < -self.tolerance

        return OverallComparison(
            baseline_overall=baseline_overall,
            current_overall=current_overall,
            delta=delta,
            is_regression=is_regression,
            modules_compared=len(baseline.get("modules", {})),
            modules_regressed=0,  # Will be filled later
            modules_improved=0,  # Will be filled later
        )

    def compare(self) -> tuple[list[CoverageComparison], OverallComparison]:
        """Perform full comparison"""
        baseline = self.load_baseline()
        current_data = self.load_current()
        current_modules = self.extract_module_coverage(current_data)

        module_comparisons = self.compare_modules(baseline, current_modules)
        overall_comparison = self.calculate_overall(baseline, current_modules)

        # Update overall stats
        overall_comparison.modules_regressed = sum(1 for c in module_comparisons if c.is_regression)
        overall_comparison.modules_improved = sum(1 for c in module_comparisons if c.delta > 0)

        return module_comparisons, overall_comparison


def print_comparison_report(
    module_comparisons: list[CoverageComparison], overall: OverallComparison, tolerance: float
):
    """Print detailed comparison report"""
    print("\n" + "=" * 80)
    print("COVERAGE COMPARISON REPORT")
    print("=" * 80)
    print(f"Tolerance:        {tolerance:.1f}%")
    print(f"Modules Compared: {overall.modules_compared}")
    print()

    print("OVERALL COVERAGE:")
    print("-" * 80)
    print(f"Baseline:  {overall.baseline_overall:>6.2f}%")
    print(f"Current:   {overall.current_overall:>6.2f}%")
    print(f"Delta:     {overall.delta:>+6.2f}%")

    if overall.is_regression:
        print(f"Status:    ❌ REGRESSION (exceeds tolerance)")
    elif overall.delta > 0:
        print(f"Status:    ✅ IMPROVED")
    else:
        print(f"Status:    ✅ STABLE")

    print()

    # Show regressions first
    regressions = [c for c in module_comparisons if c.is_regression]
    if regressions:
        print("MODULES WITH REGRESSIONS:")
        print("-" * 80)
        print(f"{'Module':<25} {'Baseline':>10} {'Current':>10} {'Delta':>10}")
        print("-" * 80)

        for comp in sorted(regressions, key=lambda x: x.delta):
            print(
                f"{comp.module:<25} {comp.baseline_percent:>9.2f}% {comp.current_percent:>9.2f}% "
                f"{comp.delta:>+9.2f}%"
            )

        print()

    # Show improvements
    improvements = [c for c in module_comparisons if c.delta > 1.0]
    if improvements:
        print(f"MODULES WITH IMPROVEMENTS (>{tolerance:.0f}%):")
        print("-" * 80)
        print(f"{'Module':<25} {'Baseline':>10} {'Current':>10} {'Delta':>10}")
        print("-" * 80)

        for comp in sorted(improvements, key=lambda x: x.delta, reverse=True)[:10]:
            print(
                f"{comp.module:<25} {comp.baseline_percent:>9.2f}% {comp.current_percent:>9.2f}% "
                f"{comp.delta:>+9.2f}%"
            )

        print()

    # Summary statistics
    print("SUMMARY:")
    print("-" * 80)
    print(f"  Modules Regressed:  {overall.modules_regressed}")
    print(f"  Modules Improved:   {overall.modules_improved}")
    print(f"  Modules Stable:     {overall.modules_compared - overall.modules_regressed - overall.modules_improved}")

    print("=" * 80)
    print()


def main():
    """Main execution"""
    import argparse

    parser = argparse.ArgumentParser(description="Compare coverage against baseline")
    parser.add_argument(
        "--baseline",
        type=Path,
        required=True,
        help="Path to baseline coverage JSON",
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Path to current coverage JSON",
    )
    parser.add_argument(
        "--tolerance",
        type=float,
        default=2.0,
        help="Tolerance percentage (default: 2.0)",
    )
    parser.add_argument(
        "--fail-on-regression",
        action="store_true",
        help="Exit with code 1 if regression detected",
    )

    args = parser.parse_args()

    try:
        comparer = CoverageComparer(
            baseline_path=args.baseline, current_path=args.current, tolerance=args.tolerance
        )

        module_comparisons, overall = comparer.compare()

        print_comparison_report(module_comparisons, overall, args.tolerance)

        # Determine exit code
        has_regression = overall.is_regression or any(c.is_regression for c in module_comparisons)

        if has_regression:
            print("❌ Coverage regression detected")
            if args.fail_on_regression:
                return 1
            else:
                print("⚠️  Continuing (--fail-on-regression not set)")
                return 0
        else:
            print("✅ Coverage gate passed - no regressions detected")
            return 0

    except FileNotFoundError as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        return 3


if __name__ == "__main__":
    sys.exit(main())
