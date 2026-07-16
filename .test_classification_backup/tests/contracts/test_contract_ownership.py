import subprocess
import sys
from pathlib import Path


@pytest.mark.p2
def test_contract_ownership_registry():
    repo_root = Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(repo_root / "scripts" / "validate_contract_ownership.py")],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (result.stderr + "\n" + result.stdout).strip()

