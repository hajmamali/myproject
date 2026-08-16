#!/usr/bin/env python3
"""
Production Reachability Analyzer
================================

Path analysis from production entry points to determine module integration.

Provides detailed analysis of which modules are reachable from production
entry points including:
- Reachability paths from each entry point
- Unreachable modules identification
- Critical path analysis
- Module distance from entry points
- Integration depth analysis
- Bottleneck identification

Usage:
    python ci/analysis/production_reachability.py --entrypoint api/main.py
    python ci/analysis/production_reachability.py --all-entrypoints --output reachability.json
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
from dataclasses import dataclass, field
from collections import defaultdict, deque
import argparse
import logging
import json

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class ReachabilityInfo:
    """Information about module reachability."""
    module: str
    is_reachable: bool = False
    reachable_from: Set[str] = field(default_factory=set)
    distance_from_entrypoints: Dict[str, int] = field(default_factory=dict)
    shortest_path: Optional[List[str]] = None
    integration_depth: int = 0
    is_bottleneck: bool = False
    bottleneck_for: Set[str] = field(default_factory=set)


class ProductionReachabilityAnalyzer:
    """Analyze production reachability from entry points."""
    
    def __init__(self, root_dir: str):
        """
        Initialize analyzer.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.reverse_dependencies: Dict[str, Set[str]] = defaultdict(set)
        self.entrypoints: Set[str] = set()
        self.reachability: Dict[str, ReachabilityInfo] = {}
        
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
        
        # Build dependency relationships
        for module_name, imports in module_imports.items():
            for imported in imports:
                # Normalize import name
                if imported.startswith('mahoun.'):
                    imported = imported.replace('mahoun.', '')
                
                # Only track dependencies within our analyzed modules
                if imported in module_imports:
                    self.dependencies[module_name].add(imported)
                    self.reverse_dependencies[imported].add(module_name)
        
        logger.info(f"Built graph with {len(self.dependencies)} modules")
    
    def add_entrypoint(self, entrypoint_path: str) -> None:
        """
        Add a production entry point.
        
        Args:
            entrypoint_path: Path to entry point file (relative to root)
        """
        entrypoint_file = self.root_dir / entrypoint_path
        
        if not entrypoint_file.exists():
            logger.warning(f"Entrypoint not found: {entrypoint_path}")
            return
        
        # Get canonical module name
        try:
            relative = entrypoint_file.relative_to(self.root_dir)
            parts = list(relative.parts)
            
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]
            
            if parts[-1] == '__init__':
                parts = parts[:-1]
            
            module_name = '.'.join(parts)
        except ValueError:
            return
        
        self.entrypoints.add(module_name)
        logger.info(f"Added entrypoint: {module_name}")
    
    def bfs_shortest_path(self, start: str, target: str) -> Optional[List[str]]:
        """
        Find shortest path from start to target using BFS.
        
        Args:
            start: Starting module
            target: Target module
            
        Returns:
            List of module names in the path, or None if no path exists
        """
        if start == target:
            return [start]
        
        queue = deque([(start, [start])])
        visited = {start}
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in self.dependencies[current]:
                if neighbor == target:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def analyze_reachability(self) -> None:
        """Analyze reachability from all entry points."""
        logger.info("Analyzing production reachability...")
        
        # Initialize reachability info for all modules
        all_modules = set(self.dependencies.keys()) | set(self.reverse_dependencies.keys())
        
        for module in all_modules:
            self.reachability[module] = ReachabilityInfo(module=module)
        
        # Analyze reachability from each entry point
        for entrypoint in self.entrypoints:
            if entrypoint not in all_modules:
                logger.warning(f"Entrypoint {entrypoint} not in dependency graph")
                continue
            
            # BFS from entrypoint
            queue = deque([(entrypoint, 0)])
            visited = {entrypoint}
            
            while queue:
                current, distance = queue.popleft()
                
                # Update reachability info
                if current in self.reachability:
                    self.reachability[current].is_reachable = True
                    self.reachability[current].reachable_from.add(entrypoint)
                    self.reachability[current].distance_from_entrypoints[entrypoint] = distance
                    
                    # Update integration depth (max distance)
                    self.reachability[current].integration_depth = max(
                        self.reachability[current].integration_depth,
                        distance
                    )
                
                # Explore dependencies
                for neighbor in self.dependencies[current]:
                    if neighbor not in visited:
                        visited.add(neighbor)
                        queue.append((neighbor, distance + 1))
        
        # Find shortest paths for reachable modules
        for module_name, info in self.reachability.items():
            if info.is_reachable and info.reachable_from:
                # Find shortest path from any entry point
                shortest = None
                shortest_length = float('inf')
                
                for entrypoint in info.reachable_from:
                    path = self.bfs_shortest_path(entrypoint, module_name)
                    if path and len(path) < shortest_length:
                        shortest = path
                        shortest_length = len(path)
                
                info.shortest_path = shortest
        
        # Identify bottlenecks (modules that many paths go through)
        self._identify_bottlenecks()
        
        logger.info("Reachability analysis complete")
    
    def _identify_bottlenecks(self) -> None:
        """Identify bottleneck modules."""
        logger.info("Identifying bottlenecks...")
        
        # Count how many shortest paths go through each module
        path_counts = defaultdict(int)
        
        for module_name, info in self.reachability.items():
            if info.shortest_path and len(info.shortest_path) > 1:
                for module in info.shortest_path[1:-1]:  # Exclude endpoints
                    path_counts[module] += 1
        
        # Mark modules with high path counts as bottlenecks
        avg_count = sum(path_counts.values()) / len(path_counts) if path_counts else 0
        
        for module, count in path_counts.items():
            if count > avg_count * 2:  # More than 2x average
                if module in self.reachability:
                    self.reachability[module].is_bottleneck = True
                    self.reachability[module].bottleneck_for = set()
                    
                    # Find which modules this is a bottleneck for
                    for other_module, other_info in self.reachability.items():
                        if other_info.shortest_path and module in other_info.shortest_path:
                            self.reachability[module].bottleneck_for.add(other_module)
        
        logger.info(f"Identified {sum(1 for info in self.reachability.values() if info.is_bottleneck)} bottlenecks")
    
    def get_unreachable_modules(self) -> List[str]:
        """Get list of unreachable modules."""
        return [
            module for module, info in self.reachability.items()
            if not info.is_reachable
        ]
    
    def get_reachable_modules(self) -> List[str]:
        """Get list of reachable modules."""
        return [
            module for module, info in self.reachability.items()
            if info.is_reachable
        ]
    
    def get_bottlenecks(self) -> List[str]:
        """Get list of bottleneck modules."""
        return [
            module for module, info in self.reachability.items()
            if info.is_bottleneck
        ]
    
    def export_json(self, output_path: str) -> None:
        """Export reachability analysis to JSON."""
        export_data = {
            "entrypoints": list(self.entrypoints),
            "total_modules": len(self.reachability),
            "reachable_count": len(self.get_reachable_modules()),
            "unreachable_count": len(self.get_unreachable_modules()),
            "bottleneck_count": len(self.get_bottlenecks()),
            "modules": {
                module: {
                    "is_reachable": info.is_reachable,
                    "reachable_from": list(info.reachable_from),
                    "distance_from_entrypoints": info.distance_from_entrypoints,
                    "shortest_path": info.shortest_path,
                    "integration_depth": info.integration_depth,
                    "is_bottleneck": info.is_bottleneck,
                    "bottleneck_for": list(info.bottleneck_for),
                }
                for module, info in self.reachability.items()
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Reachability analysis exported to: {output_path}")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("PRODUCTION REACHABILITY ANALYSIS")
        print("=" * 60)
        print(f"Entry points: {len(self.entrypoints)}")
        print(f"Total modules: {len(self.reachability)}")
        print(f"Reachable modules: {len(self.get_reachable_modules())}")
        print(f"Unreachable modules: {len(self.get_unreachable_modules())}")
        print(f"Bottleneck modules: {len(self.get_bottlenecks())}")
        
        if self.entrypoints:
            print(f"\nEntry points:")
            for entrypoint in self.entrypoints:
                print(f"  - {entrypoint}")
        
        # Show unreachable modules
        unreachable = self.get_unreachable_modules()
        if unreachable:
            print(f"\nUnreachable modules ({len(unreachable)}):")
            for module in unreachable[:10]:  # Show first 10
                info = self.reachability[module]
                print(f"  - {module}")
            if len(unreachable) > 10:
                print(f"  ... and {len(unreachable) - 10} more")
        
        # Show bottlenecks
        bottlenecks = self.get_bottlenecks()
        if bottlenecks:
            print(f"\nBottleneck modules ({len(bottlenecks)}):")
            for module in bottlenecks:
                info = self.reachability[module]
                print(f"  - {module} (bottleneck for {len(info.bottleneck_for)} modules)")
        
        # Show integration depth distribution
        depths = defaultdict(int)
        for info in self.reachability.values():
            if info.is_reachable:
                depths[info.integration_depth] += 1
        
        print(f"\nIntegration depth distribution:")
        for depth in sorted(depths.keys()):
            print(f"  Depth {depth}: {depths[depth]} modules")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Production reachability analysis"
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
        "--entrypoint",
        action="append",
        help="Add production entry point (can be used multiple times)"
    )
    parser.add_argument(
        "--default-entrypoints",
        action="store_true",
        help="Use default production entry points"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file path"
    )
    
    args = parser.parse_args()
    
    analyzer = ProductionReachabilityAnalyzer(args.root_dir)
    
    # Build dependency graph
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
    
    # Add entry points
    if args.default_entrypoints:
        default_entrypoints = [
            "api/main.py",
            "api/routers/__init__.py",
            "orchestrator/bootstrap.py",
            "switchboard.py",
        ]
        
        for entrypoint in default_entrypoints:
            analyzer.add_entrypoint(entrypoint)
    
    if args.entrypoint:
        for entrypoint in args.entrypoint:
            analyzer.add_entrypoint(entrypoint)
    
    if not analyzer.entrypoints:
        logger.error("Must specify entry points (--entrypoint or --default-entrypoints)")
        sys.exit(1)
    
    # Analyze reachability
    analyzer.analyze_reachability()
    
    if args.output:
        analyzer.export_json(args.output)
    
    analyzer.print_analysis()


if __name__ == "__main__":
    main()
