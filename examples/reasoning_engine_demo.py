"""
Reasoning Engine Demo
=====================

Demonstrates the protocol-based reasoning architecture with:
- Basic query processing
- Custom dependency injection
- Mock testing
- Error handling
- Observability

Run:
    python examples/reasoning_engine_demo.py
"""

import asyncio
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


# ============================================================================
# Demo 1: Basic Usage
# ============================================================================


async def demo_basic_usage():
    """Demonstrate basic query processing."""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Usage")
    print("=" * 70)
    
    from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
    
    # Create engine (uses DI container automatically)
    engine = UnifiedReasoningEngine()
    
    # Test queries
    queries = [
        "What are the payment terms in the contract?",
        "Generate a Cypher query to find all related cases",
        "Explain the legal implications of breach of contract",
    ]
    
    for query in queries:
        print(f"\n📝 Query: {query}")
        
        try:
            result = await engine.process_query(query)
            
            print(f"✅ Response: {result['response'][:100]}...")
            print(f"   Type: {result['query_type']}")
            print(f"   Model: {result['model_used']}")
            print(f"   Confidence: {result['confidence']:.2f}")
            print(f"   Context sources: {result['context_sources']}")
            
        except Exception as e:
            print(f"❌ Error: {e}")


# ============================================================================
# Demo 2: Dependency Injection
# ============================================================================


async def demo_dependency_injection():
    """Demonstrate custom dependency injection."""
    print("\n" + "=" * 70)
    print("DEMO 2: Dependency Injection")
    print("=" * 70)
    
    from mahoun.reasoning.adapters import get_reasoning_dependencies
    from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
    
    # Get container
    container = get_reasoning_dependencies()
    
    print(f"\n📦 Container: {container}")
    print(f"   Status: {container.get_initialization_status()}")
    
    # Access individual components
    print("\n🔧 Accessing components...")
    
    router = container.query_router
    print(f"   ✓ Router: {type(router).__name__}")
    
    orchestrator = container.model_orchestrator
    print(f"   ✓ Orchestrator: {type(orchestrator).__name__}")
    
    # Create engine with explicit dependencies
    engine = UnifiedReasoningEngine(
        router=router,
        orchestrator=orchestrator
    )
    
    print(f"\n🧠 Engine created with injected dependencies")
    
    # Process query
    result = await engine.process_query("What is the law about contracts?")
    print(f"   ✓ Query processed successfully")
    print(f"   Response length: {len(result['response'])} chars")


# ============================================================================
# Demo 3: Mock Testing
# ============================================================================


async def demo_mock_testing():
    """Demonstrate testing with mocks."""
    print("\n" + "=" * 70)
    print("DEMO 3: Mock Testing")
    print("=" * 70)
    
    from unittest.mock import Mock, AsyncMock
    from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
    from mahoun.reasoning.adapters import MockDependencyContainer
    from mahoun.core.protocols import (
        QueryRouterProtocol,
        QueryClassificationResult,
        RoutedQueryResult,
        QueryType,
        ModelOrchestratorProtocol,
        ModelDriverProtocol,
    )
    from mahoun.llm.orchestrator import ModelCapability
    
    print("\n🧪 Creating mock dependencies...")
    
    # Create mock router
    mock_router = Mock(spec=QueryRouterProtocol)
    
    async def mock_route(query: str, **kwargs):
        classification = QueryClassificationResult(
            query=query,
            query_type=QueryType.LEGAL_INQUIRY,
            confidence=0.95,
            keywords_found=["contract", "legal"],
            metadata={"mock": True},
            required_capability=ModelCapability.REASONING.value,
        )
        
        mock_rag_result = Mock()
        mock_rag_result.results = [
            Mock(content="Mock document 1"),
            Mock(content="Mock document 2"),
        ]
        
        return RoutedQueryResult(
            query=query,
            query_type=QueryType.LEGAL_INQUIRY,
            rag_result=mock_rag_result,
            classification=classification,
            metadata={"routing": "mock"},
            model_capability=ModelCapability.REASONING.value,
        )
    
    mock_router.route = AsyncMock(side_effect=mock_route)
    print("   ✓ Mock router created")
    
    # Create mock orchestrator
    mock_orchestrator = Mock(spec=ModelOrchestratorProtocol)
    mock_driver = Mock(spec=ModelDriverProtocol)
    mock_driver.model_name = "mock-model-v1"
    mock_driver.generate = Mock(return_value="This is a mock response from the model.")
    
    async def mock_get_driver(capability):
        return mock_driver
    
    mock_orchestrator.get_driver = AsyncMock(side_effect=mock_get_driver)
    print("   ✓ Mock orchestrator created")
    
    # Create engine with mocks
    engine = UnifiedReasoningEngine(
        router=mock_router,
        orchestrator=mock_orchestrator
    )
    print("   ✓ Engine created with mocks")
    
    # Test query
    result = await engine.process_query("Test query with mocks")
    
    print(f"\n✅ Mock test successful!")
    print(f"   Response: {result['response']}")
    print(f"   Model: {result['model_used']}")
    print(f"   Confidence: {result['confidence']}")
    
    # Verify mocks were called
    mock_router.route.assert_called_once()
    mock_orchestrator.get_driver.assert_called_once()
    print(f"   ✓ All mocks called as expected")


# ============================================================================
# Demo 4: Error Handling
# ============================================================================


async def demo_error_handling():
    """Demonstrate error handling."""
    print("\n" + "=" * 70)
    print("DEMO 4: Error Handling")
    print("=" * 70)
    
    from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
    
    engine = UnifiedReasoningEngine()
    
    # Test 1: Empty query
    print("\n🧪 Test 1: Empty query")
    try:
        await engine.process_query("")
        print("   ❌ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✅ Caught expected error: {e}")
    
    # Test 2: Whitespace-only query
    print("\n🧪 Test 2: Whitespace-only query")
    try:
        await engine.process_query("   ")
        print("   ❌ Should have raised ValueError")
    except ValueError as e:
        print(f"   ✅ Caught expected error: {e}")
    
    # Test 3: Valid query (should succeed)
    print("\n🧪 Test 3: Valid query")
    try:
        result = await engine.process_query("What is a contract?")
        print(f"   ✅ Query processed successfully")
        print(f"   Response length: {len(result['response'])} chars")
    except Exception as e:
        print(f"   ⚠️  Error: {e}")


# ============================================================================
# Demo 5: Observability
# ============================================================================


async def demo_observability():
    """Demonstrate observability features."""
    print("\n" + "=" * 70)
    print("DEMO 5: Observability")
    print("=" * 70)
    
    from mahoun.reasoning.adapters import get_reasoning_dependencies
    from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
    
    # Get container
    container = get_reasoning_dependencies()
    
    print("\n📊 Container Status:")
    status = container.get_initialization_status()
    for component, initialized in status.items():
        icon = "✅" if initialized else "⏳"
        print(f"   {icon} {component}: {'initialized' if initialized else 'not initialized'}")
    
    # Access router to trigger initialization
    router = container.query_router
    
    print("\n📊 Container Status (after access):")
    status = container.get_initialization_status()
    for component, initialized in status.items():
        icon = "✅" if initialized else "⏳"
        print(f"   {icon} {component}: {'initialized' if initialized else 'not initialized'}")
    
    # Get router statistics
    print("\n📊 Router Statistics:")
    stats = router.get_stats()
    for key, value in stats.items():
        print(f"   • {key}: {value}")
    
    # Process query and examine metadata
    engine = UnifiedReasoningEngine()
    result = await engine.process_query("What are the contract terms?")
    
    print("\n📊 Query Processing Metadata:")
    metadata = result.get("metadata", {})
    print(f"   • Prompt length: {metadata.get('prompt_length', 'N/A')}")
    print(f"   • Response length: {metadata.get('response_length', 'N/A')}")
    print(f"   • Classification: {metadata.get('classification', {})}")
    print(f"   • Routing: {metadata.get('routing', {})}")


# ============================================================================
# Main
# ============================================================================


async def main():
    """Run all demos."""
    print("\n" + "=" * 70)
    print("REASONING ENGINE DEMO")
    print("Protocol-Based Architecture with Dependency Injection")
    print("=" * 70)
    
    try:
        await demo_basic_usage()
        await demo_dependency_injection()
        await demo_mock_testing()
        await demo_error_handling()
        await demo_observability()
        
        print("\n" + "=" * 70)
        print("✅ ALL DEMOS COMPLETED SUCCESSFULLY")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Demo failed: {e}", exc_info=True)
        print("\n" + "=" * 70)
        print(f"❌ DEMO FAILED: {e}")
        print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
