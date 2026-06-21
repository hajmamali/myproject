"""
MAHOUN Determinism Crisis Suite
================================

Classification: CRITICAL GOVERNANCE ENFORCEMENT
Purpose: Verify deterministic execution guarantees

This test suite implements the most rigorous determinism validation
in MAHOUN's governance framework. ANY non-deterministic behavior is
classified as a CRITICAL FAILURE.

Test Categories:
1. Same Input 100x - Identical results every time
2. Concurrent Async - Parallel execution consistency
3. Retry Storm - Rapid repeated execution
4. Parallel Validation - Multi-validator consistency
5. Desktop/Enterprise Consistency - Dual-mode invariance
6. Proof Hash Consistency - Cryptographic stability
7. Derived Fact Ordering - Semantic ordering stability
8. Contradiction Stability - Conflict resolution determinism

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

__all__ = [
    "DeterminismTestBase",
    "DeterminismViolation",
    "DeterminismMetrics",
]

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
from enum import Enum


class DeterminismViolationType(str, Enum):
    """Types of determinism violations"""
    RESULT_DRIFT = "RESULT_DRIFT"
    CONFIDENCE_DRIFT = "CONFIDENCE_DRIFT"
    PROOF_HASH_DRIFT = "PROOF_HASH_DRIFT"
    DERIVED_FACTS_DRIFT = "DERIVED_FACTS_DRIFT"
    ORDERING_DRIFT = "ORDERING_DRIFT"
    CONTRADICTION_DRIFT = "CONTRADICTION_DRIFT"
    TIMING_DRIFT = "TIMING_DRIFT"
    METADATA_DRIFT = "METADATA_DRIFT"


@dataclass
class DeterminismViolation:
    """Record of a determinism violation"""
    violation_type: DeterminismViolationType
    iteration: int
    expected: Any
    actual: Any
    diff: Optional[str] = None
    context: Dict[str, Any] = None


@dataclass
class DeterminismMetrics:
    """Metrics for determinism testing"""
    total_iterations: int
    violations: List[DeterminismViolation]
    unique_results: int
    unique_hashes: int
    min_execution_time_ms: float
    max_execution_time_ms: float
    avg_execution_time_ms: float
    std_dev_execution_time_ms: float
    
    @property
    def is_deterministic(self) -> bool:
        """Check if execution was deterministic"""
        return len(self.violations) == 0 and self.unique_results == 1
    
    @property
    def determinism_score(self) -> float:
        """Calculate determinism score (0.0 to 1.0)"""
        if self.total_iterations == 0:
            return 0.0
        violation_rate = len(self.violations) / self.total_iterations
        return max(0.0, 1.0 - violation_rate)


class DeterminismTestBase:
    """Base class for determinism tests"""
    
    @staticmethod
    def compute_result_hash(result: Any) -> str:
        """
        Compute deterministic hash of result.
        
        CRITICAL: Only hash DETERMINISTIC fields. Exclude:
        - execution_time_ms (timing varies)
        - validation_timestamp (time-based)
        - audit_hash (includes timestamp)
        - correlation_id (unique per request)
        """
        import hashlib
        import json
        
        # Canonical serialization
        if hasattr(result, 'model_dump'):
            # Pydantic model
            data = result.model_dump()
        elif hasattr(result, '__dict__'):
            # Dataclass or object
            data = result.__dict__.copy()
        else:
            data = str(result)
        
        # Remove non-deterministic fields
        if isinstance(data, dict):
            # Fields that vary between executions
            non_deterministic_fields = [
                'execution_time_ms',
                'validation_timestamp', 
                'audit_hash',
                'correlation_id',
                'timestamp',  # Generic timestamp field
                'created_at',
                'updated_at',
            ]
            
            for field in non_deterministic_fields:
                data.pop(field, None)
        
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False, default=str)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    @staticmethod
    def compare_results(result1: Any, result2: Any) -> Optional[str]:
        """
        Compare two results for determinism.
        
        Returns:
            None if identical, diff string if different
        """
        import json
        
        # Convert to comparable format
        def to_comparable(obj):
            if hasattr(obj, 'model_dump'):
                return obj.model_dump()
            elif hasattr(obj, '__dict__'):
                return obj.__dict__
            else:
                return obj
        
        data1 = to_comparable(result1)
        data2 = to_comparable(result2)
        
        if data1 == data2:
            return None
        
        # Generate diff
        str1 = json.dumps(data1, sort_keys=True, indent=2)
        str2 = json.dumps(data2, sort_keys=True, indent=2)
        
        import difflib
        diff = difflib.unified_diff(
            str1.splitlines(),
            str2.splitlines(),
            lineterm='',
            fromfile='expected',
            tofile='actual'
        )
        return '\n'.join(diff)

