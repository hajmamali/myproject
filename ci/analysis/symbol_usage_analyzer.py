#!/usr/bin/env python3
"""
Symbol Usage Analyzer
=====================

Detect imported but unused modules and symbols.

Provides detailed analysis of symbol usage including:
- Imported but unused modules
- Imported but unused symbols
- Dead code detection
- Unused imports cleanup suggestions
- Symbol usage patterns
- Import optimization opportunities

Usage:
    python ci/analysis/symbol_usage_analyzer.py --directory mahoun/reasoning
    python ci/analysis/symbol_usage_analyzer.py --all --output unused_symbols.json
"""

import ast
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
class SymbolUsageInfo:
    """Information about symbol usage."""
    module: str
    imported_symbols: Set[str] = field(default_factory=set)
    used_symbols: Set[str] = field(default_factory=set)
    unused_symbols: Set[str] = field(default_factory=set)
    imported_modules: Set[str] = field(default_factory=set)
    unused_imports: Set[str] = field(default_factory=set)
    potential_dead_code: bool = False


class SymbolUsageAnalyzer:
    """Analyze symbol usage to detect unused imports."""
    
    def __init__(self, root_dir: str):
        """
        Initialize analyzer.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.symbol_usage: Dict[str, SymbolUsageInfo] = {}
        
    def extract_imports_and_symbols(self, filepath: Path) -> Tuple[Set[str], Set[str], Set[str]]:
        """
        Extract imports and symbol definitions from a Python file.
        
        Returns:
            Tuple of (imported_modules, imported_symbols, defined_symbols)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            imported_modules = set()
            imported_symbols = set()
            defined_symbols = set()
            
            for node in ast.walk(tree):
                # Extract imports
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imported_modules.add(alias.name)
                        if alias.asname:
                            imported_symbols.add(alias.asname)
                        else:
                            base_name = alias.name.split('.')[0]
                            imported_symbols.add(base_name)
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imported_modules.add(node.module)
                        
                        for alias in node.names:
                            if alias.name != '*':
                                if alias.asname:
                                    imported_symbols.add(alias.asname)
                                else:
                                    imported_symbols.add(alias.name)
                
                # Extract symbol definitions
                elif isinstance(node, ast.ClassDef):
                    defined_symbols.add(node.name)
                elif isinstance(node, ast.FunctionDef):
                    if not node.name.startswith('_'):  # Skip private
                        defined_symbols.add(node.name)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            if not target.id.startswith('_'):  # Skip private
                                defined_symbols.add(target.id)
            
            return imported_modules, imported_symbols, defined_symbols
            
        except Exception as e:
            logger.warning(f"Failed to analyze {filepath}: {e}")
            return set(), set(), set()
    
    def extract_used_symbols(self, filepath: Path) -> Set[str]:
        """Extract symbols actually used in a Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            used_symbols = set()
            
            for node in ast.walk(tree):
                # Track variable references
                if isinstance(node, ast.Name):
                    if not node.id.startswith('_'):  # Skip private
                        used_symbols.add(node.id)
                
                # Track attribute access (e.g., module.function)
                elif isinstance(node, ast.Attribute):
                    if isinstance(node.value, ast.Name):
                        if not node.value.id.startswith('_'):
                            used_symbols.add(node.value.id)
            
            return used_symbols
            
        except Exception as e:
            logger.warning(f"Failed to extract used symbols from {filepath}: {e}")
            return set()
    
    def analyze_directory(self, directory: str) -> None:
        """
        Analyze symbol usage in a directory.
        
        Args:
            directory: Directory path relative to root
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return
        
        logger.info(f"Analyzing symbol usage in: {directory}")
        
        # First pass: collect all imports and definitions
        module_data = {}
        
        for filepath in dir_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in filepath.name or "__pycache__" in filepath.parts:
                continue
            
            # Get canonical module name
            try:
                relative = filepath.relative_to(self.root_dir)
                parts = list(relative.parts)
                
                if parts[-1].endswith('.py'):
                    parts[-1] = parts[-1][:-3]
                
                if parts[-1] == '__init__':
                    parts = parts[:-1]
                
                module_name = '.'.join(parts)
            except ValueError:
                continue
            
            imported_modules, imported_symbols, defined_symbols = self.extract_imports_and_symbols(filepath)
            used_symbols = self.extract_used_symbols(filepath)
            
            module_data[module_name] = {
                'imported_modules': imported_modules,
                'imported_symbols': imported_symbols,
                'defined_symbols': defined_symbols,
                'used_symbols': used_symbols
            }
        
        # Second pass: analyze usage
        for module_name, data in module_data.items():
            # Find unused symbols (imported but not used)
            unused_symbols = data['imported_symbols'] - data['used_symbols'] - data['defined_symbols']
            
            # Find potentially unused imports
            # This is simplified - full analysis would check if imported symbols are used
            unused_imports = set()
            
            for imported_module in data['imported_modules']:
                # Check if any symbol from this module is used
                module_used = False
                for symbol in data['used_symbols']:
                    if symbol in imported_module or imported_module in symbol:
                        module_used = True
                        break
                
                if not module_used:
                    unused_imports.add(imported_module)
            
            self.symbol_usage[module_name] = SymbolUsageInfo(
                module=module_name,
                imported_symbols=data['imported_symbols'],
                used_symbols=data['used_symbols'],
                unused_symbols=unused_symbols,
                imported_modules=data['imported_modules'],
                unused_imports=unused_imports,
                potential_dead_code=len(unused_symbols) > len(data['used_symbols']) / 2
            )
        
        logger.info(f"Analyzed {len(self.symbol_usage)} modules")
    
    def get_modules_with_unused_imports(self) -> List[str]:
        """Get modules with unused imports."""
        return [
            module for module, info in self.symbol_usage.items()
            if info.unused_imports
        ]
    
    def get_modules_with_unused_symbols(self) -> List[str]:
        """Get modules with unused symbols."""
        return [
            module for module, info in self.symbol_usage.items()
            if info.unused_symbols
        ]
    
    def get_potential_dead_code(self) -> List[str]:
        """Get modules with potential dead code."""
        return [
            module for module, info in self.symbol_usage.items()
            if info.potential_dead_code
        ]
    
    def generate_cleanup_suggestions(self) -> List[str]:
        """Generate import cleanup suggestions."""
        suggestions = []
        
        for module_name, info in self.symbol_usage.items():
            if info.unused_imports:
                for unused_import in info.unused_imports:
                    suggestions.append(f"Remove unused import in {module_name}: {unused_import}")
            
            if info.unused_symbols:
                for unused_symbol in info.unused_symbols:
                    suggestions.append(f"Remove unused symbol in {module_name}: {unused_symbol}")
        
        return suggestions
    
    def export_json(self, output_path: str) -> None:
        """Export analysis to JSON."""
        export_data = {
            "total_modules": len(self.symbol_usage),
            "modules_with_unused_imports": len(self.get_modules_with_unused_imports()),
            "modules_with_unused_symbols": len(self.get_modules_with_unused_symbols()),
            "potential_dead_code_modules": len(self.get_potential_dead_code()),
            "modules": {
                module: {
                    "imported_symbols": list(info.imported_symbols),
                    "used_symbols": list(info.used_symbols),
                    "unused_symbols": list(info.unused_symbols),
                    "imported_modules": list(info.imported_modules),
                    "unused_imports": list(info.unused_imports),
                    "potential_dead_code": info.potential_dead_code,
                }
                for module, info in self.symbol_usage.items()
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Symbol usage analysis exported to: {output_path}")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("SYMBOL USAGE ANALYSIS")
        print("=" * 60)
        print(f"Total modules analyzed: {len(self.symbol_usage)}")
        print(f"Modules with unused imports: {len(self.get_modules_with_unused_imports())}")
        print(f"Modules with unused symbols: {len(self.get_modules_with_unused_symbols())}")
        print(f"Potential dead code modules: {len(self.get_potential_dead_code())}")
        
        # Show modules with unused imports
        unused_imports = self.get_modules_with_unused_imports()
        if unused_imports:
            print(f"\nModules with unused imports ({len(unused_imports)}):")
            for module in unused_imports[:10]:
                info = self.symbol_usage[module]
                print(f"  - {module}")
                for unused in list(info.unused_imports)[:3]:
                    print(f"    {unused}")
            if len(unused_imports) > 10:
                print(f"  ... and {len(unused_imports) - 10} more")
        
        # Show modules with unused symbols
        unused_symbols = self.get_modules_with_unused_symbols()
        if unused_symbols:
            print(f"\nModules with unused symbols ({len(unused_symbols)}):")
            for module in unused_symbols[:10]:
                info = self.symbol_usage[module]
                print(f"  - {module} ({len(info.unused_symbols)} unused symbols)")
            if len(unused_symbols) > 10:
                print(f"  ... and {len(unused_symbols) - 10} more")
        
        # Show cleanup suggestions
        suggestions = self.generate_cleanup_suggestions()
        if suggestions:
            print(f"\nCleanup suggestions ({len(suggestions)}):")
            for suggestion in suggestions[:10]:
                print(f"  - {suggestion}")
            if len(suggestions) > 10:
                print(f"  ... and {len(suggestions) - 10} more")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Symbol usage analysis"
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
    
    analyzer = SymbolUsageAnalyzer(args.root_dir)
    
    if args.directory:
        analyzer.analyze_directory(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            analyzer.analyze_directory(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    if args.output:
        analyzer.export_json(args.output)
    
    analyzer.print_analysis()


if __name__ == "__main__":
    main()
