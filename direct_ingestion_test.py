#!/usr/bin/env python3
"""
Direct ingestion test - minimal version
"""

import sys
import os
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

from scripts.build_judgment_kg import (
    parse_judgments_from_json, 
    CypherBridge,
    EnterpriseJudgmentCompiler
)
from pathlib import Path

def main():
    print("🚀 Starting minimal ingestion test...")
    
    # Load first 5 judgments
    data_file = Path('/home/haji/Desktop/KingMahouN/data/ara_top_333/judgments_top_333.json')
    judgments = parse_judgments_from_json(data_file)
    
    # Limit to 5 for testing
    test_judgments = judgments[:5]
    print(f"📊 Testing with {len(test_judgments)} judgments")
    
    try:
        # Test Neo4j connection
        bridge = CypherBridge()
        
        # Simple test query
        print("🔍 Testing Neo4j connection...")
        result = bridge.execute("RETURN 'Connection OK' AS status;")
        print(f"✅ Neo4j connected: {result.strip()}")
        
        # Test constraint creation
        print("📐 Testing constraint creation...")
        constraint = "CREATE CONSTRAINT test_judgment_id IF NOT EXISTS FOR (j:TestJudgment) REQUIRE j.id IS UNIQUE;"
        bridge.execute(constraint)
        print("✅ Constraints created successfully")
        
        # Test simple node creation
        print("🔧 Testing node creation...")
        node_cypher = """
        CREATE (j:TestJudgment {
            id: 'TEST_001',
            title: 'تست رای',
            created_at: datetime()
        })
        RETURN j.id AS created_id
        """
        result = bridge.execute(node_cypher)
        print(f"✅ Node created: {result.strip()}")
        
        # Clean up test node
        cleanup = "MATCH (j:TestJudgment {id: 'TEST_001'}) DELETE j"
        bridge.execute(cleanup)
        print("✅ Cleanup completed")
        
        print("\n🎉 All tests passed! Neo4j is ready for ingestion.")
        
        # Now try real ingestion with 3 judgments
        print("\n🚀 Starting real ingestion with 3 judgments...")
        
        compiler = EnterpriseJudgmentCompiler()
        result = compiler.compile(test_judgments[:3], batch_size=3)
        
        print(f"✅ Ingestion completed!")
        print(f"   Status: {result['status']}")
        print(f"   Processed: {result['processed']}")
        print(f"   Entities: {result['entities_created']}")
        print(f"   Relationships: {result['relationships_created']}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    exit_code = main()
    with open('/tmp/ingestion_test_result.txt', 'w') as f:
        f.write(f"Exit code: {exit_code}\n")
    sys.exit(exit_code)