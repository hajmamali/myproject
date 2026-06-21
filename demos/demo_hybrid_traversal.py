#!/usr/bin/env python3
"""
Hybrid Retrieval Demo (The "Delicacy" Logic)
============================================
Visualizes the "Anchor & Expand" retrieval strategy.

Scenario:
1. User searches for "Termination for default"
2. Vector Search finds "Article 46" (Anchor)
3. Graph Traversal finds:
   - "Contract C-2024" (Uses this article)
   - "Verdict V-99" (Cites this article)
4. Result: Context-aware legal answer
"""

import sys
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("demo_hybrid")


# Mock classes for demonstration without live Neo4j
@dataclass
class MockNeo4jRecord:
    data: dict

    def __getitem__(self, key):
        return self.data[key]


class MockNeo4jDriver:
    def session(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def run(self, query, **kwargs):
        # Return simulated results for specific queries
        return [
            {
                "anchor_id": "art-46",
                "anchor_label": "Article",
                "anchor_text": "Article 46: Termination for Default. The Employer may terminate...",
                "vector_score": 0.92,
                "expansions": [
                    {
                        "id": "c-2024",
                        "label": "Contract",
                        "text": "Metro Line Construction Agreement...",
                        "rel": "USES",
                    },
                    {
                        "id": "v-99",
                        "label": "Verdict",
                        "text": "Court ruling on termination validation...",
                        "rel": "CITES",
                    },
                ],
            }
        ]


async def demo_hybrid_traversal():
    print("\n" + "=" * 60)
    print('🕸️  Graph-Vector Connectivity Demo (The "Delicacy" Layer)')
    print("=" * 60)

    query = "فسخ پیمان به دلیل قصور پیمانکار"
    print(f"\n🔍 Query: {query}")

    # Initialize with Mock Driver
    from mahoun.retrieval.graph_enhanced import GraphEnhancedRetriever

    # We patch the driver for demo purposes
    retriever = GraphEnhancedRetriever(neo4j_driver=MockNeo4jDriver())

    print("\n🚀 Executing Hybrid Retrieval...")
    results = await retriever.retrieve(query)

    print(f"\n✅ Found {len(results)} Context Nodes")
    print("-" * 60)

    for i, res in enumerate(results, 1):
        icon = "⚓" if res.source == "vector_anchor" else "🔗"
        prefix = f"[{res.label}]"

        print(f"{i}. {icon} {prefix:12} {res.node_id}")
        print(f"   Score: {res.score:.4f} ({res.source})")

        if res.relationship:
            print(f"   Relationship: --[{res.relationship}]--> Anchor")

        print(f"   Content: {res.text[:80]}...")
        print("")

    print("=" * 60)
    print("Explanation:")
    print("1. Vector Search found 'Article 46' (The Rule) directly.")
    print("2. Graph Logic found 'Contract C-2024' (The Application) via relation.")
    print(
        "3. This preserves the 'Delicacy' by showing NOT just the law, but where it applied."
    )
    print("=" * 60)


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(demo_hybrid_traversal())
