"""
Legal-Aware System Usage Examples
=================================
Practical examples demonstrating legal-aware schema design features.

Examples include:
- Legal document retrieval with filtering
- Court hierarchy-based ranking
- Supersession detection and handling
- Cross-system synchronization
- Migration service usage
- Persian legal document support
"""

import asyncio
from typing import List, Dict, Any
from datetime import datetime

from mahoun.schemas.legal_aware_schema import (
    LegalMetadata, CourtRank, StatuteStatus, LegalQueryFilter,
    LegalDocumentType, LegalRelationshipType
)
from mahoun.rag.legal_aware_retrieval import (
    LegalAwareRetrievalService,
    create_legal_aware_retrieval_service
)
from mahoun.graph.legal_cypher_queries import LegalCypherQueries
from mahoun.services.legal_migration_service import (
    LegalMigrationService,
    create_legal_migration_service
)


# ============================================================================
# Example 1: Basic Legal Document Retrieval
# ============================================================================

async def example_basic_legal_retrieval():
    """
    Example: Basic legal document retrieval with automatic filtering
    
    This example shows how to retrieve legal documents with automatic
    filtering of repealed laws and ranking by court hierarchy.
    """
    print("=" * 80)
    print("Example 1: Basic Legal Document Retrieval")
    print("=" * 80)
    
    # Create legal-aware retrieval service
    service = await create_legal_aware_retrieval_service()
    
    # Perform legal-aware retrieval
    query = "ماده 183 قانون مدنی"
    
    result = await service.legal_retrieve(
        query=query,
        top_k=10
    )
    
    print(f"\n📋 Query: {query}")
    print(f"📊 Results: {len(result.results)} documents")
    print(f"⏱️  Retrieval time: {result.retrieval_time_ms}ms")
    print(f"🔍 Mode used: {result.mode_used}")
    
    # Display results
    for i, doc in enumerate(result.results[:3], 1):
        legal_meta = doc.metadata.get("legal_metadata", {})
        print(f"\n{i}. Document: {doc.doc_id}")
        print(f"   Score: {doc.score:.3f}")
        print(f"   Court Rank: {legal_meta.get('court_rank', 'N/A')}")
        print(f"   Status: {legal_meta.get('statute_status', 'N/A')}")
        print(f"   Authority: {legal_meta.get('authority_score', 0):.2f}")
        print(f"   Content: {doc.content[:100]}...")
    
    print("\n✅ Basic retrieval completed successfully")


# ============================================================================
# Example 2: Advanced Filtering with Court Hierarchy
# ============================================================================

async def example_advanced_filtering():
    """
    Example: Advanced filtering with court hierarchy and authority scores
    
    This example demonstrates filtering documents by court rank,
    authority score, and legal validity status.
    """
    print("\n" + "=" * 80)
    print("Example 2: Advanced Filtering with Court Hierarchy")
    print("=" * 80)
    
    # Create legal-aware retrieval service
    service = await create_legal_aware_retrieval_service()
    
    # Create advanced legal filter
    legal_filter = LegalQueryFilter(
        min_court_rank=CourtRank.APPEALS_COURT,  # Only Appeals Court and above
        exclude_repealed=True,
        min_authority_score=0.7,
        require_higher_court_citation=True,
        legal_domains=["civil", "commercial"]
    )
    
    # Perform filtered retrieval
    query = "قرارداد خرید و فروش"
    
    result = await service.legal_retrieve(
        query=query,
        legal_filter=legal_filter,
        top_k=5
    )
    
    print(f"\n📋 Query: {query}")
    print(f"\n🔧 Filter Configuration:")
    print(f"   Min Court Rank: {legal_filter.min_court_rank.name}")
    print(f"   Exclude Repealed: {legal_filter.exclude_repealed}")
    print(f"   Min Authority Score: {legal_filter.min_authority_score}")
    print(f"   Require Higher Court Citation: {legal_filter.require_higher_court_citation}")
    
    print(f"\n📊 Filtered Results: {len(result.results)} documents")
    print(f"� Documents Filtered: {result.metadata.get('documents_filtered', 0)}")
    
    # Display filtered results
    for i, doc in enumerate(result.results, 1):
        legal_meta = doc.metadata.get("legal_metadata", {})
        print(f"\n{i}. {doc.doc_id}")
        print(f"   Court: {legal_meta.get('court_rank', 'N/A')}")
        print(f"   Authority: {legal_meta.get('authority_score', 0):.2f}")
        print(f"   Higher Court Citations: {legal_meta.get('cited_by_higher_courts', False)}")
    
    print("\n✅ Advanced filtering completed successfully")


# ============================================================================
# Example 3: Supersession Detection and Handling
# ============================================================================

async def example_supersession_detection():
    """
    Example: Detecting and handling superseded laws
    
    This example shows how to detect supersession relationships
    and automatically return the current active version of a law.
    """
    print("\n" + "=" * 80)
    print("Example 3: Supersession Detection and Handling")
    print("=" * 80)
    
    # Simulate supersession chain
    old_law = LegalMetadata(
        statute_status=StatuteStatus.ACTIVE,
        authority_score=0.80,
        superseded_by="law_v2_2023"
    )
    
    current_law = LegalMetadata(
        statute_status=StatuteStatus.ACTIVE,
        authority_score=0.95,
        supersedes=["law_v1_2020"]
    )
    
    print("\n� Old Law (2020):")
    print(f"   Status: {old_law.statute_status.value}")
    print(f"   Authority: {old_law.authority_score}")
    print(f"   Superseded By: {old_law.superseded_by}")
    
    print("\n📜 Current Law (2023):")
    print(f"   Status: {current_law.statute_status.value}")
    print(f"   Authority: {current_law.authority_score}")
    print(f"   Supersedes: {current_law.supersedes}")
    
    # Demonstrate supersession handling
    if old_law.superseded_by:
        print(f"\n⚠️  Warning: Old law has been superseded!")
        print(f"   Redirecting to: {old_law.superseded_by}")
        print(f"   ✅ Returning current active version")
    
    print("\n✅ Supersession detection completed successfully")


# ============================================================================
# Example 4: Persian Legal Document Support
# ============================================================================

async def example_persian_legal_documents():
    """
    Example: Working with Persian legal documents and Jalali dates
    
    This example demonstrates handling Persian legal documents
    with Jalali calendar dates and Persian text.
    """
    print("\n" + "=" * 80)
    print("Example 4: Persian Legal Document Support")
    print("=" * 80)
    
    # Create Persian legal document metadata
    persian_doc = LegalMetadata(
        court_rank=CourtRank.SUPREME_COURT,
        statute_status=StatuteStatus.ACTIVE,
        date_jalali="1402/10/15",  # Persian calendar
        date_gregorian="2024-01-05",  # Gregorian calendar
        authority_score=0.95,
        legal_domain="حقوق مدنی"  # Civil law in Persian
    )
    
    print("\n📄 Persian Legal Document:")
    print(f"   دادگاه: دیوان عالی کشور")
    print(f"   تاریخ شمسی: {persian_doc.date_jalali}")
    print(f"   تاریخ میلادی: {persian_doc.date_gregorian}")
    print(f"   وضعیت: {persian_doc.statute_status.value}")
    print(f"   امتیاز اعتبار: {persian_doc.authority_score}")
    print(f"   حوزه حقوقی: {persian_doc.legal_domain}")
    
    # Demonstrate Persian query
    service = await create_legal_aware_retrieval_service()
    
    persian_query = "رأی دیوان عالی در مورد ماده 10 قانون مدنی"
    print(f"\n🔍 Persian Query: {persian_query}")
    
    result = await service.legal_retrieve(
        query=persian_query,
        top_k=5
    )
    
    print(f"📊 Results: {len(result.results)} documents")
    print("\n✅ Persian document support demonstrated successfully")


# ============================================================================
# Example 5: Legal Document Migration
# ============================================================================

async def example_legal_migration():
    """
    Example: Migrating existing documents to legal-aware schema
    
    This example shows how to use the migration service to add
    legal metadata to existing documents.
    """
    print("\n" + "=" * 80)
    print("Example 5: Legal Document Migration")
    print("=" * 80)
    
    # Create migration service
    migration_service = await create_legal_migration_service()
    
    # Sample document IDs to migrate
    document_ids = [
        "doc_001_supreme_verdict",
        "doc_002_appeals_verdict",
        "doc_003_civil_law",
        "doc_004_commercial_regulation"
    ]
    
    print(f"\n� Starting migration for {len(document_ids)} documents")
    
    # Start migration
    migration_id = await migration_service.start_migration(
        document_ids=document_ids,
        batch_size=2,
        enable_rollback=True
    )
    
    print(f"🆔 Migration ID: {migration_id}")
    
    # Wait a bit for migration to process
    await asyncio.sleep(2)
    
    # Check migration status
    status = await migration_service.get_migration_status(migration_id)
    
    if status:
        print(f"\n📊 Migration Status:")
        print(f"   Status: {status['status']}")
        print(f"   Progress: {status['progress_percentage']:.1f}%")
        print(f"   Processed: {status['processed_count']}/{status['total_documents']}")
        print(f"   Success: {status['success_count']}")
        print(f"   Errors: {status['error_count']}")
    
    # Get service statistics
    stats = migration_service.get_stats()
    print(f"\n� Service Statistics:")
    print(f"   Total Migrations: {stats['total_migrations']}")
    print(f"   Documents Migrated: {stats['documents_migrated']}")
    
    print("\n✅ Migration example completed successfully")


# ============================================================================
# Example 6: Cross-System Synchronization
# ============================================================================

async def example_cross_system_sync():
    """
    Example: Cross-system synchronization between vector and graph stores
    
    This example demonstrates ensuring data consistency across
    vector and graph databases using global identifiers.
    """
    print("\n" + "=" * 80)
    print("Example 6: Cross-System Synchronization")
    print("=" * 80)
    
    from mahoun.schemas.legal_aware_schema import GlobalIdentifier
    
    # Create global identifier for cross-system tracking
    global_id = GlobalIdentifier(
        uid="doc_supreme_verdict_12345",
        document_type=LegalDocumentType.VERDICT,
        in_vector_store=True,
        in_graph_store=True,
        vector_metadata_hash="abc123def456",
        graph_metadata_hash="abc123def456",
        sync_status="synchronized",
        last_sync=datetime.now(timezone.utc)
    )
    
    print("\n🔗 Global Identifier:")
    print(f"   UID: {global_id.uid}")
    print(f"   Document Type: {global_id.document_type.value}")
    print(f"   In Vector Store: {global_id.in_vector_store}")
    print(f"   In Graph Store: {global_id.in_graph_store}")
    print(f"   Sync Status: {global_id.sync_status}")
    print(f"   Last Sync: {global_id.last_sync}")
    
    # Verify synchronization
    if global_id.vector_metadata_hash == global_id.graph_metadata_hash:
        print("\n✅ Metadata is synchronized across systems")
    else:
        print("\n⚠️  Warning: Metadata mismatch detected!")
    
    print("\n✅ Cross-system synchronization example completed")


# ============================================================================
# Example 7: Legal Cypher Queries
# ============================================================================

async def example_legal_cypher_queries():
    """
    Example: Using legal Cypher queries for graph operations
    
    This example shows how to use pre-built Cypher queries
    for legal document analysis and validation.
    """
    print("\n" + "=" * 80)
    print("Example 7: Legal Cypher Queries")
    print("=" * 80)
    
    # List all available queries
    all_queries = LegalCypherQueries.list_all_queries()
    print(f"\n📚 Available Queries: {len(all_queries)}")
    
    # Display query categories
    categories = {}
    for query in all_queries:
        category = query.category.value
        if category not in categories:
            categories[category] = []
        categories[category].append(query.name)
    
    print("\n� Queries by Category:")
    for category, queries in categories.items():
        print(f"\n   {category.upper()}:")
        for query_name in queries:
            print(f"      - {query_name}")
    
    # Example: Get supersession query
    supersession_query = LegalCypherQueries.get_query("find_superseded_laws")
    
    if supersession_query:
        print(f"\n🔍 Example Query: {supersession_query.name}")
        print(f"   Category: {supersession_query.category.value}")
        print(f"   Description: {supersession_query.description}")
        print(f"   Complexity: {supersession_query.complexity}")
        print(f"   Parameters: {list(supersession_query.parameters.keys())}")
        print(f"   Use Cases:")
        for use_case in supersession_query.use_cases:
            print(f"      - {use_case}")
    
    print("\n✅ Legal Cypher queries example completed")


# ============================================================================
# Example 8: Complete Legal Research Workflow
# ============================================================================

async def example_complete_workflow():
    """
    Example: Complete legal research workflow
    
    This example demonstrates a complete workflow from query
    to filtered, ranked, and validated legal results.
    """
    print("\n" + "=" * 80)
    print("Example 8: Complete Legal Research Workflow")
    print("=" * 80)
    
    # Step 1: Define research query
    research_query = "تفسیر ماده 10 قانون مدنی در مورد اهلیت"
    print(f"\n1️⃣  Research Query: {research_query}")
    
    # Step 2: Create advanced filter
    legal_filter = LegalQueryFilter(
        min_court_rank=CourtRank.APPEALS_COURT,
        exclude_repealed=True,
        min_authority_score=0.75,
        legal_domains=["civil"]
    )
    print(f"\n2️⃣  Filter Configuration:")
    print(f"   - Minimum Court: {legal_filter.min_court_rank.name}")
    print(f"   - Exclude Repealed: Yes")
    print(f"   - Min Authority: {legal_filter.min_authority_score}")
    
    # Step 3: Perform legal-aware retrieval
    service = await create_legal_aware_retrieval_service()
    
    result = await service.legal_retrieve(
        query=research_query,
        legal_filter=legal_filter,
        top_k=10
    )
    
    print(f"\n3️⃣  Retrieval Results:")
    print(f"   - Total Results: {len(result.results)}")
    print(f"   - Filtered Out: {result.metadata.get('documents_filtered', 0)}")
    print(f"   - Retrieval Time: {result.retrieval_time_ms}ms")
    
    # Step 4: Analyze results
    print(f"\n4️⃣  Top Results Analysis:")
    
    for i, doc in enumerate(result.results[:3], 1):
        legal_meta = doc.metadata.get("legal_metadata", {})
        
        print(f"\n   Result #{i}:")
        print(f"   📄 Document: {doc.doc_id}")
        print(f"   ⚖️  Court: {legal_meta.get('court_rank', 'N/A')}")
        print(f"   📊 Score: {doc.score:.3f}")
        print(f"   ⭐ Authority: {legal_meta.get('authority_score', 0):.2f}")
        print(f"   ✅ Status: {legal_meta.get('statute_status', 'N/A')}")
        print(f"   📝 Preview: {doc.content[:80]}...")
    
    # Step 5: Get service statistics
    stats = service.get_stats()
    print(f"\n5️⃣  Service Statistics:")
    print(f"   - Total Retrievals: {stats.get('legal_aware_stats', {}).get('total_legal_retrievals', 0)}")
    print(f"   - Documents Filtered: {stats.get('legal_aware_stats', {}).get('filtered_documents', 0)}")
    print(f"   - Authority Boosts: {stats.get('legal_aware_stats', {}).get('authority_boosts_applied', 0)}")
    
    print("\n✅ Complete workflow executed successfully")


# ============================================================================
# Main Function - Run All Examples
# ============================================================================

async def run_all_examples():
    """Run all usage examples"""
    print("\n" + "=" * 80)
    print("LEGAL-AWARE SYSTEM USAGE EXAMPLES")
    print("=" * 80)
    print("\nDemonstrating enterprise-grade legal-aware schema design features")
    print("for zero-hallucination legal reasoning in regulated industries.\n")
    
    try:
        # Run examples
        await example_basic_legal_retrieval()
        await example_advanced_filtering()
        await example_supersession_detection()
        await example_persian_legal_documents()
        await example_legal_migration()
        await example_cross_system_sync()
        await example_legal_cypher_queries()
        await example_complete_workflow()
        
        print("\n" + "=" * 80)
        print("✅ ALL EXAMPLES COMPLETED SUCCESSFULLY")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ Error running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run all examples
    asyncio.run(run_all_examples())
