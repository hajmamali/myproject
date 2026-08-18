"""
PHASE 3 - TEST 1: DETERMINISM VERIFICATION (HARDCORE - REAL EXECUTION)
==================================================================
NO MOCKS. NO STUBS. REAL EXECUTION ONLY.
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
class TestDeterminismHardcore:
    """HARDCORE: Real execution determinism tests"""
    
    @pytest.fixture(scope="class")
    def cleanup_ledger(self):
        ledger_path = Path(os.environ.get("MAHOUN_LEDGER_PATH", "/tmp/mahoun_phase3_ledger.json"))
        if ledger_path.exists():
            ledger_path.unlink()
        yield
        if ledger_path.exists():
            ledger_path.unlink()
    
    async def test_001_same_inputs_produce_identical_verdict_id(self, cleanup_ledger):
        """TEST 1.1: Same case_id+inputs must produce identical verdict_id"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        assert engine is not None
        
        question = "آیا قرارداد اجاره با فوت موجر منحل می‌شود؟"
        facts = ["موجر در تاریخ ۱۴۰۴/۰۱/۰۱ فوت شده است"]
        case_id = "det_case_001"
        
        verdict_ids = []
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"run_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=question, facts=facts, case_id=case_id
                )
                verdict_ids.append(exec_result.verdict.verdict_id)
        
        assert len(set(verdict_ids)) == 1, f"Verdict IDs not identical: {verdict_ids}"
        print(f"✅ Verdict ID determinism PASSED: {verdict_ids[0]}")
    
    async def test_002_same_inputs_produce_identical_final_verdict(self, cleanup_ledger):
        """TEST 1.2: Same inputs must produce identical final_verdict text"""
        from api.routers.reasoning import get_verdict_engine, get_immutable_ledger
        from mahoun.core.governance import GovernanceContextManager
        
        engine = get_verdict_engine()
        
        question = "آیا مالکیت انتقال یافته است؟"
        facts = ["فروشنده سند را تحویل داده است"]
        case_id = "det_case_002"
        
        final_verdicts = []
        for i in range(3):
            async with GovernanceContextManager.active_context(
                correlation_id=f"run_{i}", execution_mode="STRICT"
            ):
                exec_result = await engine.generate_verdict(
                    question=question, facts=facts, case_id=case_id
                )
                final_verdicts.append(exec_result.verdict.final_verdict)
        
        assert len(set(final_verdicts)) == 1, f"Final verdicts differ: {final_verdicts}"
        print(f"✅ Final verdict determinism PASSED")
