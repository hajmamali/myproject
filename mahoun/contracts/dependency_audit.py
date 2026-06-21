"""
MAHOUN Dependency & Integrity Auditor
=====================================
Ensures all critical dependencies and environmental requirements are met.
"""

import sys
import argparse
import pkg_resources
from typing import List

CRITICAL_DEPENDENCIES = [
    "torch",
    "neo4j",
    "pydantic",
    "hypothesis",
    "pytest",
    "yaml"
]

def audit_dependencies() -> List[str]:
    missing = []
    for dep in CRITICAL_DEPENDENCIES:
        try:
            pkg_resources.get_distribution(dep)
        except pkg_resources.DistributionNotFound:
            missing.append(dep)
        except Exception:
            # Fallback for complex names
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)
    return missing

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MAHOUN Dependency Auditor")
    parser.add_argument("--fail-on-missing", action="store_true")
    args = parser.parse_args()
    
    print("Auditing system dependencies...")
    missing = audit_dependencies()
    
    if missing:
        print(f"CRITICAL ERROR: Missing dependencies: {', '.join(missing)}")
        if args.fail_on_missing:
            sys.exit(1)
    else:
        print("Dependency audit: OK")
        sys.exit(0)
