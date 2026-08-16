#!/usr/bin/env python3
"""
Module Classification Script
============================

Categorize modules by architectural role and purpose.

Provides intelligent classification of modules including:
- Core vs peripheral classification
- Layer identification (domain, infrastructure, presentation)
- Architectural pattern detection (service, repository, factory)
- Dependency level classification (high-level vs low-level)
- Integration status (wired, standalone, entrypoint)
- Purpose categorization (business logic, utilities, adapters)

Usage:
    python ci/analysis/module_classifier.py --directory mahoun/reasoning
    python ci/analysis/module_classifier.py --all --output classification.json
"""

import ast
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional
from dataclasses import dataclass, field
from enum import Enum
import argparse
import logging
import json
import re

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ArchitecturalLayer(Enum):
    """Architectural layer classification."""
    DOMAIN = "domain"  # Business logic, domain models
    INFRASTRUCTURE = "infrastructure"  # External dependencies, database
    PRESENTATION = "presentation"  # API, UI, CLI
    APPLICATION = "application"  # Use cases, orchestration
    UTILITIES = "utilities"  # Helper functions, common code
    ADAPTERS = "adapters"  # Integration with external systems
    UNKNOWN = "unknown"


class ArchitecturalPattern(Enum):
    """Architectural pattern classification."""
    SERVICE = "service"  # Business service
    REPOSITORY = "repository"  # Data access
    FACTORY = "factory"  # Object creation
    BUILDER = "builder"  # Complex object construction
    STRATEGY = "strategy"  # Algorithm selection
    OBSERVER = "observer"  # Event handling
    DECORATOR = "decorator"  # Function/class decoration
    SINGLETON = "singleton"  # Single instance
    PROTOTYPE = "prototype"  # Object cloning
    UNKNOWN = "unknown"


class DependencyLevel(Enum):
    """Dependency level classification."""
    HIGH_LEVEL = "high_level"  # Depends on many other modules
    LOW_LEVEL = "low_level"  # Few dependencies, foundational
    MEDIUM_LEVEL = "medium_level"  # Balanced dependencies
    UNKNOWN = "unknown"


@dataclass
class ModuleClassification:
    """Comprehensive classification for a module."""
    module: str
    layer: ArchitecturalLayer = ArchitecturalLayer.UNKNOWN
    pattern: ArchitecturalPattern = ArchitecturalPattern.UNKNOWN
    dependency_level: DependencyLevel = DependencyLevel.UNKNOWN
    is_core: bool = False
    is_peripheral: bool = False
    is_infrastructure: bool = False
    is_business_logic: bool = False
    is_utility: bool = False
    is_adapter: bool = False
    purpose_tags: Set[str] = field(default_factory=set)
    confidence: float = 0.0  # Classification confidence


class ModuleClassifier:
    """Classify modules by architectural role."""
    
    def __init__(self, root_dir: str):
        """
        Initialize classifier.
        
        Args:
            root_dir: Project root directory
        """
        self.root_dir = Path(root_dir)
        self.classifications: Dict[str, ModuleClassification] = {}
        
        # Classification heuristics
        self.domain_keywords = {
            'verdict', 'reasoning', 'evidence', 'legal', 'law', 'contract',
            'case', 'court', 'judgment', 'precedent', 'ruling', 'statute'
        }
        
        self.infrastructure_keywords = {
            'database', 'db', 'storage', 'cache', 'queue', 'network', 'api',
            'http', 'grpc', 'graphql', 'neo4j', 'redis', 'postgres'
        }
        
        self.presentation_keywords = {
            'api', 'router', 'controller', 'view', 'handler', 'endpoint',
            'cli', 'command', 'interface', 'ui', 'web'
        }
        
        self.application_keywords = {
            'orchestrator', 'coordinator', 'manager', 'service', 'workflow',
            'pipeline', 'process', 'job', 'task', 'executor'
        }
        
        self.utility_keywords = {
            'util', 'helper', 'common', 'shared', 'base', 'abstract',
            'constant', 'config', 'setting', 'type', 'model'
        }
        
        self.adapter_keywords = {
            'adapter', 'converter', 'mapper', 'transformer', 'serializer',
            'parser', 'formatter', 'bridge', 'gateway', 'client'
        }
    
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
    
    def classify_layer(self, module_name: str, imports: Set[str]) -> ArchitecturalLayer:
        """Classify module by architectural layer."""
        module_lower = module_name.lower()
        
        # Check module name and path
        if any(kw in module_lower for kw in self.domain_keywords):
            return ArchitecturalLayer.DOMAIN
        elif any(kw in module_lower for kw in self.infrastructure_keywords):
            return ArchitecturalLayer.INFRASTRUCTURE
        elif any(kw in module_lower for kw in self.presentation_keywords):
            return ArchitecturalLayer.PRESENTATION
        elif any(kw in module_lower for kw in self.application_keywords):
            return ArchitecturalLayer.APPLICATION
        elif any(kw in module_lower for kw in self.utility_keywords):
            return ArchitecturalLayer.UTILITIES
        elif any(kw in module_lower for kw in self.adapter_keywords):
            return ArchitecturalLayer.ADAPTERS
        
        # Check imports for layer hints
        import_lower = ' '.join(imports).lower()
        
        if any(kw in import_lower for kw in self.infrastructure_keywords):
            return ArchitecturalLayer.INFRASTRUCTURE
        elif any(kw in import_lower for kw in self.presentation_keywords):
            return ArchitecturalLayer.PRESENTATION
        
        return ArchitecturalLayer.UNKNOWN
    
    def classify_pattern(self, module_name: str, filepath: Path) -> ArchitecturalPattern:
        """Classify module by architectural pattern."""
        module_lower = module_name.lower()
        
        # Check module name for pattern hints
        if 'service' in module_lower:
            return ArchitecturalPattern.SERVICE
        elif 'repository' in module_lower or 'repo' in module_lower:
            return ArchitecturalPattern.REPOSITORY
        elif 'factory' in module_lower:
            return ArchitecturalPattern.FACTORY
        elif 'builder' in module_lower:
            return ArchitecturalPattern.BUILDER
        elif 'strategy' in module_lower:
            return ArchitecturalPattern.STRATEGY
        elif 'observer' in module_lower or 'listener' in module_lower:
            return ArchitecturalPattern.OBSERVER
        elif 'decorator' in module_lower or 'wrapper' in module_lower:
            return ArchitecturalPattern.DECORATOR
        
        # Check file content for pattern implementations
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read().lower()
            
            if 'singleton' in source or '_instance' in source:
                return ArchitecturalPattern.SINGLETON
            elif 'prototype' in source or 'clone' in source:
                return ArchitecturalPattern.PROTOTYPE
            elif 'registry' in source or 'register' in source:
                return ArchitecturalPattern.OBSERVER
                
        except Exception:
            pass
        
        return ArchitecturalPattern.UNKNOWN
    
    def classify_dependency_level(self, imports: Set[str]) -> DependencyLevel:
        """Classify module by dependency level."""
        import_count = len(imports)
        
        if import_count == 0:
            return DependencyLevel.LOW_LEVEL
        elif import_count < 5:
            return DependencyLevel.LOW_LEVEL
        elif import_count < 15:
            return DependencyLevel.MEDIUM_LEVEL
        else:
            return DependencyLevel.HIGH_LEVEL
    
    def classify_purpose(self, module_name: str, layer: ArchitecturalLayer) -> Set[str]:
        """Classify module purpose based on layer and name."""
        tags = set()
        module_lower = module_name.lower()
        
        # Core vs peripheral
        if any(core in module_lower for core in ['core', 'main', 'central', 'kernel']):
            tags.add('core')
        elif any(peripheral in module_lower for peripheral in ['extra', 'optional', 'addon', 'plugin']):
            tags.add('peripheral')
        
        # Business logic detection
        if layer == ArchitecturalLayer.DOMAIN:
            tags.add('business_logic')
        
        # Infrastructure detection
        if layer == ArchitecturalLayer.INFRASTRUCTURE:
            tags.add('infrastructure')
        
        # Utility detection
        if layer == ArchitecturalLayer.UTILITIES:
            tags.add('utility')
        
        # Adapter detection
        if layer == ArchitecturalLayer.ADAPTERS:
            tags.add('adapter')
        
        # Specific purpose tags
        if 'test' in module_lower:
            tags.add('testing')
        if 'config' in module_lower or 'setting' in module_lower:
            tags.add('configuration')
        if 'security' in module_lower or 'auth' in module_lower:
            tags.add('security')
        if 'monitoring' in module_lower or 'metric' in module_lower:
            tags.add('monitoring')
        if 'logging' in module_lower or 'log' in module_lower:
            tags.add('logging')
        
        return tags
    
    def classify_module(self, filepath: Path) -> Optional[ModuleClassification]:
        """Classify a single module."""
        try:
            # Get canonical module name
            relative = filepath.relative_to(self.root_dir)
            parts = list(relative.parts)
            
            if parts[-1].endswith('.py'):
                parts[-1] = parts[-1][:-3]
            
            if parts[-1] == '__init__':
                parts = parts[:-1]
            
            module_name = '.'.join(parts)
            
            # Extract imports
            imports = self.extract_imports(filepath)
            
            # Classify
            layer = self.classify_layer(module_name, imports)
            pattern = self.classify_pattern(module_name, filepath)
            dependency_level = self.classify_dependency_level(imports)
            purpose_tags = self.classify_purpose(module_name, layer)
            
            # Determine core/peripheral
            is_core = 'core' in purpose_tags
            is_peripheral = 'peripheral' in purpose_tags
            is_infrastructure = layer == ArchitecturalLayer.INFRASTRUCTURE
            is_business_logic = 'business_logic' in purpose_tags
            is_utility = 'utility' in purpose_tags
            is_adapter = 'adapter' in purpose_tags
            
            # Calculate confidence based on classification strength
            confidence = 0.5  # Base confidence
            if layer != ArchitecturalLayer.UNKNOWN:
                confidence += 0.2
            if pattern != ArchitecturalPattern.UNKNOWN:
                confidence += 0.2
            if purpose_tags:
                confidence += 0.1
            
            return ModuleClassification(
                module=module_name,
                layer=layer,
                pattern=pattern,
                dependency_level=dependency_level,
                is_core=is_core,
                is_peripheral=is_peripheral,
                is_infrastructure=is_infrastructure,
                is_business_logic=is_business_logic,
                is_utility=is_utility,
                is_adapter=is_adapter,
                purpose_tags=purpose_tags,
                confidence=min(confidence, 1.0)
            )
            
        except Exception as e:
            logger.warning(f"Failed to classify {filepath}: {e}")
            return None
    
    def analyze_directory(self, directory: str) -> None:
        """
        Classify all modules in a directory.
        
        Args:
            directory: Directory path relative to root
        """
        dir_path = self.root_dir / directory
        
        if not dir_path.exists():
            logger.warning(f"Directory not found: {dir_path}")
            return
        
        logger.info(f"Classifying modules in: {directory}")
        
        for filepath in dir_path.rglob("*.py"):
            # Skip test files and __pycache__
            if "test" in filepath.name or "__pycache__" in filepath.parts:
                continue
            
            classification = self.classify_module(filepath)
            
            if classification:
                self.classifications[classification.module] = classification
        
        logger.info(f"Classified {len(self.classifications)} modules")
    
    def get_by_layer(self, layer: ArchitecturalLayer) -> List[str]:
        """Get modules classified to a specific layer."""
        return [
            module for module, cls in self.classifications.items()
            if cls.layer == layer
        ]
    
    def get_by_pattern(self, pattern: ArchitecturalPattern) -> List[str]:
        """Get modules classified to a specific pattern."""
        return [
            module for module, cls in self.classifications.items()
            if cls.pattern == pattern
        ]
    
    def get_core_modules(self) -> List[str]:
        """Get core modules."""
        return [
            module for module, cls in self.classifications.items()
            if cls.is_core
        ]
    
    def get_business_logic_modules(self) -> List[str]:
        """Get business logic modules."""
        return [
            module for module, cls in self.classifications.items()
            if cls.is_business_logic
        ]
    
    def export_json(self, output_path: str) -> None:
        """Export classification to JSON."""
        export_data = {
            "total_modules": len(self.classifications),
            "layer_distribution": {
                layer.value: len(self.get_by_layer(layer))
                for layer in ArchitecturalLayer
            },
            "pattern_distribution": {
                pattern.value: len(self.get_by_pattern(pattern))
                for pattern in ArchitecturalPattern
            },
            "core_modules": len(self.get_core_modules()),
            "business_logic_modules": len(self.get_business_logic_modules()),
            "modules": {
                module: {
                    "layer": cls.layer.value,
                    "pattern": cls.pattern.value,
                    "dependency_level": cls.dependency_level.value,
                    "is_core": cls.is_core,
                    "is_peripheral": cls.is_peripheral,
                    "is_infrastructure": cls.is_infrastructure,
                    "is_business_logic": cls.is_business_logic,
                    "is_utility": cls.is_utility,
                    "is_adapter": cls.is_adapter,
                    "purpose_tags": list(cls.purpose_tags),
                    "confidence": cls.confidence,
                }
                for module, cls in self.classifications.items()
            }
        }
        
        output_file = Path(output_path)
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        logger.info(f"Classification exported to: {output_path}")
    
    def print_analysis(self) -> None:
        """Print human-readable analysis."""
        print("\n" + "=" * 60)
        print("MODULE CLASSIFICATION")
        print("=" * 60)
        print(f"Total modules classified: {len(self.classifications)}")
        
        # Layer distribution
        print("\nLayer distribution:")
        for layer in ArchitecturalLayer:
            count = len(self.get_by_layer(layer))
            if count > 0:
                print(f"  {layer.value}: {count}")
        
        # Pattern distribution
        print("\nPattern distribution:")
        for pattern in ArchitecturalPattern:
            count = len(self.get_by_pattern(pattern))
            if count > 0:
                print(f"  {pattern.value}: {count}")
        
        # Core and business logic
        print(f"\nCore modules: {len(self.get_core_modules())}")
        print(f"Business logic modules: {len(self.get_business_logic_modules())}")
        
        # Show examples by layer
        print("\nExamples by layer:")
        for layer in ArchitecturalLayer:
            modules = self.get_by_layer(layer)[:3]
            if modules:
                print(f"  {layer.value}:")
                for module in modules:
                    cls = self.classifications[module]
                    print(f"    - {module} ({cls.confidence:.2f} confidence)")
        
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Module classification analysis"
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
    
    classifier = ModuleClassifier(args.root_dir)
    
    if args.directory:
        classifier.analyze_directory(args.directory)
    elif args.all:
        key_directories = [
            "mahoun/reasoning",
            "mahoun/pipelines/ingestion",
            "mahoun/guardrails",
            "mahoun/graph",
        ]
        
        for directory in key_directories:
            classifier.analyze_directory(directory)
    else:
        logger.error("Must specify --directory or --all")
        sys.exit(1)
    
    if args.output:
        classifier.export_json(args.output)
    
    classifier.print_analysis()


if __name__ == "__main__":
    main()
