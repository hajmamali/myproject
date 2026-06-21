"""
E2E Smoke Tests for MAHOUN Orchestrator (Desktop-Minimal Mode)
================================================================

این تست‌ها برای سنجش حداقلی سلامت SelfImprovementOrchestrator و wiring 
در حالت desktop_minimal طراحی شده‌اند.

تست‌ها شامل:
- بررسی runtime configuration
- instantiation موفق orchestrator
- بررسی وضعیت component ها در desktop_minimal mode
- تست graceful degradation (component های غیرفعال به درستی None هستند)

Usage:
    from mahoun.orchestrator.smoke_tests import run_e2e_smoke_test_desktop_minimal
    run_e2e_smoke_test_desktop_minimal()
"""

import sys
from typing import Any, Dict, Optional

from mahoun.core.runtime_config import get_runtime_settings
from orchestrator import SelfImprovementOrchestrator, OrchestratorState


def print_section(title: str, char: str = "="):
    """Print a formatted section header"""
    print(f"\n{char * 80}")
    print(f"  {title}")
    print(f"{char * 80}\n")


def print_key_value(key: str, value: Any, indent: int = 0):
    """Print a key-value pair with optional indentation"""
    prefix = "  " * indent
    if isinstance(value, bool):
        symbol = "✅" if value else "❌"
        print(f"{prefix}{symbol} {key}: {value}")
    else:
        print(f"{prefix}• {key}: {value}")


def run_e2e_smoke_test_desktop_minimal() -> None:
    """
    End-to-end smoke test for SelfImprovementOrchestrator in desktop_minimal mode.
    
    این تست:
    1. Runtime settings را بررسی می‌کند
    2. SelfImprovementOrchestrator را instantiate می‌کند
    3. وضعیت component ها را در desktop_minimal mode بررسی می‌کند
    4. Graceful degradation را تست می‌کند
    
    توجه:
    - این تست انتظار دارد MAHOUN_MODE=desktop_minimal باشد
    - component های سنگین (graph, LoRA training) باید disable باشند
    - هشدارهای مربوط به import های ناموفق (مثل FeedbackLoop) نرمال و قابل قبول هستند
    """
    
    print_section("MAHOUN E2E Smoke Test - Desktop-Minimal Mode", "=")
    
    # ============================================================================
    # Phase 1: Verify Runtime Configuration
    # ============================================================================
    print_section("Phase 1: Runtime Configuration", "-")
    
    try:
        settings = get_runtime_settings()
        
        print_key_value("Mode", settings.mode)
        print_key_value("Graph Enabled", settings.graph_enabled)
        print_key_value("Graph Backend", settings.graph_backend)
        print_key_value("LoRA Training Enabled", settings.lora_training_enabled)
        print_key_value("LoRA Inference Backend", settings.lora_inference_backend)
        print_key_value("LLM Backend", settings.llm_backend)
        print_key_value("Embedding Backend", settings.embedding_backend)
        
        # Check if we're in desktop_minimal mode
        if settings.mode != "desktop_minimal":
            print(f"\n⚠️  WARNING: Expected mode 'desktop_minimal', but got '{settings.mode}'")
            print("   This test is designed for desktop_minimal mode.")
            print("   Continuing anyway, but results may differ from expectations.\n")
        else:
            print("\n✅ Runtime mode verified: desktop_minimal\n")
            
    except Exception as e:
        print(f"❌ FAILED: Could not load runtime settings")
        print(f"   Error: {type(e).__name__}: {e}")
        return
    
    # ============================================================================
    # Phase 2: Instantiate Orchestrator
    # ============================================================================
    print_section("Phase 2: Orchestrator Instantiation", "-")
    
    try:
        print("Attempting to create SelfImprovementOrchestrator instance...")
        
        # Create orchestrator with all optional components set to None
        # This is appropriate for desktop_minimal mode
        orchestrator = SelfImprovementOrchestrator(
            rl_bandit_bridge=None,
            active_learning_pipeline=None,
            causal_ab_bridge=None,
            performance_monitor=None,
            feedback_loop=None,
            enable_auto_recovery=False,  # Disable auto-recovery for testing
            health_check_interval=300.0,  # Longer interval for desktop mode
        )
        
        print("✅ SelfImprovementOrchestrator created successfully")
        print(f"   Initial state: {orchestrator.state.value}")
        print(f"   Runtime settings mode: {orchestrator.settings.mode}")
        
    except Exception as e:
        print(f"❌ FAILED: Could not instantiate orchestrator")
        print(f"   Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # ============================================================================
    # Phase 3: Test Component Access (Graceful Degradation)
    # ============================================================================
    print_section("Phase 3: Component Access & Graceful Degradation", "-")
    
    print("Testing component getters (expecting None or disabled components in desktop_minimal):\n")
    
    # Test each component getter
    component_tests = [
        ("Indexing Service", lambda: orchestrator.get_indexing_service()),
        ("Graph Service", lambda: orchestrator.get_graph_service()),
        ("RAG Retriever", lambda: orchestrator.get_rag_retriever()),
        ("Chunking Service", lambda: orchestrator.get_chunking_service()),
        ("Embedding Service", lambda: orchestrator.get_embedding_service()),
        ("Vector Store Manager", lambda: orchestrator.get_vector_store_manager()),
        ("PEFT Manager", lambda: orchestrator.get_peft_manager()),
        ("LoRA Trainer", lambda: orchestrator.get_lora_trainer()),
    ]
    
    component_results: Dict[str, Any] = {}
    for component_name, getter_func in component_tests:
        try:
            component = getter_func()
            if component is None:
                print(f"  • {component_name}: None (gracefully disabled) ✅")
                component_results[component_name] = "disabled"
            else:
                print(f"  • {component_name}: Available ({type(component).__name__}) ⚠️")
                component_results[component_name] = "available"
        except Exception as e:
            print(f"  • {component_name}: Error - {type(e).__name__}: {str(e)[:60]}... ❌")
            component_results[component_name] = "error"
    
    # ============================================================================
    # Phase 4: Health Status & Statistics
    # ============================================================================
    print_section("Phase 4: Health Status & Statistics", "-")
    
    try:
        health_status = orchestrator.get_health_status()
        print("Health Status:")
        print_key_value("Overall State", health_status.get("state", "unknown"), indent=1)
        print_key_value("Total Components", health_status.get("total_components", 0), indent=1)
        print_key_value("Healthy Components", health_status.get("healthy_components", 0), indent=1)
        print_key_value("Unhealthy Components", health_status.get("unhealthy_components", 0), indent=1)
        
    except Exception as e:
        print(f"⚠️  Could not retrieve health status: {e}")
    
    try:
        statistics = orchestrator.get_statistics()
        print("\nStatistics:")
        print_key_value("Uptime (seconds)", statistics.get("uptime_seconds", 0), indent=1)
        print_key_value("Total Errors", statistics.get("total_errors", 0), indent=1)
        print_key_value("Recoveries", statistics.get("recoveries", 0), indent=1)
        
    except Exception as e:
        print(f"⚠️  Could not retrieve statistics: {e}")
    
    # ============================================================================
    # Phase 5: Desktop-Minimal Mode Verification
    # ============================================================================
    print_section("Phase 5: Desktop-Minimal Mode Verification", "-")
    
    print("Checking desktop_minimal mode constraints:\n")
    
    checks_passed = 0
    checks_total = 0
    
    # Check 1: Graph should be disabled
    checks_total += 1
    if not settings.graph_enabled and settings.graph_backend == "disabled_fallback":
        print("  ✅ Graph operations correctly disabled")
        checks_passed += 1
    else:
        print("  ❌ Graph should be disabled in desktop_minimal mode")
    
    # Check 2: LoRA training should be disabled
    checks_total += 1
    if not settings.lora_training_enabled:
        print("  ✅ LoRA training correctly disabled")
        checks_passed += 1
    else:
        print("  ❌ LoRA training should be disabled in desktop_minimal mode")
    
    # Check 3: Orchestrator should use runtime settings
    checks_total += 1
    if orchestrator.settings.mode == "desktop_minimal":
        print("  ✅ Orchestrator using correct runtime settings")
        checks_passed += 1
    else:
        print("  ❌ Orchestrator not using desktop_minimal settings")
    
    # Check 4: Heavy components should be None
    checks_total += 1
    heavy_components = ["Graph Service", "LoRA Trainer"]
    all_heavy_disabled = all(
        component_results.get(comp) == "disabled" 
        for comp in heavy_components
    )
    if all_heavy_disabled:
        print("  ✅ Heavy components correctly disabled/None")
        checks_passed += 1
    else:
        print("  ⚠️  Some heavy components are not None (may still be acceptable)")
    
    # ============================================================================
    # Final Summary
    # ============================================================================
    print_section("Test Summary", "=")
    
    print(f"Runtime Mode: {settings.mode}")
    print(f"Orchestrator State: {orchestrator.state.value}")
    print(f"Desktop-Minimal Checks: {checks_passed}/{checks_total} passed")
    print(f"\nComponent Status:")
    for comp_name, status in component_results.items():
        status_symbol = {
            "disabled": "✅",
            "available": "⚠️",
            "error": "❌"
        }.get(status, "?")
        print(f"  {status_symbol} {comp_name}: {status}")
    
    if checks_passed == checks_total:
        print("\n" + "=" * 80)
        print("  ✅ ALL CHECKS PASSED - Desktop-Minimal Mode Working Correctly")
        print("=" * 80 + "\n")
    else:
        print("\n" + "=" * 80)
        print(f"  ⚠️  {checks_total - checks_passed} CHECK(S) FAILED - Review Results Above")
        print("=" * 80 + "\n")
    
    print("📝 Note: This is a smoke test for orchestrator infrastructure.")
    print("   For end-to-end query processing, additional integration with")
    print("   RAG pipeline, LLM backend, and document processing is required.\n")


def run_quick_import_test() -> None:
    """
    Quick test to verify imports work without instantiation.
    
    این تست سبک‌تر است و فقط import ها را چک می‌کند.
    """
    print("=" * 80)
    print("  Quick Import Test")
    print("=" * 80 + "\n")
    
    try:
        from mahoun.core.runtime_config import get_runtime_settings
        print("✅ core.runtime_config imported")
        
        settings = get_runtime_settings()
        print(f"✅ Runtime settings loaded: mode={settings.mode}")
        
        from orchestrator import SelfImprovementOrchestrator
        print("✅ SelfImprovementOrchestrator imported")
        
        from orchestrator import OrchestratorState, ComponentStatus
        print("✅ Orchestrator enums imported")
        
        print("\n✅ All imports successful!\n")
        
    except Exception as e:
        print(f"\n❌ Import failed: {type(e).__name__}: {e}\n")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    """
    Direct execution support.
    
    Usage:
        python orchestrator/smoke_tests.py
        
    Or:
        python -m orchestrator.smoke_tests
    """
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        run_quick_import_test()
    else:
        run_e2e_smoke_test_desktop_minimal()

