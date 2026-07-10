"""
Backfill Vectors to Graph
=========================
Utility script to populate Neo4j nodes with GGUF embeddings.
Run this after setting up GGUF models to enable Hybrid Search.

Usage:
    python scripts/backfill_vectors.py --label Verdict --limit 100
"""

import sys
import asyncio
import logging
import argparse
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from mahoun.pipelines.sync.graph_vector_sync import GraphVectorSync
from mahoun.graph.neo4j.schema import SchemaManager

# Mock Neo4j driver for demo/offline environment if specific env var is set
# In production, this would use the real driver
try:
    from mahoun.core.database import get_neo4j_driver

    HAS_NEO4J = True
except ImportError:
    HAS_NEO4J = False

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("backfill")


async def main():
    parser = argparse.ArgumentParser(description="Backfill Graph Vectors")
    parser.add_argument(
        "--label", type=str, default="Verdict", help="Node label to backfill"
    )
    parser.add_argument("--limit", type=int, default=100, help="Max nodes to process")
    args = parser.parse_args()

    print(f"🚀 Starting Backfill for {args.label} (Limit: {args.limit})")

    if not HAS_NEO4J:
        print("⚠️  Neo4j driver not found. Skipping usage.")
        # For demonstration, we just initialize the service to show it loads
        sync_service = GraphVectorSync(neo4j_driver=None)
        print("✅ GraphVectorSync service initialized successfully")
        return

    driver = get_neo4j_driver()
    if not driver:
        print("❌ Could not connect to Neo4j. basic config missing?")
        return

    # Initialize Sync Service
    sync_service = GraphVectorSync(neo4j_driver=driver)
    schema_manager = SchemaManager(driver.session())

    # Ensure Index Exists
    print("🛠️  Verifying Vector Indexes...")
    schema_manager.create_vector_indexes()

    # Run Backfill
    print("🔄 Processing Nodes...")
    await sync_service.backfill_graph_vectors(label=args.label)

    print("\n✅ Backfill Complete!")


if __name__ == "__main__":
    asyncio.run(main())
