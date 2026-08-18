"""
Diagnostic: trace the complete approval path for proc2.
Does NOT modify production files. Operates on temp workspace.
"""

import hashlib
import os
import re
import shutil
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
GATE_SCRIPT = PROJECT_ROOT / "ci" / "first_step" / "gate_10_constitutional_integrity.sh"


def run_gate(ws, env_override=None):
    env = os.environ.copy()
    if env_override:
        env.update(env_override)
    return subprocess.run(
        ["bash", str(ws / "ci" / "first_step" / "gate_10_constitutional_integrity.sh")],
        cwd=str(ws),
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )


def setup_workspace(tmp_path):
    ws = tmp_path
    gate_dir = ws / "ci" / "first_step"
    gate_dir.mkdir(parents=True)
    shutil.copy(GATE_SCRIPT, gate_dir / "gate_10_constitutional_integrity.sh")
    os.chmod(gate_dir / "gate_10_constitutional_integrity.sh", 0o755)

    const_dir = ws / "mahoun" / "constitutional" / "constitution"
    const_dir.mkdir(parents=True)
    (const_dir / "CONSTITUTION.md").write_text("# Constitution\n\nVersion 1.\n")
    return ws


def test_diagnostic_trace_approved_change(tmp_path):
    """Trace every step of the approval path for proc2."""
    ws = setup_workspace(tmp_path)

    # 1. Bootstrap
    proc_boot = run_gate(ws)
    print(f"\n[B] bootstrap exit={proc_boot.returncode}")
    assert proc_boot.returncode == 0

    # 2. Modify constitutional file
    const_file = ws / "mahoun" / "constitutional" / "constitution" / "CONSTITUTION.md"
    const_file.write_text("# Constitution\n\nVersion 2 (approved).\n")

    # 3. Compute the current hash ourselves (independent of gate output)
    manifest_lines = []
    for mdfile in sorted((ws / "mahoun" / "constitutional").rglob("*.md")):
        rel = str(mdfile.relative_to(ws))
        h = hashlib.sha256(mdfile.read_bytes()).hexdigest()
        manifest_lines.append(f"{h}  {rel}")
    expected_manifest = "\n".join(manifest_lines) + "\n"
    expected_hash = hashlib.sha256(expected_manifest.encode()).hexdigest()
    print(f"\n[D1] expected current hash (our computation): {expected_hash}")

    # 4. Run gate without approval to get the gate's own hash for comparison
    proc1 = run_gate(ws)
    out1 = proc1.stdout + proc1.stderr
    hash_match_gate = re.search(r'Current combined hash:\s+([0-9a-f]{64})', out1)
    gate_hash = hash_match_gate.group(1) if hash_match_gate else "NOT_FOUND"
    print(f"[D2] gate's current hash (from proc1 output): {gate_hash}")
    print(f"[D3] our hash == gate's hash: {expected_hash == gate_hash}")

    stored_match = re.search(r'Stored hash:\s+([0-9a-f]{64})', out1)
    stored_hash = stored_match.group(1) if stored_match else "NOT_FOUND"
    print(f"[D4] stored manifest hash (from proc1): {stored_hash}")

    seal_match = re.search(r'Manifest seal:\s+([0-9a-f]{64})', out1)
    seal_hash = seal_match.group(1) if seal_match else "NOT_FOUND"
    print(f"[D5] manifest seal (from proc1): {seal_hash}")
    print(f"[D6] seal == stored: {seal_hash == stored_hash}")

    # 5. Now run gate WITH the env var approval
    approval_env = expected_hash  # use our independently computed hash
    print(f"\n[D7] CONSTITUTIONAL_CHANGE_APPROVED = {approval_env}")
    print(f"[D8] approval == current hash: {approval_env == gate_hash}")

    # Check: does the subprocess actually see the env var?
    env_check = subprocess.run(
        ["bash", "-c", 'echo "ENV_VAR_EXISTS=$CONSTITUTIONAL_CHANGE_APPROVED"'],
        cwd=str(ws),
        env={**os.environ, "CONSTITUTIONAL_CHANGE_APPROVED": approval_env},
        capture_output=True,
        text=True,
    )
    print(f"[D9] env var visible in subprocess: {env_check.stdout.strip()}")

    proc2 = run_gate(ws, env_override={
        "CONSTITUTIONAL_CHANGE_APPROVED": approval_env,
    })
    out2 = proc2.stdout + proc2.stderr
    print(f"\n[D10] proc2 exit code: {proc2.returncode}")
    print(f"[D11] proc2 full stdout:\n{proc2.stdout}")
    print(f"[D12] proc2 full stderr:\n{proc2.stderr}")

    # Check for approval-finding messages
    has_approval_msg = "Found approval" in out2 or "approval" in out2.lower()
    has_no_approval = "NO APPROVAL" in out2
    has_hash_mismatch = "APPROVAL HASH MISMATCH" in out2
    has_tampering = "TAMPERING" in out2
    has_approved = "approved" in out2.lower() or "accepted" in out2.lower()
    print(f"\n[D13] 'Found approval' in output: {has_approval_msg}")
    print(f"[D14] 'NO APPROVAL' in output: {has_no_approval}")
    print(f"[D15] 'APPROVAL HASH MISMATCH' in output: {has_hash_mismatch}")
    print(f"[D16] 'TAMPERING' in output: {has_tampering}")
    print(f"[D17] 'approved/accepted' in output: {has_approved}")

    # Now the critical question: does the script fail at the diff step?
    # Check if proc1 exited at the "Changed files" section
    last_lines = [l for l in out1.strip().split('\n') if l][-5:]
    print(f"\n[D18] proc1 last 5 lines: {last_lines}")

    proc1_exit_after_diff = proc1.returncode
    print(f"[D19] proc1 exit code: {proc1_exit_after_diff}")

    # The approval should succeed
    assert proc2.returncode == 0, (
        f"proc2 failed with exit {proc2.returncode}\n"
        f"stdout: {proc2.stdout}\nstderr: {proc2.stderr}"
    )