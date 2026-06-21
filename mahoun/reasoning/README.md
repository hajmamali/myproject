# Reasoning Layer - Protocol-Based Architecture

## Overview

The reasoning layer implements a sophisticated protocol-based architecture with dependency injection, enabling:

- **Loose coupling** through protocol interfaces
- **Testability** via mock injection
- **Type safety** with runtime validation
- **Observability** with full metadata tracking
- **Graceful degradation** on failures

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                   UnifiedReasoningEngine                     │
│                      (Facade Pattern)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ depends on
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              ReasoningDependencyContainer                    │
│           (Dependency Injection Container)                   │
└─────────────────────────────────────────────────────────────┘
                              │
                ┌─────────────┼─────────────┐
                ▼             ▼             ▼
    ┌──────────────┐  ┌──────────────┐  ┌──────────────┐
    │QueryRouter   │  │RAGService    │  │Orchestrator  │
    │Protocol      │  │Protocol      │  │Protocol      │
    └──────────────┘  └──────────────┘  └──────────────┘
```

## Core Components

### 1. Protocols (`mahoun/core/protocols.py`)

Defines the contracts that all implementations must satisfy:

- `QueryRouterProtocol`: Query classification and routing
- `RAGServiceProtocol`: Document retrieval
- `ModelOrchestratorProtocol`: Model lifecycle management
- `ModelDriverProtocol`: LLM inference
- `ReasoningEngineProtocol`: End-to-end query processing

### 2. Dependency Container (`mahoun/reasoning/adapters.py`)

Manages dependency lifecycle with:

- **Lazy initialization**: Resources created on first access
- **Singleton pattern**: One instance per dependency
- **Thread safety**: Lock-based synchronization
- **Protocol validation**: Runtime type checking

### 3. Unified Engine (`mahoun/reasoning/unified_engine.py`)

High-level facade that orchestrates:

1. Query routing and classification
2. Context retrieval via RAG
3. Model capability selection
4. Prompt engineering
5. Inference execution
6. Response assembly with metadata

## Usage

### Basic Usage (Production)

```python
from mahoun.reasoning.unified_engine import UnifiedReasoningEngine

# Create engine (uses DI container automatically)
engine = UnifiedReasoningEngine()

# Process query
result = await engine.process_query("What are the contract terms?")

print(result["response"])
print(f"Confidence: {result['confidence']}")
print(f"Model: {result['model_used']}")
```

### Advanced Usage (Custom Dependencies)

```python
from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
from mahoun.reasoning.adapters import get_reasoning_dependencies

# Get container
container = get_reasoning_dependencies()

# Access individual components
router = container.query_router
rag_service = container.rag_service
orchestrator = container.model_orchestrator

# Create engine with explicit dependencies
engine = UnifiedReasoningEngine(
    router=router,
    orchestrator=orchestrator
)

result = await engine.process_query("Generate Cypher query")
```

### Testing with Mocks

```python
from unittest.mock import Mock, AsyncMock
from mahoun.reasoning.unified_engine import UnifiedReasoningEngine
from mahoun.reasoning.adapters import MockDependencyContainer
from mahoun.core.protocols import QueryRouterProtocol

# Create mock router
mock_router = Mock(spec=QueryRouterProtocol)
mock_router.route = AsyncMock(return_value=...)

# Create mock container
container = MockDependencyContainer(query_router=mock_router)

# Create engine with mocks
engine = UnifiedReasoningEngine(router=container.query_router)

# Test
result = await engine.process_query("test")
assert result["response"] == "expected"
```

## Response Format

All queries return a standardized response:

```python
{
    "response": str,              # Generated answer
    "query_type": str,            # Classified type (e.g., "legal_inquiry")
    "model_used": str,            # Model identifier
    "capability": str,            # Capability used (coding/reasoning/general)
    "confidence": float,          # Classification confidence [0, 1]
    "context_sources": int,       # Number of retrieved documents
    "metadata": {
        "classification": {...},  # Classification details
        "routing": {...},         # Routing metadata
        "prompt_length": int,     # Prompt size
        "response_length": int    # Response size
    }
}
```

## Query Types

The system supports multiple query types:

- `CONTRACT`: Contract-related queries
- `DELAY_ANALYSIS`: Delay analysis queries
- `LEGAL_INQUIRY`: Legal reasoning queries
- `TECHNICAL_INQUIRY`: Technical queries
- `CYPHER_GENERATION`: Graph query generation
- `GENERAL`: General queries

## Model Capabilities

Queries are routed to appropriate models:

- `CODING`: Qwen-Coder (Cypher, technical)
- `REASONING`: Granite-Legal (legal analysis)
- `GENERAL`: Fallback model

## Error Handling

The system provides comprehensive error handling:

```python
try:
    result = await engine.process_query(query)
except ValueError as e:
    # Invalid input (empty query, etc.)
    print(f"Invalid input: {e}")
except RuntimeError as e:
    # Processing failure (routing, retrieval, inference)
    print(f"Processing failed: {e}")
```

## Observability

Full observability through:

- **Logging**: Structured logs at each pipeline stage
- **Metadata**: Complete processing metadata in response
- **Statistics**: Router statistics via `router.get_stats()`
- **Container status**: `container.get_initialization_status()`

## Thread Safety

All components are thread-safe:

- Container uses double-checked locking
- Router delegates to thread-safe components
- Engine is stateless (safe for concurrent requests)

## Performance

- **Lazy initialization**: Fast startup, resources loaded on demand
- **Singleton pattern**: No redundant initialization
- **Warm model swapping**: Models stay loaded between requests
- **Efficient caching**: LRU cache for container instance

## Testing

Comprehensive test suite:

- `tests/test_reasoning_protocols.py`: Protocol and DI tests
- `tests/contracts/test_reasoning_protocols_contracts.py`: Contract verification

Run tests:

```bash
pytest tests/test_reasoning_protocols.py -v
pytest tests/contracts/test_reasoning_protocols_contracts.py -v
```

## Type Checking

All code is fully type-checked:

```bash
mypy mahoun/core/protocols.py
mypy mahoun/reasoning/adapters.py
mypy mahoun/reasoning/unified_engine.py
```

## Design Patterns

- **Protocol-Oriented Programming**: Interface-based design
- **Dependency Injection**: Loose coupling, testability
- **Facade Pattern**: Simplified interface to complex subsystem
- **Strategy Pattern**: Pluggable routing and model selection
- **Singleton Pattern**: Shared resource management
- **Factory Pattern**: Object creation abstraction
- **Template Method**: Standardized processing pipeline

## Best Practices

1. **Always use protocols**: Never depend on concrete implementations
2. **Validate at boundaries**: Use `validate_protocol_implementation()`
3. **Handle errors gracefully**: Catch and wrap exceptions
4. **Log extensively**: Use structured logging
5. **Test with mocks**: Use `MockDependencyContainer` for tests
6. **Reset in teardown**: Call `reset_global_container()` after tests

## Migration Guide

If you have existing code using `QueryRouter` directly:

### Before:
```python
from mahoun.rag.query_router import QueryRouter

router = QueryRouter()
result = await router.route(query)
```

### After:
```python
from mahoun.reasoning.unified_engine import UnifiedReasoningEngine

engine = UnifiedReasoningEngine()
result = await engine.process_query(query)
```

Or if you need just the router:

```python
from mahoun.reasoning.adapters import get_query_router

router = get_query_router()
result = await router.route(query)
```

## Future Enhancements

- [ ] Async container initialization
- [ ] Health checks for dependencies
- [ ] Metrics collection (Prometheus)
- [ ] Circuit breaker pattern
- [ ] Request tracing (OpenTelemetry)
- [ ] Configuration hot-reload
- [ ] Multi-tenancy support

## References

- [PEP 544 - Protocols](https://peps.python.org/pep-0544/)
- [Dependency Injection in Python](https://python-dependency-injector.ets-labs.org/)
- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
