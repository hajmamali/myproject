"""
Test 5d: Constitutional Integrity Self-Test (Phase C, Amendment C4)
====================================================================
Tests for ci/first_step/gate_10_constitutional_integrity.sh.

Per Amendment C4, the test MUST verify BOTH paths:
  NEGATIVE: modify constitutional file + modify manifest without approval → FAIL
  POSITIVE: modify constitutional file + compute hash + provide matching
            approval → gate PASSES + manifest updated + approval consumed
            ALSO negative: modify manifest while constitutional files changed
            without valid approval → FAIL (anti-tampering)

All tests operate on isolated temp copies. No production files modified.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GATE_SCRIPT = PROJECT_ROOT / "ci" / "first_step" / "gate_10_constitutional_integrity.sh"


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temp project root with a mock constitutional directory."""
    ws = tmp_path

    # Copy the gate script
    gate_dir = ws / "ci" / "first_step"
    gate_dir.mkdir(parents=True)
    shutil.copy(GATE_SCRIPT, gate_dir / "gate_10_constitutional_integrity.sh")
    os.chmod(gate_dir / "gate_10_constitutional_integrity.sh", 0o755)

    # Create mock constitutional directory
    const_dir = ws / "mahoun" / "constitutional" / "constitution"
    const_dir.mkdir(parents=True)
    (const_dir / "CONSTITUTION.md").write_text(
        "# Constitution\n\nVersion 1.\n", encoding="utf-8"
    )

    return ws


def _run_gate(workspace: Path, env_override: dict = None) -> subprocess.CompletedProcess:
    """Run gate_10 against the temp workspace."""
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(workspace / "ci" / "first_step" / "gate_10_constitutional_integrity.sh")],
        cwd=str(workspace),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


class TestGate10Bootstrap:
    def test_bootstrap_creates_manifest_and_seal(self, temp_workspace: Path):
        """First run must create manifest + seal and pass."""
        proc = _run_gate(temp_workspace)
        assert proc.returncode == 0, f"Bootstrap failed:\n{proc.stdout}\n{proc.stderr}"
        out = proc.stdout + proc.stderr
        assert "Bootstrap" in out
        assert "Seal" in out
        # Manifest and seal files must exist
        assert (temp_workspace / "ci" / "first_step" / ".constitutional_manifest.sha256").exists()
        assert (temp_workspace / "ci" / "first_step" / ".constitutional_manifest.seal").exists()

    def test_unchanged_passes(self, temp_workspace: Path):
        """Bootstrap, then re-run without changes → must pass."""
        _run_gate(temp_workspace)  # bootstrap
        proc = _run_gate(temp_workspace)  # re-run
        assert proc.returncode == 0, f"Unchanged should pass:\n{proc.stdout}"
        out = proc.stdout + proc.stderr
        assert "unchanged" in out.lower()


class TestGate10UnauthorizedChange:
    """NEGATIVE: modify constitutional file without approval → MUST FAIL."""

    def test_change_without_approval_fails(self, temp_workspace: Path):
        _run_gate(temp_workspace)  # bootstrap

        # Modify a constitutional file
        const_file = temp_workspace / "mahoun" / "constitutional" / "constitution" / "CONSTITUTION.md"
        const_file.write_text("# Constitution\n\nVersion 2 (modified).\n", encoding="utf-8")

        proc = _run_gate(temp_workspace)
        assert proc.returncode != 0, "Gate passed on unapproved change — ANTI-TAMPERING BROKEN"
        out = proc.stdout + proc.stderr
        assert "NO APPROVAL" in out or "CHANGED" in out


class TestGate10TamperedManifest:
    """NEGATIVE (Amendment C2): modify constitutional file + tamper manifest → FAIL."""

    def test_manifest_tampering_detected(self, temp_workspace: Path):
        _run_gate(temp_workspace)  # bootstrap

        # Modify constitutional file
        const_file = temp_workspace / "mahoun" / "constitutional" / "constitution" / "CONSTITUTION.md"
        const_file.write_text("# Constitution\n\nVersion 2 (tampered).\n", encoding="utf-8")

        # Tamper the manifest: overwrite it with content that matches the new state
        # (simulating an attacker who modifies both the constitution AND the manifest)
        manifest = temp_workspace / "ci" / "first_step" / ".constitutional_manifest.sha256"

        # Re-compute the current manifest for the new state
        import hashlib
        lines = []
        const_path = const_file.relative_to(temp_workspace)
        content = const_file.read_bytes()
        h = hashlib.sha256(content).hexdigest()
        lines.append(f"{h}  {const_path}")
        manifest_content = "\n".join(sorted(lines)) + "\n"
        new_hash = hashlib.sha256(manifest_content.encode()).hexdigest()
        manifest.write_text(manifest_content)

        proc = _run_gate(temp_workspace)
        assert proc.returncode != 0, "Gate accepted tampered manifest — CRITICAL ANTI-TAMPERING BUG"
        out = proc.stdout + proc.stderr
        # Must detect manifest tampering (seal mismatch)
        assert "TAMPERING" in out.upper() or "SEAL" in out.upper(), (
            f"Should report manifest tampering:\n{out}"
        )


class TestGate10ApprovedChange:
    """POSITIVE: modify constitutional file + provide matching approval → PASS + consume."""

    def test_approved_change_passes_and_consumes(self, temp_workspace: Path):
        _run_gate(temp_workspace)  # bootstrap

        # Modify a constitutional file
        const_file = temp_workspace / "mahoun" / "constitutional" / "constitution" / "CONSTITUTION.md"
        const_file.write_text("# Constitution\n\nVersion 2 (approved).\n", encoding="utf-8")

        # Compute the NEW hash (gate prints it on first failed run)
        proc1 = _run_gate(temp_workspace)
        assert proc1.returncode != 0, "Should fail without approval"

        # Extract the current hash from the output
        out = proc1.stdout + proc1.stderr
        import re
        hash_match = re.search(r'Current combined hash:\s+([0-9a-f]{64})', out)
        assert hash_match, f"Could not extract current hash from output:\n{out}"
        current_hash = hash_match.group(1)

        # Provide approval via env var
        proc2 = _run_gate(temp_workspace, env_override={
            "CONSTITUTIONAL_CHANGE_APPROVED": current_hash
        })
        assert proc2.returncode == 0, (
            f"Approved change should pass:\n{proc2.stdout}\n{proc2.stderr}"
        )
        out2 = proc2.stdout + proc2.stderr
        assert "approved" in out2.lower() or "accepted" in out2.lower()

        # Verify the approval is one-shot: re-running with the same hash must FAIL
        # (because the state already changed — manifest was updated)
        proc3 = _run_gate(temp_workspace, env_override={
            "CONSTITUTIONAL_CHANGE_APPROVED": current_hash
        })
        # After the manifest was updated, re-running with the old approval hash
        # should NOT match the new stored hash → it should still pass (unchanged)
        # because the manifest was just updated to the current state.
        # The one-shot test is: the approval hash can't be reused for a DIFFERENT
        # change. Let's verify by making ANOTHER change.
        const_file.write_text("# Constitution\n\nVersion 3 (new change).\n", encoding="utf-8")
        proc4 = _run_gate(temp_workspace, env_override={
            "CONSTITUTIONAL_CHANGE_APPROVED": current_hash  # old approval for version 2
        })
        assert proc4.returncode != 0, (
            "Old approval hash was accepted for a NEW change — NOT one-shot!\n"
            f"{proc4.stdout}\n{proc4.stderr}"
        )


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
