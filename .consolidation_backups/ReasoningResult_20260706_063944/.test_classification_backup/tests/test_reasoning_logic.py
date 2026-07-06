#!/usr/bin/env python3
"""
MAHOUN Logical Stress-Test: reasoning_logic_test.py
Phase 1: Logic over Data (Hierarchy & Exceptions)
Engineer: Adversarial Systems Engineer
"""

import sys
import os
import logging
import time
import pytest
from dotenv import load_dotenv
from typing import List, Dict, Any

# Load environment variables
load_dotenv()
if not os.getenv("NEO4J_PASSWORD"):
    os.environ["NEO4J_PASSWORD"] = os.getenv("DB_NEO4J_PASSWORD", "dev_password_change_me")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("LogicTest")

try:
    from mahoun.graph.neo4j.connection import get_connection
    from mahoun.graph.neo4j.operations import GraphOperations
    from mahoun.reasoning.reasoning_engine import DeepLegalReasoningEngine
    from mahoun.core.models import ReasoningResult
except ImportError as e:
    logger.error(f"Failed to import core modules: {e}")
    sys.exit(1)

class TestReasoningLogic:
    @classmethod
    def setup_class(cls):
        logger.info("🧠 INITIALIZING REASONING LOGIC TEST...")
        try:
            cls.conn = get_connection()
            cls.connected = cls.conn.verify_connection()
            cls.ops = GraphOperations(connection=cls.conn)
            cls.engine = DeepLegalReasoningEngine()
        except Exception as e:
            logger.error(f"❌ Initialization failed: {e}")
            cls.connected = False

    def setup_method(self):
        """Inject the 'Logic Battle' universe before each test"""
        if not self.connected: return
        logger.info("💉 Injecting conflicting legal universe into Neo4j and Knowledge Base...")
        
        # 1. Inject into Neo4j (for audit and graph retrieval tests)
        self.ops.create_node("Article", {
            "id": "ART_10_TAX",
            "title": "Article 10",
            "text": "Every citizen must pay 10% tax on digital assets.",
            "source": "Civil Law 1400",
            "test_tag": "logic_battle"
        })
        
        self.ops.create_node("Article", {
            "id": "NOTE_1_EXEMPT",
            "title": "Note 1 of Article 10",
            "text": "Students are exempt from digital asset tax.",
            "source": "Civil Law 1401",
            "test_tag": "logic_battle"
        })
        
        self.ops.create_node("Article", {
            "id": "CIRCULAR_505",
            "title": "Circular 505",
            "text": "ALL individuals (including students) must pay 5% tax for server maintenance.",
            "source": "Tax Org 1402",
            "test_tag": "logic_battle"
        })
        
        # 2. Register Rules in Reasoning Engine
        # Rule A: Tax Rule
        self.engine.add_legal_rule(
            "RULE_TAX_10", 
            "trading digital assets", 
            "must pay 10% tax",
            confidence=0.9
        )
        # Rule B: Exemption Rule
        self.engine.add_legal_rule(
            "RULE_STUDENT_EXEMPT", 
            "student trading digital assets", 
            "exempt from digital asset tax",
            confidence=1.0
        )
        # Rule C: Maintenance Fee
        self.engine.add_legal_rule(
            "RULE_MAINTENANCE_5", 
            "using trading servers", 
            "must pay 5% maintenance fee",
            confidence=0.95
        )
        
        # 3. Define Hierarchy in UltraGraphBuilder
        # Note: We simulate the HAS_EXCEPTION relationship in the engine's internal graph
        entities = [
            {"id": "exempt from digital asset tax", "label": "Student Exemption", "type": "LegalExemption"},
            {"id": "must pay 10% tax", "label": "Asset Tax", "type": "LegalObligation"}
        ]
        relationships = [
            {
                "source_id": "exempt from digital asset tax",
                "target_id": "must pay 10% tax",
                "type": "HAS_EXCEPTION",
                "properties": {"test_tag": "logic_battle"}
            }
        ]
        self.engine.graph_builder.build_graph(entities, relationships)
        
        logger.info("✅ Legal logic universe initialized.")

    def teardown_method(self):
        """Cleanup after each test"""
        if not self.connected: return
        logger.info("🧹 Cleaning up logic_battle nodes...")
        query = "MATCH (n) WHERE n.test_tag = 'logic_battle' DETACH DELETE n"
        self.conn.execute_query(query)

    def test_student_bitcoin_logic_trap(self):
        """The 'Logical Trap' Query Verification"""
        if not self.connected: pytest.skip("Neo4j offline")
        
        question = "I am a student trading Bitcoin. According to the laws, do I have to pay any tax or fees? If yes, how much?"
        
        # Facts that should trigger the rules
        facts = [
            "User is a student",
            "User is trading digital assets (Bitcoin)",
            "User is using trading servers"
        ]
        
        context = (
            "Evidence: User identity confirmed as student. Operation: Bitcoin trading on platform servers."
        )
        
        logger.info(f"❓ Querying Reasoning Engine: {question}")
        start_time = time.time()
        
        result = self.engine.deep_reason(question, context, facts=facts)
        latency = time.time() - start_time
        
        # Process output
        answer = result.final_answer
        explanation = self.engine.explain_reasoning(result)
        
        logger.info(f"🤖 Engine Final Answer: {answer}")
        logger.info(f"📍 Inference Path (Visited Nodes): {result.visited_nodes}")
        logger.info(f"🧬 Reasoning Chain Steps: {[step.step for step in result.reasoning_chain]}")
        
        # Success Criteria Verification
        has_10_percent = "10%" in answer or "RULE_TAX_10" in str(result.used_rule_ids)
        # Check if it mentions exemption AND correctly applies it (doesn't just list it)
        has_exemption = any(word in answer.lower() for word in ["exempt", "exemption", "معاف", "معافیت"])
        has_5_percent = "5%" in answer or "RULE_MAINTENANCE_5" in str(result.used_rule_ids)
        
        # Logical Conflict Resolution Check: 
        # If it says "must pay 10%" AND "is exempt" without resolving, it fails Deduction 2.
        overrode_tax = has_exemption and ("not pay 10%" in answer.lower() or "exempt from the 10%" in answer.lower() or "معاف از مالیات ۱۰" in answer)
        
        logger.info(f"Verification Results:")
        logger.info(f"  - 10% Tax Identified: {has_10_percent}")
        logger.info(f"  - 5% Fee Identified: {has_5_percent}")
        logger.info(f"  - Student Exemption Detected: {has_exemption}")
        logger.info(f"  - Conflict Correctally Resolved (Override): {overrode_tax}")
        
        # Assertions
        assert has_10_percent, "Deduction 1 Failed: System did not recognize the existence of 10% asset tax."
        assert has_5_percent, "Deduction 3 Failed: System did not identify the 5% maintenance fee as a separate entity."
        assert has_exemption, "Deduction 2 Failed: System did not detect the student exemption."
        
        # The ultimate test: Did it apply the hierarchy?
        if not overrode_tax:
            logger.warning("⚠️ CRITICAL: System listed both Tax and Exemption but failed to resolve the conflict via HAS_EXCEPTION hierarchy.")
        
        # Bonus Check
        has_hierarchy = any(word in answer.lower() for word in ["hierarchy", "standing", "superior", "note", "circular", "سلسله مراتب", "بالادستی"])
        if has_hierarchy:
            logger.info("🏆 ELITE BONUS: System explicitly explained the legal hierarchy!")

        # Print full explanation for debugging
        report_path = os.path.join(os.getcwd(), "reasoning_report.txt")
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(f"QUESTION: {question}\n")
            f.write(f"FINAL ANSWER: {answer}\n")
            f.write(f"VISITED NODES: {result.visited_nodes}\n")
            f.write("-" * 50 + "\n")
            f.write(explanation)
        
        logger.info(f"📄 Full reasoning report saved to {report_path}")
        
        logger.info("\n" + "="*20 + " FULL REASONING EXPLANATION " + "="*20 + "\n" + explanation + "\n" + "="*60)

        assert overrode_tax, "Logic Failure: System failed to correctly apply exemption over general tax rule."

if __name__ == "__main__":
    pytest.main([__file__, "-s"])
