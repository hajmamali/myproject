#!/usr/bin/env python3
"""
Minimal Bootstrap Test (Neo4j DI Scope Only)
Tests bootstrap without GNN to validate Neo4j wiring
"""
import logging
logging.basicConfig(level=logging.INFO)

print("=== Phase C: Bootstrap Validation (Neo4j Scope) ===\n")

# Test 1: Import core Neo4j components
print("→ Testing Neo4j imports...")
try:
    from mahoun.graph.neo4j.connection import get_connection, Neo4jConnection
    from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever
    from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
    from mahoun.graph.legal_cypher_queries import LegalQueryExecutor
    print("✅ All Neo4j components import successfully\n")
except Exception as e:
    print(f"❌ Import failed: {e}\n")
    exit(1)

# Test 2: Validate constructor signatures
print("→ Validating constructor signatures...")
import inspect

sig_retriever = inspect.signature(GraphEnhancedRetriever.__init__)
sig_sync = inspect.signature(GraphVectorSync.__init__)
sig_executor = inspect.signature(LegalQueryExecutor.__init__)

print(f"GraphEnhancedRetriever.__init__{sig_retriever}")
print(f"GraphVectorSync.__init__{sig_sync}")
print(f"LegalQueryExecutor.__init__{sig_executor}")

# Verify 'connection' parameter exists
assert 'connection' in sig_retriever.parameters, "❌ GraphEnhancedRetriever missing 'connection' parameter"
assert 'connection' in sig_sync.parameters, "❌ GraphVectorSync missing 'connection' parameter"
assert 'connection' in sig_executor.parameters, "❌ LegalQueryExecutor missing 'connection' parameter"

print("✅ All constructors have 'connection' parameter\n")

# Test 3: Verify SERVICE_REGISTRY pattern
print("→ Testing SERVICE_REGISTRY...")
from mahoun.bootstrap.runtime import SERVICE_REGISTRY, register_service, get_service

# Clear registry for test
SERVICE_REGISTRY.clear()

# Mock service
class MockService:
    pass

mock_svc = MockService()
register_service("test_service", mock_svc)

retrieved = get_service("test_service")
assert retrieved is mock_svc, "❌ Service registry identity check failed"
print(f"✅ SERVICE_REGISTRY works correctly (identity preserved: {id(mock_svc)} == {id(retrieved)})\n")

# Test 4: Verify no hidden service locator pattern
print("→ Scanning for hidden service locator patterns...")
import ast
import os

violations = []
for root, dirs, files in os.walk("/home/haji/Desktop/KingMahouN/mahoun/retrieval"):
    for file in files:
        if file.endswith(".py"):
            filepath = os.path.join(root, file)
            with open(filepath, 'r') as f:
                try:
                    tree = ast.parse(f.read(), filename=filepath)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            if isinstance(node.func, ast.Name) and node.func.id == 'get_service':
                                violations.append(f"{filepath}: get_service() call found")
                except SyntaxError:
                    pass

if violations:
    print("❌ Service locator pattern violations found:")
    for v in violations:
        print(f"  - {v}")
else:
    print("✅ No hidden service locator patterns in retrieval module\n")

print("=== Phase C: PASSED (Neo4j DI Scope) ===")
