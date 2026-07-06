"""Enterprise Architecture Governance Platform."""

from .cache import FileCache, IncrementalParser
from .detectors import BareExceptDetector, RawDatabaseDetector, RawHttpDetector
from .duplicates import DuplicateAnalysis, DuplicateGroup
from .engine import GovernanceEngine
from .model import Detector, Finding, Severity
from .parallel_parser import ParallelParser
from .registry import DetectorRegistry
from .rule_engine import Rule, RuleEngine

__all__ = [
    "FileCache",
    "IncrementalParser",
    "GovernanceEngine",
    "Detector",
    "Finding",
    "Severity",
    "DuplicateAnalysis",
    "DuplicateGroup",
    "DetectorRegistry",
    "ParallelParser",
    "Rule",
    "RuleEngine",
    "RawDatabaseDetector",
    "RawHttpDetector",
    "BareExceptDetector",
]
