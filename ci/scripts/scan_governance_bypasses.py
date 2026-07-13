#!/usr/bin/env python3
import os
import re
import sys
from pathlib import Path

def scan_for_bypasses():
    root_dir = Path(__file__).resolve().parent.parent.parent
    scan_dirs = [root_dir / "mahoun", root_dir / "api"]
    
    # Exclude test directories/files
    mutation_patterns = [
        re.compile(r"MERGE\s*\("),
        re.compile(r"CREATE\s*\("),
        re.compile(r"DETACH\s+DELETE"),
        re.compile(r"SET\s+\w+\.\w+\s*=")
    ]
    
    governance_import_patterns = [
        re.compile(r"import\s+mahoun\.core\.governance_kernel"),
        re.compile(r"from\s+mahoun\.core\.governance_kernel"),
        re.compile(r"import\s+mahoun\.core\.unified_governance"),
        re.compile(r"from\s+mahoun\.core\.unified_governance"),
        re.compile(r"mahoun\.core\.governance\."),
        re.compile(r"governed_session"),
        re.compile(r"enforce_governance")
    ]
    
    violations = []
    
    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
            
        for py_file in scan_dir.rglob("*.py"):
            if "test" in str(py_file).lower():
                continue
                
            try:
                content = py_file.read_text(encoding="utf-8")
            except Exception:
                continue
                
            has_mutation = any(p.search(content) for p in mutation_patterns)
            
            if has_mutation:
                has_governance = any(p.search(content) for p in governance_import_patterns)
                if not has_governance:
                    violations.append(py_file)
                    
    if violations:
        print("ERROR: Governance bypasses detected! The following files contain graph mutations but no governance imports:")
        for v in violations:
            print(f" - {v.relative_to(root_dir)}")
        sys.exit(1)
        
    print("SUCCESS: All files with graph mutations correctly import governance modules.")
    sys.exit(0)

if __name__ == "__main__":
    scan_for_bypasses()
