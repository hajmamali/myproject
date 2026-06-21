#!/usr/bin/env python
"""
Initialize Legal Knowledge Graph Schema
========================================

This script initializes the Neo4j schema for the legal knowledge graph.
It creates all necessary constraints, indexes, and fulltext indexes.

Usage:
    python graph/neo4j/init_schema.py
"""

import asyncio
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from mahoun.graph.neo4j.connection import get_connection
from mahoun.graph.neo4j.schema import SchemaManager
from mahoun.graph.neo4j.runner import GovernedSchemaRunner


async def main() -> int:
    """Initialize the legal knowledge graph schema"""
    print("=" * 60)
    print("Legal Knowledge Graph Schema Initialization")
    print("=" * 60)
    
    # Get URI from environment
    uri = os.getenv('NEO4J_URI', 'bolt://localhost:7687')
    
    print(f"\n📡 Connecting to Neo4j at {uri}...")
    
    try:
        # Use singleton get_connection() for DI compliance
        connection = get_connection()
        
        # Verify connectivity
        if not connection.verify_connectivity():
            print("❌ Failed to connect to Neo4j")
            return 1
        
        print("✅ Connected successfully")
        
        # Perform health check
        print("\n🏥 Performing health check...")
        health = connection.health_check()
        print(f"   Status: {health['status']}")
        print(f"   Response time: {health['response_time_ms']}ms")
        print(f"   Current nodes: {health['node_count']}")
        
        # GOVERNANCE FIX: Use governed session for schema operations
        from mahoun.core.governance.governance_context import GovernanceContextManager
        
        async with GovernanceContextManager.active_context(
            correlation_id="schema_initialization",
            actor_id="system_schema_manager"
        ):
            with connection.governed_session(
                correlation_id="schema_initialization",
                actor_id="system_schema_manager"
            ) as governed_session:
                # Use adapter to bridge SchemaManager (QueryRunner) with GovernedNeo4jSession
                runner = GovernedSchemaRunner(governed_session)
                manager = SchemaManager(runner)
                
                # Create constraints
                print("\n🔒 Creating constraints for 10 node types...")
                if manager.create_constraints():
                    print("✅ Constraints created successfully")
                else:
                    print("⚠️  Some constraints failed to create")
                
                # Create indexes
                print("\n📇 Creating indexes for frequently searched fields...")
                if manager.create_indexes():
                    print("✅ Indexes created successfully")
                else:
                    print("⚠️  Some indexes failed to create")
                
                # Create fulltext indexes
                print("\n🔍 Creating fulltext indexes for Law, Article, Verdict...")
                if manager.create_fulltext_indexes():
                    print("✅ Fulltext indexes created successfully")
                else:
                    print("⚠️  Some fulltext indexes failed to create")
                
                # Validate schema
                print("\n✓ Validating schema...")
                validation = manager.validate_schema()
                
                print(f"   Constraints: {'✅' if validation['constraints'] else '❌'}")
                print(f"   Indexes: {'✅' if validation['indexes'] else '❌'}")
                print(f"   Fulltext indexes: {'✅' if validation['fulltext_indexes'] else '❌'}")
                
                if all(validation.values()):
                    print("\n🎉 Schema initialization completed successfully!")
                    return 0
                else:
                    print("\n⚠️  Schema initialization completed with warnings")
                    return 1
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    finally:
        if 'connection' in locals():
            connection.close()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
