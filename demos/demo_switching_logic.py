#!/usr/bin/env python3
"""
Model Switching Logic Demo
==========================
Verifies the "Brain" of the system:
1. Analyzes query intent (Router)
2. Selects correct model capability (Coding vs Reasoning)
3. Swaps models dynamically (Orchestrator)
4. Generates appropriate response (Unified Engine)
"""

import sys
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("demo_switch")

from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
from mahoun.llm.orchestrator import get_orchestrator


async def demo_logic_switching():
    print("\n" + "=" * 60)
    print("🧠 Reasoning Pipeline: Model Switching Demo")
    print("=" * 60)

    engine = UnifiedReasoningEngine()
    orchestrator = get_orchestrator()

    # Test Scenarios
    scenarios = [
        {
            "query": "یک کوئری سایفر بنویس که تمام قراردادهای با تأخیر بالای ۳۰ روز را پیدا کند.",
            "expected_capability": "coding",
            "desc": "Technical Request -> Qwen-Coder",
        },
        {
            "query": "آیا طبق شرایط عمومی پیمان، کارفرما می‌تواند قرارداد را فسخ کند؟",
            "expected_capability": "reasoning",
            "desc": "Legal Inquiry -> Granite-Legal",
        },
        {
            "query": "Show me a graph query to find unrelated people.",
            "expected_capability": "coding",
            "desc": "Graph Request -> Qwen-Coder",
        },
    ]

    print(
        f"\n🚀 Starting Sequence (Max Loaded Models: {orchestrator.max_loaded_models})"
    )

    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🔸 Step {i}: {scenario['desc']}")
        print(f"   Query: {scenario['query']}")

        try:
            # Execute pipeline
            result = await engine.process_query(scenario["query"])

            # Validation
            used_capability = result["capability"].value
            expected = scenario["expected_capability"]

            print(f"   ✅ Routed to: {result['query_type'].value}")
            print(f"   ✅ Capability: {used_capability} (Expected: {expected})")
            print(f"   ✅ Model Used: {result['model_used']}")

            # Show snippet of generated prompt or response
            # (In a real run, this would be the actual generation)
            print(f"   ℹ️  Confidence: {result['confidence']:.2f}")

        except Exception as e:
            print(f"   ❌ Error: {e}")
            logger.error("Processing failed", exc_info=True)

    print("\n" + "=" * 60)
    print("Demo Complete!")
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(demo_logic_switching())
