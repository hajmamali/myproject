#!/usr/bin/env python3
"""
Dynamic Wiring Detector
=======================

Identify dynamic registration patterns and plugin systems.

Provides analysis of dynamic wiring mechanisms including:
- Dynamic import patterns (importlib, __import__)
- Registry-based wiring
- Plugin discovery systems
- Decorator-based registration
- Configuration-driven loading
- Factory pattern implementations

Usage:
    python ci/analysis/dynamic_wiring_detector.py --directory mahoun/reasoning
    python ci/analysis/dynamic_wiring_detector.py --all --output dynamic_wiring.json
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
class DynamicWiringInfo:
    """Information about dynamic wiring patterns."""
    module: str
    has_importlib: bool = False
    has_import_function: bool = False
    has_registry: bool = False
    has_plugin_discovery: bool = False
    has_decorator_registration: bool = False
    has_factory_pattern: bool = False
    has_config_loading: bool = False
    dynamic_imports: Set[str] = field(default_factory=set)
    registry_names: Set[str] = field(default_factory=set)
    decorator_names: Set[str] = field(default_factory=set)
    factory_names: Set[str] = field(default_factory=set)
    config_patterns: Set[str] = field(default_factory=set)


class DynamicWiringDetector:
    """Detect dynamic wiring patterns in Python code."""
    
    def __init__(self, root_dir: str):
        """
        Initialize detector.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.dynamic_wiring: Dict[str, DynamicWiringInfo] = {}
        
    def detect_dynamic_patterns(self, filepath: Path) -> DynamicWiringInfo:
        """
        Detect dynamic wiring patterns in a Python file.
        
        Args:
            filepath: Path to Python file
            
        Returns:
            DynamicWiringInfo with detected patterns
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            info = DynamicWiringInfo(module=filepath.stem)
            
            # Track function calls and attributes
            function_calls = set()
            attribute_accesses = set()
            decorator_names = set()
            
            for node in ast.walk(tree):
                # Detect importlib usage
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if 'importlib' in alias.name:
                            info.has_importlib = True
                
                elif isinstance(node, ast.ImportFrom):
                    if node.module and 'importlib' in node.module:
                        info.has_importlib = True
                
                # Detect __import__ usage
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        if node.func.id == '__import__':
                            info.has_import_function = True
                            function_calls.add('__import__')
                        elif node.func.id == 'import_module':
                            info.has_importlib = True
                            function_calls.add('import_module')
                
                # Detect registry patterns (dict/set assignments)
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Subscript):
                            # registry[key] = value
                            if isinstance(target.value, ast.Name):
                                if any(reg in target.value.id.lower() for reg in 
                                   ['registry', 'register', 'plugins', 'handlers', 'mapping']):
                                    info.has_registry = True
                                    info.registry_names.add(target.value.id)
                
                # Detect decorator registration
                elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.ClassDef):
                    for decorator in node.decorator_list:
                        if isinstance(decorator, ast.Name):
                            decorator_names.add(decorator.id)
                            
                            # Check for registration decorators
                            if any(reg in decorator.id.lower() for reg in 
                               ['register', 'plugin', 'handler', 'route', 'command']):
                                info.has_decorator_registration = True
                                info.decorator_names.add(decorator.id)
                
                # Detect factory patterns
                elif isinstance(node, ast.FunctionDef):
                    if 'factory' in node.name.lower() or 'create' in node.name.lower():
                        info.has_factory_pattern = True
                        info.factory_names.add(node.name)
                
                # Detect config loading patterns
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if any(config in node.func.attr.lower() for config in 
                           ['load', 'get', 'from', 'parse']):
                            if isinstance(node.func.value, ast.Name):
                                if any(conf in node.func.value.id.lower() for conf in 
                                   ['config', 'settings', 'env', 'yaml', 'json']):
                                    info.has_config_loading = True
                                    info.config_patterns.add(f"{node.func.value.id}.{node.func.attr}")
                
                # Detect plugin discovery patterns
                elif isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Attribute):
                        if any(discovery in node.func.attr.lower() for discovery in 
                           ['discover', 'load_plugins', 'register_plugins', 'scan']):
                            info.has_plugin_discovery = True
            
            # Track dynamic imports from string literals
            for node in ast.walk(tree):
                if isinstance(node, ast.Str) or isinstance(node, ast.Constant):
                    if isinstance(node, ast.Constant):
                        value = node.value if isinstance(node.value, str) else None
                    else:
                        value = node.s
                    
                    if value and isinstance(value, str):
                        # Check if it looks like a module path
                        if '.' in value and not value.startswith('.'):
                            if any(keyword in value.lower() for keyword in 
                               ['plugin', 'handler', 'module', 'component']):
                                info.dynamic_imports.add(value)
            
            return info
            
        except Exception as e:
            logger.warning(f"Failed to analyze {filepath}: {e}")
            return DynamicWiringInfo(module=filepath.stem)
    
    def analyze_directory(self, directory: str) -> None:
        """
        Analyze dynamic wiring patterns in a directory.
        
        Args:
            directory: Directory path relative to root
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return
        
        logger.info(f"Analyzing dynamic wiring in: {directory}")
        
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
            
            info = self.detect_dynamic_patterns(filepath)
            info.module = module_name
            self.dynamic_wiring[module_name] = info
        
        logger.info(f"Analyzed {len(self.dynamic_wiring)} modules")
    
    def get_dynamic_wiring_modules(self) -> List[str]:
        """Get modules with any dynamic wiring patterns."""
        return [
            module for module, info in self.dynamic_wiring.items()
            if (info.has_importlib or info.has_import_function or 
                info.has_registry or info.has_plugin_discovery or
                info.has_decorator_registration or info.has_factory_pattern or
                info.has_config_loading)
        ]
    
    def get_registry_modules(self) -> List[str]:
        """Get modules with registry patterns."""
        return [
            module for module, info in self.dynamic_wiring.items()
            if info.has_registry
        ]
    
    def get_plugin_systems(self) -> List[str]:
        """Get modules with plugin discovery systems."""
        return [
            module for module, info in self.dynamic_wiring.items()
            if info.has_plugin_discovery
        ]
    
    def get_factory_modules(self) -> List[str]:
        """Get modules with factory patterns."""
        return [
            module for module, info in self.dynamic_wiring.items()
            if info.has_factory_pattern
        ]
    
    def export_json(self, output_path: str) -> None:
        """Export analysis to JSON."""
        export_data = {
            "total_modules": len(self.dynamic_wiring),
            "dynamic_wiring_modules": len(self.get_dynamic_wiring_modules()),
            "registry_modules": len(self.get_registry_modules()),
            "plugin_systems": len(self.get_plugin_systems()),
            "factory_modules": len(self.get_factory_modules()),
            "modules": {
                module: {
                    "has_importlib": info.has_importlib,
                    "has_import_function": info.has_import_function,
                    "has_registry": info.has_registry,
                    "has_plugin_discovery": info.has_plugin_discovery,
                    "has_decorator_registration": info.has_decorator_registration,
                    "has_factory_pattern": info.has_factory_pattern,
                    "has_config_loading": info.has_config_loading,
                    "dynamic_imports": list(info.dynamic_imports),
                    "registry_names": list(info.registry_names),
                    "decorator_names": list(info.decorator_names),
                    "factory_names": list(info.factory_names),
                    "config_patterns": list(info.config_patterns),
                }
                for module, info in self.dynamic_wiring.items()
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Dynamic wiring analysis exported to: {output_path}")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("DYNAMIC WIRING DETECTION")
        print("=" * 60)
        print(f"Total modules analyzed: {len(self.dynamic_wiring)}")
        print(f"Modules with dynamic wiring: {len(self.get_dynamic_wiring_modules())}")
        print(f"Registry-based modules: {len(self.get_registry_modules())}")
        print(f"Plugin systems: {len(self.get_plugin_systems())}")
        print(f"Factory patterns: {len(self.get_factory_modules())}")
        
        # Show dynamic wiring modules
        dynamic_modules = self.get_dynamic_wiring_modules()
        if dynamic_modules:
            print(f"\nModules with dynamic wiring ({len(dynamic_modules)}):")
            for module in dynamic_modules[:10]:
                info = self.dynamic_wiring[module]
                patterns = []
                if info.has_importlib:
                    patterns.append("importlib")
                if info.has_registry:
                    patterns.append("registry")
                if info.has_plugin_discovery:
                    patterns.append("plugin-discovery")
                if info.has_decorator_registration:
                    patterns.append("decorator")
                if info.has_factory_pattern:
                    patterns.append("factory")
                if info.has_config_loading:
                    patterns.append("config-loading")
                
                print(f"  - {module}: {', '.join(patterns)}")
            if len(dynamic_modules) > 10:
                print(f"  ... and {len(dynamic_modules) - 10} more")
        
        # Show registry modules
        registry_modules = self.get_registry_modules()
        if registry_modules:
            print(f"\nRegistry-based modules ({len(registry_modules)}):")
            for module in registry_modules:
                info = self.dynamic_wiring[module]
                print(f"  - {module}: {', '.join(info.registry_names)}")
        
        # Show plugin systems
        plugin_systems = self.get_plugin_systems()
        if plugin_systems:
            print(f"\nPlugin systems ({len(plugin_systems)}):")
            for module in plugin_systems:
                print(f"  - {module}")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Dynamic wiring detection"
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
    
    detector = DynamicWiringDetector(args.root_dir)
    
    if args.directory:
        detector.analyze_directory(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            detector.analyze_directory(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    if args.output:
        detector.export_json(args.output)
    
    detector.print_analysis()


if __name__ == "__main__":
    main()
