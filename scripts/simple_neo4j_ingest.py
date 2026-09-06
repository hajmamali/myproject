#!/usr/bin/env python3
"""
Simple direct Neo4j ingestion for ARA judgments
No complex dependencies - just Neo4j driver
"""
import json
import sys
from pathlib import Path
from datetime import datetime

# Add project to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mahoun.graph.neo4j.connection import get_connection

def ingest_judgments(input_file: str, dry_run: bool = True, limit: int = None):
    """
    Simple ingestion to Neo4j
    """
    print("=" * 80)
    print("Simple ARA Judgment Ingestion to Neo4j")
    print("=" * 80)
    print(f"\n📄 Input: {input_file}")
    print(f"🔸 Dry-run: {dry_run}")
    
    # Load data
    with open(input_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    judgments = data['judgments']
    if limit:
        judgments = judgments[:limit]
    
    print(f"📊 Judgments to process: {len(judgments)}")
    
    if dry_run:
        print("\n🔸 DRY-RUN MODE - No actual writes")
        print("\n📋 Sample of what would be ingested:")
        for i, j in enumerate(judgments[:3], 1):
            m = j['metadata']
            print(f"\n{i}. {m['judgment_id']}")
            print(f"   Title: {m['title'][:60]}...")
            print(f"   Quality: {m['quality_score']}")
            print(f"   Court: {m['court_level']}, Area: {m['legal_area']}")
            print(f"   Parties: {len(m['parties'])}, Refs: {len(m['legal_references'])}")
        
        print(f"\n... and {len(judgments) - 3} more")
        print("\n✅ Dry-run complete")
        return
    
    # Real ingestion
    print("\n🔌 Connecting to Neo4j...")
    try:
        conn = get_connection()
        print("   ✅ Connected")
    except Exception as e:
        print(f"   ❌ Connection failed: {e}")
        return
    
    print(f"\n🚀 Starting ingestion of {len(judgments)} judgments...")
    
    success_count = 0
    error_count = 0
    
    for i, judgment in enumerate(judgments, 1):
        m = judgment['metadata']
        
        if i % 10 == 0 or i == 1:
            print(f"   [{i}/{len(judgments)}] Processing {m['judgment_id']}...")
        
        try:
            # Create Judgment node
            cypher = """
            CREATE (j:Judgment:ARACorpus {
                judgment_id: $judgment_id,
                title: $title,
                full_text: $full_text,
                court_level: $court_level,
                legal_area: $legal_area,
                date: $date,
                quality_score: $quality_score,
                word_count: $word_count,
                verdict_type: $verdict_type,
                import_timestamp: datetime(),
                source: 'ara.jri.ac.ir'
            })
            RETURN j.judgment_id as node_id
            """
            
            result = conn._raw_execute(cypher, {
                'judgment_id': m['judgment_id'],
                'title': m['title'],
                'full_text': judgment.get('full_text', '')[:10000],  # Limit size
                'court_level': m['court_level'],
                'legal_area': m['legal_area'],
                'date': m['date'],
                'quality_score': m['quality_score'],
                'word_count': m['word_count'],
                'verdict_type': m['verdict_type']
            })
            
            # Create entity nodes for parties
            for party in m['parties'][:10]:  # Limit to 10
                entity_cypher = """
                MERGE (e:Entity:Party {name: $name})
                WITH e
                MATCH (j:Judgment {judgment_id: $judgment_id})
                MERGE (j)-[:HAS_PARTY]->(e)
                """
                conn._raw_execute(entity_cypher, {
                    'name': party,
                    'judgment_id': m['judgment_id']
                })
            
            # Create entity nodes for legal references
            for ref in m['legal_references'][:10]:  # Limit to 10
                ref_cypher = """
                MERGE (r:Entity:LegalReference {text: $text})
                WITH r
                MATCH (j:Judgment {judgment_id: $judgment_id})
                MERGE (j)-[:CITES]->(r)
                """
                conn._raw_execute(ref_cypher, {
                    'text': ref,
                    'judgment_id': m['judgment_id']
                })
            
            success_count += 1
            
        except Exception as e:
            error_count += 1
            print(f"   ❌ Error on {m['judgment_id']}: {e}")
    
    print("\n" + "=" * 80)
    print("✅ Ingestion Complete!")
    print("=" * 80)
    print(f"Success: {success_count}/{len(judgments)}")
    print(f"Errors: {error_count}/{len(judgments)}")
    
    # Verification query
    print("\n🔍 Verification:")
    count_result = conn._raw_execute("MATCH (j:Judgment:ARACorpus) RETURN count(j) as count")
    if count_result:
        print(f"   Total ARA judgments in graph: {count_result[0]['count']}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Simple Neo4j ingestion for ARA judgments')
    parser.add_argument('--input', required=True, help='Input JSON file')
    parser.add_argument('--dry-run', action='store_true', help='Dry run mode')
    parser.add_argument('--limit', type=int, help='Limit number of judgments')
    
    args = parser.parse_args()
    
    ingest_judgments(args.input, args.dry_run, args.limit)

if __name__ == '__main__':
    main()
