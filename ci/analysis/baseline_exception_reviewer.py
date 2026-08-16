#!/usr/bin/env python3
"""
Baseline Exception Reviewer
===========================

Review baseline exceptions to identify truly obsolete modules vs legitimate standalone.

Analyzes:
- Example/demo modules (safe to remove)
- Experimental/prototype modules
- Superseded modules with newer versions
- Package-level exceptions (should be individual modules)
- Backup files and temporary code
- Legitimate standalone modules (should keep)

Usage:
    python ci/analysis/baseline_exception_reviewer.py --baseline ci/gates/module_wiring_baseline.json
    python ci/analysis/baseline_exception_reviewer.py --baseline ci/gates/module_wiring_baseline.json --output review.json
"""

import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import argparse
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ExceptionReview:
    """Review result for a baseline exception."""
    module: str
    current_reason: str
    recommended_action: str  # keep, remove, investigate
    review_reason: str
    confidence: float
    suggested_replacement: Optional[str] = None


class BaselineExceptionReviewer:
    """Review baseline exceptions for obsolescence."""
    
    def __init__(self, root_dir: str):
        """
        Initialize reviewer.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.reviews: List[ExceptionReview] = []
        
        # Patterns for identifying obsolete modules
        self.example_patterns = {
            'example', 'demo', 'sample', 'test_', 'tutorial', 'playground'
        }
        
        self.experimental_patterns = {
            'experimental', 'prototype', 'proto', 'temp', 'tmp', 'wip'
        }
        
        self.backup_patterns = {
            '.bak', '.backup', '.old', '.legacy', '_old', '_backup', '_legacy'
        }
        
    def check_file_exists(self, module_name: str) -> bool:
        """Check if module file still exists."""
        # Try different path variations
        possible_paths = [
            module_name,  # as-is
            f"mahoun.{module_name}",  # with mahoun prefix
            module_name.replace('.', '/'),  # as file path
            f"mahoun/{module_name.replace('.', '/')}",  # with mahoun prefix as path
        ]
        
        for path_str in possible_paths:
            file_path = self.root_dir / path_str
            
            # Try with .py extension
            if not file_path.suffix:
                file_path = file_path.with_suffix('.py')
            
            if file_path.exists():
                return True
            
            # Try as package directory
            package_path = self.root_dir / path_str
            if package_path.exists() and package_path.is_dir():
                return True
        
        return False
    
    def check_is_example_module(self, module_name: str) -> bool:
        """Check if module is an example/demo."""
        return any(pattern in module_name.lower() for pattern in self.example_patterns)
    
    def check_is_experimental(self, module_name: str) -> bool:
        """Check if module is experimental."""
        return any(pattern in module_name.lower() for pattern in self.experimental_patterns)
    
    def check_is_package_level(self, module_name: str) -> bool:
        """Check if exception is at package level (should be individual modules)."""
        # Package-level exceptions end without a specific module name
        # e.g., "pipelines.ingestion" instead of "pipelines.ingestion.handler"
        parts = module_name.split('.')
        
        # If it's just a package name without a specific module, it's package-level
        file_path = self.root_dir / '/'.join(parts)
        
        if file_path.exists() and file_path.is_dir():
            # Check if there's an __init__.py
            init_file = file_path / '__init__.py'
            if init_file.exists():
                return True
        
        return False
    
    def check_has_newer_version(self, module_name: str) -> Optional[str]:
        """Check if there's a newer version of this module."""
        # Look for v2, v3, etc. versions
        base_name = module_name.split('.')[-1]
        
        # Check for versioned alternatives
        if '_v' not in base_name.lower():
            # This might be the old version, look for newer
            potential_newer = []
            
            # Search for versioned alternatives
            parent_dir = self.root_dir / '/'.join(module_name.split('.')[:-1])
            
            if parent_dir.exists():
                for file in parent_dir.glob("*.py"):
                    file_base = file.stem
                    if base_name in file_base and file_base != base_name:
                        if '_v' in file_base.lower():
                            potential_newer.append(file_base)
            
            if potential_newer:
                # Return the highest version
                return max(potential_newer, key=lambda x: int(x.split('_v')[-1]) if '_v' in x else 0)
        
        return None
    
    def review_baseline_exception(self, module_name: str, current_reason: str) -> ExceptionReview:
        """
        Review a single baseline exception.
        
        Args:
            module_name: Module name from baseline
            current_reason: Current reason for exception
            
        Returns:
            ExceptionReview with recommendation
        """
        # Check if file still exists
        file_exists = self.check_file_exists(module_name)
        
        if not file_exists:
            return ExceptionReview(
                module=module_name,
                current_reason=current_reason,
                recommended_action="remove",
                review_reason="Module file no longer exists",
                confidence=1.0
            )
        
        # Check if it's an example module
        if self.check_is_example_module(module_name):
            return ExceptionReview(
                module=module_name,
                current_reason=current_reason,
                recommended_action="remove",
                review_reason="Example/demo module - safe to remove",
                confidence=0.9
            )
        
        # Check if it's experimental
        if self.check_is_experimental(module_name):
            return ExceptionReview(
                module=module_name,
                current_reason=current_reason,
                recommended_action="investigate",
                review_reason="Experimental module - review if still needed",
                confidence=0.7
            )
        
        # Check if it's package-level
        if self.check_is_package_level(module_name):
            return ExceptionReview(
                module=module_name,
                current_reason=current_reason,
                recommended_action="investigate",
                review_reason="Package-level exception - should be individual modules",
                confidence=0.8
            )
        
        # Check for newer versions
        newer_version = self.check_has_newer_version(module_name)
        if newer_version:
            return ExceptionReview(
                module=module_name,
                current_reason=current_reason,
                recommended_action="remove",
                review_reason=f"Superseded by newer version: {newer_version}",
                confidence=0.85,
                suggested_replacement=newer_version
            )
        
        # Default: keep for now
        return ExceptionReview(
            module=module_name,
            current_reason=current_reason,
            recommended_action="keep",
            review_reason="Legitimate standalone module - keep in baseline",
            confidence=0.6
        )
    
    def review_baseline(self, baseline_path: str) -> None:
        """
        Review all exceptions in baseline.
        
        Args:
            baseline_path: Path to baseline JSON file
        """
        baseline_file = Path(baseline_path)
        
        if not baseline_file.exists():
            logger.error(f"Baseline file not found: {baseline_path}")
            return
        
        try:
            with open(baseline_file, 'r') as f:
                data = json.load(f)
            
            exceptions = data.get("exceptions", {})
            
            logger.info(f"Reviewing {len(exceptions)} baseline exceptions...")
            
            for module_name, exception_data in exceptions.items():
                current_reason = exception_data.get("reason", "No reason provided")
                review = self.review_baseline_exception(module_name, current_reason)
                self.reviews.append(review)
            
            logger.info(f"Review complete: {len(self.reviews)} exceptions reviewed")
            
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
    
    def get_removal_candidates(self) -> List[ExceptionReview]:
        """Get exceptions recommended for removal."""
        return [r for r in self.reviews if r.recommended_action == "remove"]
    
    def get_investigation_candidates(self) -> List[ExceptionReview]:
        """Get exceptions that need investigation."""
        return [r for r in self.reviews if r.recommended_action == "investigate"]
    
    def get_keep_candidates(self) -> List[ExceptionReview]:
        """Get exceptions recommended to keep."""
        return [r for r in self.reviews if r.recommended_action == "keep"]
    
    def export_json(self, output_path: str) -> None:
        """Export review results to JSON."""
        export_data = {
            "total_exceptions": len(self.reviews),
            "removal_candidates": len(self.get_removal_candidates()),
            "investigation_candidates": len(self.get_investigation_candidates()),
            "keep_candidates": len(self.get_keep_candidates()),
            "reviews": [
                {
                    "module": review.module,
                    "current_reason": review.current_reason,
                    "recommended_action": review.recommended_action,
                    "review_reason": review.review_reason,
                    "confidence": review.confidence,
                    "suggested_replacement": review.suggested_replacement,
                }
                for review in self.reviews
            ]
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Review results exported to: {output_path}")
    
    def print_review(self) -> None:
        """Print human-readable review."""
        print("\n" + "=" * 60)
        print("BASELINE EXCEPTION REVIEW")
        print("=" * 60)
        print(f"Total exceptions reviewed: {len(self.reviews)}")
        print(f"Removal candidates: {len(self.get_removal_candidates())}")
        print(f"Investigation needed: {len(self.get_investigation_candidates())}")
        print(f"Keep candidates: {len(self.get_keep_candidates())}")
        
        # Show removal candidates
        removals = self.get_removal_candidates()
        if removals:
            print(f"\n🗑️  REMOVAL CANDIDATES ({len(removals)}):")
            for review in removals:
                print(f"  - {review.module}")
                print(f"    Reason: {review.review_reason}")
                print(f"    Confidence: {review.confidence:.2f}")
                if review.suggested_replacement:
                    print(f"    Replacement: {review.suggested_replacement}")
        
        # Show investigation candidates
        investigations = self.get_investigation_candidates()
        if investigations:
            print(f"\n🔍 INVESTIGATION NEEDED ({len(investigations)}):")
            for review in investigations:
                print(f"  - {review.module}")
                print(f"    Reason: {review.review_reason}")
                print(f"    Confidence: {review.confidence:.2f}")
        
        # Show keep candidates (high confidence only)
        keeps = [r for r in self.get_keep_candidates() if r.confidence >= 0.8]
        if keeps:
            print(f"\n✅ CONFIDENT KEEP CANDIDATES ({len(keeps)}):")
            for review in keeps:
                print(f"  - {review.module}")
                print(f"    Reason: {review.review_reason}")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Baseline exception review"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--baseline",
        default="ci/gates/module_wiring_baseline.json",
        help="Path to baseline JSON file"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    reviewer = BaselineExceptionReviewer(args.root_dir)
    reviewer.review_baseline(args.baseline)
    
    if args.output:
        reviewer.export_json(args.output)
    
    reviewer.print_review()


if __name__ == "__main__":
    main()
