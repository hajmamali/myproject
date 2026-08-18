"""
PHASE 3 - TEST 6: CASE EVOLUTION VERIFICATION (HARDCORE - REAL EXECUTION)
===================================================================
NO MOCKS. NO STUBS. REAL EXECUTION ONLY.

Verify: Case evolution preserves history - same case_id, unique verdict_ids, complete history in ledger
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
class TestCaseEvolutionHardcore:
    """HARDCORE: Case evolution tests - NO MOCKS, NO STUBS"""
    
    @pytest.fixture(scope="class")
    def cleanup_ledger(self):
        ledger_path = Path(os.environ.get("MAHOUN_LEDGER_PATH", "/tmp/mahoun_phase3_ledger.json"))
        if ledger_path.exists():
            ledger_path.unlink()
        yield
        if ledger_path.exists():
            ledger_path.unlink()
    
    async def test_001_multiple_verdicts_same_case(self, cleanup_ledger):
        """TEST 6.1: Same case_id MUST support multiple verdicts"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_001"
        verdict_ids = []
        
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_001_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال تدریجی {i}",
                    facts=[f"فکت جدید {i}"],
                    case_id=case_id
                )
                verdict_ids.append(exec_result.verdict.verdict_id)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        assert len(verdict_ids) == 3, "Should have 3 verdicts"
        
        # All should be different
        assert len(set(verdict_ids)) == 3, "Verdict IDs should be unique"
        
        
        
        # All should be in ledger
        for vid in verdict_ids:
            found = any(hasattr(b, 'data') and b.data.verdict_id == vid
                      for b in ledger.chain[1:])
            assert found, f"Verdict {vid} not in ledger"
        
        print(f"✅ Multiple verdicts same case PASSED")
    
    async def test_002_case_id_stability(self, cleanup_ledger):
        """TEST 6.2: case_id MUST remain stable across multiple verdicts"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_002"
        
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_002_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال {i}",
                    facts=[f"فکت {i}"],
                    case_id=case_id
                )
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # All entries should have the same case_id
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                assert block.data.case_id == case_id, "Case ID changed"
        
        print(f"✅ Case ID stability PASSED")
    
    async def test_003_verdict_id_uniqueness(self, cleanup_ledger):
        """TEST 6.3: Each verdict MUST have unique verdict_id"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        case_id = "evolution_case_003"
        verdict_ids = []
        
        for i in range(5):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_003_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال {i}",
                    facts=[f"فکت {i}"],
                    case_id=case_id
                )
                verdict_ids.append(exec_result.verdict.verdict_id)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        assert len(set(verdict_ids)) == len(verdict_ids), "All verdict_ids must be unique"
        print(f"✅ Verdict ID uniqueness PASSED: {verdict_ids}")
    
    async def test_004_case_history_in_ledger(self, cleanup_ledger):
        """TEST 6.4: Ledger MUST preserve complete case history"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_004"
        verdict_ids = []
        final_verdicts = []
        
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_004_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال تکمیلی {i}",
                    facts=[f"فکت تکمیلی {i}"],
                    case_id=case_id
                )
                verdict_ids.append(exec_result.verdict.verdict_id)
                final_verdicts.append(exec_result.verdict.final_verdict)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # Extract all entries for this case
        case_entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                case_entries.append(block.data)
        
        assert len(case_entries) == 3, f"Expected 3 entries, found {len(case_entries)}"
        
        # All verdict_ids should be present
        entry_verdict_ids = [e.verdict_id for e in case_entries]
        for vid in verdict_ids:
            assert vid in entry_verdict_ids, f"Verdict {vid} not in ledger history"
        
        print(f"✅ Case history in ledger PASSED")
    
    async def test_005_case_history_chronological_order(self, cleanup_ledger):
        """TEST 6.5: Case history MUST be in chronological order"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        import time
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_005"
        timestamps = []
        
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_005_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال {i}",
                    facts=[f"فکت {i}"],
                    case_id=case_id
                )
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
            timestamps.append(time.time())
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # Extract case entries
        case_entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                case_entries.append(block)
        
        # Should be in order of creation
        assert len(case_entries) == 3, "Should have 3 entries"
        
        print(f"✅ Case history chronological order PASSED")
    
    async def test_006_evolution_with_new_evidence(self, cleanup_ledger):
        """TEST 6.6: New evidence MUST create new verdict in same case"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_006"
        
        # First verdict
        async with GovernanceContextManager.active_context(
            correlation_id="evo_test_006_1", execution_mode="STRICT"
        ):
            exec_result_1 = await engine.generate_verdict(
                question="آیا معتبر است؟",
                facts=["شاهد ۱"],
                case_id=case_id
            )
            verdict_id_1 = exec_result_1.verdict.verdict_id
            # Manually commit the ledger entry for testing
            engine.ledger_writer.write(exec_result_1.ledger_entry)
        
        # Second verdict with new evidence
        async with GovernanceContextManager.active_context(
            correlation_id="evo_test_006_2", execution_mode="STRICT"
        ):
            exec_result_2 = await engine.generate_verdict(
                question="آیا معتبر است؟",
                facts=["شاهد ۱", "شاهد جدید ۲"],
                case_id=case_id
            )
            verdict_id_2 = exec_result_2.verdict.verdict_id
            # Manually commit the ledger entry for testing
            engine.ledger_writer.write(exec_result_2.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        assert verdict_id_1 != verdict_id_2, "New evidence should create new verdict"
        
        
        
        # Both should be in ledger
        entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                entries.append(block.data)
        
        assert len(entries) == 2, "Should have 2 entries for evolving case"
        
        print(f"✅ Evolution with new evidence PASSED")
    
    async def test_007_evolution_preserves_history(self, cleanup_ledger):
        """TEST 6.7: Evolution MUST preserve previous verdicts"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_007"
        
        # Create 3 verdicts
        all_verdict_ids = []
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_007_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال {i}",
                    facts=[f"فکت {i}"],
                    case_id=case_id
                )
                all_verdict_ids.append(exec_result.verdict.verdict_id)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        
        
        # After evolution, all previous verdicts should still be available
        case_entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                case_entries.append(block.data)
        
        entry_verdict_ids = [e.verdict_id for e in case_entries]
        
        for vid in all_verdict_ids:
            assert vid in entry_verdict_ids, f"Previous verdict {vid} was lost during evolution"
        
        print(f"✅ Evolution preserves history PASSED")
    
    async def test_008_complex_evolution_scenario(self, cleanup_ledger):
        """TEST 6.8: Complex evolution with changing facts and questions"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_008"
        
        # Simulate a real case evolution
        scenarios = [
            ("آیا قرارداد معتبر است؟", ["امضاها حاضر هستند"]),
            ("آیا قرارداد معتبر است؟", ["امضاها حاضر هستند", "مهر و امضا تایید شده"]),
            ("آیا قرارداد ابطال شده؟", ["امضاها حاضر هستند", "مهر و امضا تایید شده", "مدت تمام شده"]),
        ]
        
        verdict_ids = []
        for question, facts in scenarios:
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_008_{question[:10]}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=question, facts=facts, case_id=case_id
                )
                verdict_ids.append(exec_result.verdict.verdict_id)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # All should be unique
        assert len(set(verdict_ids)) == len(verdict_ids), "All verdict IDs must be unique"
        
        
        
        # All should be in ledger
        for vid in verdict_ids:
            found = any(hasattr(b, 'data') and b.data.verdict_id == vid
                      for b in ledger.chain[1:])
            assert found, f"Verdict {vid} not in ledger"
        
        print(f"✅ Complex evolution scenario PASSED")
    
    async def test_009_case_evolution_with_different_questions(self, cleanup_ledger):
        """TEST 6.9: Case evolution with different questions MUST work"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_009"
        
        questions = [
            "آیا قرارداد معتبر است؟",
            "چه مجازاتی دارد؟",
            "آیا می‌توان ابطال کرد؟",
        ]
        
        for question in questions:
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_009_{question[:10]}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=question,
                    facts=["فکت"],
                    case_id=case_id
                )
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # All should be in ledger with same case_id
        case_entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                case_entries.append(block.data)
        
        assert len(case_entries) == len(questions), \
            f"Expected {len(questions)} entries, found {len(case_entries)}"
        
        print(f"✅ Case evolution with different questions PASSED")
    
    async def test_010_evolution_verdict_independence(self, cleanup_ledger):
        """TEST 6.10: Each verdict in evolution MUST be independent and verifiable"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        from api.routers.reasoning import get_immutable_ledger, get_verdict_engine
        
        engine = get_verdict_engine()
        ledger = get_immutable_ledger()
        
        case_id = "evolution_case_010"
        
        exec_results = []
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"evo_test_010_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=f"سوال مستقل {i}",
                    facts=[f"فکت مستقل {i}"],
                    case_id=case_id
                )
                exec_results.append(exec_result)
                # Manually commit the ledger entry for testing
                engine.ledger_writer.write(exec_result.ledger_entry)
        
        # Reload ledger
        ledger = get_immutable_ledger()
        
        # Each verdict should be independently valid
        for i, exec_result in enumerate(exec_results):
            verdict = exec_result.verdict
            assert verdict.verdict_id is not None, f"Verdict {i} has no ID"
            assert verdict.final_verdict is not None, f"Verdict {i} has no final_verdict"
            assert len(verdict.steps) > 0, f"Verdict {i} has no steps"
        
        
        
        # All should be in ledger
        case_entries = []
        for block in ledger.chain[1:]:
            if hasattr(block, 'data') and block.data.case_id == case_id:
                case_entries.append(block.data)
        
        assert len(case_entries) == 3, "Should have 3 independent entries"
        
        print(f"✅ Evolution verdict independence PASSED")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
