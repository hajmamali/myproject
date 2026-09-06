#!/usr/bin/env python3
"""
Test with Python Neo4j driver directly
"""
import sys
import os
sys.path.insert(0, '/home/haji/Desktop/KingMahouN')

def main():
    try:
        print("🔍 Testing Python Neo4j driver...")
        
        # Try importing neo4j
        from neo4j import GraphDatabase
        print("✅ Neo4j driver imported successfully")
        
        # Connect to Neo4j
        uri = "bolt://localhost:7687"
        auth = ("neo4j", "dev_neo4j_password_2026")
        
        print(f"🔌 Connecting to {uri}...")
        
        driver = GraphDatabase.driver(uri, auth=auth)
        
        # Test connection
        with driver.session() as session:
            result = session.run("RETURN 'Connection successful!' AS message")
            record = result.single()
            print(f"✅ Neo4j response: {record['message']}")
            
            # Test creating a simple judgment node
            print("🔧 Testing judgment node creation...")
            cypher = """
            CREATE (j:Judgment:ARACorpus {
                judgment_id: 'PYTHON_TEST_001',
                title: 'تست با Python Driver',
                court_level: 'supreme',
                quality_score: 0.9,
                created_at: datetime()
            })
            RETURN j.judgment_id AS created_id
            """
            
            result = session.run(cypher)
            record = result.single()
            print(f"✅ Created judgment: {record['created_id']}")
            
            # Count existing judgments
            count_result = session.run("MATCH (j:Judgment:ARACorpus) RETURN count(j) as count")
            count_record = count_result.single()
            print(f"📊 Total ARA judgments in graph: {count_record['count']}")
            
            # Clean up test node
            session.run("MATCH (j:Judgment {judgment_id: 'PYTHON_TEST_001'}) DELETE j")
            print("✅ Cleanup completed")
        
        driver.close()
        print("\n🎉 Python driver test successful! Neo4j is accessible.")
        return 0
        
    except ImportError as e:
        print(f"❌ Neo4j driver not available: {e}")
        print("💡 Install with: pip install neo4j")
        return 1
        
    except Exception as e:
        print(f"❌ Connection error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    result = main()
    print(f"\nExit code: {result}")
    sys.exit(result)