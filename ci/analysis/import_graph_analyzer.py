#!/usr/bin/env python3
"""
Import Graph Analyzer
=====================

Dependency graph visualization and analysis for architectural insights.

Provides detailed analysis of module dependencies including:
- Dependency graph visualization (DOT format for Graphviz)
- Circular dependency detection
- Dependency depth analysis
- Critical path identification
- Module coupling metrics
- Dependency clusters detection

Usage:
    python ci/analysis/import_graph_analyzer.py --directory mahoun/reasoning
    python ci/analysis/import_graph_analyzer.py --all --output graph.dot
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import argparse
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class DependencyInfo:
    """Information about module dependencies."""
    module: str
    depends_on: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)
    depth: int = 0
    is_circular: bool = False
    circular_with: Set[str] = field(default_factory=set)


class ImportGraphAnalyzer:
    """Analyze and visualize import dependency graphs."""
    
    def __init__(self, root_dir: str):
        """
        Initialize analyzer.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.dependencies: Dict[str, DependencyInfo] = {}
        
    def extract_imports(self, filepath: Path) -> Set[str]:
        """Extract import statements from a Python file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            
            tree = ast.parse(source)
            imports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.add(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.add(node.module)
            
            return imports
            
        except Exception as e:
            logger.warning(f"Failed to extract imports from {filepath}: {e}")
            return set()
    
    def build_dependency_graph(self, directory: str) -> None:
        """
        Build dependency graph for a directory.
        
        Args:
            directory: Directory path relative to root
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return
        
        logger.info(f"Building dependency graph for: {directory}")
        
        # First pass: collect all modules and their imports
        module_imports = {}
        
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
            
            imports = self.extract_imports(filepath)
            
            # Filter to local imports only
            local_imports = {imp for imp in imports if imp.startswith('mahoun')}
            
            module_imports[module_name] = local_imports
            
            # Initialize dependency info
            if module_name not in self.dependencies:
                self.dependencies[module_name] = DependencyInfo(module=module_name)
        
        # Second pass: build dependency relationships
        for module_name, imports in module_imports.items():
            for imported in imports:
                # Normalize import name
                if imported.startswith('mahoun.'):
                    imported = imported.replace('mahoun.', '')
                
                # Only track dependencies within our analyzed modules
                if imported in module_imports:
                    self.dependencies[module_name].depends_on.add(imported)
                    self.dependencies[imported].dependents.add(module_name)
        
        logger.info(f"Built graph with {len(self.dependencies)} modules")
    
    def detect_circular_dependencies(self) -> List[Tuple[str, ...]]:
        """
        Detect circular dependencies using DFS.
        
        Returns:
            List of circular dependency chains
        """
        logger.info("Detecting circular dependencies...")
        
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(module: str, path: List[str]) -> None:
            if module in rec_stack:
                # Found a cycle
                cycle_start = path.index(module)
                cycle = tuple(path[cycle_start:] + [module])
                if cycle not in cycles:
                    cycles.append(cycle)
                return
            
            if module in visited:
                return
            
            visited.add(module)
            rec_stack.add(module)
            
            if module in self.dependencies:
                for dependent in self.dependencies[module].depends_on:
                    dfs(dependent, path + [module])
            
            rec_stack.remove(module)
        
        for module in self.dependencies:
            dfs(module, [])
        
        # Mark circular dependencies
        for cycle in cycles:
            for module in cycle:
                if module in self.dependencies:
                    self.dependencies[module].is_circular = True
                    self.dependencies[module].circular_with.update(cycle)
        
        logger.info(f"Found {len(cycles)} circular dependencies")
        return cycles
    
    def calculate_dependency_depth(self) -> None:
        """Calculate dependency depth for each module using BFS."""
        logger.info("Calculating dependency depths...")
        
        # Find root modules (no dependents)
        roots = [
            module for module, info in self.dependencies.items()
            if len(info.dependents) == 0
        ]
        
        # BFS from roots to calculate depth
        for root in roots:
            queue = deque([(root, 0)])
            visited = {root}
            
            while queue:
                module, depth = queue.popleft()
                
                if module in self.dependencies:
                    self.dependencies[module].depth = max(
                        self.dependencies[module].depth,
                        depth
                    )
                    
                    for dependent in self.dependencies[module].depends_on:
                        if dependent not in visited:
                            visited.add(dependent)
                            queue.append((dependent, depth + 1))
    
    def calculate_coupling_metrics(self) -> Dict[str, Dict[str, float]]:
        """
        Calculate coupling metrics for each module.
        
        Returns:
            Dict mapping module names to coupling metrics
        """
        metrics = {}
        
        for module_name, info in self.dependencies.items():
            # Afferent coupling (number of modules that depend on this one)
            ca = len(info.dependents)
            
            # Efferent coupling (number of modules this one depends on)
            ce = len(info.depends_on)
            
            # Instability (I = Ce / (Ca + Ce))
            total = ca + ce
            instability = ce / total if total > 0 else 0
            
            metrics[module_name] = {
                'afferent_coupling': ca,
                'efferent_coupling': ce,
                'instability': instability,
                'total_dependencies': total
            }
        
        return metrics
    
    def find_critical_path(self) -> List[str]:
        """
        Find the longest dependency path (critical path).
        
        Returns:
            List of module names in the critical path
        """
        logger.info("Finding critical path...")
        
        if not self.dependencies:
            return []
        
        # Find module with maximum depth
        max_depth_module = max(
            self.dependencies.items(),
            key=lambda x: x[1].depth
        )
        
        # Trace back from this module to find the path
        path = []
        current = max_depth_module[0]
        
        while current:
            path.append(current)
            
            # Find dependent with next lower depth
            next_module = None
            for dependent in self.dependencies[current].dependents:
                if dependent in self.dependencies:
                    if self.dependencies[dependent].depth == self.dependencies[current].depth - 1:
                        next_module = dependent
                        break
            
            current = next_module
        
        path.reverse()
        logger.info(f"Critical path length: {len(path)}")
        return path
    
    def export_dot_graph(self, output_path: str) -> None:
        """
        Export dependency graph in DOT format for Graphviz.
        
        Args:
            output_path: Output file path for DOT file
        """
        logger.info(f"Exporting DOT graph to: {output_path}")
        
        with open(output_path, 'w') as f:
            f.write("digraph DependencyGraph {\n")
            f.write("  rankdir=LR;\n")
            f.write("  node [shape=box];\n")
            f.write("\n")
            
            # Add nodes
            for module_name, info in self.dependencies.items():
                label = module_name.split('.')[-1]  # Use short name
                color = "red" if info.is_circular else "black"
                f.write(f'  "{module_name}" [label="{label}", color={color}];\n')
            
            f.write("\n")
            
            # Add edges
            for module_name, info in self.dependencies.items():
                for dependent in info.depends_on:
                    f.write(f'  "{module_name}" -> "{dependent}";\n')
            
            f.write("}\n")
        
        logger.info("DOT graph exported successfully")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("IMPORT GRAPH ANALYSIS")
        print("=" * 60)
        print(f"Total modules: {len(self.dependencies)}")
        
        # Circular dependencies
        circular_count = sum(1 for info in self.dependencies.values() if info.is_circular)
        print(f"Circular dependencies: {circular_count}")
        
        if circular_count > 0:
            print("\nCircular dependency chains:")
            for module_name, info in self.dependencies.items():
                if info.is_circular:
                    print(f"  {module_name} <-> {', '.join(info.circular_with)}")
        
        # Dependency depth
        max_depth = max((info.depth for info in self.dependencies.values()), default=0)
        print(f"\nMaximum dependency depth: {max_depth}")
        
        # Coupling metrics
        metrics = self.calculate_coupling_metrics()
        
        print("\nMost unstable modules (high efferent coupling):")
        sorted_by_instability = sorted(
            metrics.items(),
            key=lambda x: x[1]['instability'],
            reverse=True
        )[:5]
        
        for module, metric in sorted_by_instability:
            print(f"  {metric['instability']:.2f} - {module}")
        
        # Critical path
        critical_path = self.find_critical_path()
        if critical_path:
            print(f"\nCritical path ({len(critical_path)} modules):")
            for i, module in enumerate(critical_path):
                print(f"  {i+1}. {module}")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import graph analysis and visualization"
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
        help="Output DOT file path for Graphviz"
    )
    
    args = parser.parse_args()
    
    analyzer = ImportGraphAnalyzer(args.root_dir)
    
    if args.directory:
        analyzer.build_dependency_graph(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            analyzer.build_dependency_graph(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    analyzer.detect_circular_dependencies()
    analyzer.calculate_dependency_depth()
    
    if args.output:
        analyzer.export_dot_graph(args.output)
    
    analyzer.print_analysis()


if __name__ == "__main__":
    main()
