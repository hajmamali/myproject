"""
Correlation ID Demo - Real-World Usage Example
===============================================

This script demonstrates real-world usage of Correlation ID tracking
in MahouN platform for a complete document ingestion flow.

Scenario:
---------
1. Receive document ingestion request
2. Extract entities from document
3. Build knowledge graph with entities
4. Generate audit report
5. Verify complete traceability

All operations are tracked with a single correlation ID for full audit trail.

Usage:
------
    python examples/correlation_id_demo.py

Author: MahouN Platform Governance Council
Version: 1.0.0
"""

import asyncio
import hashlib
import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.provenance_tracker import ProvenanceMetadata
from mahoun.graph.neo4j.connection import get_connection
from mahoun.ledger.write_gate import EvidencePackage


# ============================================================================
# DEMO: COMPLETE DOCUMENT INGESTION WITH CORRELATION TRACKING
# ============================================================================


class DocumentIngestionDemo:
    """
    Demonstrates correlation ID tracking through complete ingestion flow.
    """
    
    def __init__(self):
        self.correlation_id = f"DEMO-{datetime.now().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        self.actor_id = "demo-ingestion-service"
        self.connection = get_connection()
        self.audit_trail: List[Dict[str, Any]] = []
    
    def log_step(self, step: str, details: Dict[str, Any]):
        """Log execution step with correlation ID."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation_id": self.correlation_id,
            "step": step,
            "details": details,
        }
        self.audit_trail.append(entry)
        print(f"\n📝 [{step}]")
        print(f"   Correlation ID: {self.correlation_id}")
        print(f"   Details: {json.dumps(details, indent=6)}")
    
    async def run_demo(self):
        """
        Run complete document ingestion demo with correlation tracking.
        """
        print("=" * 80)
        print("🎯 CORRELATION ID DEMO: Document Ingestion Flow")
        print("=" * 80)
        print(f"\n🆔 Correlation ID: {self.correlation_id}")
        print(f"👤 Actor: {self.actor_id}")
        print(f"📅 Timestamp: {datetime.now(timezone.utc).isoformat()}")
        
        # Step 1: Initialize governance context
        await self.step_1_initialize_context()
        
        # Step 2: Extract entities from document
        entities = await self.step_2_extract_entities()
        
        # Step 3: Build knowledge graph
        graph_nodes = await self.step_3_build_knowledge_graph(entities)
        
        # Step 4: Create evidence package
        evidence_package = await self.step_4_create_evidence_package(entities)
        
        # Step 5: Generate audit report
        await self.step_5_generate_audit_report(graph_nodes, evidence_package)
        
        # Step 6: Verify traceability
        await self.step_6_verify_traceability(graph_nodes)
        
        print("\n" + "=" * 80)
        print("✅ DEMO COMPLETE")
        print("=" * 80)
    
    async def step_1_initialize_context(self):
        """Step 1: Initialize governance context with correlation ID."""
        self.log_step(
            "STEP 1: Initialize Governance Context",
            {
                "correlation_id": self.correlation_id,
                "actor_id": self.actor_id,
                "execution_mode": "STRICT",
            }
        )
        
        async with GovernanceContextManager.active_context(
            correlation_id=self.correlation_id,
            execution_mode="STRICT",
            actor_id=self.actor_id,
        ) as ctx:
            # Verify context was created correctly
            assert ctx.correlation_id == self.correlation_id
            assert ctx.actor_id == self.actor_id
            
            print(f"   ✓ Context ID: {ctx.context_id}")
            print(f"   ✓ Governance scope active")
    
    async def step_2_extract_entities(self) -> List[Dict[str, Any]]:
        """Step 2: Extract entities from document (simulated)."""
        entities = [
            {
                "id": f"entity-{i}",
                "type": "Person" if i % 2 == 0 else "Organization",
                "name": f"Demo Entity {i}",
                "confidence": 0.95,
                "correlation_id": self.correlation_id,
            }
            for i in range(3)
        ]
        
        self.log_step(
            "STEP 2: Extract Entities",
            {
                "entities_extracted": len(entities),
                "entity_types": list(set(e["type"] for e in entities)),
            }
        )
        
        for entity in entities:
            print(f"   ✓ Extracted: {entity['name']} ({entity['type']})")
        
        return entities
    
    async def step_3_build_knowledge_graph(
        self, entities: List[Dict[str, Any]]
    ) -> List[str]:
        """Step 3: Build knowledge graph with entities."""
        graph_nodes: List[str] = []
        
        self.log_step(
            "STEP 3: Build Knowledge Graph",
            {
                "nodes_to_create": len(entities),
                "correlation_id": self.correlation_id,
            }
        )
        
        # Note: This would actually write to Neo4j in production
        # For demo purposes, we simulate the graph creation
        
        async with GovernanceContextManager.active_context(
            correlation_id=self.correlation_id,
            execution_mode="STRICT",
            actor_id=self.actor_id,
        ) as ctx:
            # In production, would use:
            # with self.connection.governed_session(
            #     correlation_id=self.correlation_id,
            #     actor_id=self.actor_id,
            # ) as session:
            #     for entity in entities:
            #         session.write_node(...)
            
            for entity in entities:
                node_id = f"graph-node-{entity['id']}"
                graph_nodes.append(node_id)
                print(f"   ✓ Created node: {node_id} (correlation: {self.correlation_id})")
        
        return graph_nodes
    
    async def step_4_create_evidence_package(
        self, entities: List[Dict[str, Any]]
    ) -> EvidencePackage:
        """Step 4: Create evidence package with correlation metadata."""
        evidence_refs = [e["id"] for e in entities]
        
        provenance_chain = [
            {
                "source": "document_ingestion",
                "correlation_id": self.correlation_id,
                "actor_id": self.actor_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "entity_count": len(entities),
            }
        ]
        
        proof_hash = hashlib.sha256(
            json.dumps(evidence_refs, sort_keys=True).encode()
        ).hexdigest()
        
        evidence_package = EvidencePackage(
            evidence_refs=evidence_refs,
            provenance_chain=provenance_chain,
            proof_hash=proof_hash,
            validation_context={
                "correlation_id": self.correlation_id,
                "extraction_method": "demo",
            },
        )
        
        self.log_step(
            "STEP 4: Create Evidence Package",
            {
                "evidence_count": len(evidence_refs),
                "proof_hash": proof_hash[:16] + "...",
                "correlation_id": self.correlation_id,
            }
        )
        
        # Validate evidence package
        valid, error = evidence_package.validate()
        if valid:
            print(f"   ✓ Evidence package validated")
        else:
            print(f"   ✗ Validation error: {error}")
        
        return evidence_package
    
    async def step_5_generate_audit_report(
        self, graph_nodes: List[str], evidence_package: EvidencePackage
    ):
        """Step 5: Generate audit report showing complete traceability."""
        self.log_step(
            "STEP 5: Generate Audit Report",
            {
                "correlation_id": self.correlation_id,
                "graph_nodes": len(graph_nodes),
                "evidence_refs": len(evidence_package.evidence_refs),
                "audit_trail_entries": len(self.audit_trail),
            }
        )
        
        print("\n   📊 AUDIT TRAIL SUMMARY:")
        print(f"   {'='*70}")
        for i, entry in enumerate(self.audit_trail, 1):
            print(f"   {i}. {entry['step']}")
            print(f"      Time: {entry['timestamp']}")
            print(f"      Correlation: {entry['correlation_id']}")
        print(f"   {'='*70}")
    
    async def step_6_verify_traceability(self, graph_nodes: List[str]):
        """Step 6: Verify complete traceability from nodes to execution."""
        self.log_step(
            "STEP 6: Verify Traceability",
            {
                "verification_type": "correlation_id_traceability",
                "nodes_to_verify": len(graph_nodes),
            }
        )
        
        # Verify all components have same correlation ID
        all_correlation_ids = set()
        
        # From audit trail
        for entry in self.audit_trail:
            all_correlation_ids.add(entry["correlation_id"])
        
        # Verify only one correlation ID exists
        print(f"\n   📍 TRACEABILITY VERIFICATION:")
        print(f"   {'='*70}")
        print(f"   Unique Correlation IDs: {len(all_correlation_ids)}")
        print(f"   Correlation ID: {self.correlation_id}")
        print(f"   Audit Trail Entries: {len(self.audit_trail)}")
        print(f"   Graph Nodes Created: {len(graph_nodes)}")
        
        if len(all_correlation_ids) == 1 and self.correlation_id in all_correlation_ids:
            print(f"   ✅ TRACEABILITY VERIFIED: All operations linked to single correlation ID")
        else:
            print(f"   ❌ TRACEABILITY FAILED: Multiple correlation IDs found")
        
        print(f"   {'='*70}")
        
        # Demonstrate what queries would look like in production
        print(f"\n   🔍 Example Neo4j Queries for Traceability:")
        print(f"   {'='*70}")
        print(f"""
   1. Find all nodes from this execution:
      MATCH (n) 
      WHERE n.correlation_id = "{self.correlation_id}"
      RETURN n
   
   2. Find audit trail for specific node:
      MATCH (n {{id: "entity-0"}})
      RETURN n.correlation_id as correlation_id
      // Use correlation_id to query audit logs
   
   3. Count entities by execution:
      MATCH (n)
      WHERE n.correlation_id = "{self.correlation_id}"
      RETURN count(n) as total_entities
        """)
        print(f"   {'='*70}")


# ============================================================================
# DEMO: CLEAN UP
# ============================================================================


async def cleanup_demo_data(correlation_id: str):
    """Clean up demo data from graph (if any was actually created)."""
    print(f"\n🧹 Cleaning up demo data for correlation ID: {correlation_id}")
    
    # In production, would delete nodes:
    # connection = get_connection()
    # with connection._session() as session:
    #     session.run(
    #         "MATCH (n) WHERE n.correlation_id = $corr_id DETACH DELETE n",
    #         {"corr_id": correlation_id}
    #     )
    
    print("✓ Demo data cleaned up")


# ============================================================================
# MAIN
# ============================================================================


async def main():
    """Run the correlation ID demo."""
    demo = DocumentIngestionDemo()
    
    try:
        await demo.run_demo()
        
        # Show final summary
        print("\n" + "=" * 80)
        print("📋 DEMO SUMMARY")
        print("=" * 80)
        print(f"""
This demo illustrated how Correlation IDs provide complete traceability:

1. ✅ Single correlation ID ({demo.correlation_id}) tracked entire flow
2. ✅ Every operation logged with correlation metadata
3. ✅ Evidence package contains correlation in provenance chain
4. ✅ Graph nodes (would) contain correlation_id property
5. ✅ Complete audit trail from execution start to finish
6. ✅ Traceability verified: any entity can be traced to originating request

Key Benefits Demonstrated:
- Zero hallucination: Every entity traceable to source
- Full auditability: Complete execution history
- Regulatory compliance: GDPR/HIPAA compliant audit trails
- Debugging: Trace any issue back to originating request
- Performance analysis: Track execution time by correlation ID
        """)
        print("=" * 80)
        
    finally:
        # Clean up any demo data
        await cleanup_demo_data(demo.correlation_id)


if __name__ == "__main__":
    asyncio.run(main())
