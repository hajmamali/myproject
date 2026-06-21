"""
MAHOUN Determinism Test 1: Same Input 100x
===========================================

Classification: CRITICAL DETERMINISM ENFORCEMENT
Purpose: Verify identical results for identical inputs

This test executes the SAME reasoning request 100 times and verifies
that EVERY execution produces IDENTICAL results.

Invariants Tested:
- DET-G1: Same input → Same output (always)
- DET-G2: Same proof hash (cryptographic stability)
- DET-G3: Same derived facts (semantic stability)
- DET-G4: Same execution path (no randomness)

ANY deviation is a CRITICAL FAILURE.

Author: MahouN AEO Governance Council
Version: 1.0.0
"""

import pytest
import asyncio
import hashlib
from typing import List, Dict, Any
from datetime import datetime, timezone

from mahoun.reasoning.unified_reasoning_service import (
    UnifiedReasoningService,
    ReasoningRequest,
    ReasoningResponse,
    ReasoningTask,
    ReasoningMode
)
from mahoun.core.fortress_validator import FortressValidator
from tests.determinism import (
    DeterminismTestBase,
    DeterminismViolation,
    DeterminismMetrics,
    DeterminismViolationType
)


class TestSameInput100x(DeterminismTestBase):
    """Test determinism with 100 identical executions"""
    
    @pytest.mark.asyncio
    async def test_symbolic_reasoning_100x_determinism(self):
        """
        Test 1.1: Symbolic reasoning must be 100% deterministic
        
        Execute same symbolic reasoning 100 times, verify:
        - Identical result
        - Identical confidence
        - Identical proof_tree hash
        - Identical derived_facts
        - Identical audit_hash
        """
        # Setup
        service = UnifiedReasoningService(enable_neural=False)
        
        # Create deterministic request
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="What can we infer?",
            facts=[
                "mortal(socrates)",
                "human(socrates)",
            ],
            rules=[
                "mortal(X) :- human(X)",
            ],
            mode=ReasoningMode.SYMBOLIC,
            max_depth=10,
            return_proof=True
        )
        
        # Execute 100 times
        results: List[ReasoningResponse] = []
        execution_times: List[float] = []
        
        for i in range(100):
            start = asyncio.get_event_loop().time()
            response = await service.reason(request)
            end = asyncio.get_event_loop().time()
            
            results.append(response)
            execution_times.append((end - start) * 1000)  # ms
        
        # Analyze determinism
        metrics = self._analyze_determinism(results, execution_times)
        
        # Assert determinism
        assert metrics.is_deterministic, (
            f"DETERMINISM VIOLATION: Symbolic reasoning produced "
            f"{metrics.unique_results} unique results (expected 1)\n"
            f"Violations: {len(metrics.violations)}\n"
            f"Score: {metrics.determinism_score:.2%}\n"
            f"Details: {self._format_violations(metrics.violations[:5])}"
        )
        
        # Verify cryptographic stability
        assert metrics.unique_hashes == 1, (
            f"HASH DRIFT: {metrics.unique_hashes} unique hashes detected"
        )
        
        # Log success
        print(f"\n✅ DETERMINISM VERIFIED: 100/100 identical results")
        print(f"   Execution time: {metrics.avg_execution_time_ms:.2f}ms "
              f"(±{metrics.std_dev_execution_time_ms:.2f}ms)")
    
    @pytest.mark.asyncio
    async def test_hybrid_reasoning_100x_determinism(self):
        """
        Test 1.2: Hybrid reasoning determinism (if neural disabled)
        
        Hybrid mode with neural disabled should be deterministic.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.BACKWARD_PROOF,
            query="Prove: mortal(socrates)",
            facts=["human(socrates)"],
            rules=["mortal(X) :- human(X)"],
            mode=ReasoningMode.HYBRID,  # Will fallback to symbolic
            return_proof=True
        )
        
        # Execute 100 times
        results = []
        for _ in range(100):
            response = await service.reason(request)
            results.append(response)
        
        # Analyze
        metrics = self._analyze_determinism(results, [0.0] * 100)
        
        # Assert
        assert metrics.is_deterministic, (
            f"HYBRID DETERMINISM VIOLATION: {metrics.unique_results} unique results"
        )
        
        print(f"✅ HYBRID DETERMINISM VERIFIED: 100/100 identical")
    
    @pytest.mark.asyncio
    async def test_proof_tree_hash_stability_100x(self):
        """
        Test 1.3: Proof tree hash must be cryptographically stable
        
        The proof_tree hash must be IDENTICAL across all executions.
        Any drift indicates non-deterministic proof generation.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Infer all facts",
            facts=[
                "parent(tom, bob)",
                "parent(bob, ann)",
            ],
            rules=[
                "ancestor(X, Y) :- parent(X, Y)",
                "ancestor(X, Z) :- parent(X, Y), ancestor(Y, Z)",
            ],
            mode=ReasoningMode.SYMBOLIC,
            return_proof=True
        )
        
        # Execute 100 times and collect proof hashes
        proof_hashes = []
        for _ in range(100):
            response = await service.reason(request)
            
            # Compute proof tree hash
            if response.proof_tree:
                proof_hash = self._compute_proof_tree_hash(response.proof_tree)
                proof_hashes.append(proof_hash)
        
        # Verify all hashes identical
        unique_hashes = set(proof_hashes)
        
        assert len(unique_hashes) == 1, (
            f"PROOF HASH DRIFT: {len(unique_hashes)} unique proof hashes detected\n"
            f"Hashes: {list(unique_hashes)[:5]}"
        )
        
        print(f"✅ PROOF HASH STABILITY VERIFIED: 100/100 identical hashes")
    
    @pytest.mark.asyncio
    async def test_derived_facts_ordering_100x(self):
        """
        Test 1.4: Derived facts ordering must be deterministic
        
        The order of derived_facts must be IDENTICAL across executions.
        Non-deterministic ordering indicates unstable inference.
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Derive all facts",
            facts=[
                "a(1)", "a(2)", "a(3)",
                "b(1)", "b(2)", "b(3)",
            ],
            rules=[
                "c(X) :- a(X), b(X)",
            ],
            mode=ReasoningMode.SYMBOLIC,
            return_proof=True
        )
        
        # Execute 100 times
        derived_facts_sequences = []
        for _ in range(100):
            response = await service.reason(request)
            derived_facts_sequences.append(tuple(response.derived_facts))
        
        # Verify all sequences identical
        unique_sequences = set(derived_facts_sequences)
        
        assert len(unique_sequences) == 1, (
            f"DERIVED FACTS ORDERING DRIFT: {len(unique_sequences)} unique orderings\n"
            f"Sequences: {list(unique_sequences)[:3]}"
        )
        
        print(f"✅ DERIVED FACTS ORDERING VERIFIED: 100/100 identical")
    
    @pytest.mark.asyncio
    async def test_confidence_score_stability_100x(self):
        """
        Test 1.5: Confidence scores must be numerically stable
        
        Confidence scores must be IDENTICAL (no floating-point drift).
        """
        service = UnifiedReasoningService(enable_neural=False)
        
        request = ReasoningRequest(
            task=ReasoningTask.FORWARD_INFERENCE,
            query="Test confidence",
            facts=["test(1)"],
            rules=["result(X) :- test(X)"],
            mode=ReasoningMode.SYMBOLIC
        )
        
        # Execute 100 times
        confidences = []
        for _ in range(100):
            response = await service.reason(request)
            confidences.append(response.confidence)
        
        # Verify all confidences identical
        unique_confidences = set(confidences)
        
        assert len(unique_confidences) == 1, (
            f"CONFIDENCE DRIFT: {len(unique_confidences)} unique values\n"
            f"Values: {sorted(unique_confidences)}"
        )
        
        print(f"✅ CONFIDENCE STABILITY VERIFIED: 100/100 identical")
    
    @pytest.mark.asyncio
    async def test_fortress_validation_determinism_100x(self):
        """
        Test 1.6: FortressValidator must produce deterministic audit hashes
        
        The audit_hash must be IDENTICAL for identical responses.
        """
        validator = FortressValidator(strict_mode=False)
        
        # Create identical response (contract already disabled in conftest.py)
        from mahoun.reasoning.unified_reasoning_service import ReasoningResponse, ReasoningMode
        
        response = ReasoningResponse(
            success=True,
            result="Tax exemption applies",
            confidence=0.92,
            reasoning_mode=ReasoningMode.SYMBOLIC,
            execution_time_ms=150.0,
            proof_tree={"depth": 5, "nodes": 10},
            derived_facts=["fact1", "fact2", "fact3"],
            fortress_validated=False,
            audit_hash=None,
            validation_timestamp=None,
            correlation_id=None,
            metadata={"agreement_score": 0.90}
        )
        
        # Validate 100 times with SAME correlation_id for deterministic hashing
        audit_hashes_fixed = []
        for _ in range(100):
            import copy
            response_copy = copy.deepcopy(response)
            result = await validator.validate(response_copy, correlation_id="baseline")
            audit_hashes_fixed.append(response_copy.audit_hash)
        
        unique_hashes = set(audit_hashes_fixed)
        
        assert len(unique_hashes) == 1, (
            f"AUDIT HASH DRIFT: {len(unique_hashes)} unique hashes\n"
            f"Hashes: {list(unique_hashes)[:5]}"
        )
        
        print(f"✅ FORTRESS VALIDATION DETERMINISM VERIFIED: 100/100 identical")
    
    # ========================================================================
    # HELPER METHODS
    # ========================================================================
    
    def _analyze_determinism(
        self,
        results: List[ReasoningResponse],
        execution_times: List[float]
    ) -> DeterminismMetrics:
        """Analyze results for determinism violations"""
        
        if not results:
            return DeterminismMetrics(
                total_iterations=0,
                violations=[],
                unique_results=0,
                unique_hashes=0,
                min_execution_time_ms=0.0,
                max_execution_time_ms=0.0,
                avg_execution_time_ms=0.0,
                std_dev_execution_time_ms=0.0
            )
        
        # Baseline (first result)
        baseline = results[0]
        baseline_hash = self.compute_result_hash(baseline)
        
        # Collect violations
        violations = []
        result_hashes = set()
        
        for i, result in enumerate(results):
            result_hash = self.compute_result_hash(result)
            result_hashes.add(result_hash)
            
            # Check result drift
            if result.result != baseline.result:
                violations.append(DeterminismViolation(
                    violation_type=DeterminismViolationType.RESULT_DRIFT,
                    iteration=i,
                    expected=baseline.result,
                    actual=result.result,
                    diff=self.compare_results(baseline, result)
                ))
            
            # Check confidence drift
            if result.confidence != baseline.confidence:
                violations.append(DeterminismViolation(
                    violation_type=DeterminismViolationType.CONFIDENCE_DRIFT,
                    iteration=i,
                    expected=baseline.confidence,
                    actual=result.confidence
                ))
            
            # Check derived facts drift
            if result.derived_facts != baseline.derived_facts:
                violations.append(DeterminismViolation(
                    violation_type=DeterminismViolationType.DERIVED_FACTS_DRIFT,
                    iteration=i,
                    expected=baseline.derived_facts,
                    actual=result.derived_facts
                ))
        
        # Compute statistics
        import statistics
        
        return DeterminismMetrics(
            total_iterations=len(results),
            violations=violations,
            unique_results=len(result_hashes),
            unique_hashes=len(result_hashes),
            min_execution_time_ms=min(execution_times) if execution_times else 0.0,
            max_execution_time_ms=max(execution_times) if execution_times else 0.0,
            avg_execution_time_ms=statistics.mean(execution_times) if execution_times else 0.0,
            std_dev_execution_time_ms=statistics.stdev(execution_times) if len(execution_times) > 1 else 0.0
        )
    
    def _compute_proof_tree_hash(self, proof_tree: Any) -> str:
        """Compute deterministic hash of proof tree"""
        import json
        import hashlib
        
        # Convert to canonical JSON
        if hasattr(proof_tree, 'to_dict'):
            data = proof_tree.to_dict()
        elif isinstance(proof_tree, dict):
            data = proof_tree
        else:
            data = str(proof_tree)
        
        canonical = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(canonical.encode()).hexdigest()
    
    def _format_violations(self, violations: List[DeterminismViolation]) -> str:
        """Format violations for error message"""
        lines = []
        for v in violations:
            lines.append(
                f"  [{v.violation_type.value}] Iteration {v.iteration}: "
                f"expected={v.expected}, actual={v.actual}"
            )
        return '\n'.join(lines)


# ============================================================================
# PYTEST CONFIGURATION
# ============================================================================

@pytest.fixture(scope="module")
def determinism_test_config():
    """Configuration for determinism tests"""
    return {
        "iterations": 100,
        "tolerance": 0.0,  # Zero tolerance for determinism
        "timeout_seconds": 300,  # 5 minutes for 100 iterations
    }

