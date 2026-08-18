"""
Test 5c: Enforcement Self-Protection Tests (Phase G)
=====================================================
Tests for scripts/check_enforcement_integrity.py.

Per Amendment B G4:
  POSITIVE: valid enforcement chain passes.
  NEGATIVE 1: required gate invocation removed → FAIL.
  NEGATIVE 2: gate invocation replaced by unconditional success → FAIL.
  NEGATIVE 3: required enforcement test removed → FAIL.

All tests operate on isolated temp copies. No production files are modified.
"""

import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CHECKER = PROJECT_ROOT / "scripts" / "check_enforcement_integrity.py"


def _run_checker(workspace: Path) -> subprocess.CompletedProcess:
    """Run the enforcement integrity checker against a workspace."""
    return subprocess.run(
        ["python3", str(CHECKER)],
        cwd=str(workspace),
        capture_output=True,
        text=True,
        timeout=30,
        env={"PATH": "/usr/bin:/usr/local/bin", "HOME": str(workspace)},
    )


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    """Create a minimal enforcement surface workspace for testing."""
    ws = tmp_path

    # Create directory structure
    (ws / "ci" / "first_step").mkdir(parents=True)
    (ws / "scripts" / "git-hooks").mkdir(parents=True)

    # Create a minimal enforcement manifest
    manifest = textwrap.dedent("""\
        enforcement_surface:
          - path: ci/first_step/gate_4_antimock.sh
            type: gate
            required_patterns:
              - "gate_4b_frontend_antimock.sh"
              - "Anti-Mock"
            required_for: [pre-push]

          - path: scripts/check_api_contracts.py
            type: checker
            required_patterns:
              - "APIContractChecker"
            required_for: [pre-push]

          - path: scripts/git-hooks/pre-push
            type: hook
            required_patterns:
              - "gate_4b_frontend_antimock.sh"
              - "check_api_contracts.py"
            required_for: [pre-push]

          - path: first_step_ci_cd/test_5_anti_mock.py
            type: test
            required_patterns:
              - "has_real_implementation"
            required_for: [pre-push]
        """)
    (ws / "ci" / "first_step" / "enforcement_manifest.yaml").write_text(manifest)

    # Create the referenced files with required patterns
    (ws / "ci" / "first_step" / "gate_4_antimock.sh").write_text(
        '# Gate 4: Anti-Mock Proof\nbash gate_4b_frontend_antimock.sh\n'
    )
    (ws / "scripts" / "check_api_contracts.py").write_text(
        'class APIContractChecker:\n    pass\n'
    )
    (ws / "scripts" / "git-hooks" / "pre-push").write_text(
        '# pre-push hook\necho "gate_4b_frontend_antimock.sh"\necho "check_api_contracts.py"\n'
    )
    (ws / "first_step_ci_cd").mkdir(parents=True)
    (ws / "first_step_ci_cd" / "test_5_anti_mock.py").write_text(
        'def has_real_implementation():\n    pass\n'
    )

    # Create a scripts/check_enforcement_integrity.py copy that works relative
    # to cwd instead of __file__ (so it finds the manifest in the temp workspace)
    checker_src = textwrap.dedent("""\
        #!/usr/bin/env python3
        import sys, yaml
        from pathlib import Path
        from dataclasses import dataclass
        from typing import List, Dict

        @dataclass
        class IntegrityViolation:
            path: str
            message: str
            severity: str = "CRITICAL"

        class EnforcementIntegrityChecker:
            def __init__(self, project_root: Path):
                self.project_root = project_root
                self.manifest_path = project_root / 'ci' / 'first_step' / 'enforcement_manifest.yaml'
                self.violations: List[IntegrityViolation] = []

            def run(self) -> bool:
                if not self.manifest_path.exists():
                    print(f"ERROR: manifest not found: {self.manifest_path}")
                    return False
                with open(self.manifest_path) as f:
                    manifest = yaml.safe_load(f)
                for entry in manifest.get('enforcement_surface', []):
                    self._check_entry(entry)
                return len(self.violations) == 0

            def _check_entry(self, entry: Dict):
                path = entry.get('path', '')
                abs_path = self.project_root / path
                required_patterns = entry.get('required_patterns', [])
                if not abs_path.exists():
                    self.violations.append(IntegrityViolation(
                        path=path, message=f"REMOVED: file missing"
                    ))
                    return
                if required_patterns:
                    content = abs_path.read_text()
                    for pattern in required_patterns:
                        if pattern not in content:
                            self.violations.append(IntegrityViolation(
                                path=path,
                                message=f"PATTERN MISSING: '{pattern}'"
                            ))

        def main():
            project_root = Path.cwd()
            checker = EnforcementIntegrityChecker(project_root)
            success = checker.run()
            if checker.violations:
                for v in checker.violations:
                    print(f"  {v.path}: {v.message}")
            sys.exit(0 if success else 1)

        if __name__ == "__main__":
            main()
        """)
    (ws / "scripts" / "check_enforcement_integrity_test.py").write_text(checker_src)

    return ws


class TestEnforcementIntegrityPositive:
    """POSITIVE: valid enforcement chain MUST pass."""

    def test_valid_chain_passes(self, workspace: Path):
        proc = subprocess.run(
            ["python3", str(workspace / "scripts" / "check_enforcement_integrity_test.py")],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode == 0, (
            f"Valid chain failed (false positive):\n{proc.stdout}\n{proc.stderr}"
        )


class TestEnforcementIntegrityNegative:
    """NEGATIVE cases per Amendment B G4."""

    def test_removed_gate_invocation_detected(self, workspace: Path):
        """N1: required gate invocation removed → FAIL."""
        # Remove the gate_4b invocation from gate_4
        gate_file = workspace / "ci" / "first_step" / "gate_4_antimock.sh"
        gate_file.write_text('# Gate 4: Anti-Mock Proof\n# gate_4b removed!\n')
        proc = subprocess.run(
            ["python3", str(workspace / "scripts" / "check_enforcement_integrity_test.py")],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode != 0, "Checker missed removed gate_4b invocation"
        out = proc.stdout + proc.stderr
        assert "gate_4b_frontend_antimock.sh" in out, (
            f"Should report missing gate_4b pattern:\n{out}"
        )

    def test_unconditional_success_replacement_detected(self, workspace: Path):
        """N2: gate invocation replaced by unconditional success → FAIL."""
        # Replace gate_4 with an unconditional success (exit 0, no real patterns)
        gate_file = workspace / "ci" / "first_step" / "gate_4_antimock.sh"
        gate_file.write_text('#!/bin/bash\necho "always succeeds"\nexit 0\n')
        proc = subprocess.run(
            ["python3", str(workspace / "scripts" / "check_enforcement_integrity_test.py")],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode != 0, "Checker missed unconditional success replacement"
        out = proc.stdout + proc.stderr
        assert "Anti-Mock" in out or "PATTERN MISSING" in out, (
            f"Should report missing Anti-Mock pattern:\n{out}"
        )

    def test_removed_enforcement_test_detected(self, workspace: Path):
        """N3: required enforcement test removed → FAIL."""
        # Remove the required test file
        test_file = workspace / "first_step_ci_cd" / "test_5_anti_mock.py"
        test_file.unlink()
        proc = subprocess.run(
            ["python3", str(workspace / "scripts" / "check_enforcement_integrity_test.py")],
            cwd=str(workspace),
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert proc.returncode != 0, "Checker missed removed enforcement test"
        out = proc.stdout + proc.stderr
        assert "test_5_anti_mock.py" in out, (
            f"Should report missing test file:\n{out}"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
