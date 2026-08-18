import sys
import os
import unittest
import threading
from datetime import datetime, timezone
from mahoun.graph.neo4j.query_builder import CypherQueryBuilder
from mahoun.ledger.blockchain import ImmutableLedger
from mahoun.ledger.models import LedgerEntry


class TestHardening(unittest.TestCase):
    def test_query_builder_tenant_isolation(self):
        builder = CypherQueryBuilder(tenant_id="tenant_123")
        query = builder.match("LegalDoc", {"id": "doc1"}).build()

        # Verify tenant_id is in parameters and query
        self.assertEqual(builder.parameters["_tenant_id"], "tenant_123")
        self.assertIn("tenant_id: $_tenant_id", query)
        self.assertIn("MATCH (n:LegalDoc", query)

    def test_query_builder_parameterization(self):
        builder = CypherQueryBuilder()
        builder.where_exact("n", "status", "active")
        query = builder.build()

        # Verify no string injection
        self.assertIn("WHERE n.status = $where_n_status_", query)
        # Verify value is in parameters
        param_key = [
            k for k in builder.parameters.keys() if k.startswith("where_n_status_")
        ][0]
        self.assertEqual(builder.parameters[param_key], "active")

    def test_ledger_thread_safety(self):
        # Test basic append with locking (local)
        ledger = ImmutableLedger()  # In-memory genesis only

        def append_worker(i):
            entry = LedgerEntry(
                verdict_id=f"v_{i}",
                case_id=f"c_{i}",
                referenced_ltm_nodes=[],
                referenced_facts=[],
                confidence=1.0,
                invariant_version="1.0",
                guard_mode="STRICT",
                created_at=datetime.now(timezone.utc),
            )
            ledger.append(entry)

        threads = []
        for i in range(10):
            t = threading.Thread(target=append_worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Chain should have 11 blocks (1 genesis + 10 appends)
        self.assertEqual(len(ledger.chain), 11)
        self.assertTrue(ledger.verify_integrity())


if __name__ == "__main__":
    unittest.main()
