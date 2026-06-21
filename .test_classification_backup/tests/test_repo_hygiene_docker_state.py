import re
import pytest
from pathlib import Path


def test_docker_compose_has_no_legacy_platform33_references():
    """
    Gate: docker-compose.yml must not reference legacy 'platform33_' volumes.
    
    Ensures we don't regress to old volume naming that breaks compose hygiene.
    """
    compose_file = Path(__file__).parent.parent / "docker-compose.yml"
    
    if not compose_file.exists():
        pytest.skip("docker-compose.yml not found")
    
    content = compose_file.read_text()
    
    assert "platform33" not in content.lower(), \
        "docker-compose.yml contains legacy 'platform33' references. " \
        "All volumes should use 'mahoun_' prefix."


def test_no_tracked_files_mention_platform33_outside_docs():
    """
    Gate: Prevent legacy 'platform33' references in code.
    
    Allows references in:
    - docs (for migration guides)
    - tests (for validation)
    - cleanup scripts (for detection)
    """
    repo_root = Path(__file__).parent.parent
    
    code_patterns = ["**/*.py", "**/*.yml", "**/*.yaml"]
    exclude_patterns = [
        "docs/**",
        "**/reports/**",
        "**/.git/**",
        "**/venv/**",
        "**/test_*.py",
        "**/tests/**",
        "scripts/docker/clean_legacy_state.sh"
    ]
    
    violations = []
    
    for pattern in code_patterns:
        for file_path in repo_root.glob(pattern):
            if any(file_path.match(excl) for excl in exclude_patterns):
                continue
            
            if not file_path.is_file():
                continue
            
            try:
                content = file_path.read_text()
                if "platform33" in content.lower():
                    matches = [
                        (i + 1, line.strip())
                        for i, line in enumerate(content.split('\n'))
                        if "platform33" in line.lower()
                    ]
                    violations.append((file_path, matches))
            except (UnicodeDecodeError, PermissionError):
                pass
    
    if violations:
        msg = "Found legacy 'platform33' references in code:\n"
        for file_path, matches in violations:
            msg += f"\n{file_path}:\n"
            for line_num, line in matches[:3]:
                msg += f"  Line {line_num}: {line[:80]}\n"
        
        pytest.fail(msg)


def test_clean_legacy_state_script_exists():
    """
    Gate: Ensure cleanup script exists and is executable.
    """
    script_path = Path(__file__).parent.parent / "scripts" / "docker" / "clean_legacy_state.sh"
    
    assert script_path.exists(), \
        "scripts/docker/clean_legacy_state.sh not found"
    
    assert script_path.stat().st_mode & 0o111, \
        "clean_legacy_state.sh is not executable"
    
    content = script_path.read_text()
    
    assert "platform33" in content.lower(), \
        "Script should check for platform33 legacy volumes"
    
    assert "--force" in content, \
        "Script should support --force flag"
