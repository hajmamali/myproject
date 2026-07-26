import os
import ast
from pathlib import Path
import pytest

@pytest.mark.p2
def test_no_duplicate_governance_classes():
    """
    CI-enforced regression test.
    Ensures no class named GovernanceContext or MutationAuthorizationBoundary
    is defined anywhere outside of the canonical mahoun/core/governance/ package.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    mahoun_dir = project_root / "mahoun"
    
    canonical_package = mahoun_dir / "core" / "governance"
    
    forbidden_classes = {"GovernanceContext", "MutationAuthorizationBoundary"}
    violations = []
    
    for root, _, files in os.walk(mahoun_dir):
        root_path = Path(root)
        
        # Skip the canonical package where these are legitimately defined
        if canonical_package in root_path.parents or root_path == canonical_package:
            continue
            
        # Skip tests directory inside mahoun (if any) to avoid false positives on mock classes
        # though ideally tests shouldn't redefine these either
        if "tests" in root_path.parts:
            continue

        for file in files:
            if file.endswith(".py"):
                file_path = root_path / file
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        tree = ast.parse(f.read(), filename=str(file_path))
                        
                    for node in ast.walk(tree):
                        if isinstance(node, ast.ClassDef):
                            if node.name in forbidden_classes:
                                violations.append(f"{node.name} defined in {file_path.relative_to(project_root)}")
                except SyntaxError:
                    pass # Ignore syntax errors in other files
                except Exception as e:
                    pass

    assert not violations, (
        f"ARCHITECTURAL VIOLATION: Duplicate governance classes found outside canonical package:\n"
        + "\n".join(violations)
        + "\n\nDo NOT define your own GovernanceContext or MutationAuthorizationBoundary."
    )
