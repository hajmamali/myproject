#!/usr/bin/env python3
"""
MAHOUN Schema Drift Detector with Semantic Classification
========================================================

Classification: CRITICAL / CI-GATING
Purpose: Detect schema drift by comparing schema hashes against a baseline
        with semantic classification of changes.

This script is run in CI to ensure that schema changes are intentional
and tracked. Any untracked schema change fails the pipeline.

Semantic Classification Categories:
- Formatting: Whitespace, indentation changes
- Comments: Comment-only changes
- Docstrings: Documentation string changes  
- Typing: Type annotation changes
- Structural: Schema structure modification
- Validation: Validation rule changes
- Contract: Contract term changes
- Behavioral: Logic/behavior changes

Usage:
    python ci/scripts/schema_drift_detector.py [--update-baseline]
    python ci/scripts/schema_drift_detector.py --classify
    python ci/scripts/schema_drift_detector.py --verify-semantic

Author: MAHOUN Platform Governance Council
Version: 2.0.0
"""

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Add root to path for imports
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

# Import semantic classifier
try:
    from mahoun.governance.semantic_drift_classifier import (
        SchemaDriftCategory,
        SemanticDriftClassification,
        SemanticDriftReport,
        DriftSeverity,
        get_schema_classifier,
    )
    SEMANTIC_CLASSIFIER_AVAILABLE = True
except ImportError:
    SEMANTIC_CLASSIFIER_AVAILABLE = False


SCHEMA_PATHS = [
    "mahoun/schemas/legal_struct_schema.py",
    "mahoun/schemas/text_schema.py",
    "mahoun/schemas/contracts/core_contracts.py",
    "mahoun/schemas/contracts/graph_contracts.py",
    "mahoun/schemas/contracts/invariants_contracts.py",
    "mahoun/schemas/contracts/ledger_contracts.py",
    "mahoun/schemas/contracts/reasoning_contracts.py",
    "mahoun/schemas/contracts/schemas_contracts.py",
    "mahoun/core/governance/violations.py",
    "mahoun/core/governance/policies.py",
    "mahoun/core/governance/ontology_enforcer.py",
    "mahoun/core/protocols.py",
    "constitution/RedLines.yaml",
    "core_manifest.yaml",
]

BASELINE_PATH = Path("ci/schema_baseline.json")


def compute_file_hash(file_path: Path) -> str:
    """Compute SHA-256 hash of a file."""
    if not file_path.exists():
        return "MISSING"
    content = file_path.read_bytes()
    return hashlib.sha256(content).hexdigest()


def compute_current_hashes(root: Path) -> Dict[str, str]:
    """Compute hashes for all tracked schema files."""
    hashes: Dict[str, str] = {}
    for rel_path in sorted(SCHEMA_PATHS):
        full_path = root / rel_path
        hashes[rel_path] = compute_file_hash(full_path)
    return hashes


def load_baseline(baseline_path: Path) -> Dict[str, str]:
    """Load baseline hashes from file."""
    if not baseline_path.exists():
        return {}
    with open(baseline_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_baseline(baseline_path: Path, hashes: Dict[str, str]) -> None:
    """Save current hashes as new baseline."""
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    with open(baseline_path, "w", encoding="utf-8") as f:
        json.dump(hashes, f, indent=2, sort_keys=True)


# =============================================================================
# SEMANTIC CLASSIFICATION FUNCTIONS
# =============================================================================

def classify_schema_file(path: str, content: str = "") -> "SemanticDriftClassification":
    """
    Classify a schema file based on its path and content patterns.
    Used when old content is not available for full comparison.
    """
    # YAML files in constitution directory
    if path.endswith('.yaml') or path.endswith('.yml'):
        if any(kw in path for kw in ['constitution', 'RedLines', 'manifest', 'kernel']):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.CONTRACT,
                severity=DriftSeverity.HIGH,
                old_path=path,
                confidence=0.95,
                evidence=[f"Governance contract/configuration: {path}"],
                details={"file_type": "governance_yaml"}
            )
        return SemanticDriftClassification(
            category=SchemaDriftCategory.CONTRACT,
            severity=DriftSeverity.HIGH,
            old_path=path,
            confidence=0.9,
            evidence=[f"YAML schema/config: {path}"],
            details={"file_type": "yaml"}
        )
    
    # Python schema files
    if 'contract' in path.lower():
        return SemanticDriftClassification(
            category=SchemaDriftCategory.CONTRACT,
            severity=DriftSeverity.HIGH,
            old_path=path,
            confidence=0.95,
            evidence=[f"Contract schema: {path}"],
            details={"file_type": "contract_schema"}
        )
    
    if 'governance' in path.lower():
        if any(kw in path.lower() for kw in ['policy', 'violation', 'enforcer']):
            return SemanticDriftClassification(
                category=SchemaDriftCategory.VALIDATION,
                severity=DriftSeverity.HIGH,
                old_path=path,
                confidence=0.9,
                evidence=[f"Governance validation: {path}"],
                details={"file_type": "governance_validation"}
            )
        return SemanticDriftClassification(
            category=SchemaDriftCategory.CONTRACT,
            severity=DriftSeverity.HIGH,
            old_path=path,
            confidence=0.95,
            evidence=[f"Governance core: {path}"],
            details={"file_type": "governance_core"}
        )
    
    # Check content for validation patterns
    if content and any(kw in content.lower() for kw in ['validate', 'validation']):
        return SemanticDriftClassification(
            category=SchemaDriftCategory.VALIDATION,
            severity=DriftSeverity.HIGH,
            old_path=path,
            confidence=0.85,
            evidence=[f"Validation logic: {path}"],
            details={"file_type": "validation"}
        )
    
    # Default for Python files
    return SemanticDriftClassification(
        category=SchemaDriftCategory.STRUCTURAL,
        severity=DriftSeverity.MEDIUM,
        old_path=path,
        confidence=0.8,
        evidence=[f"Schema file: {path}"],
        details={"file_type": "schema"}
    )


def get_file_from_git(root: Path, path: str) -> Optional[str]:
    """Try to get file content from git history."""
    try:
        result = subprocess.run(
            ['git', 'show', f'HEAD:{path}'],
            cwd=root,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return result.stdout
    except Exception:
        pass
    return None


def classify_with_git_history(
    root: Path,
    baseline: Dict[str, str],
    current: Dict[str, str],
    verbose: bool = True
) -> "SemanticDriftReport":
    """
    Classify schema drift with git history for proper semantic analysis.
    Uses the semantic classifier to compare old and new content.
    """
    if not SEMANTIC_CLASSIFIER_AVAILABLE:
        print("SCHEMA_DRIFT_WARNING: Semantic classifier not available.")
        return SemanticDriftReport()
    
    report = SemanticDriftReport()
    classifier = get_schema_classifier()
    
    # Identify drifted files (hash changed)
    drifted = []
    for path, current_hash in current.items():
        baseline_hash = baseline.get(path)
        if baseline_hash is not None and current_hash != baseline_hash:
            drifted.append(path)
    
    if verbose:
        print(f"Analyzing {len(drifted)} drifted files with git history...")
    
    for path in drifted:
        try:
            full_path = root / path
            if not full_path.exists():
                if verbose:
                    print(f"  ⚠ Skipping missing file: {path}")
                continue
            
            current_content = full_path.read_text(encoding="utf-8")
            old_content = get_file_from_git(root, path)
            
            if old_content and old_content != current_content:
                classification = classifier.classify_schema_change(
                    path, old_content, current_content
                )
                report.add_classification(classification)
                if verbose:
                    print(f"  ✓ {path}: {classification.category.value} "
                          f"({classification.confidence:.1%})")
            else:
                classification = classify_schema_file(path, current_content)
                report.add_classification(classification)
                if verbose:
                    print(f"  ⚠ {path}: {classification.category.value} "
                          f"(fallback, confidence: {classification.confidence:.1%})")
                
        except Exception as e:
            if verbose:
                print(f"  ❌ {path}: Classification error - {e}")
            classification = SemanticDriftClassification(
                category=SchemaDriftCategory.BEHAVIORAL,
                severity=DriftSeverity.CRITICAL,
                old_path=path,
                confidence=0.5,
                evidence=[f"Classification failed: {str(e)}"],
                details={"error": str(e), "fallback": True}
            )
            report.add_classification(classification)
            continue
    
    return report


def print_semantic_report(report: "SemanticDriftReport") -> None:
    """Print a semantic drift report."""
    print("\n" + "=" * 70)
    print("SEMANTIC SCHEMA DRIFT REPORT")
    print("=" * 70)
    
    if not report.classifications:
        print("✅ No schema drift detected.")
        print("=" * 70)
        return
    
    print(f"\nTotal Classifications: {len(report.classifications)}")
    print("-" * 70)
    
    # Group by category
    by_category: Dict[str, List["SemanticDriftClassification"]] = {}
    for classification in report.classifications:
        cat = classification.category.value
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(classification)
    
    for category, drifts in sorted(by_category.items()):
        print(f"\n{category}:")
        for drift in drifts:
            severity = drift.severity.value
            print(f"  [{severity}] {drift.old_path}")
            print(f"           Confidence: {drift.confidence:.1%}")
            if drift.evidence:
                print(f"           {drift.evidence[0]}")
    
    # Summary by severity
    print("\n" + "-" * 70)
    print("Summary by Severity:")
    by_severity: Dict[str, int] = {}
    for classification in report.classifications:
        sev = classification.severity.value
        by_severity[sev] = by_severity.get(sev, 0) + 1
    
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    for severity in severity_order:
        if severity in by_severity:
            print(f"  {severity}: {by_severity[severity]}")
    
    print("=" * 70)


# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description="MAHOUN Schema Drift Detector with Semantic Classification",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python ci/scripts/schema_drift_detector.py              # Basic hash check
  python ci/scripts/schema_drift_detector.py --update-baseline  # Update baseline
  python ci/scripts/schema_drift_detector.py --classify        # Semantic classification
  python ci/scripts/schema_drift_detector.py --verify-semantic # Full semantic check
        """
    )
    
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update baseline with current hashes"
    )
    parser.add_argument(
        "--classify",
        action="store_true",
        help="Classify drift semantically without failing"
    )
    parser.add_argument(
        "--verify-semantic",
        action="store_true",
        help="Verify with semantic classification, fail on drift"
    )
    
    args = parser.parse_args()
    
    update_mode = args.update_baseline
    classify_mode = args.classify
    verify_semantic_mode = args.verify_semantic
    
    # Backward compatibility: check for old-style arguments
    if not any([update_mode, classify_mode, verify_semantic_mode]):
        update_mode = "--update-baseline" in sys.argv
        classify_mode = "--classify" in sys.argv
        verify_semantic_mode = "--verify-semantic" in sys.argv
    
    print("🔍 MAHOUN Schema Drift Detector starting...")
    root = Path.cwd()
    current = compute_current_hashes(root)
    baseline = load_baseline(root / BASELINE_PATH)

    if update_mode:
        save_baseline(root / BASELINE_PATH, current)
        print(f"✅ Baseline updated: {root / BASELINE_PATH}")
        print(f"   Tracked files: {len(current)}")
        sys.exit(0)

    if not baseline:
        print("⚠️  No baseline found. Run with --update-baseline first.")
        print("   Creating initial baseline...")
        save_baseline(root / BASELINE_PATH, current)
        print(f"✅ Initial baseline created: {root / BASELINE_PATH}")
        sys.exit(0)

    # Identify changes using hash comparison
    drifted = []
    new_files = []
    removed_files = []

    for path, current_hash in current.items():
        baseline_hash = baseline.get(path)
        if baseline_hash is None:
            new_files.append(path)
        elif current_hash != baseline_hash:
            drifted.append(path)

    for path in baseline:
        if path not in current:
            removed_files.append(path)

    total_issues = len(drifted) + len(new_files) + len(removed_files)

    # Handle semantic classification modes first
    if classify_mode or verify_semantic_mode:
        if SEMANTIC_CLASSIFIER_AVAILABLE and (drifted or new_files or removed_files):
            report = classify_with_git_history(root, baseline, current, verbose=True)
            print_semantic_report(report)
            
            if verify_semantic_mode and report.classifications:
                print("\n🚨 SCHEMA DRIFT DETECTED (Semantic Classification)")
                print("   Run: python ci/scripts/schema_drift_detector.py --update-baseline")
                sys.exit(1)
            elif verify_semantic_mode:
                print("\n✅ Schema integrity verified. No semantic drift detected.")
                sys.exit(0)
            # For --classify mode, don't exit, continue to show hash info
        else:
            if classify_mode or verify_semantic_mode:
                if not SEMANTIC_CLASSIFIER_AVAILABLE:
                    print("⚠️  Semantic classifier not available. Falling back to hash comparison.")
                elif not (drifted or new_files or removed_files):
                    print("✅ Schema integrity verified. No drift detected.")
                    sys.exit(0)
    
    # Original hash-based detection and reporting
    if drifted:
        print("❌ SCHEMA DRIFT DETECTED:")
        for path in drifted:
            print(f"   CHANGED: {path}")
            print(f"     baseline: {baseline[path][:16]}...")
            print(f"     current:  {current[path][:16]}...")

    if new_files:
        print("❌ NEW UNTRACKED SCHEMA FILES:")
        for path in new_files:
            print(f"   NEW: {path}")

    if removed_files:
        print("❌ REMOVED SCHEMA FILES:")
        for path in removed_files:
            print(f"   REMOVED: {path}")

    if total_issues > 0:
        print("-" * 50)
        print(
            f"🚨 SCHEMA DRIFT: {total_issues} issue(s) detected.",
            file=sys.stderr,
        )
        print(
            "   Run 'python ci/scripts/schema_drift_detector.py --update-baseline' "
            "to accept changes.",
            file=sys.stderr,
        )
        print(
            "   Use --classify for semantic drift classification.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"✅ Schema integrity verified. {len(current)} files unchanged.")
    sys.exit(0)


if __name__ == "__main__":
    main()
