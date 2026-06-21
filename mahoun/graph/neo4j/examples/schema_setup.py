"""
Example: Neo4j Schema Setup
Shows how to initialize and manage database schema
"""
from mahoun.graph.neo4j import (
    get_connection,
    SchemaManager,
    Constraint,
    Index,
    initialize_default_schema,
)


def setup_basic_schema():
    """Setup basic schema with default constraints and indexes"""
    conn = get_connection()
    
    with conn.session() as session:
        # Initialize default RAG schema
        success = initialize_default_schema(session)
        
        if success:
            print("✓ Default schema initialized successfully")
        else:
            print("✗ Failed to initialize schema")


def setup_custom_schema():
    """Setup custom schema with specific constraints and indexes"""
    conn = get_connection()
    
    with conn.session() as session:
        manager = SchemaManager(session)
        
        # Define custom constraints
        constraints = [
            Constraint(
                name="unique_user_email",
                label="User",
                properties=["email"],
                constraint_type="unique"
            ),
            Constraint(
                name="user_name_exists",
                label="User",
                properties=["name"],
                constraint_type="exists"
            ),
        ]
        
        # Define custom indexes
        indexes = [
            Index(
                name="user_name_index",
                label="User",
                properties=["name"],
                index_type="btree"
            ),
            Index(
                name="user_bio_fulltext",
                label="User",
                properties=["bio"],
                index_type="fulltext"
            ),
        ]
        
        # Initialize schema
        success = manager.initialize_schema(constraints, indexes)
        
        if success:
            print("✓ Custom schema initialized successfully")
        else:
            print("✗ Failed to initialize custom schema")


def inspect_schema():
    """Inspect current database schema"""
    conn = get_connection()
    
    with conn.session() as session:
        manager = SchemaManager(session)
        
        # Get all constraints
        constraints = manager.get_constraints()
        print(f"\n📋 Constraints ({len(constraints)}):")
        for c in constraints:
            print(f"  - {c.get('name', 'N/A')}: {c.get('type', 'N/A')}")
        
        # Get all indexes
        indexes = manager.get_indexes()
        print(f"\n📊 Indexes ({len(indexes)}):")
        for idx in indexes:
            print(f"  - {idx.get('name', 'N/A')}: {idx.get('type', 'N/A')}")
        
        # Get node labels
        labels = manager.get_node_labels()
        print(f"\n🏷️  Node Labels ({len(labels)}):")
        for label in sorted(labels):
            print(f"  - {label}")
        
        # Get relationship types
        rel_types = manager.get_relationship_types()
        print(f"\n🔗 Relationship Types ({len(rel_types)}):")
        for rel_type in sorted(rel_types):
            print(f"  - {rel_type}")


if __name__ == "__main__":
    print("=== Neo4j Schema Setup ===\n")
    
    # Setup default schema
    print("1. Setting up default schema...")
    setup_basic_schema()
    
    # Setup custom schema
    print("\n2. Setting up custom schema...")
    setup_custom_schema()
    
    # Inspect schema
    print("\n3. Inspecting schema...")
    inspect_schema()
