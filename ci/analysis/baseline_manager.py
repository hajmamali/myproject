#!/usr/bin/env python3
"""
Baseline Manager
===============

Manage frozen baseline exceptions for module wiring validation.

Provides comprehensive baseline management including:
- Baseline creation and updates
- Exception review and approval
- Baseline comparison and diff
- Exception expiration handling
- Baseline validation and integrity checks
- Migration between baseline versions

Usage:
    python ci/analysis/baseline_manager.py --create
    python ci/analysis/baseline_manager.py --review
    python ci/analysis/baseline_manager.py --validate
"""

import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


BASELINE_FILE = "ci/gates/module_wiring_baseline.json"
BACKUP_DIR = "ci/gates/baseline_backups"


@dataclass
class BaselineException:
    """Single baseline exception entry."""
    module: str
    reason: str = ""
    added_date: str = ""
    expires_date: Optional[str] = None
    approved_by: str = ""
    status: str = "active"  # active, expired, deprecated


@dataclass
class BaselineMetadata:
    """Baseline metadata."""
    version: str
    created_date: str
    last_modified: str
    author: str
    description: str = ""
    total_exceptions: int = 0


@dataclass
class Baseline:
    """Complete baseline data structure."""
    metadata: BaselineMetadata
    exceptions: Dict[str, BaselineException] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert baseline to dictionary for JSON serialization."""
        return {
            "metadata": {
                "version": self.metadata.version,
                "created_date": self.metadata.created_date,
                "last_modified": self.metadata.last_modified,
                "author": self.metadata.author,
                "description": self.metadata.description,
                "total_exceptions": self.metadata.total_exceptions
            },
            "exceptions": {
                module: {
                    "reason": exc.reason,
                    "added_date": exc.added_date,
                    "expires_date": exc.expires_date,
                    "approved_by": exc.approved_by,
                    "status": exc.status
                }
                for module, exc in self.exceptions.items()
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Baseline':
        """Create baseline from dictionary."""
        metadata_data = data.get("metadata", {})
        metadata = BaselineMetadata(
            version=metadata_data.get("version", "1.0"),
            created_date=metadata_data.get("created_date", datetime.now().isoformat()),
            last_modified=metadata_data.get("last_modified", datetime.now().isoformat()),
            author=metadata_data.get("author", "unknown"),
            description=metadata_data.get("description", ""),
            total_exceptions=metadata_data.get("total_exceptions", 0)
        )
        
        exceptions = {}
        for module, exc_data in data.get("exceptions", {}).items():
            exceptions[module] = BaselineException(
                module=module,
                reason=exc_data.get("reason", ""),
                added_date=exc_data.get("added_date", datetime.now().isoformat()),
                expires_date=exc_data.get("expires_date"),
                approved_by=exc_data.get("approved_by", ""),
                status=exc_data.get("status", "active")
            )
        
        return cls(metadata=metadata, exceptions=exceptions)


class BaselineManager:
    """Manage baseline exceptions for module wiring validation."""
    
    def __init__(self, root_dir: str):
        """
        Initialize baseline manager.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.baseline_path = self.root_dir / BASELINE_FILE
        self.backup_dir = self.root_dir / BACKUP_DIR
        self.baseline: Optional[Baseline] = None
        
    def load_baseline(self) -> Optional[Baseline]:
        """Load baseline from file."""
        if not self.baseline_path.exists():
            logger.warning(f"Baseline file not found: {self.baseline_path}")
            return None
        
        try:
            with open(self.baseline_path, 'r') as f:
                data = json.load(f)
            
            self.baseline = Baseline.from_dict(data)
            logger.info(f"Loaded baseline with {len(self.baseline.exceptions)} exceptions")
            return self.baseline
            
        except Exception as e:
            logger.error(f"Failed to load baseline: {e}")
            return None
    
    def save_baseline(self) -> bool:
        """Save baseline to file."""
        if not self.baseline:
            logger.error("No baseline to save")
            return False
        
        try:
            # Create backup before saving
            self._create_backup()
            
            # Update metadata
            self.baseline.metadata.last_modified = datetime.now().isoformat()
            self.baseline.metadata.total_exceptions = len(self.baseline.exceptions)
            
            # Save baseline
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.baseline_path, 'w') as f:
                json.dump(self.baseline.to_dict(), f, indent=2)
            
            logger.info(f"Baseline saved to: {self.baseline_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save baseline: {e}")
            return False
    
    def _create_backup(self) -> None:
        """Create backup of current baseline."""
        if not self.baseline_path.exists():
            return
        
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = self.backup_dir / f"baseline_{timestamp}.json"
        
        try:
            import shutil
            shutil.copy2(self.baseline_path, backup_path)
            logger.info(f"Backup created: {backup_path}")
        except Exception as e:
            logger.warning(f"Failed to create backup: {e}")
    
    def create_baseline(
        self,
        exceptions: List[str],
        version: str = "1.0",
        author: str = "system",
        description: str = ""
    ) -> bool:
        """
        Create new baseline with exceptions.
        
        Args:
            exceptions: List of module names to add as exceptions
            version: Baseline version
            author: Baseline author
            description: Baseline description
            
        Returns:
            True if successful
        """
        metadata = BaselineMetadata(
            version=version,
            created_date=datetime.now().isoformat(),
            last_modified=datetime.now().isoformat(),
            author=author,
            description=description,
            total_exceptions=len(exceptions)
        )
        
        baseline_exceptions = {}
        for module in exceptions:
            baseline_exceptions[module] = BaselineException(
                module=module,
                reason="Initial baseline exception",
                added_date=datetime.now().isoformat(),
                approved_by=author,
                status="active"
            )
        
        self.baseline = Baseline(metadata=metadata, exceptions=baseline_exceptions)
        return self.save_baseline()
    
    def add_exception(
        self,
        module: str,
        reason: str,
        expires_date: Optional[str] = None,
        approved_by: str = "system"
    ) -> bool:
        """
        Add exception to baseline.
        
        Args:
            module: Module name
            reason: Reason for exception
            expires_date: Optional expiration date
            approved_by: Approver name
            
        Returns:
            True if successful
        """
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                logger.error("Cannot add exception: no baseline loaded")
                return False
        
        exception = BaselineException(
            module=module,
            reason=reason,
            added_date=datetime.now().isoformat(),
            expires_date=expires_date,
            approved_by=approved_by,
            status="active"
        )
        
        self.baseline.exceptions[module] = exception
        return self.save_baseline()
    
    def remove_exception(self, module: str) -> bool:
        """
        Remove exception from baseline.
        
        Args:
            module: Module name to remove
            
        Returns:
            True if successful
        """
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                logger.error("Cannot remove exception: no baseline loaded")
                return False
        
        if module in self.baseline.exceptions:
            del self.baseline.exceptions[module]
            return self.save_baseline()
        else:
            logger.warning(f"Exception not found: {module}")
            return False
    
    def review_exceptions(self) -> None:
        """Review current baseline exceptions."""
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                logger.error("No baseline to review")
                return
        
        print("\n" + "=" * 60)
        print("BASELINE EXCEPTIONS REVIEW")
        print("=" * 60)
        print(f"Version: {self.baseline.metadata.version}")
        print(f"Created: {self.baseline.metadata.created_date}")
        print(f"Last Modified: {self.baseline.metadata.last_modified}")
        print(f"Author: {self.baseline.metadata.author}")
        print(f"Total Exceptions: {len(self.baseline.exceptions)}")
        
        if self.baseline.metadata.description:
            print(f"Description: {self.baseline.metadata.description}")
        
        print("\nExceptions:")
        
        # Group by status
        active = []
        expired = []
        deprecated = []
        
        for module, exc in self.baseline.exceptions.items():
            if exc.status == "active":
                active.append((module, exc))
            elif exc.status == "expired":
                expired.append((module, exc))
            elif exc.status == "deprecated":
                deprecated.append((module, exc))
        
        if active:
            print(f"\nActive ({len(active)}):")
            for module, exc in active:
                print(f"  - {module}")
                print(f"    Reason: {exc.reason}")
                print(f"    Added: {exc.added_date}")
                if exc.expires_date:
                    print(f"    Expires: {exc.expires_date}")
                print(f"    Approved by: {exc.approved_by}")
        
        if expired:
            print(f"\nExpired ({len(expired)}):")
            for module, exc in expired:
                print(f"  - {module} (expired: {exc.expires_date})")
        
        if deprecated:
            print(f"\nDeprecated ({len(deprecated)}):")
            for module, exc in deprecated:
                print(f"  - {module}")
        
        print("=" * 60)
    
    def validate_baseline(self) -> bool:
        """
        Validate baseline integrity.
        
        Returns:
            True if baseline is valid
        """
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                logger.error("No baseline to validate")
                return False
        
        issues = []
        
        # Check for expired exceptions
        now = datetime.now()
        for module, exc in self.baseline.exceptions.items():
            if exc.expires_date:
                try:
                    expires = datetime.fromisoformat(exc.expires_date)
                    if expires < now and exc.status == "active":
                        issues.append(f"Expired exception still active: {module}")
                        exc.status = "expired"
                except ValueError:
                    issues.append(f"Invalid expiration date for: {module}")
        
        # Check for duplicate reasons (potential grouping opportunity)
        reason_counts = {}
        for exc in self.baseline.exceptions.values():
            reason_counts[exc.reason] = reason_counts.get(exc.reason, 0) + 1
        
        for reason, count in reason_counts.items():
            if count > 5:
                issues.append(f"Many exceptions share same reason: '{reason}' ({count} modules)")
        
        if issues:
            logger.warning(f"Baseline validation found {len(issues)} issues:")
            for issue in issues:
                logger.warning(f"  - {issue}")
            return False
        else:
            logger.info("Baseline validation passed")
            return True
    
    def cleanup_expired(self) -> int:
        """
        Remove expired exceptions from baseline.
        
        Returns:
            Number of exceptions removed
        """
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                logger.error("No baseline to cleanup")
                return 0
        
        now = datetime.now()
        to_remove = []
        
        for module, exc in self.baseline.exceptions.items():
            if exc.expires_date:
                try:
                    expires = datetime.fromisoformat(exc.expires_date)
                    if expires < now:
                        to_remove.append(module)
                except ValueError:
                    pass
        
        for module in to_remove:
            del self.baseline.exceptions[module]
        
        if to_remove:
            self.save_baseline()
            logger.info(f"Removed {len(to_remove)} expired exceptions")
        
        return len(to_remove)
    
    def compare_with_list(self, current_unwired: List[str]) -> Dict[str, List[str]]:
        """
        Compare baseline with current unwired modules list.
        
        Args:
            current_unwired: List of currently unwired modules
            
        Returns:
            Dict with 'new_unwired', 'resolved', 'still_unwired' lists
        """
        if not self.baseline:
            self.load_baseline()
            if not self.baseline:
                return {
                    "new_unwired": current_unwired,
                    "resolved": [],
                    "still_unwired": []
                }
        
        baseline_exceptions = set(self.baseline.exceptions.keys())
        current_set = set(current_unwired)
        
        new_unwired = current_set - baseline_exceptions
        resolved = baseline_exceptions - current_set
        still_unwired = baseline_exceptions & current_set
        
        return {
            "new_unwired": sorted(list(new_unwired)),
            "resolved": sorted(list(resolved)),
            "still_unwired": sorted(list(still_unwired))
        }


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Baseline management for module wiring validation"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--create",
        action="store_true",
        help="Create new baseline from unwired modules list"
    )
    parser.add_argument(
        "--unwired-file",
        help="File containing list of unwired modules (for --create)"
    )
    parser.add_argument(
        "--add",
        help="Add exception for specific module"
    )
    parser.add_argument(
        "--reason",
        help="Reason for exception (for --add)"
    )
    parser.add_argument(
        "--remove",
        help="Remove exception for specific module"
    )
    parser.add_argument(
        "--review",
        action="store_true",
        help="Review current baseline exceptions"
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate baseline integrity"
    )
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Remove expired exceptions"
    )
    parser.add_argument(
        "--compare",
        help="Compare with current unwired modules file"
    )
    parser.add_argument(
        "--version",
        help="Baseline version (for --create)"
    )
    parser.add_argument(
        "--author",
        default="system",
        help="Baseline author (for --create)"
    )
    parser.add_argument(
        "--description",
        default="",
        help="Baseline description (for --create)"
    )
    
    args = parser.parse_args()
    
    manager = BaselineManager(args.root_dir)
    
    if args.create:
        if not args.unwired_file:
            logger.error("--unwired-file required for --create")
            sys.exit(1)
        
        try:
            with open(args.unwired_file, 'r') as f:
                data = json.load(f)
                unwired = data.get('exceptions', [])
        except Exception as e:
            logger.error(f"Failed to load unwired file: {e}")
            sys.exit(1)
        
        version = args.version or "1.0"
        success = manager.create_baseline(
            exceptions=unwired,
            version=version,
            author=args.author,
            description=args.description
        )
        
        if success:
            logger.info("Baseline created successfully")
        else:
            logger.error("Failed to create baseline")
            sys.exit(1)
    
    elif args.add:
        if not args.reason:
            logger.error("--reason required for --add")
            sys.exit(1)
        
        success = manager.add_exception(
            module=args.add,
            reason=args.reason,
            approved_by=args.author
        )
        
        if success:
            logger.info(f"Exception added for: {args.add}")
        else:
            logger.error("Failed to add exception")
            sys.exit(1)
    
    elif args.remove:
        success = manager.remove_exception(args.remove)
        
        if success:
            logger.info(f"Exception removed for: {args.remove}")
        else:
            logger.error("Failed to remove exception")
            sys.exit(1)
    
    elif args.review:
        manager.review_exceptions()
    
    elif args.validate:
        valid = manager.validate_baseline()
        sys.exit(0 if valid else 1)
    
    elif args.cleanup:
        removed = manager.cleanup_expired()
        logger.info(f"Cleaned up {removed} expired exceptions")
    
    elif args.compare:
        if not args.compare:
            logger.error("--compare requires file path")
            sys.exit(1)
        
        try:
            with open(args.compare, 'r') as f:
                data = json.load(f)
                current_unwired = data.get('exceptions', [])
        except Exception as e:
            logger.error(f"Failed to load comparison file: {e}")
            sys.exit(1)
        
        comparison = manager.compare_with_list(current_unwired)
        
        print("\n" + "=" * 60)
        print("BASELINE COMPARISON")
        print("=" * 60)
        print(f"New unwired modules: {len(comparison['new_unwired'])}")
        print(f"Resolved modules: {len(comparison['resolved'])}")
        print(f"Still unwired: {len(comparison['still_unwired'])}")
        
        if comparison['new_unwired']:
            print("\nNew unwired modules (not in baseline):")
            for module in comparison['new_unwired']:
                print(f"  - {module}")
        
        if comparison['resolved']:
            print("\nResolved modules (in baseline but no longer unwired):")
            for module in comparison['resolved']:
                print(f"  - {module}")
        
        print("=" * 60)
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
