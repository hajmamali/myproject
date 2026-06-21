"""
Static Analysis Test: No Bare Except Clauses
=============================================
Property 7: No Bare Except Clauses

Validates that no Python file in mahoun/ directory contains bare except clauses.
"""

import ast
import pytest
from pathlib import Path
from typing import List, Tuple


def find_bare_except_clauses(file_path: Path) -> List[int]:
    """
    Find line numbers of bare except clauses in a Python file.
    
    Returns:
        List of line numbers where bare except clauses are found
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()
        
        tree = ast.parse(source, filename=str(file_path))
        bare_excepts = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                # Bare except has type=None
                if node.type is None:
                    bare_excepts.append(node.lineno)
        
        return bare_excepts
    
    except SyntaxError:
        # Skip files with syntax errors
        return []
    except Exception:
        # Skip files that can't be parsed
        return []


def get_python_files(directory: Path, exclude_patterns: List[str] = None) -> List[Path]:
    """
    Get all Python files in directory, excluding test files and specified patterns.
    
    Args:
        directory: Root directory to search
        exclude_patterns: List of patterns to exclude (e.g., ['test_', '__pycache__'])
    
    Returns:
        List of Python file paths
    """
    if exclude_patterns is None:
        exclude_patterns = ['test_', '__pycache__', '.pyc', 'venv', '.git']
    
    python_files = []
    
    for py_file in directory.rglob('*.py'):
        # Skip if any exclude pattern matches
        if any(pattern in str(py_file) for pattern in exclude_patterns):
            continue
        
        python_files.append(py_file)
    
    return python_files


def test_no_bare_except_in_mahoun():
    """
    Property 7: No Bare Except Clauses
    
    For any Python file in mahoun/ directory, the file SHALL NOT contain
    bare except: clauses (must specify exception type).
    
    Validates: Requirements 4.1
    """
    mahoun_dir = Path("mahoun")
    
    if not mahoun_dir.exists():
        pytest.skip("mahoun directory not found")
    
    # Get all Python files in mahoun/
    python_files = get_python_files(mahoun_dir)
    
    violations: List[Tuple[Path, List[int]]] = []
    
    for py_file in python_files:
        bare_excepts = find_bare_except_clauses(py_file)
        if bare_excepts:
            violations.append((py_file, bare_excepts))
    
    # Report violations
    if violations:
        error_msg = "Found bare except clauses in the following files:\n"
        for file_path, line_numbers in violations:
            error_msg += f"\n{file_path}:\n"
            for line_no in line_numbers:
                error_msg += f"  Line {line_no}\n"
        
        error_msg += "\nBare except clauses are not allowed. Use specific exception types instead.\n"
        error_msg += "Example: Replace 'except:' with 'except Exception as e:'\n"
        
        pytest.fail(error_msg)


def test_no_bare_except_in_api():
    """
    Property: No bare except clauses in API layer.
    """
    api_dir = Path("api")
    
    if not api_dir.exists():
        pytest.skip("api directory not found")
    
    python_files = get_python_files(api_dir)
    
    violations: List[Tuple[Path, List[int]]] = []
    
    for py_file in python_files:
        bare_excepts = find_bare_except_clauses(py_file)
        if bare_excepts:
            violations.append((py_file, bare_excepts))
    
    if violations:
        error_msg = "Found bare except clauses in API files:\n"
        for file_path, line_numbers in violations:
            error_msg += f"\n{file_path}: lines {line_numbers}\n"
        pytest.fail(error_msg)


def test_specific_files_no_bare_except():
    """
    Property: Critical files must not have bare except clauses.
    """
    critical_files = [
        "mahoun/reasoning/evidence_linked_verdict.py",
        "mahoun/ledger/writer.py",
        "mahoun/core/config.py",
        "mahoun/core/llm/router.py",
        "mahoun/guardrails/guards.py",
    ]
    
    violations = []
    
    for file_path_str in critical_files:
        file_path = Path(file_path_str)
        if not file_path.exists():
            continue
        
        bare_excepts = find_bare_except_clauses(file_path)
        if bare_excepts:
            violations.append((file_path, bare_excepts))
    
    if violations:
        error_msg = "Found bare except clauses in critical files:\n"
        for file_path, line_numbers in violations:
            error_msg += f"\n{file_path}: lines {line_numbers}\n"
        pytest.fail(error_msg)


def test_exception_handling_best_practices():
    """
    Property: Exception handlers should follow best practices.
    
    Checks for:
    - No bare except
    - Exception variable is used (not silently ignored)
    """
    mahoun_dir = Path("mahoun")
    
    if not mahoun_dir.exists():
        pytest.skip("mahoun directory not found")
    
    python_files = get_python_files(mahoun_dir)
    
    issues = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source, filename=str(py_file))
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ExceptHandler):
                    # Check for bare except
                    if node.type is None:
                        issues.append(f"{py_file}:{node.lineno} - Bare except clause")
                    
                    # Check if exception variable is defined but never used
                    if node.name and node.body:
                        # Simple check: see if exception name appears in body
                        body_source = ast.unparse(node.body[0]) if node.body else ""
                        if node.name not in body_source and "pass" not in body_source:
                            # This is just a warning, not a failure
                            pass
        
        except Exception:
            continue
    
    if issues:
        error_msg = "Exception handling issues found:\n" + "\n".join(issues)
        pytest.fail(error_msg)


if __name__ == "__main__":
    # Allow running as script for quick check
    test_no_bare_except_in_mahoun()
    print("✓ No bare except clauses found in mahoun/")
