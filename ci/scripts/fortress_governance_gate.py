#!/usr/bin/env python3
"""
MAHOUN Fortress & Governance CI Gate
======================================

Classification: CRITICAL / CI-GATING / FAIL-CLOSED
Purpose: Validates FortressValidator integration, GovernanceLock enforcement,
         GovernanceContext mandatory usage, and provenance tracking across the codebase.

Exit Codes:
    0 - All governance gates pass
    1 - One or more governance gates failed
    2 - Critical configuration files missing

Author: MAHOUN Platform Governance Council
Version: 2.0.0
"""

import ast
import re
import sys
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

# Files that MUST import/use FortressValidator or FortressProtectedReasoningService
FORTRESS_REQUIRED_FILES = [
    "api/routers/reasoning.py",
    "mahoun/reasoning/fortress_integration.py",
]

# Files that MUST import/use GovernanceLock
GOVERNANCE_LOCK_REQUIRED_FILES = [
    "mahoun/reasoning/unified_reasoning_service.py",
]

# Files that MUST import/use GovernanceContextManager
GOVERNANCE_CONTEXT_REQUIRED_FILES = [
    "api/routers/reasoning.py",
    "mahoun/reasoning/fortress_integration.py",
]

# Files that MUST reference provenance
PROVENANCE_REQUIRED_FILES = [
    "mahoun/core/governance/governance_context.py",
    "mahoun/core/governance/provenance_tracker.py",
]

# Critical governance files that MUST exist
CRITICAL_FILES = [
    "mahoun/core/fortress_validator.py",
    "mahoun/core/governance_lock.py",
    "mahoun/core/governance/governance_context.py",
    "mahoun/core/governance/provenance_tracker.py",
    "mahoun/core/governance/validator_pipeline.py",
    "mahoun/core/governance/deterministic_resolver.py",
    "mahoun/core/governance/ontology_enforcer.py",
    "mahoun/core/governance/violations.py",
    "mahoun/reasoning/fortress_integration.py",
    "constitution/RedLines.yaml",
    "monitoring/prometheus/alerts/governance_alerts.yml",
]

# Patterns that indicate governance bypass attempts
BYPASS_PATTERNS = [
    # Disabling fortress validation
    (r'strict_mode\s*=\s*False', "Fortress strict_mode=False disables security enforcement"),
    # Skipping governance checks
    (r'SKIP_GOVERNANCE|BYPASS_FORTRESS|DISABLE_VALIDATION', "Governance bypass flag detected"),
    # Silencing security exceptions
    (r'except\s+SecurityBreachException.*:\s*\n\s*pass', "Silent SecurityBreachException handling"),
    # Lowering agreement thresholds below safe minimum
    (r'agreement_threshold\s*=\s*0\.[0-4]', "Agreement threshold below safe minimum (0.5)"),
]

# ============================================================================
# GATE CHECKS
# ============================================================================


class GateResult:
    """Result of a single gate check."""

    def __init__(self, name: str):
        self.name = name
        self.passed = True
        self.violations: list[str] = []

    def fail(self, message: str):
        self.passed = False
        self.violations.append(message)

    def __str__(self):
        status = "✅ PASS" if self.passed else "❌ FAIL"
        result = f"  {status}: {self.name}"
        for v in self.violations:
            result += f"\n    ⛔ {v}"
        return result


def gate_critical_files_exist(root: Path) -> GateResult:
    """Gate 1: Verify all critical governance files exist."""
    gate = GateResult("Critical Governance Files Exist")
    for filepath in CRITICAL_FILES:
        full_path = root / filepath
        if not full_path.exists():
            gate.fail(f"MISSING: {filepath}")
    return gate


def gate_fortress_integration(root: Path) -> GateResult:
    """Gate 2: Verify FortressValidator is integrated in required files."""
    gate = GateResult("FortressValidator Integration")

    for filepath in FORTRESS_REQUIRED_FILES:
        full_path = root / filepath
        if not full_path.exists():
            gate.fail(f"File not found: {filepath}")
            continue

        content = full_path.read_text(encoding="utf-8")

        has_fortress = (
            "FortressValidator" in content
            or "FortressProtectedReasoningService" in content
            or "fortress_integration" in content
        )

        if not has_fortress:
            gate.fail(f"FortressValidator not integrated in {filepath}")

    return gate


def gate_governance_lock(root: Path) -> GateResult:
    """Gate 3: Verify GovernanceLock is used in required files."""
    gate = GateResult("GovernanceLock Enforcement")

    for filepath in GOVERNANCE_LOCK_REQUIRED_FILES:
        full_path = root / filepath
        if not full_path.exists():
            gate.fail(f"File not found: {filepath}")
            continue

        content = full_path.read_text(encoding="utf-8")

        if "GovernanceLock" not in content:
            gate.fail(f"GovernanceLock not imported/used in {filepath}")

    # Verify GovernanceLock is fail-closed (defaults to STRICT)
    lock_file = root / "mahoun/core/governance_lock.py"
    if lock_file.exists():
        content = lock_file.read_text(encoding="utf-8")
        if "GovernanceMode.STRICT" not in content:
            gate.fail("GovernanceLock does not default to STRICT mode (fail-closed violation)")
    else:
        gate.fail("governance_lock.py not found")

    return gate


def gate_governance_context(root: Path) -> GateResult:
    """Gate 4: Verify GovernanceContextManager is enforced in required files."""
    gate = GateResult("GovernanceContext Enforcement")

    for filepath in GOVERNANCE_CONTEXT_REQUIRED_FILES:
        full_path = root / filepath
        if not full_path.exists():
            gate.fail(f"File not found: {filepath}")
            continue

        content = full_path.read_text(encoding="utf-8")

        has_context = (
            "GovernanceContextManager" in content
            or "GovernanceScopeEnforcer" in content
            or "require_context" in content
        )

        if not has_context:
            gate.fail(f"GovernanceContextManager not enforced in {filepath}")

    return gate


def gate_provenance_tracking(root: Path) -> GateResult:
    """Gate 5: Verify provenance tracking is implemented."""
    gate = GateResult("Provenance Tracking")

    for filepath in PROVENANCE_REQUIRED_FILES:
        full_path = root / filepath
        if not full_path.exists():
            gate.fail(f"File not found: {filepath}")
            continue

        content = full_path.read_text(encoding="utf-8")

        if "provenance" not in content.lower() and "ProvenanceTracker" not in content:
            gate.fail(f"Provenance tracking not found in {filepath}")

    return gate


def gate_bypass_prevention(root: Path) -> GateResult:
    """Gate 6: Scan for governance bypass patterns in production code."""
    gate = GateResult("Governance Bypass Prevention")

    # Scan production code (exclude tests, venv, archive)
    skip_dirs = {".venv", "venv", ".pytest_cache", "tests", "archive", ".git",
                 ".kilo", ".qoder", ".claude", ".deepseek", "build", "__pycache__",
                 "node_modules", ".mypy_cache", ".ruff_cache"}

    for py_file in root.rglob("*.py"):
        if any(d in py_file.parts for d in skip_dirs):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            rel_path = str(py_file.relative_to(root))

            for pattern, message in BYPASS_PATTERNS:
                matches = re.finditer(pattern, content)
                for match in matches:
                    line_no = content.count('\n', 0, match.start()) + 1
                    gate.fail(f"{rel_path}:{line_no} - {message}")

        except (UnicodeDecodeError, PermissionError):
            continue

    return gate


def gate_monitoring_alerts(root: Path) -> GateResult:
    """Gate 7: Verify monitoring alerts are configured."""
    gate = GateResult("Monitoring Alerts Configuration")

    alerts_file = root / "monitoring/prometheus/alerts/governance_alerts.yml"
    if not alerts_file.exists():
        gate.fail("governance_alerts.yml not found")
        return gate

    content = alerts_file.read_text(encoding="utf-8")

    # Required alert rules
    required_alerts = [
        "GovernanceBypassAttemptDetected",
        "FortressValidationFailureHigh",
        "MissingGovernanceContext",
    ]

    for alert_name in required_alerts:
        if alert_name not in content:
            gate.fail(f"Required alert '{alert_name}' not found in governance_alerts.yml")

    # Verify Prometheus config loads alert rules
    prom_config = root / "monitoring/prometheus/prometheus.yml"
    if prom_config.exists():
        prom_content = prom_config.read_text(encoding="utf-8")
        if "rule_files" not in prom_content:
            gate.fail("Prometheus config missing rule_files directive")
    else:
        gate.fail("prometheus.yml not found")

    return gate


def gate_audit_trail(root: Path) -> GateResult:
    """Gate 8: Verify audit trail accessibility."""
    gate = GateResult("Audit Trail Accessibility")

    # Check that ProofCarryingResponse exists
    proof_files = list(root.rglob("proof_carrying*"))
    if not proof_files:
        gate.fail("ProofCarryingResponse model not found")

    # Check that ledger is available
    ledger_files = list((root / "mahoun/ledger").rglob("*.py")) if (root / "mahoun/ledger").exists() else []
    if not ledger_files:
        gate.fail("Immutable ledger module not found")

    # Check that audit endpoint exists in reasoning router
    router_file = root / "api/routers/reasoning.py"
    if router_file.exists():
        content = router_file.read_text(encoding="utf-8")
        if "query-ledger" not in content and "audit" not in content.lower():
            gate.fail("Audit trail endpoint not found in reasoning router")

    return gate


def gate_redlines_integrity(root: Path) -> GateResult:
    """Gate 9: Verify RedLines.yaml constitution is present and non-empty."""
    gate = GateResult("RedLines Constitution Integrity")

    redlines_file = root / "constitution/RedLines.yaml"
    if not redlines_file.exists():
        gate.fail("constitution/RedLines.yaml not found")
        return gate

    content = redlines_file.read_text(encoding="utf-8")
    if len(content.strip()) < 100:
        gate.fail("RedLines.yaml appears too small to be a valid constitution")

    return gate


# ============================================================================
# MAIN EXECUTION
# ============================================================================


def main():
    """Run all governance CI gates."""
    print("=" * 60)
    print("🛡️  MAHOUN Fortress & Governance CI Gate")
    print("=" * 60)
    print()

    root = Path.cwd()

    # Run all gates
    gates = [
        gate_critical_files_exist(root),
        gate_fortress_integration(root),
        gate_governance_lock(root),
        gate_governance_context(root),
        gate_provenance_tracking(root),
        gate_bypass_prevention(root),
        gate_monitoring_alerts(root),
        gate_audit_trail(root),
        gate_redlines_integrity(root),
    ]

    # Print results
    total_violations = 0
    failed_gates = 0

    for gate in gates:
        print(gate)
        if not gate.passed:
            failed_gates += 1
            total_violations += len(gate.violations)

    print()
    print("=" * 60)
    print(f"Results: {len(gates) - failed_gates}/{len(gates)} gates passed")
    print(f"Total violations: {total_violations}")
    print("=" * 60)

    if failed_gates > 0:
        print()
        print("🚨 GOVERNANCE CI GATE FAILED", file=sys.stderr)
        print(f"   {failed_gates} gate(s) failed with {total_violations} total violation(s)", file=sys.stderr)
        print("   Fix all violations before merging.", file=sys.stderr)
        sys.exit(1)
    else:
        print()
        print("✅ ALL GOVERNANCE CI GATES PASSED")
        print("   Fortress, Governance Lock, Context, Provenance, and Monitoring verified.")
        sys.exit(0)


if __name__ == "__main__":
    main()
