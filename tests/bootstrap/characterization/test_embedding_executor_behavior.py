"""
🎯 EmbeddingModelsExecutor Complete Behavioral Characterization Suite

This is the main orchestrator that runs ALL complexity levels:
🟢 EASY → 🟡 MEDIUM → 🔴 HARD → ⚫ ULTRA HARD

Before P0 refactoring, this suite must pass and create golden master snapshots.
After refactoring, this suite must pass with IDENTICAL snapshots = zero regression.

Test Philosophy:
- Interface contracts protect syntax  
- Behavioral contracts protect semantics
- Golden master snapshots protect observable behavior
- Regression = ANY deviation from baseline behavior

Complexity Levels:
🟢 EASY: Basic success path (happy case)
🟡 MEDIUM: Dependencies, failures (realistic failures)  
🔴 HARD: Rollback, timing, edge cases (complex scenarios)
⚫ ULTRA HARD: Adversarial, race conditions, state corruption (extreme stress)
"""

import asyncio
import pytest
import time
from pathlib import Path
from typing import List, Dict, Any
import json

from mahoun.bootstrap.golden_master.behavior_recorder import BehavioralSnapshot

# Import all test scenarios
from .scenarios.embedding_success_easy import test_embedding_executor_easy_success
from .scenarios.embedding_neo4j_missing_medium import test_embedding_executor_missing_neo4j  
from .scenarios.embedding_rollback_race_hard import test_embedding_executor_rollback_race_conditions
from .scenarios.embedding_adversarial_ultra_hard import test_embedding_executor_adversarial_ultra_hard


class CharacterizationTestOrchestrator:
    """
    Orchestrates the complete behavioral characterization test suite.
    
    Responsibilities:
    - Run tests in complexity order
    - Compare snapshots for regression detection
    - Generate comprehensive behavioral report
    - Validate behavioral contracts
    """
    
    def __init__(self):
        self.snapshots_dir = Path(__file__).parent / "golden_master" / "snapshots"
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.test_results = {}
        
    async def run_complete_suite(self) -> Dict[str, Any]:
        """Run all characterization tests and collect behavioral evidence"""
        
        print("🎯 Starting Complete EmbeddingModelsExecutor Behavioral Characterization")
        print("=" * 80)
        
        suite_start_time = time.time()
        all_passed = True
        
        # Test complexity progression: EASY → MEDIUM → HARD → ULTRA HARD
        test_scenarios = [
            ("🟢 EASY", "Basic Success Path", test_embedding_executor_easy_success),
            ("🟡 MEDIUM", "Neo4j Missing Dependency", test_embedding_executor_missing_neo4j),
            ("🔴 HARD", "Rollback Race Conditions", test_embedding_executor_rollback_race_conditions),  
            ("⚫ ULTRA HARD", "Adversarial State Corruption", test_embedding_executor_adversarial_ultra_hard)
        ]
        
        for level, description, test_func in test_scenarios:
            print(f"\n{level} Running: {description}")
            print("-" * 60)
            
            scenario_start = time.time()
            try:
                # Run the characterization test
                snapshot = await test_func()
                
                # Validate snapshot quality
                self._validate_snapshot_quality(snapshot, level)
                
                # Record test result
                scenario_duration = time.time() - scenario_start
                self.test_results[level] = {
                    "status": "PASSED",
                    "duration": scenario_duration,
                    "snapshot_path": snapshot.metadata.get("snapshot_path", "unknown"),
                    "events_count": len(snapshot.events),
                    "mutations_count": len(snapshot.context_mutations.get("services_added", [])),
                    "description": description
                }
                
                print(f"   ✅ {level} PASSED ({scenario_duration:.2f}s)")
                print(f"   📊 Events captured: {len(snapshot.events)}")
                print(f"   🔄 Context mutations: {len(snapshot.context_mutations.get('services_added', []))}")
                
            except Exception as e:
                all_passed = False
                scenario_duration = time.time() - scenario_start
                
                self.test_results[level] = {
                    "status": "FAILED", 
                    "duration": scenario_duration,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "description": description
                }
                
                print(f"   ❌ {level} FAILED ({scenario_duration:.2f}s)")
                print(f"   💥 Error: {e}")
        
        suite_duration = time.time() - suite_start_time
        
        # Generate comprehensive report
        report = self._generate_behavioral_report(all_passed, suite_duration)
        
        print(f"\n🎯 Characterization Suite Completed ({suite_duration:.2f}s)")
        print("=" * 80)
        
        if all_passed:
            print("✅ ALL TESTS PASSED - Golden Master Snapshots Created")
            print("🔒 Behavioral baseline established for P0 refactoring protection")
        else:
            print("❌ SOME TESTS FAILED - Behavioral baseline incomplete")
            print("⚠️  Fix failing tests before proceeding with refactoring")
            
        return report
        
    def _validate_snapshot_quality(self, snapshot: BehavioralSnapshot, level: str):
        """Validate that snapshot contains sufficient behavioral evidence"""
        
        # Basic snapshot integrity
        assert snapshot.executor_name == "EmbeddingModelsExecutor"
        assert snapshot.timestamp > 0
        assert len(snapshot.events) > 0
        
        # Level-specific validations
        if level == "🟢 EASY":
            # Success path must have completion events
            completion_events = [e for e in snapshot.events if "completed" in e["type"]]
            assert len(completion_events) > 0, "Success path missing completion events"
            
        elif level == "🟡 MEDIUM":
            # Failure path must have exception events  
            exception_events = [e for e in snapshot.events if "exception" in e["type"]]
            assert len(exception_events) > 0, "Failure path missing exception events"
            
        elif level == "🔴 HARD":
            # Rollback path must have rollback events
            rollback_events = [e for e in snapshot.events if "rollback" in e["type"]]
            assert len(rollback_events) > 0, "Hard path missing rollback events"
            
        elif level == "⚫ ULTRA HARD":
            # Adversarial path must have stress/corruption events
            stress_events = [e for e in snapshot.events if any(
                keyword in e["type"] for keyword in ["stress", "corruption", "adversarial", "memory"]
            )]
            assert len(stress_events) > 0, "Ultra hard path missing stress events"
            
    def _generate_behavioral_report(self, all_passed: bool, suite_duration: float) -> Dict[str, Any]:
        """Generate comprehensive behavioral characterization report"""
        
        report = {
            "suite_metadata": {
                "executor": "EmbeddingModelsExecutor",
                "timestamp": time.time(),
                "duration": suite_duration,
                "all_passed": all_passed,
                "total_scenarios": len(self.test_results)
            },
            "test_results": self.test_results,
            "behavioral_coverage": {
                "success_paths": "🟢 EASY" in self.test_results and self.test_results["🟢 EASY"]["status"] == "PASSED",
                "failure_paths": "🟡 MEDIUM" in self.test_results and self.test_results["🟡 MEDIUM"]["status"] == "PASSED", 
                "rollback_paths": "🔴 HARD" in self.test_results and self.test_results["🔴 HARD"]["status"] == "PASSED",
                "adversarial_paths": "⚫ ULTRA HARD" in self.test_results and self.test_results["⚫ ULTRA HARD"]["status"] == "PASSED"
            },
            "regression_protection": {
                "snapshot_files_created": len([r for r in self.test_results.values() if r["status"] == "PASSED"]),
                "behavioral_contracts_established": all_passed,
                "refactoring_safety": "HIGH" if all_passed else "LOW"
            },
            "next_steps": {
                "ready_for_refactoring": all_passed,
                "required_actions": [] if all_passed else ["Fix failing characterization tests", "Re-establish behavioral baseline"]
            }
        }
        
        # Save report
        report_path = self.snapshots_dir / "behavioral_characterization_report.json"
        with open(report_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        print(f"\n📊 Behavioral report saved: {report_path}")
        
        return report


@pytest.mark.asyncio
async def test_complete_embedding_executor_characterization():
    """
    🎯 Main entry point for complete behavioral characterization.
    
    This test must be run before ANY refactoring of EmbeddingModelsExecutor.
    It establishes the behavioral baseline that protects against regressions.
    """
    
    orchestrator = CharacterizationTestOrchestrator()
    report = await orchestrator.run_complete_suite()
    
    # Critical assertion: ALL characterization tests must pass
    assert report["suite_metadata"]["all_passed"], (
        "Behavioral characterization incomplete. "
        "All tests must pass before refactoring can proceed safely."
    )
    
    # Verify behavioral coverage
    coverage = report["behavioral_coverage"]
    assert all(coverage.values()), f"Incomplete behavioral coverage: {coverage}"
    
    print(f"\n🔒 Behavioral baseline established for EmbeddingModelsExecutor")
    print(f"📁 Golden master snapshots: {report['regression_protection']['snapshot_files_created']}")
    print(f"🛡️ Refactoring safety level: {report['regression_protection']['refactoring_safety']}")
    
    return report


if __name__ == "__main__":
    # Direct execution for development/debugging
    asyncio.run(test_complete_embedding_executor_characterization())