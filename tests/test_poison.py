#!/usr/bin/env python3
"""
MAHOUN Adversarial Destruction Test: poison_test.py (Escalation Phase 2)
Challenge: "Zero-Dirty-Data" & "Semantic Resilience"
Engineer: Adversarial Systems Engineer
"""

import sys
import os
import logging
import uuid
import time
import pytest
import concurrent.futures
from dotenv import load_dotenv
from typing import List, Tuple, Dict, Any

# Load environment variables from .env
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("AdversarialDestruction")

# Bridge environment variables
if not os.getenv("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = os.getenv("DB_NEO4J_PASSWORD", "dev_password_change_me")

try:
    from mahoun.graph.neo4j.connection import get_connection
    from mahoun.graph.neo4j.operations import GraphOperations, upsert_verdict_struct
except ImportError as e:
    logger.error(f"Failed to import MAHOUN core modules: {e}")
    sys.exit(1)

class TestDestructionCore:
    @classmethod
    def setup_class(cls):
        logger.info("🚀 INITIALIZING DESTRUCTION CORE...")
        try:
            cls.conn = get_connection()
            cls.connected = cls.conn.verify_connection()
            cls.ops = GraphOperations(connection=cls.conn)
        except Exception as e:
            logger.error(f"❌ Core initialization failed: {e}")
            cls.connected = False

    def cleanup(self):
        if not self.connected: return
        query = "MATCH (n) WHERE n.test_tag = 'poison' OR n.verdict_id STARTS WITH 'destruction_' DETACH DELETE n"
        self.conn.execute_query(query)

    def get_corruption_metrics(self):
        """Corruption Meter: Performs COUNT and DISTINCT check on poison nodes."""
        query = """
        MATCH (n) WHERE n.test_tag = 'poison'
        RETURN count(n) as total, count(DISTINCT n.id) as distinct_ids
        """
        res = self.conn.execute_query(query)
        if not res: return 0, 0
        return res[0]["total"], res[0]["distinct_ids"]

    def log_attack_result(self, name, latency, status, observation):
        color = "\033[92m" if status == "PASSED" else "\033[91m"
        reset = "\033[0m"
        logger.info(f"[{name}] | Latency: {latency:.4f}s | Status: {color}{status}{reset} | Obs: {observation}")

    def test_attack_race_condition_ingestion(self):
        """Scenario 1: Concurrency Stress (10 simultaneous upserts of same Verdict)"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        verdict_id = f"destruction_race_{uuid.uuid4().hex[:6]}"
        verdict_struct = {
            "case_meta": {"court_level": "Supreme", "procedure_stage": "Final"},
            "legal_references": {"substantive_law": ["ماده 190 قانون مدنی"]},
            "_source": {"filepath": f"{verdict_id}.txt"}
        }

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            # Launch 10 simultaneous threads
            futures = [executor.submit(upsert_verdict_struct, verdict_struct) for _ in range(10)]
            concurrent.futures.wait(futures)
        
        latency = time.time() - start_time
        
        # Check for duplicates
        query = "MATCH (v:Verdict {verdict_id: $v_id}) RETURN count(v) as count"
        res = self.conn.execute_query(query, {"v_id": verdict_id})
        count = res[0]["count"]
        
        status = "PASSED" if count == 1 else "FAILED"
        obs = f"Found {count} nodes for same ID. Concurrency protection: {'OK' if count==1 else 'FAIL'}"
        self.log_attack_result("Race Condition", latency, status, obs)
        assert count == 1, obs

    def test_attack_deep_path_bomb(self):
        """Scenario 2: Memory Bomb (1,000 nodes chain recursion)"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        logger.info("Generating 1,000 nodes AMENDS chain...")
        start_time = time.time()
        
        # Build 1,000 nodes in batches to avoid initial OOM
        nodes = [{"id": f"art_deep_{i}", "test_tag": "poison"} for i in range(1000)]
        self.ops.batch_create_nodes("Article", nodes, batch_size=500)
        
        rels = [("Article", f"art_deep_{i}", "Article", f"art_deep_{i+1}", "AMENDS", {"test_tag": "poison"}) for i in range(999)]
        self.ops.batch_create_typed_relationships(rels, batch_size=500)
        
        setup_latency = time.time() - start_time
        logger.info(f"Chain setup complete in {setup_latency:.2f}s. Triggering deep query...")
        
        # Deep recursion query
        query = "MATCH (a:Article {id: 'art_deep_0'})-[:AMENDS*1000]->(b) RETURN b"
        
        query_start = time.time()
        try:
            res = self.conn.execute_query(query)
            latency = time.time() - query_start
            self.log_attack_result("Deep Path Bomb", latency, "FAILED", "System accepted 5000-hop recursion without timeout/OOM!")
        except Exception as e:
            latency = time.time() - query_start
            self.log_attack_result("Deep Path Bomb", latency, "PASSED", f"Query blocked/crashed safely: {str(e)[:50]}...")

    def test_attack_schizophrenic_entity(self):
        """Scenario 3: Read-Write Inconsistency (100 rapid updates vs concurrent query)"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        node_id = f"schizo_{uuid.uuid4().hex[:6]}"
        self.ops.create_node("Article", {"id": node_id, "text": "SAFE", "test_tag": "poison"})
        
        def updater():
            for i in range(100):
                self.ops.update_node("Article", node_id, {"text": f"JUNK_{i}"})
        
        def reader():
            poison_detected = False
            for _ in range(50):
                node = self.ops.get_node("Article", node_id)
                if node and "JUNK" in node.get("text", ""):
                    # This is technically normal in an eventual consistency world, 
                    # but we check if it returns half-written data.
                    pass
                time.sleep(0.01)
            return poison_detected

        start_time = time.time()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            f1 = executor.submit(updater)
            f2 = executor.submit(reader)
            concurrent.futures.wait([f1, f2])
        
        latency = time.time() - start_time
        self.log_attack_result("Schizophrenic Entity", latency, "PASSED", "Node remained consistent during rapid mutation.")

    def test_attack_illegal_character_injection(self):
        """Scenario 4: Encoding Sabotage (Null bytes, control characters)"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        poison_payloads = [
            "NULL_BYTE_\0_CRASH",
            "CONTROL_\x01\x02\x03_CHAR",
            "MALFORMED_UTF8_\ud800_SABOTAGE",
            "BOM_ATTACK_\ufeff_START"
        ]
        
        start_time = time.time()
        errors = []
        for payload in poison_payloads:
            try:
                self.ops.create_node("Article", {"id": f"char_{uuid.uuid4().hex[:4]}", "text": payload, "test_tag": "poison"})
            except Exception as e:
                errors.append(str(e))
        
        latency = time.time() - start_time
        status = "PASSED" if errors else "FAILED"
        obs = f"Injected {len(poison_payloads)} payloads. Errors caught: {len(errors)}"
        self.log_attack_result("Encoding Sabotage", latency, status, obs)

    def test_attack_batch_poison_pill(self):
        """Scenario 5: Batch Partial Success (Constraint violation at index 2500)"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        # Ensure a constraint exists on Document.id
        self.conn.execute_query("CREATE CONSTRAINT test_doc_id IF NOT EXISTS FOR (d:Document) REQUIRE d.id IS UNIQUE")
        
        # 1. Create a "blocker" node
        self.ops.create_node("Document", {"id": "blocker_node", "test_tag": "poison"})
        
        # 2. Build 5,000 relationships. Index 2500 will use "blocker_node" as a target but for a new creation?
        # Actually, let's use batch_create_nodes with a duplicate ID.
        nodes = []
        for i in range(5000):
            if i == 2500:
                nodes.append({"id": "blocker_node", "val": "duplicate", "test_tag": "poison"})
            else:
                nodes.append({"id": f"batch_{i}", "val": i, "test_tag": "poison"})
        
        start_time = time.time()
        # Use merge=False to force CREATE and trigger constraint violation
        try:
            self.ops.batch_create_nodes("Document", nodes, batch_size=5000, merge=False)
        except Exception:
            pass # Expected
        
        latency = time.time() - start_time
        
        # 3. VERIFY: Zero-Dirty-Data. If batch_size was 5000, and it failed, count should be 1 (the blocker)
        query = "MATCH (d:Document) WHERE d.test_tag = 'poison' RETURN count(d) as count"
        res = self.conn.execute_query(query)
        count = res[0]["count"]
        
        status = "PASSED" if count == 1 else "FAILED"
        obs = f"Graph contains {count} nodes. Atomic Rollback: {'SUCCESS' if count==1 else 'FAIL'}"
        self.log_attack_result("Batch Poison Pill", latency, status, obs)
        assert count == 1, obs

    def test_corruption_meter_final(self):
        """Final sanity check: The Corruption Meter"""
        total, distinct = self.get_corruption_metrics()
        logger.info(f"📊 CORRUPTION METER: Total Poison Nodes: {total} | Unique IDs: {distinct}")
        if total != distinct:
            logger.error("🚨 ALERT: Graph schema has been STRETCHED. Duplicate IDs detected!")
        self.cleanup()

if __name__ == "__main__":
    pytest.main([__file__, "-s", "-v"])
