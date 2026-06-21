"""
Tests for Neo4j Schema Management
"""
import pytest
pytest.importorskip("neo4j")

# Skip these tests by default - require running Neo4j server
pytestmark = pytest.mark.integration

from mahoun.graph.neo4j import (
    get_connection,
    SchemaManager,
    Constraint,
    Index,
)


@pytest.fixture
def session():
    """Get Neo4j session for testing"""
    conn = get_connection()
    with conn.session() as session:
        yield session


@pytest.fixture
def manager(session):
    """Get SchemaManager instance"""
    return SchemaManager(session)


def test_create_unique_constraint(manager):
    """Test creating unique constraint"""
    constraint = Constraint(
        name="test_unique_constraint",
        label="TestNode",
        properties=["test_id"],
        constraint_type="unique"
    )
    
    success = manager.create_constraint(constraint)
    assert success
    
    # Cleanup
    manager.drop_constraint("test_unique_constraint")


def test_create_exists_constraint(manager):
    """Test creating existence constraint"""
    constraint = Constraint(
        name="test_exists_constraint",
        label="TestNode",
        properties=["required_field"],
        constraint_type="exists"
    )
    
    success = manager.create_constraint(constraint)
    assert success
    
    # Cleanup
    manager.drop_constraint("test_exists_constraint")


def test_create_node_key_constraint(manager):
    """Test creating node key constraint"""
    constraint = Constraint(
        name="test_node_key",
        label="TestNode",
        properties=["field1", "field2"],
        constraint_type="node_key"
    )
    
    success = manager.create_constraint(constraint)
    assert success
    
    # Cleanup
    manager.drop_constraint("test_node_key")


def test_create_btree_index(manager):
    """Test creating B-tree index"""
    index = Index(
        name="test_btree_index",
        label="TestNode",
        properties=["indexed_field"],
        index_type="btree"
    )
    
    success = manager.create_index(index)
    assert success
    
    # Cleanup
    manager.drop_index("test_btree_index")


def test_create_fulltext_index(manager):
    """Test creating fulltext index"""
    index = Index(
        name="test_fulltext_index",
        label="TestNode",
        properties=["text_field"],
        index_type="fulltext"
    )
    
    success = manager.create_index(index)
    assert success
    
    # Cleanup
    manager.drop_index("test_fulltext_index")


def test_get_constraints(manager):
    """Test getting all constraints"""
    constraints = manager.get_constraints()
    assert isinstance(constraints, list)


def test_get_indexes(manager):
    """Test getting all indexes"""
    indexes = manager.get_indexes()
    assert isinstance(indexes, list)


def test_get_node_labels(manager):
    """Test getting node labels"""
    labels = manager.get_node_labels()
    assert isinstance(labels, set)


def test_get_relationship_types(manager):
    """Test getting relationship types"""
    rel_types = manager.get_relationship_types()
    assert isinstance(rel_types, set)


def test_initialize_schema(manager):
    """Test initializing schema with multiple constraints and indexes"""
    constraints = [
        Constraint(
            name="test_init_constraint_1",
            label="TestInit",
            properties=["id"],
            constraint_type="unique"
        ),
        Constraint(
            name="test_init_constraint_2",
            label="TestInit",
            properties=["name"],
            constraint_type="exists"
        ),
    ]
    
    indexes = [
        Index(
            name="test_init_index_1",
            label="TestInit",
            properties=["name"],
            index_type="btree"
        ),
    ]
    
    success = manager.initialize_schema(constraints, indexes)
    assert success
    
    # Cleanup
    manager.drop_constraint("test_init_constraint_1")
    manager.drop_constraint("test_init_constraint_2")
    manager.drop_index("test_init_index_1")


def test_create_constraints_legal_kg(manager):
    """Test creating all constraints for legal knowledge graph"""
    success = manager.create_constraints()
    assert success
    
    # Verify constraints were created
    constraints = manager.get_constraints()
    constraint_names = {c.get('name') for c in constraints}
    
    required_constraints = {
        "unique_law_id", "unique_article_id", "unique_note_id",
        "unique_clause_id", "unique_court_id", "unique_branch_id",
        "unique_verdict_id", "unique_case_id", "unique_person_id",
        "unique_party_id"
    }
    
    assert required_constraints.issubset(constraint_names)


def test_create_indexes_legal_kg(manager):
    """Test creating indexes for legal knowledge graph"""
    success = manager.create_indexes()
    assert success
    
    # Verify indexes were created
    indexes = manager.get_indexes()
    index_names = {idx.get('name') for idx in indexes}
    
    required_indexes = {
        "law_name_idx", "law_year_idx", "article_number_idx",
        "court_name_idx", "verdict_case_number_idx", "verdict_date_idx"
    }
    
    assert required_indexes.issubset(index_names)


def test_create_fulltext_indexes_legal_kg(manager):
    """Test creating fulltext indexes for legal knowledge graph"""
    success = manager.create_fulltext_indexes()
    assert success
    
    # Verify fulltext indexes were created
    indexes = manager.get_indexes()
    index_names = {idx.get('name') for idx in indexes}
    
    required_fulltext = {
        "law_fulltext_idx", "article_fulltext_idx", "verdict_fulltext_idx"
    }
    
    assert required_fulltext.issubset(index_names)


def test_validate_schema_legal_kg(manager):
    """Test schema validation for legal knowledge graph"""
    # First create the schema
    manager.create_constraints()
    manager.create_indexes()
    manager.create_fulltext_indexes()
    
    # Validate
    validation_results = manager.validate_schema()
    
    assert validation_results["constraints"] is True
    assert validation_results["indexes"] is True
    assert validation_results["fulltext_indexes"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
