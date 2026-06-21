"""
Data Governance Module
======================

Comprehensive data governance framework for dataset versioning, bias analysis,
lineage tracking, and quality metrics.

This module provides:
- DVC-based dataset versioning with cryptographic hashes
- Bias detection and fairness metrics
- Complete data lineage tracking
- Schema enforcement and validation
- Data quality metrics and drift detection

Validates Requirements: Data Governance & Compliance
"""

from mahoun.governance.dataset_versioning import DatasetVersionManager
from mahoun.governance.bias_analysis import BiasAnalyzer, FairnessMetrics
from mahoun.governance.lineage_tracker import LineageTracker
from mahoun.governance.quality_metrics import DataQualityAnalyzer

__all__ = [
    "DatasetVersionManager",
    "BiasAnalyzer",
    "FairnessMetrics",
    "LineageTracker",
    "DataQualityAnalyzer",
]
