"""
Ratchet regression test for the governance compliance validator.

Runs `scripts/validate_governance_compliance.GovernanceValidator` against
the live repo and asserts that the violation count does not exceed the
"current floor" captured below.

This test FAILS when the violation count regresses upward, forcing the
developer to (a) fix the regression or (b) lower the floor with an
explicit commit that records the new (lower) accepted level.  It never
fails for improvements — when violations drop the floor must be lowered
in the same commit.

The floor was captured at 0 violations on 2026-07-17 after the
governance remediation pass:
  - api/database.py: removed dead get_neo4j(); added startup exemption comment
  - api/routers/system.py: health check rewired to execute_query (governed read)
  - mahoun/graph/neo4j/init_schema.py: GOVERNED EXEMPTION for startup DDL
  - scripts/integrate_orphan_modules.py: patched the patch-string false positive
  - scripts/validate_governance_compliance.py: added .worktrees/ to exclude_patterns
"""

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent

# Maximum number of governance violations permitted by the validator
# today.  Lower this to the new observed value when fixing violations;
# never raise it without a Kernel Directive review (see AGENTRULES.md §6).
_CURRENT_FLOOR = 0


@pytest.fixture(scope="module")
def validator_results():
    """Run the GovernanceValidator once and return the violation list."""
    # Import the validator module from the repo root
    sys.path.insert(0, str(_REPO_ROOT))
    from scripts.validate_governance_compliance import (
        GovernanceValidator,
        ViolationSeverity,
    )

    validator = GovernanceValidator(_REPO_ROOT)
    # Run all checks (avoids the full validate_all() print spam + exit).
    validator._check_mutation_boundary_usage()
    validator._check_direct_driver_creation()
    validator._check_raw_session_usage()
    validator._check_authorized_context_usage()
    validator._check_mutation_bypasses()
    return validator


def test_governance_violation_count_does_not_regress(validator_results):
    """The validator must not detect more violations than the recorded floor."""
    count = len(validator_results.violations)
    assert count <= _CURRENT_FLOOR, (
        f"Governance violation count REGRESSED: expected <= {_CURRENT_FLOOR}, "
        f"got {count}. New violations:\n"
        + "\n".join(
            f"  [{v.severity.value}] {v.file_path}:{v.line_number} "
            f"[{v.category}] {v.description}"
            for v in validator_results.violations
        )
        + "\n\nFix the new violations, or lower _CURRENT_FLOOR only after "
        "remediating them per AGENTRULES.md §6."
    )


def test_no_critical_or_high_governance_violations(validator_results):
    """CRITICAL and HIGH severity violations must always be zero."""
    severe = [
        v
        for v in validator_results.violations
        if v.severity.value
        in (ViolationSeverity.CRITICAL.value, ViolationSeverity.HIGH.value)
    ]
    assert not severe, (
        "Found CRITICAL/HIGH governance violations — these are Kernel "
        "Directive violations and must be remediated immediately:\n"
        + "\n".join(
            f"  [{v.severity.value}] {v.file_path}:{v.line_number} "
            f"[{v.category}] {v.description}"
            for v in severe
        )
    )
