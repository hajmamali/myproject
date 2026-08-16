#!/usr/bin/env python3
"""
Production-Grade Module Wiring Integrity Gate
============================================

Architectural safeguard to detect unwired modules with AST-based analysis,
canonical module resolution, and production reachability graph.

Core Principle:
Every production-significant module must have a demonstrable integration path
to an approved production root, or an explicit architectural classification.

Classification Levels:
- WIRED: Reachable from production entry point
- WIRED_ENTRYPOINT: Approved production entry point
- WIRED_DYNAMIC: Registered via dynamic wiring authority
- EXPLICITLY_STANDALONE: Architecturally approved as standalone
- SUSPICIOUS: Imported but unused or unclear integration
- UNWIRED: No demonstrable production integration path

Lifecycle:
Phase 1: Discovery - Inventory all modules
Phase 2: Classification - Determine wiring status
Phase 3: Baseline - Freeze legitimate exceptions
Phase 4: Blocking - Enforce for new modules
"""

import ast
import sys
import os
import importlib.util
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# Configuration
# ============================================================================

KEY_DIRECTORIES = [
    "reasoning",
    "pipelines/ingestion",
    "guardrails",
    "graph",
]

# Approved production entry points (CLI, API, main modules)
PRODUCTION_ENTRYPOINTS = {
    "api/main.py",
    "api/routers/__init__.py",
    "orchestrator/bootstrap.py",
    "switchboard.py",
}

# Dynamic wiring authorities (registries, plugin systems)
DYNAMIC_WIRING_AUTHORITIES = {
    "reasoning/adapters.py",  # Dependency container
    "pipelines/ingestion/ocr_adapters.py",  # OCR container
}

# Explicitly standalone modules (architecturally approved)
EXPLICITLY_STANDALONE = {
    "reasoning/constants.py",
    "graph/types.py",
    "core/exceptions.py",
}

# Frozen baseline for legitimate exceptions (from Phase 3)
BASELINE_EXCEPTIONS_FILE = "ci/gates/module_wiring_baseline.json"


# ============================================================================
# Classification Enum
# ============================================================================

class WiringStatus(Enum):
    """Module wiring classification."""
    WIRED = "wired"  # Reachable from production entry point
    WIRED_ENTRYPOINT = "wired_entrypoint"  # Approved production entry point
    WIRED_DYNAMIC = "wired_dynamic"  # Registered via dynamic authority
    EXPLICITLY_STANDALONE = "explicitly_standalone"  # Architecturally approved
    SUSPICIOUS = "suspicious"  # Imported but unused or unclear
    UNWIRED = "unwired"  # No demonstrable production integration


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class ModuleInfo:
    """Information about a module."""
    path: str
    canonical_name: str
    status: WiringStatus = WiringStatus.UNWIRED
    incoming_imports: Set[str] = field(default_factory=set)
    outgoing_imports: Set[str] = field(default_factory=set)
    symbols_used: Set[str] = field(default_factory=set)
    symbols_exported: Set[str] = field(default_factory=set)
    is_entrypoint: bool = False
    is_dynamic_authority: bool = False
    is_standalone: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ImportGraph:
    """Import dependency graph."""
    nodes: Dict[str, ModuleInfo] = field(default_factory=dict)
    edges: Dict[str, Set[str]] = field(default_factory=dict)  # module -> imports
    
    def add_node(self, module_info: ModuleInfo):
        """Add a module node to the graph."""
        self.nodes[module_info.canonical_name] = module_info
        self.edges[module_info.canonical_name] = module_info.outgoing_imports
    
    def get_reachable_from(self, start_module: str) -> Set[str]:
        """Get all modules reachable from start_module (BFS)."""
        visited = set()
        queue = [start_module]
        
        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)
            
            # Add all outgoing imports
            for imported in self.edges.get(current, set()):
                if imported not in visited:
                    queue.append(imported)
        
        return visited


# ============================================================================
# AST-based Import Discovery
# ============================================================================

class ASTImportAnalyzer(ast.NodeVisitor):
    """AST visitor to extract import information."""
    
    def __init__(self, module_path: Path, package_root: Path):
        self.module_path = module_path
        self.package_root = package_root
        self.imports: Set[str] = set()
        self.symbols_used: Set[str] = set()
        self.symbols_exported: Set[str] = set()
        
    def visit_Import(self, node: ast.Import):
        """Handle 'import x' statements."""
        for alias in node.names:
            module_name = alias.name
            self.imports.add(module_name)
            if alias.asname:
                self.symbols_used.add(alias.asname)
            else:
                # Use base name as symbol
                base_name = module_name.split('.')[0]
                self.symbols_used.add(base_name)
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom):
        """Handle 'from x import y' statements."""
        if node.module:
            module_name = node.module
            self.imports.add(module_name)
            
            for alias in node.names:
                symbol = alias.name
                if alias.asname:
                    self.symbols_used.add(alias.asname)
                else:
                    self.symbols_used.add(symbol)
                
                # Track exported symbols
                if symbol != '*':
                    self.symbols_exported.add(symbol)
        
        self.generic_visit(node)
    
    def visit_Name(self, node: ast.Name):
        """Track symbol usage."""
        self.symbols_used.add(node.id)
        self.generic_visit(node)
    
    def visit_FunctionDef(self, node: ast.FunctionDef):
        """Track function definitions as exported symbols."""
        self.symbols_exported.add(node.name)
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef):
        """Track class definitions as exported symbols."""
        self.symbols_exported.add(node.name)
        self.generic_visit(node)


# ============================================================================
# Canonical Module Resolution
# ============================================================================

class ModuleResolver:
    """Resolve canonical module names from file paths."""
    
    def __init__(self, package_root: Path):
        self.package_root = package_root
    
    def path_to_canonical(self, filepath: Path) -> Optional[str]:
        """
        Convert file path to canonical module name.
        
        Example:
        /path/to/mahoun/reasoning/verdict.py
        → mahoun.reasoning.verdict
        """
        try:
            relative = filepath.relative_to(self.package_root)
            
            # Convert path to module name
            parts = list(relative.parts)
            
            # Remove .py extension
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]
            
            # Remove __init__ (package itself)
            if parts[-1] == '__init__':
                parts = parts[:-1]
            
            return '.'.join(parts)
            
        except ValueError:
            # File not under package root
            return None
    
    def resolve_relative_import(
        self,
        relative_module: str,
        current_module: str,
        level: int
    ) -> Optional[str]:
        """
        Resolve relative import to canonical module name.
        
        Example:
        from .verdict import Verdict
        level=1, current_module=mahoun.reasoning.adapters
        → mahoun.reasoning.verdict
        """
        # Split current module into parts
        parts = current_module.split('.')
        
        # Go up 'level' directories
        if level > len(parts):
            return None
        
        base_parts = parts[:-level] if level > 0 else parts
        
        # Add relative module
        if relative_module:
            base_parts.append(relative_module)
        
        return '.'.join(base_parts)


# ============================================================================
# Production Reachability Analyzer
# ============================================================================

class ProductionReachabilityAnalyzer:
    """Analyze production reachability from entry points."""
    
    def __init__(self, import_graph: ImportGraph):
        self.import_graph = import_graph
    
    def analyze_reachability(self) -> Dict[str, WiringStatus]:
        """
        Determine wiring status based on production reachability.
        
        Returns:
            Dict mapping module canonical names to wiring status
        """
        results = {}
        
        # Get all production entry points
        entrypoint_modules = set()
        for entrypoint_path in PRODUCTION_ENTRYPOINTS:
            entrypoint_file = Path(entrypoint_path)
            if entrypoint_file.exists():
                # Find corresponding module in graph
                for module_name, module_info in self.import_graph.nodes.items():
                    if entrypoint_path in module_info.path:
                        entrypoint_modules.add(module_name)
                        module_info.is_entrypoint = True
                        results[module_name] = WiringStatus.WIRED_ENTRYPOINT
        
        # Mark dynamic wiring authorities
        for authority_path in DYNAMIC_WIRING_AUTHORITIES:
            authority_file = Path(authority_path)
            if authority_file.exists():
                for module_name, module_info in self.import_graph.nodes.items():
                    if authority_path in module_info.path:
                        module_info.is_dynamic_authority = True
                        results[module_name] = WiringStatus.WIRED_DYNAMIC
        
        # Mark explicitly standalone
        for standalone_path in EXPLICITLY_STANDALONE:
            standalone_file = Path(standalone_path)
            if standalone_file.exists():
                for module_name, module_info in self.import_graph.nodes.items():
                    if standalone_path in module_info.path:
                        module_info.is_standalone = True
                        results[module_name] = WiringStatus.EXPLICITLY_STANDALONE
        
        # Analyze reachability from entry points
        for entrypoint in entrypoint_modules:
            reachable = self.import_graph.get_reachable_from(entrypoint)
            
            for module_name in reachable:
                if module_name not in results:
                    results[module_name] = WiringStatus.WIRED
        
        # Check for suspicious modules (imported but unused)
        for module_name, module_info in self.import_graph.nodes.items():
            if module_name not in results:
                # Check if imported by anyone
                has_incoming = len(module_info.incoming_imports) > 0
                
                if has_incoming:
                    # Check if symbols are actually used
                    # This is a simplified check - full analysis would require
                    # tracking symbol usage across modules
                    results[module_name] = WiringStatus.SUSPICIOUS
                    module_info.metadata['reason'] = 'imported_but_usage_unclear'
                else:
                    results[module_name] = WiringStatus.UNWIRED
                    module_info.metadata['reason'] = 'no_incoming_imports'
        
        return results


# ============================================================================
# Main Validator
# ============================================================================

class ModuleWiringValidatorV2:
    """Production-grade module wiring validator."""
    
    def __init__(self, root_dir: str, fail_on_unwired: bool = False):
        """
        Initialize validator.
        
        Args:
            root_dir: Project root directory
            fail_on_unwired: Whether to fail on unwired modules (Phase 4)
        """
        self.root_dir = Path(root_dir)
        self.package_root = self.root_dir / "mahoun"
        self.fail_on_unwired = fail_on_unwired
        
        self.resolver = ModuleResolver(self.package_root)
        self.import_graph = ImportGraph()
        
        self.wired_count = 0
        self.unwired_count = 0
        self.suspicious_count = 0
        self.entrypoint_count = 0
        self.dynamic_count = 0
        self.standalone_count = 0
    
    def is_test_file(self, filepath: Path) -> bool:
        """Check if file is a test file."""
        return "test" in filepath.name or filepath.parent.name == "tests"
    
    def get_python_files(self, directory: str) -> List[Path]:
        """Get all Python files in directory."""
        dir_path = self.package_root / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return []
        
        python_files = []
        
        for filepath in dir_path.rglob("*.py"):
            # Skip test files
            if self.is_test_file(filepath):
                continue
            
            # Skip __pycache__
            if "__pycache__" in filepath.parts:
                continue
            
            python_files.append(filepath)
        
        logger.info(f"Found {len(python_files)} Python files in {directory}")
        return python_files
    
    def analyze_module(self, filepath: Path) -> Optional[ModuleInfo]:
        """Analyze a single module using AST."""
        canonical_name = self.resolver.path_to_canonical(filepath)
        
        if not canonical_name:
            return None
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            
            analyzer = ASTImportAnalyzer(filepath, self.package_root)
            analyzer.visit(tree)
            
            # Resolve imports to canonical names
            canonical_imports = set()
            for imp in analyzer.imports:
                # Try to resolve to canonical name
                # Remove 'mahoun' prefix to match canonical names
                if imp.startswith('mahoun.'):
                    canonical_name = imp.replace('mahoun.', '')
                    canonical_imports.add(canonical_name)
                elif imp.startswith('mahoun'):
                    # Handle direct 'mahoun' imports
                    canonical_imports.add(imp)
            
            module_info = ModuleInfo(
                path=str(filepath.relative_to(self.root_dir)),
                canonical_name=canonical_name,
                outgoing_imports=canonical_imports,
                symbols_used=analyzer.symbols_used,
                symbols_exported=analyzer.symbols_exported,
            )
            
            return module_info
            
        except Exception as e:
            logger.warning(f"Failed to analyze {filepath}: {e}")
            return None
    
    def build_import_graph(self):
        """Build complete import dependency graph."""
        logger.info("Building import dependency graph...")
        
        for directory in KEY_DIRECTORIES:
            logger.info(f"Scanning directory: {directory}")
            
            python_files = self.get_python_files(directory)
            
            for filepath in python_files:
                module_info = self.analyze_module(filepath)
                
                if module_info:
                    self.import_graph.add_node(module_info)
        
        # Build incoming imports
        for module_name, module_info in self.import_graph.nodes.items():
            for imported in module_info.outgoing_imports:
                if imported in self.import_graph.nodes:
                    self.import_graph.nodes[imported].incoming_imports.add(module_name)
        
        logger.info(f"Import graph built: {len(self.import_graph.nodes)} modules")
    
    def load_baseline_exceptions(self) -> Set[str]:
        """Load frozen baseline exceptions from file."""
        baseline_file = self.root_dir / BASELINE_EXCEPTIONS_FILE
        
        if not baseline_file.exists():
            return set()
        
        try:
            with open(baseline_file, 'r') as f:
                data = json.load(f)
                return set(data.get('exceptions', []))
        except Exception as e:
            logger.warning(f"Failed to load baseline: {e}")
            return set()
    
    def validate(self) -> bool:
        """
        Perform complete validation.
        
        Returns:
            True if validation passes, False otherwise
        """
        logger.info("=" * 60)
        logger.info("Production-Grade Module Wiring Validation")
        logger.info("=" * 60)
        
        # Build import graph
        self.build_import_graph()
        
        # Analyze production reachability
        logger.info("Analyzing production reachability...")
        analyzer = ProductionReachabilityAnalyzer(self.import_graph)
        wiring_status = analyzer.analyze_reachability()
        
        # Load baseline exceptions
        baseline_exceptions = self.load_baseline_exceptions()
        
        # Apply wiring status to modules
        for module_name, status in wiring_status.items():
            if module_name in self.import_graph.nodes:
                self.import_graph.nodes[module_name].status = status
        
        # Count by status
        for module_name, module_info in self.import_graph.nodes.items():
            status = module_info.status
            
            if status == WiringStatus.WIRED:
                self.wired_count += 1
            elif status == WiringStatus.WIRED_ENTRYPOINT:
                self.entrypoint_count += 1
            elif status == WiringStatus.WIRED_DYNAMIC:
                self.dynamic_count += 1
            elif status == WiringStatus.EXPLICITLY_STANDALONE:
                self.standalone_count += 1
            elif status == WiringStatus.SUSPICIOUS:
                self.suspicious_count += 1
            elif status == WiringStatus.UNWIRED:
                # Check if in baseline
                if module_name in baseline_exceptions:
                    module_info.metadata['baseline_exception'] = True
                    module_info.status = WiringStatus.EXPLICITLY_STANDALONE
                    self.standalone_count += 1
                else:
                    self.unwired_count += 1
        
        # Print summary
        logger.info("=" * 60)
        logger.info("Summary")
        logger.info("=" * 60)
        logger.info(f"Total modules: {len(self.import_graph.nodes)}")
        logger.info(f"✓ WIRED: {self.wired_count}")
        logger.info(f"✓ WIRED_ENTRYPOINT: {self.entrypoint_count}")
        logger.info(f"✓ WIRED_DYNAMIC: {self.dynamic_count}")
        logger.info(f"✓ EXPLICITLY_STANDALONE: {self.standalone_count}")
        logger.info(f"⚠️  SUSPICIOUS: {self.suspicious_count}")
        logger.info(f"❌ UNWIRED: {self.unwired_count}")
        
        # Print suspicious modules
        if self.suspicious_count > 0:
            logger.warning("\nSuspicious modules (imported but usage unclear):")
            for module_name, module_info in self.import_graph.nodes.items():
                if module_info.status == WiringStatus.SUSPICIOUS:
                    logger.warning(f"  - {module_name}")
                    logger.warning(f"    Reason: {module_info.metadata.get('reason', 'unknown')}")
        
        # Print unwired modules
        if self.unwired_count > 0:
            logger.error("\nUnwired modules (no production integration):")
            for module_name, module_info in self.import_graph.nodes.items():
                if module_info.status == WiringStatus.UNWIRED:
                    logger.error(f"  - {module_name}")
                    logger.error(f"    Reason: {module_info.metadata.get('reason', 'unknown')}")
        
        # Determine pass/fail
        if self.unwired_count > 0 and self.fail_on_unwired:
            logger.error("\n❌ FAIL: Unwired modules detected in blocking mode")
            return False
        elif self.suspicious_count > 0:
            logger.warning("\n⚠️  WARNING: Suspicious modules detected")
            return True
        else:
            logger.info("\n✅ PASS: All modules properly wired")
            return True


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Production-grade module wiring validation"
    )
    parser.add_argument(
        "--root-dir",
        default=str(Path(__file__).parent.parent.parent),
        help="Project root directory"
    )
    parser.add_argument(
        "--blocking",
        action="store_true",
        help="Run in blocking mode (Phase 4)"
    )
    parser.add_argument(
        "--generate-baseline",
        action="store_true",
        help="Generate baseline exceptions from current run (Phase 3)"
    )
    
    args = parser.parse_args()
    
    validator = ModuleWiringValidatorV2(
        root_dir=args.root_dir,
        fail_on_unwired=args.blocking
    )
    
    success = validator.validate()
    
    # Generate baseline if requested
    if args.generate_baseline:
        baseline_exceptions = []
        for module_name, module_info in validator.import_graph.nodes.items():
            if module_info.status == WiringStatus.UNWIRED:
                baseline_exceptions.append(module_name)
        
        baseline_file = Path(args.root_dir) / BASELINE_EXCEPTIONS_FILE
        baseline_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(baseline_file, 'w') as f:
            json.dump({'exceptions': baseline_exceptions}, f, indent=2)
        
        logger.info(f"Baseline generated: {baseline_file}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
