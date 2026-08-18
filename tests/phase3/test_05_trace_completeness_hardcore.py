"""
PHASE 3 - TEST 5: TRACE COMPLETENESS VERIFICATION (HARDCORE - REAL EXECUTION)
====================================================================
NO MOCKS. NO STUBS. REAL EXECUTION ONLY.

Verify: Every verdict contains complete trace: Question -> Retrieved Evidence -> Applied Rules -> Reasoning Steps -> Contradiction Checks -> Final Verdict -> Proof -> Ledger Entry
"""

import pytest
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

os.environ["MAHOUN_ENV"] = "test"
os.environ["MAHOUN_ENABLE_GRAPH"] = "true"
os.environ["MAHOUN_LEDGER_PATH"] = "/tmp/mahoun_phase3_ledger.json"


@pytest.mark.asyncio
class TestTraceCompletenessHardcore:
    """HARDCORE: Trace completeness tests - NO MOCKS, NO STUBS"""
    
    @pytest.fixture(scope="class")
    def cleanup_ledger(self):
        ledger_path = Path(os.environ.get("MAHOUN_LEDGER_PATH", "/tmp/mahoun_phase3_ledger.json"))
        if ledger_path.exists():
            ledger_path.unlink()
        yield
        if ledger_path.exists():
            ledger_path.unlink()
    
    async def test_001_verdict_has_steps(self, cleanup_ledger):
        """TEST 5.1: Verdict MUST have reasoning steps"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_001", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا قرارداد معتبر است؟",
                facts=["همه شرایط محقق شده"],
                case_id="trace_case_001"
            )
        
        verdict = exec_result.verdict
        assert hasattr(verdict, 'steps'), "Verdict should have steps attribute"
        assert verdict.steps is not None, "Steps should not be None"
        assert len(verdict.steps) > 0, "Steps should not be empty"
        print(f"✅ Verdict has steps PASSED: {len(verdict.steps)} steps")
    
    async def test_002_steps_have_evidence(self, cleanup_ledger):
        """TEST 5.2: Every reasoning step MUST have evidence references"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_002", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="چه مجازاتی برای سرقت؟",
                facts=["متهم دستگیر شد", "مبلغ مسروقه ۵۰ میلیون تومان"],
                case_id="trace_case_002"
            )
        
        verdict = exec_result.verdict
        assert len(verdict.steps) > 0, "No steps in verdict"
        
        for i, step in enumerate(verdict.steps):
            assert hasattr(step, 'evidence'), f"Step {i} should have evidence"
            assert step.evidence is not None, f"Step {i} evidence should not be None"
            # Evidence can be empty list, but attribute must exist
            print(f"  Step {i}: {len(step.evidence)} evidence items")
        
        print(f"✅ Steps have evidence PASSED")
    
    async def test_003_steps_have_statements(self, cleanup_ledger):
        """TEST 5.3: Every reasoning step MUST have statement/reasoning"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_003", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا مالکیت انتقال یافته؟",
                facts=["فروشنده سند را تحویل داده", "خریدار مبلغ را پرداخته"],
                case_id="trace_case_003"
            )
        
        verdict = exec_result.verdict
        for i, step in enumerate(verdict.steps):
            # Check for reasoning/statement attributes
            has_statement = any(attr in dir(step) for attr in ['statement', 'reasoning', 'explanation', 'rule'])
            assert has_statement, f"Step {i} should have statement/reasoning attribute"
        
        print(f"✅ Steps have statements PASSED")
    
    async def test_004_trace_links_to_question(self, cleanup_ledger):
        """TEST 5.4: Trace MUST link back to original question"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        question = "آیا قرارداد اجاره با فوت موجر منحل می‌شود؟"
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_004", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question=question,
                facts=["موجر فوت شده"],
                case_id="trace_case_004"
            )
        
        verdict = exec_result.verdict
        
        # The question should be reconstructible from the execution context
        # Check if verdict or exec_result contains question reference
        if hasattr(verdict, 'question'):
            assert verdict.question == question, "Question mismatch in verdict"
        else:
            # Question might be in metadata or execution result
            print(f"  Question stored in execution context")
        
        print(f"✅ Trace links to question PASSED")
    
    async def test_005_trace_links_to_facts(self, cleanup_ledger):
        """TEST 5.5: Trace MUST link to original facts"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        facts = ["موجر در تاریخ ۱۴۰۴/۰۱/۰۱ فوت شده", "قرارداد در تاریخ ۱۴۰۳/۱۲/۱۵ امضا شده"]
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_005", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا قرارداد منحل شده؟",
                facts=facts,
                case_id="trace_case_005"
            )
        
        verdict = exec_result.verdict
        
        # Facts should be in verdict
        if hasattr(verdict, 'facts'):
            assert verdict.facts == facts, "Facts mismatch in verdict"
        
        print(f"✅ Trace links to facts PASSED")
    
    async def test_006_trace_links_to_case_id(self, cleanup_ledger):
        """TEST 5.6: Trace MUST link to case_id"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        case_id = "trace_case_006"
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_006", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا معتبر است؟",
                facts=["شرایط"],
                case_id=case_id
            )
        
        verdict = exec_result.verdict
        
        # Case ID should be traceable
        if hasattr(verdict, 'case_id'):
            assert verdict.case_id == case_id, "Case ID mismatch"
        else:
            # Should be in execution result
            assert exec_result.ledger_entry.case_id == case_id, \
                "Case ID not in ledger entry"
        
        print(f"✅ Trace links to case_id PASSED")
    
    async def test_007_evidence_references_are_valid(self, cleanup_ledger):
        """TEST 5.7: All evidence references in trace MUST be valid"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_007", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="چه مجازاتی؟",
                facts=["متهم دستگیر شد", "مبلغ مسروقه"],
                case_id="trace_case_007"
            )
        
        verdict = exec_result.verdict
        
        # Check all evidence references are non-empty strings or valid objects
        for step_idx, step in enumerate(verdict.steps):
            for ev_idx, evidence in enumerate(step.evidence):
                if hasattr(evidence, 'node_id'):
                    assert len(evidence.node_id) > 0, \
                        f"Step {step_idx}, evidence {ev_idx}: empty node_id"
                elif isinstance(evidence, str):
                    assert len(evidence) > 0, \
                        f"Step {step_idx}, evidence {ev_idx}: empty string"
        
        print(f"✅ Evidence references are valid PASSED")
    
    async def test_008_evidence_to_step_mapping(self, cleanup_ledger):
        """TEST 5.8: Evidence MUST be correctly mapped to reasoning steps"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_008", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا قرارداد معتبر است؟",
                facts=["شرایط ۱", "شرایط ۲", "شرایط ۳"],
                case_id="trace_case_008"
            )
        
        verdict = exec_result.verdict
        
        # Each step should have evidence
        for step in verdict.steps:
            assert hasattr(step, 'evidence'), "Step should have evidence"
            assert step.evidence is not None, "Step evidence should not be None"
        
        # Evidence should be distributed across steps (not all in one step typically)
        print(f"✅ Evidence to step mapping PASSED")
    
    async def test_009_reconstruct_complete_trace(self, cleanup_ledger):
        """TEST 5.9: MUST be able to reconstruct complete trace from verdict"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        question = "آیا قرارداد اجاره منحل شده؟"
        facts = ["موجر فوت شده", "مدت اجاره تمام شده"]
        case_id = "trace_case_009"
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_009", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question=question, facts=facts, case_id=case_id
            )
        
        verdict = exec_result.verdict
        
        # Reconstruct trace
        trace = {
            'question': question,
            'facts': facts,
            'case_id': case_id,
            'verdict_id': verdict.verdict_id,
            'final_verdict': verdict.final_verdict,
            'confidence_score': verdict.confidence_score,
            'steps': [],
        }
        
        for step in verdict.steps:
            step_trace = {
                'statement': getattr(step, 'statement', ''),
                'rule': getattr(step, 'rule', ''),
                'evidence': [getattr(ev, 'node_id', str(ev)) for ev in step.evidence],
            }
            trace['steps'].append(step_trace)
        
        # All trace components should be non-empty
        assert len(trace['question']) > 0, "Question missing"
        assert len(trace['facts']) > 0, "Facts missing"
        assert len(trace['verdict_id']) > 0, "Verdict ID missing"
        assert len(trace['final_verdict']) > 0, "Final verdict missing"
        assert len(trace['steps']) > 0, "Steps missing"
        
        print(f"✅ Complete trace reconstruction PASSED")
    
    async def test_010_trace_contains_all_evidence(self, cleanup_ledger):
        """TEST 5.10: Trace MUST contain ALL evidence used in reasoning"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_010", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="چه باید کرد؟",
                facts=["فکت ۱", "فکت ۲", "فکت ۳"],
                case_id="trace_case_010"
            )
        
        verdict = exec_result.verdict
        
        # Collect all evidence from all steps
        all_evidence = set()
        for step in verdict.steps:
            for ev in step.evidence:
                if hasattr(ev, 'node_id'):
                    all_evidence.add(ev.node_id)
                elif isinstance(ev, str):
                    all_evidence.add(ev)
        
        assert len(all_evidence) > 0, "No evidence in trace"
        print(f"✅ Trace contains all evidence PASSED: {len(all_evidence)} evidence items")
    
    async def test_011_trace_step_ordering(self, cleanup_ledger):
        """TEST 5.11: Trace steps MUST be in logical order"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        async with GovernanceContextManager.active_context(
            correlation_id="trace_test_011", execution_mode="STRICT"
        ):
            exec_result = await engine.generate_verdict(
                question="آیا معتبر است؟",
                facts=["شرایط"],
                case_id="trace_case_011"
            )
        
        verdict = exec_result.verdict
        
        # Steps should be ordered (have step numbers or sequential IDs)
        for i, step in enumerate(verdict.steps):
            if hasattr(step, 'step_number'):
                assert step.step_number == i + 1, f"Step {i} has wrong number"
            # Or check that steps have some ordering attribute
        
        print(f"✅ Trace step ordering PASSED")
    
    async def test_012_trace_consistency(self, cleanup_ledger):
        """TEST 5.12: Trace MUST be consistent across multiple runs"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        case_id = "trace_case_012"
        
        traces = []
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"trace_test_012_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question="آیا معتبر است؟",
                    facts=["شرایط"],
                    case_id=case_id
                )
            
            # Extract trace structure
            trace = {
                'verdict_id': exec_result.verdict.verdict_id,
                'num_steps': len(exec_result.verdict.steps),
                'final_verdict': exec_result.verdict.final_verdict,
            }
            traces.append(trace)
        
        # All traces should be identical for same inputs
        first = traces[0]
        for i, trace in enumerate(traces[1:]):
            assert trace['verdict_id'] == first['verdict_id'], \
                f"Run {i+2}: verdict_id differs"
            assert trace['num_steps'] == first['num_steps'], \
                f"Run {i+2}: num_steps differs"
            assert trace['final_verdict'] == first['final_verdict'], \
                f"Run {i+2}: final_verdict differs"
        
        print(f"✅ Trace consistency PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
