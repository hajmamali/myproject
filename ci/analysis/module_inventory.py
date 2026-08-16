#!/usr/bin/env python3
"""
Module Inventory Script
=======================

Complete module listing with metadata for architectural analysis.

Provides comprehensive inventory of all Python modules in the codebase
with detailed metadata including:
- File size and line count
- Import dependencies (incoming/outgoing)
- Symbol exports (classes, functions)
- Last modification time
- Test coverage indicators
- Architectural classification hints

Usage:
    python ci/analysis/module_inventory.py --directory mahoun/reasoning
    python ci/analysis/module_inventory.py --all --output inventory.json
"""

import ast
import os
import sys
import json
from pathlib import Path
from typing import Dict, List, Set, Any, Optional
from dataclasses import dataclass, field, asdict
from datetime import datetime
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ModuleMetadata:
    """Comprehensive metadata for a single module."""
    path: str
    canonical_name: str
    size_bytes: int
    line_count: int
    last_modified: str
    incoming_imports: Set[str] = field(default_factory=set)
    outgoing_imports: Set[str] = field(default_factory=set)
    exported_classes: Set[str] = field(default_factory=set)
    exported_functions: Set[str] = field(default_factory=set)
    exported_variables: Set[str] = field(default_factory=set)
    has_tests: bool = False
    test_file_path: Optional[str] = None
    is_package: bool = False
    docstring: Optional[str] = None
    complexity_score: int = 0  # Cyclomatic complexity approximation


class ModuleInventoryAnalyzer:
    """Analyze and inventory Python modules."""
    
    def __init__(self, root_dir: str):
        """
        Initialize analyzer.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.modules: Dict[str, ModuleMetadata] = {}
        
    def is_test_file(self, filepath: Path) -> bool:
        """Check if file is a test file."""
        return "test" in filepath.name or filepath.parent.name == "tests"
    
    def find_test_file(self, module_path: Path) -> Optional[Path]:
        """Find corresponding test file for a module."""
        # Try common test file patterns
        test_patterns = [
            module_path.parent / f"test_{module_path.name}",
            module_path.parent.parent / "tests" / f"test_{module_path.name}",
            module_path.parent.parent / "tests" / module_path.name,
        ]
        
        for pattern in test_patterns:
            if pattern.exists():
                return pattern
        
        return None
    
    def analyze_module(self, filepath: Path) -> Optional[ModuleMetadata]:
        """Analyze a single Python module."""
        try:
            # Basic file metadata
            stat = filepath.stat()
            size_bytes = stat.st_size
            last_modified = datetime.fromtimestamp(stat.st_mtime).isoformat()
            
            # Read file content
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            line_count = len(source.splitlines())
            
            # Parse AST
            tree = ast.parse(source)
            
            # Extract module docstring
            docstring = ast.get_docstring(tree)
            
            # Analyze AST for imports and exports
            imports = set()
            classes = set()
            functions = set()
            variables = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
                elif isinstance(node, ast.ClassDef):
                    classes.add(node.name)
                elif isinstance(node, ast.FunctionDef):
                    # Skip private functions
                    if not node.name.startswith('_'):
                        functions.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            # Skip private variables
                            if not target.id.startswith('_'):
                                variables.add(target.id)
            
            # Calculate canonical name
            try:
                relative_path = filepath.relative_to(self.root_dir)
                parts = list(relative_path.parts)
                
                # Remove .py extension
                if parts[-1].endswith('.py'):
                    parts[-1] = parts[-1][:-3]
                
                # Remove __init__ (package itself)
                if parts[-1] == '__init__':
                    parts = parts[:-1]
                    is_package = True
                else:
                    is_package = False
                
                canonical_name = '.'.join(parts)
            except ValueError:
                canonical_name = str(filepath)
                is_package = False
            
            # Find test file
            test_file = self.find_test_file(filepath)
            has_tests = test_file is not None
            
            # Approximate complexity (count of control structures)
            complexity_score = 0
            for node in ast.walk(tree):
                if isinstance(node, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                    complexity_score += 1
                elif isinstance(node, ast.BoolOp):
                    complexity_score += len(node.values) - 1
            
            return ModuleMetadata(
                path=str(filepath.relative_to(self.root_dir)),
                canonical_name=canonical_name,
                size_bytes=size_bytes,
                line_count=line_count,
                last_modified=last_modified,
                outgoing_imports=imports,
                exported_classes=classes,
                exported_functions=functions,
                exported_variables=variables,
                has_tests=has_tests,
                test_file_path=str(test_file.relative_to(self.root_dir)) if test_file else None,
                is_package=is_package,
                docstring=docstring,
                complexity_score=complexity_score
            )
            
        except Exception as e:
            logger.warning(f"Failed to analyze {filepath}: {e}")
            return None
    
    def inventory_directory(self, directory: str) -> Dict[str, ModuleMetadata]:
        """
        Inventory all modules in a directory.
        
        Args:
            directory: Directory path relative to root
            
        Returns:
            Dict mapping canonical names to module metadata
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return {}
        
        logger.info(f"Inventorying directory: {directory}")
        
        for filepath in dir_path.rglob("*.py"):
            # Skip test files
            if self.is_test_file(filepath):
                continue
            
            # Skip __pycache__
            if "__pycache__" in filepath.parts:
                continue
            
            module_metadata = self.analyze_module(filepath)
            
            if module_metadata:
                self.modules[module_metadata.canonical_name] = module_metadata
        
        logger.info(f"Found {len(self.modules)} modules in {directory}")
        return self.modules
    
    def build_import_graph(self):
        """Build incoming import relationships."""
        logger.info("Building import graph...")
        
        for module_name, module_info in self.modules.items():
            for imported in module_info.outgoing_imports:
                # Try to match imported module to canonical names
                # This is simplified - full resolution would require more sophisticated matching
                for target_name, target_info in self.modules.items():
                    if imported in target_name or target_name in imported:
                        target_info.incoming_imports.add(module_name)
        
        logger.info("Import graph built")
    
    def generate_summary(self) -> Dict[str, Any]:
        """Generate summary statistics."""
        total_modules = len(self.modules)
        total_lines = sum(m.line_count for m in self.modules.values())
        total_size = sum(m.size_bytes for m in self.modules.values())
        
        modules_with_tests = sum(1 for m in self.modules.values() if m.has_tests)
        packages = sum(1 for m in self.modules.values() if m.is_package)
        
        avg_complexity = sum(m.complexity_score for m in self.modules.values()) / total_modules if total_modules > 0 else 0
        
        return {
            "total_modules": total_modules,
            "total_lines": total_lines,
            "total_size_bytes": total_size,
            "modules_with_tests": modules_with_tests,
            "test_coverage": modules_with_tests / total_modules if total_modules > 0 else 0,
            "packages": packages,
            "average_complexity": avg_complexity,
            "inventory_timestamp": datetime.now().isoformat()
        }
    
    def export_json(self, output_path: str) -> None:
        """Export inventory to JSON file."""
        # Convert sets to lists for JSON serialization
        export_data = {
            "summary": self.generate_summary(),
            "modules": {
                name: {
                    **asdict(module_info),
                    "incoming_imports": list(module_info.incoming_imports),
                    "outgoing_imports": list(module_info.outgoing_imports),
                    "exported_classes": list(module_info.exported_classes),
                    "exported_functions": list(module_info.exported_functions),
                    "exported_variables": list(module_info.exported_variables),
                }
                for name, module_info in self.modules.items()
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Inventory exported to: {output_path}")
    
    def print_summary(self) -> None:
        """Print human-readable summary."""
        summary = self.generate_summary()
        
        print("\n" + "=" * 60)
        print("MODULE INVENTORY SUMMARY")
        print("=" * 60)
        print(f"Total modules: {summary['total_modules']}")
        print(f"Total lines of code: {summary['total_lines']:,}")
        print(f"Total size: {summary['total_size_bytes']:,} bytes")
        print(f"Modules with tests: {summary['modules_with_tests']} ({summary['test_coverage']:.1%})")
        print(f"Packages: {summary['packages']}")
        print(f"Average complexity: {summary['average_complexity']:.1f}")
        print("=" * 60)
        
        # Show largest modules
        print("\nLargest modules by line count:")
        sorted_modules = sorted(
            self.modules.items(),
            key=lambda x: x[1].line_count,
            reverse=True
        )[:10]
        
        for name, meta in sorted_modules:
            print(f"  {meta.line_count:5d} lines - {name}")
        
        # Show most complex modules
        print("\nMost complex modules:")
        sorted_complexity = sorted(
            self.modules.items(),
            key=lambda x: x[1].complexity_score,
            reverse=True
        )[:10]
        
        for name, meta in sorted_complexity:
            print(f"  {meta.complexity_score:3d} complexity - {name}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Module inventory analysis"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--directory",
        help="Specific directory to inventory (relative to root)"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Inventory all key directories"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    analyzer = ModuleInventoryAnalyzer(args.root_dir)
    
    if args.directory:
        analyzer.inventory_directory(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            analyzer.inventory_directory(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    analyzer.build_import_graph()
    
    if args.output:
        analyzer.export_json(args.output)
    
    analyzer.print_summary()


if __name__ == "__main__":
    main()
