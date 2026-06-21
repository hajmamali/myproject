"""
Repository Hygiene Test - Prevent Root-Level Test Files
========================================================
This test enforces that all pytest test files live under tests/ directory,
preventing "test file sprawl" in the repository root.
"""

import subprocess
from pathlib import Path


def test_no_root_level_test_files():
    """Enforce: no test_*.py files in repository root."""
    repo_root = Path(__file__).resolve().parent.parent
    
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=5,
    )
    
    if result.returncode != 0:
        return
    
    tracked_files = result.stdout.strip().split('\n')
    
    root_test_files = [
        f for f in tracked_files
        if '/' not in f and (f.startswith('test_') or f.endswith('_test.py'))
    ]
    
    assert len(root_test_files) == 0, (
        f"❌ REPO HYGIENE VIOLATION: Found {len(root_test_files)} test file(s) in repository root.\n"
        f"All test files MUST be under tests/ directory.\n"
        f"Found:\n" + "\n".join(f"  - {f}" for f in root_test_files) + "\n\n"
        f"To fix: git mv {root_test_files[0]} tests/{root_test_files[0]}"
    )


def test_no_root_level_pytest_artifacts():
    """Ensure .pytest_cache and similar artifacts are gitignored."""
    repo_root = Path(__file__).resolve().parent.parent
    
    result = subprocess.run(
        ["git", "ls-files", ".pytest_cache", "pytest.ini"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        timeout=5,
    )
    
    if result.returncode != 0:
        return
    
    tracked_artifacts = [f for f in result.stdout.strip().split('\n') if f]
    
    assert len(tracked_artifacts) == 0, (
        f"❌ REPO HYGIENE VIOLATION: Found pytest artifacts tracked by git.\n"
        f"These should be in .gitignore:\n" + "\n".join(f"  - {a}" for a in tracked_artifacts)
    )
