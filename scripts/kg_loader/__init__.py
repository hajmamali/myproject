"""
Ultra-Advanced Knowledge Graph Loader
====================================

Enterprise-grade KG loading system using existing MahouN batch infrastructure.

Components:
- data_source.py: Real legal data source (integrates with build_legal_kg.py)
- handlers.py: Task handlers for Laws, Articles, Citations
- config.py: KG-specific configuration
- checkpoint.py: Checkpoint/resume support
- metrics.py: KG-specific metrics
- cli.py: CLI interface

Architecture:
- Reuses mahoun.graph.batch (Worker, Queue, BatchProcessor)
- Reuses mahoun.metrics (MetricsCollector, Prometheus)
- Zero duplication, maximum modularity
"""

__version__ = "1.0.0"

from .config import KGLoaderConfig
from .data_source import RealLegalDataSource

__all__ = [
    'KGLoaderConfig',
    'RealLegalDataSource',
]
