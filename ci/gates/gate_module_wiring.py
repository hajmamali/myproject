#!/usr/bin/env python3
"""
Module Wiring Validation Gate
============================

Architectural safeguard to detect unwired modules with zero production imports.

This gate prevents the "Build vs Wire Gap" pattern where advanced features
are built but never integrated into production.

Detection Logic:
1. Scan for Python modules in key directories
2. Check if module has any production imports (excluding tests)
3. Flag modules with zero production imports as potentially unwired
4. Allow whitelist for intentionally standalone modules

Exit Codes:
0: All modules properly wired
1: Unwired modules detected (BLOCKING in production)
"""

import os
import sys
import ast
import subprocess
from pathlib import Path
from typing import Dict, List, Set, Tuple
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# Configuration
KEY_DIRECTORIES = [
    "mahoun/reasoning",
    "mahoun/pipelines/ingestion", 
    "mahoun/guardrails",
    "mahoun/graph",
]

# Whitelist for modules that are intentionally standalone (not imported in production)
WHITELIST = {
    # Test files
    "test_",
    "_test.py",
    
    # Demo/example files
    "demo_",
    "example_",
    
    # Backup files
    "_backup",
    
    # Migration scripts
    "migration_",
    
    # Standalone utilities that don't need production imports
    "utils.py",
    "constants.py",
    "types.py",
}

# Files that are expected to have zero production imports
ZERO_IMPORT_WHITELIST = {
    "__init__.py",  # Package initialization files
    "conftest.py",  # Pytest configuration
}


class ModuleWiringValidator:
    """Validates module wiring by checking production import counts."""
    
    def __init__(self, root_dir: str, fail_on_unwired: bool = True):
        """
        Initialize validator.
        
        Args:
            root_dir: Project root directory
            fail_on_unwired: Whether to fail on unwired modules (production mode)
        """
        self.root_dir = Path(root_dir)
        self.fail_on_unwired = fail_on_unwired
        self.unwired_modules: List[Dict[str, any]] = []
        self.wired_modules: List[Dict[str, any]] = []
        
    def is_test_file(self, filepath: Path) -> bool:
        """Check if file is a test file."""
        return any(pattern in filepath.name for pattern in ["test_", "_test.py"])
    
    def is_whitelisted(self, filepath: Path) -> bool:
        """Check if file is whitelisted as intentionally standalone."""
        filename = filepath.name
        
        # Check zero import whitelist
        if filename in ZERO_IMPORT_WHITELIST:
            return True
            
        # Check general whitelist patterns
        for pattern in WHITELIST:
            if pattern in filename:
                return True
                
        return False
    
    def get_python_files(self, directory: Path) -> List[Path]:
        """Get all Python files in directory."""
        python_files = []
        
        if not directory.exists():
            return python_files
            
        for filepath in directory.rglob("*.py"):
            # Skip test files
            if self.is_test_file(filepath):
                continue
                
            # Skip whitelisted files
            if self.is_whitelisted(filepath):
                continue
                
            # Skip __pycache__ and hidden directories
            if any(part.startswith('.') or part == '__pycache__' 
                   for part in filepath.parts):
                continue
                
            python_files.append(filepath)
            
        return python_files
    
    def count_production_imports(self, filepath: Path) -> int:
        """
        Count production imports for a module.
        
        Uses grep to search for imports of this module across the codebase,
        excluding test files and the module itself.
        """
        module_name = filepath.stem
        module_dir = filepath.parent
        
        # Create import patterns to search for
        import_patterns = [
            f"from {module_dir.name}.{module_name} import",
            f"from {module_dir.name}.{module_name}.",
            f"import {module_dir.name}.{module_name}",
        ]
        
        total_imports = 0
        
        # Search for each pattern
        for pattern in import_patterns:
            try:
                # Use grep to search for imports
                cmd = [
                    "grep", "-r", pattern, str(self.root_dir),
                    "--include=*.py",
                    "--exclude-dir=__pycache__",
                    "--exclude-dir=.git",
                    "--exclude-dir=tests",
                    "--exclude-dir=.test_classification_backup",
                    "--exclude=test_",
                    "--exclude=_test.py",
                ]
                
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                
                if result.returncode == 0:
                    # Count lines, but exclude the module itself
                    lines = result.stdout.strip().split('\n') if result.stdout.strip() else []
                    non_self_imports = [
                        line for line in lines 
                        if str(module_dir) not in line or module_name not in line
                    ]
                    total_imports += len(non_self_imports)
                    
            except subprocess.TimeoutExpired:
                logger.warning(f"Timeout searching for imports in {filepath}")
            except Exception as e:
                logger.warning(f"Error searching for imports in {filepath}: {e}")
        
        return total_imports
    
    def validate_directory(self, directory: str) -> None:
        """Validate all modules in a directory."""
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {directory}")
            return
            
        logger.info(f"Scanning directory: {directory}")
        
        python_files = self.get_python_files(dir_path)
        
        for filepath in python_files:
            import_count = self.count_production_imports(filepath)
            
            module_info = {
                "path": str(filepath.relative_to(self.root_dir)),
                "import_count": import_count,
                "is_wired": import_count > 0
            }
            
            if import_count == 0:
                self.unwired_modules.append(module_info)
                logger.warning(f"⚠️  UNWIRED: {module_info['path']} (0 production imports)")
            else:
                self.wired_modules.append(module_info)
                logger.info(f"✓ WIRED: {module_info['path']} ({import_count} imports)")
    
    def validate_all(self) -> bool:
        """Validate all key directories."""
        logger.info("=" * 60)
        logger.info("Module Wiring Validation")
        logger.info("=" * 60)
        
        for directory in KEY_DIRECTORIES:
            self.validate_directory(directory)
        
        # Summary
        logger.info("=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info(f"Total wired modules: {len(self.wired_modules)}")
        logger.info(f"Total unwired modules: {len(self.unwired_modules)}")
        
        if self.unwired_modules:
            logger.warning("\nUnwired modules detected:")
            for module in self.unwired_modules:
                logger.warning(f"  - {module['path']}")
            
            if self.fail_on_unwired:
                logger.error("\n❌ FAIL: Unwired modules detected in production mode")
                return False
            else:
                logger.warning("\n⚠️  WARNING: Unwired modules detected (non-blocking)")
                return True
        else:
            logger.info("\n✅ PASS: All modules properly wired")
            return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Validate module wiring to detect unwired components"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--fail-on-unwired",
        action="store_true",
        default=True,
        help="Fail if unwired模块 detected (production mode)"
    )
    parser.add_argument(
        "--non-blocking",
        action="store_true",
        help="Run in non-blocking mode (warnings only)"
    )
    
    args = parser.parse_args()
    
    if args.non_blocking:
        args.fail_on_unwired = False
    
    validator = ModuleWiringValidator(
        root_dir=args.root_dir,
        fail_on_unwired=args.fail_on_unwired
    )
    
    success = validator.validate_all()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
