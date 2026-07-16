import pytest
pytest.importorskip("neo4j")
"""
Test Neo4j Vector Schema
========================
Verifies that SchemaManager correctly attempts to create vector indexes.
Uses unittest.mock to avoid needing a live Neo4j database.
"""

import unittest
from unittest.mock import MagicMock, call
from mahoun.graph.neo4j.schema import SchemaManager
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


class TestNeo4jVectorSchema(unittest.TestCase):
    def setUp(self):
        self.mock_session = MagicMock()
        self.manager = SchemaManager(self.mock_session)

    def test_create_vector_indexes(self):
        """Test creates correct vector indexes for Verdict and Article"""
        # Execute
        result = self.manager.create_vector_indexes()

        # Verify
        self.assertTrue(result)

        # Check calls
        calls = self.mock_session.run.call_args_list
        self.assertEqual(len(calls), 2, "Should create 2 indexes")

        # Verify Verdict Index
        verdict_call = str(calls[0])
        self.assertIn("CREATE VECTOR INDEX verdict_embedding_idx", verdict_call)
        self.assertIn("FOR (n:Verdict)", verdict_call)
        self.assertIn("vector.dimensions`: 768", verdict_call)

        # Verify Article Index
        article_call = str(calls[1])
        self.assertIn("CREATE VECTOR INDEX article_embedding_idx", article_call)
        self.assertIn("FOR (n:Article)", article_call)
        self.assertIn("vector.dimensions`: 768", article_call)

        print("✅ Neo4j Vector Schema verification passed!")


if __name__ == "__main__":
    unittest.main()
