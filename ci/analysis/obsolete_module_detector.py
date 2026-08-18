#!/usr/bin/env python3
"""
Obsolete Module Detector
========================

Identify obsolete/legacy modules that have been upgraded but old versions remain.

Detects:
- Versioned modules (v2, v3, etc.)
- Backup modules (_old, _backup, _legacy)
- Duplicate modules with similar functionality
- Modules in baseline that may be truly obsolete
- Dead code patterns

Usage:
    python ci/analysis/obsolete_module_detector.py --directory mahoun/reasoning
    python ci/analysis/obsolete_module_detector.py --all --output obsolete.json
"""

import sys
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
import argparse
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ObsoleteModuleInfo:
    """Information about potentially obsolete module."""
    module: str
    reason: str
    confidence: float  # 0.0 to 1.0
    suggested_replacement: Optional[str] = None
    file_size: int = 0
    last_modified: str = ""
    import_count: int = 0


class ObsoleteModuleDetector:
    """Detect obsolete and legacy modules."""
    
    def __init__(self, root_dir: str):
        """
        Initialize detector.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.potential_obsolete: List[ObsoleteModuleInfo] = []
        self.all_modules: Set[str] = set()
        
    def is_versioned_module(self, module_name: str) -> Optional[Tuple[str, str]]:
        """
        Check if module is versioned (e.g., module_v2, module_v3).
        
        Returns:
            Tuple of (base_name, version) if versioned, None otherwise
        """
        # Match patterns like: module_v2, module_v3, module_v2_0
        match = re.search(r'(.*)_v(\d+)(?:_\d+)?$', module_name)
        if match:
            base_name = match.group(1)
            version = match.group(2)
            return (base_name, version)
        
        return None
    
    def is_backup_module(self, module_name: str) -> Optional[str]:
        """
        Check if module is a backup (_old, _backup, _legacy).
        
        Returns:
            Reason string if backup, None otherwise
        """
        backup_patterns = {
            '_old': 'old version',
            '_backup': 'backup',
            '_legacy': 'legacy',
            '_deprecated': 'deprecated',
            '_unused': 'unused',
            '_temp': 'temporary',
        }
        
        for pattern, reason in backup_patterns.items():
            if module_name.endswith(pattern):
                return reason
        
        return None
    
    def find_duplicate_modules(self, directory: str) -> Dict[str, List[str]]:
        """
        Find modules with similar names that might be duplicates.
        
        Args:
            directory: Directory path relative to root
            
        Returns:
            Dict mapping base names to list of similar modules
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            return {}
        
        modules = []
        
        for filepath in dir_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in filepath.name or "__pycache__" in filepath.parts:
                continue
            
            # Get module name
            try:
                relative = filepath.relative_to(self.root_dir)
                parts = list(relative.parts)
                
                if parts[-1].endswith('.py'):
                    parts[-1] = parts[-1][:-3]
                
                if parts[-1] == '__init__':
                    parts = parts[:-1]
                
                module_name = '.'.join(parts)
                modules.append(module_name)
            except ValueError:
                continue
        
        # Group by base name
        duplicates = {}
        
        for module in modules:
            base_name = module.split('.')[-1]
            
            # Check for versioned modules
            versioned = self.is_versioned_module(base_name)
            if versioned:
                base_name = versioned[0]
            
            if base_name not in duplicates:
                duplicates[base_name] = []
            
            duplicates[base_name].append(module)
        
        # Only keep groups with multiple modules
        return {k: v for k, v in duplicates.items() if len(v) > 1}
    
    def check_import_usage(self, module_name: str) -> int:
        """
        Check how many times a module is imported.
        
        Args:
            module_name: Module name to check
            
        Returns:
            Number of imports
        """
        # Simplified check - in production would use AST analysis
        import_count = 0
        
        for filepath in self.root_dir.rglob("*.py"):
            if "test" in filepath.name or "__pycache__" in filepath.parts:
                continue
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Check for import patterns
                if f"from {module_name}" in content or f"import {module_name}" in content:
                    import_count += 1
            except Exception:
                pass
        
        return import_count
    
    def detect_obsolete_modules(self, directory: str) -> None:
        """
        Detect obsolete modules in a directory.
        
        Args:
            directory: Directory path relative to root
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return
        
        logger.info(f"Detecting obsolete modules in: {directory}")
        
        # Find duplicate modules
        duplicates = self.find_duplicate_modules(directory)
        
        # Analyze each group
        for base_name, modules in duplicates.items():
            if len(modules) < 2:
                continue
            
            # Sort modules to find the most recent
            sorted_modules = sorted(modules)
            
            # Check for versioned modules
            versioned_modules = {}
            for module in modules:
                versioned = self.is_versioned_module(module.split('.')[-1])
                if versioned:
                    base, version = versioned
                    versioned_modules[module] = int(version)
            
            if versioned_modules:
                # Find highest version
                latest = max(versioned_modules.items(), key=lambda x: x[1])[0]
                
                # Mark older versions as obsolete
                for module in modules:
                    if module != latest and module in versioned_modules:
                        filepath = self.root_dir / module.replace('.', '/')
                        if not filepath.suffix:
                            filepath = filepath.with_suffix('.py')
                        
                        if filepath.exists():
                            stat = filepath.stat()
                            import_count = self.check_import_usage(module)
                            
                            self.potential_obsolete.append(ObsoleteModuleInfo(
                                module=module,
                                reason=f"Older version of {latest}",
                                confidence=0.8,
                                suggested_replacement=latest,
                                file_size=stat.st_size,
                                last_modified=str(stat.st_mtime),
                                import_count=import_count
                            ))
            
            # Check for backup modules
            for module in modules:
                backup_reason = self.is_backup_module(module.split('.')[-1])
                if backup_reason:
                    # Find the non-backup version
                    for other_module in modules:
                        if other_module != module and not self.is_backup_module(other_module.split('.')[-1]):
                            filepath = self.root_dir / module.replace('.', '/')
                            if not filepath.suffix:
                                filepath = filepath.with_suffix('.py')
                            
                            if filepath.exists():
                                stat = filepath.stat()
                                import_count = self.check_import_usage(module)
                                
                                self.potential_obsolete.append(ObsoleteModuleInfo(
                                    module=module,
                                    reason=f"Backup module ({backup_reason})",
                                    confidence=0.9,
                                    suggested_replacement=other_module,
                                    file_size=stat.st_size,
                                    last_modified=str(stat.st_mtime),
                                    import_count=import_count
                                ))
                            break
        
        # Also check for individual backup modules
        for filepath in dir_path.rglob("*.py"):
            if "test" in filepath.name or "__pycache__" in filepath.parts:
                continue
            
            filename = filepath.stem
            backup_reason = self.is_backup_module(filename)
            
            if backup_reason:
                try:
                    relative = filepath.relative_to(self.root_dir)
                    parts = list(relative.parts)
                    
                    if parts[-1].endswith('.py'):
                        parts[-1] = parts[-1][:-3]
                    
                    if parts[-1] == '__init__':
                        parts = parts[:-1]
                    
                    module_name = '.'.join(parts)
                    
                    stat = filepath.stat()
                    import_count = self.check_import_usage(module_name)
                    
                    self.potential_obsolete.append(ObsoleteModuleInfo(
                        module=module_name,
                        reason=f"Backup module ({backup_reason})",
                        confidence=0.9,
                        file_size=stat.st_size,
                        last_modified=str(stat.st_mtime),
                        import_count=import_count
                    ))
                except ValueError:
                    pass
        
        logger.info(f"Found {len(self.potential_obsolete)} potentially obsolete modules")
    
    def get_high_confidence_obsolete(self, threshold: float = 0.8) -> List[ObsoleteModuleInfo]:
        """Get obsolete modules with confidence above threshold."""
        return [m for m in self.potential_obsolete if m.confidence >= threshold]
    
    def get_unused_obsolete(self) -> List[ObsoleteModuleInfo]:
        """Get obsolete modules with zero imports."""
        return [m for m in self.potential_obsolete if m.import_count == 0]
    
    def export_json(self, output_path: str) -> None:
        """Export analysis to JSON."""
        export_data = {
            "total_potential_obsolete": len(self.potential_obsolete),
            "high_confidence_count": len(self.get_high_confidence_obsolete()),
            "unused_count": len(self.get_unused_obsolete()),
            "modules": [
                {
                    "module": info.module,
                    "reason": info.reason,
                    "confidence": info.confidence,
                    "suggested_replacement": info.suggested_replacement,
                    "file_size": info.file_size,
                    "last_modified": info.last_modified,
                    "import_count": info.import_count,
                }
                for info in self.potential_obsolete
            ]
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Obsolete module analysis exported to: {output_path}")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("OBSOLETE MODULE DETECTION")
        print("=" * 60)
        print(f"Total potentially obsolete modules: {len(self.potential_obsolete)}")
        print(f"High confidence (>=0.8): {len(self.get_high_confidence_obsolete())}")
        print(f"Unused (0 imports): {len(self.get_unused_obsolete())}")
        
        if self.potential_obsolete:
            print(f"\nPotentially obsolete modules:")
            
            # Group by confidence
            high_conf = self.get_high_confidence_obsolete()
            if high_conf:
                print(f"\nHigh confidence ({len(high_conf)}):")
                for info in high_conf:
                    print(f"  - {info.module}")
                    print(f"    Reason: {info.reason}")
                    print(f"    Confidence: {info.confidence:.2f}")
                    if info.suggested_replacement:
                        print(f"    Replacement: {info.suggested_replacement}")
                    print(f"    Imports: {info.import_count}")
            
            # Show unused modules
            unused = self.get_unused_obsolete()
            if unused:
                print(f"\nUnused obsolete modules ({len(unused)}):")
                for info in unused:
                    print(f"  - {info.module} ({info.reason})")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Obsolete module detection"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--directory",
        help="Specific directory to analyze (relative to root)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Analyze all key directories"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    detector = ObsoleteModuleDetector(args.root_dir)
    
    if args.directory:
        detector.detect_obsolete_modules(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            detector.detect_obsolete_modules(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    if args.output:
        detector.export_json(args.output)
    
    detector.print_analysis()


if __name__ == "__main__":
    main()
