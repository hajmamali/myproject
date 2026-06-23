"""
Neo4j Schema Management
Handles constraints, indexes, and schema migrations
"""

import logging
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Set

logger = logging.getLogger(__name__)

# ============================================================================
# Schema Identifier Allowlists and Validator (Patch Group C)
# Prevent schema drift via unconstrained f-string DDL interpolation.
# ============================================================================

_SCHEMA_IDENTIFIER_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")
_ALLOWED_CONSTRAINT_TYPES = frozenset({"unique", "exists", "node_key"})
_ALLOWED_INDEX_TYPES = frozenset({"btree", "fulltext", "vector"})


def _validate_schema_identifier(value: str, kind: str) -> str:
    """Reject any schema identifier that is not a clean ASCII word.

    Raises ValueError for empty, non-ASCII, or pattern-violating identifiers.
    This prevents Cypher injection via f-string DDL interpolation.
    """
    if not value or not value.strip():
        raise ValueError(f"Schema {kind} must be a non-empty string")
    if not _SCHEMA_IDENTIFIER_RE.match(value):
        raise ValueError(
            f"Schema {kind} '{value}' contains forbidden characters. Allowed pattern: ^[A-Za-z][A-Za-z0-9_]*$"
        )
    return value


class QueryRunner(Protocol):
    """Minimal query execution interface for schema operations."""

    def run(self, query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Execute a Cypher query and return results as list of dicts."""
        ...


@dataclass
class Constraint:
    """Schema constraint definition"""

    name: str
    label: str
    properties: List[str]
    constraint_type: str  # 'unique', 'exists', 'node_key'


@dataclass
class Index:
    """Schema index definition"""

    name: str
    label: str
    properties: List[str]
    index_type: str  # 'btree', 'fulltext', 'vector'


class SchemaManager:
    """Manages Neo4j database schema"""

    def __init__(self, runner: QueryRunner):
        self._runner = runner

    def create_constraint(self, constraint: Constraint) -> bool:
        """Create a constraint in the database."""
        try:
            # PATCH GROUP C: validate all identifiers before DDL interpolation
            _validate_schema_identifier(constraint.name, "constraint name")
            _validate_schema_identifier(constraint.label, "node label")
            for prop in constraint.properties:
                _validate_schema_identifier(prop, "property name")
            if constraint.constraint_type not in _ALLOWED_CONSTRAINT_TYPES:
                raise ValueError(
                    f"Unknown constraint type: {constraint.constraint_type!r}. "
                    f"Allowed: {sorted(_ALLOWED_CONSTRAINT_TYPES)}"
                )

            if constraint.constraint_type == "unique":
                query = (
                    f"CREATE CONSTRAINT {constraint.name} IF NOT EXISTS "
                    f"FOR (n:{constraint.label}) "
                    f"REQUIRE n.{constraint.properties[0]} IS UNIQUE"
                )
            elif constraint.constraint_type == "exists":
                query = (
                    f"CREATE CONSTRAINT {constraint.name} IF NOT EXISTS "
                    f"FOR (n:{constraint.label}) "
                    f"REQUIRE n.{constraint.properties[0]} IS NOT NULL"
                )
            else:  # node_key
                props = ", ".join([f"n.{p}" for p in constraint.properties])
                query = (
                    f"CREATE CONSTRAINT {constraint.name} IF NOT EXISTS "
                    f"FOR (n:{constraint.label}) "
                    f"REQUIRE ({props}) IS NODE KEY"
                )

            self._runner.run(query)
            logger.info(f"Created constraint: {constraint.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create constraint {constraint.name}: {e}")
            return False

    def create_index(self, index: Index) -> bool:
        """Create an index in the database."""
        try:
            # PATCH GROUP C: validate all identifiers before DDL interpolation
            _validate_schema_identifier(index.name, "index name")
            _validate_schema_identifier(index.label, "node label")
            for prop in index.properties:
                _validate_schema_identifier(prop, "property name")
            if index.index_type not in _ALLOWED_INDEX_TYPES:
                raise ValueError(f"Unknown index type: {index.index_type!r}. Allowed: {sorted(_ALLOWED_INDEX_TYPES)}")

            if index.index_type == "btree":
                props = ", ".join([f"n.{p}" for p in index.properties])
                query = f"CREATE INDEX {index.name} IF NOT EXISTS FOR (n:{index.label}) ON ({props})"
            elif index.index_type == "fulltext":
                props = ", ".join([f"n.{p}" for p in index.properties])
                query = f"CREATE FULLTEXT INDEX {index.name} IF NOT EXISTS FOR (n:{index.label}) ON EACH [{props}]"
            else:  # vector
                query = (
                    f"CREATE VECTOR INDEX {index.name} IF NOT EXISTS "
                    f"FOR (n:{index.label}) "
                    f"ON n.{index.properties[0]} "
                    f"OPTIONS {{indexConfig: {{`vector.dimensions`: 768, "
                    f"`vector.similarity_function`: 'cosine'}}}}"
                )

            self._runner.run(query)
            logger.info(f"Created index: {index.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index.name}: {e}")
            return False

    def drop_constraint(self, constraint_name: str) -> bool:
        """Drop a constraint from the database."""
        try:
            # PATCH GROUP C: validate identifier before DDL
            _validate_schema_identifier(constraint_name, "constraint name")
            query = f"DROP CONSTRAINT {constraint_name} IF EXISTS"
            self._runner.run(query)
            logger.info(f"Dropped constraint: {constraint_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop constraint {constraint_name}: {e}")
            return False

    def drop_index(self, index_name: str) -> bool:
        """Drop an index from the database."""
        try:
            # PATCH GROUP C: validate identifier before DDL
            _validate_schema_identifier(index_name, "index name")
            query = f"DROP INDEX {index_name} IF EXISTS"
            self._runner.run(query)
            logger.info(f"Dropped index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            return False
            return False

    def get_constraints(self) -> List[Dict]:
        """Get all constraints in the database"""
        try:
            result = self._runner.run("SHOW CONSTRAINTS")
            return result
        except Exception as e:
            logger.error(f"Failed to get constraints: {e}")
            return []

    def get_indexes(self) -> List[Dict]:
        """Get all indexes in the database"""
        try:
            result = self._runner.run("SHOW INDEXES")
            return result
        except Exception as e:
            logger.error(f"Failed to get indexes: {e}")
            return []

    def get_node_labels(self) -> Set[str]:
        """Get all node labels in the database"""
        try:
            result = self._runner.run("CALL db.labels()")
            return {record["label"] for record in result}
        except Exception as e:
            logger.error(f"Failed to get node labels: {e}")
            return set()

    def get_relationship_types(self) -> Set[str]:
        """Get all relationship types in the database"""
        try:
            result = self._runner.run("CALL db.relationshipTypes()")
            return {record["relationshipType"] for record in result}
        except Exception as e:
            logger.error(f"Failed to get relationship types: {e}")
            return set()

    def initialize_schema(self, constraints: List[Constraint], indexes: List[Index]) -> bool:
        """Initialize database schema with constraints and indexes"""
        success = True

        # Create constraints first
        for constraint in constraints:
            if not self.create_constraint(constraint):
                success = False

        # Then create indexes
        for index in indexes:
            if not self.create_index(index):
                success = False

        return success

    def create_constraints(self) -> bool:
        """Create all constraints for legal knowledge graph (10 node types)"""
        constraints = [
            # Law node constraints
            Constraint(
                name="unique_law_id",
                label="Law",
                properties=["id"],
                constraint_type="unique",
            ),
            # Article node constraints
            Constraint(
                name="unique_article_id",
                label="Article",
                properties=["id"],
                constraint_type="unique",
            ),
            # Note node constraints
            Constraint(
                name="unique_note_id",
                label="Note",
                properties=["id"],
                constraint_type="unique",
            ),
            # Clause node constraints
            Constraint(
                name="unique_clause_id",
                label="Clause",
                properties=["id"],
                constraint_type="unique",
            ),
            # Court node constraints
            Constraint(
                name="unique_court_id",
                label="Court",
                properties=["id"],
                constraint_type="unique",
            ),
            # Branch node constraints
            Constraint(
                name="unique_branch_id",
                label="Branch",
                properties=["id"],
                constraint_type="unique",
            ),
            # Verdict node constraints
            Constraint(
                name="unique_verdict_id",
                label="Verdict",
                properties=["id"],
                constraint_type="unique",
            ),
            # Case node constraints
            Constraint(
                name="unique_case_id",
                label="Case",
                properties=["id"],
                constraint_type="unique",
            ),
            # Person node constraints
            Constraint(
                name="unique_person_id",
                label="Person",
                properties=["id"],
                constraint_type="unique",
            ),
            # Party node constraints
            Constraint(
                name="unique_party_id",
                label="Party",
                properties=["id"],
                constraint_type="unique",
            ),
        ]

        success = True
        for constraint in constraints:
            if not self.create_constraint(constraint):
                success = False

        logger.info(f"Created {len(constraints)} constraints for legal knowledge graph")
        return success

    def create_indexes(self) -> bool:
        """Create indexes for frequently searched fields"""
        indexes = [
            # Law indexes
            Index(
                name="law_name_idx",
                label="Law",
                properties=["name"],
                index_type="btree",
            ),
            Index(
                name="law_year_idx",
                label="Law",
                properties=["year"],
                index_type="btree",
            ),
            Index(
                name="law_category_idx",
                label="Law",
                properties=["category"],
                index_type="btree",
            ),
            # Article indexes
            Index(
                name="article_number_idx",
                label="Article",
                properties=["number"],
                index_type="btree",
            ),
            Index(
                name="article_law_id_idx",
                label="Article",
                properties=["law_id"],
                index_type="btree",
            ),
            Index(
                name="article_law_name_idx",
                label="Article",
                properties=["law_name"],
                index_type="btree",
            ),
            # Court indexes
            Index(
                name="court_name_idx",
                label="Court",
                properties=["name"],
                index_type="btree",
            ),
            Index(
                name="court_type_idx",
                label="Court",
                properties=["type"],
                index_type="btree",
            ),
            Index(
                name="court_province_idx",
                label="Court",
                properties=["province"],
                index_type="btree",
            ),
            Index(
                name="court_city_idx",
                label="Court",
                properties=["city"],
                index_type="btree",
            ),
            # Verdict indexes
            Index(
                name="verdict_case_number_idx",
                label="Verdict",
                properties=["case_number"],
                index_type="btree",
            ),
            Index(
                name="verdict_date_idx",
                label="Verdict",
                properties=["date"],
                index_type="btree",
            ),
            Index(
                name="verdict_type_idx",
                label="Verdict",
                properties=["type"],
                index_type="btree",
            ),
            # Case indexes
            Index(
                name="case_number_idx",
                label="Case",
                properties=["case_number"],
                index_type="btree",
            ),
            Index(
                name="case_date_idx",
                label="Case",
                properties=["date"],
                index_type="btree",
            ),
            # Vector Indexes (for GGUF embeddings - 768d)
            Index(
                name="verdict_embedding_idx",
                label="Verdict",
                properties=["embedding"],
                index_type="vector",
            ),
            Index(
                name="article_embedding_idx",
                label="Article",
                properties=["embedding"],
                index_type="vector",
            ),
        ]

        success = True
        for index in indexes:
            if not self.create_index(index):
                success = False

        logger.info(f"Created {len(indexes)} indexes for legal knowledge graph")
        return success

    def create_fulltext_indexes(self) -> bool:
        """Create fulltext indexes for Law, Article, and Verdict"""
        indexes = [
            # Law fulltext index
            Index(
                name="law_fulltext_idx",
                label="Law",
                properties=["name", "full_name", "full_text"],
                index_type="fulltext",
            ),
            # Article fulltext index
            Index(
                name="article_fulltext_idx",
                label="Article",
                properties=["content"],
                index_type="fulltext",
            ),
            # Verdict fulltext index
            Index(
                name="verdict_fulltext_idx",
                label="Verdict",
                properties=["content", "reasoning"],
                index_type="fulltext",
            ),
        ]

        success = True
        for index in indexes:
            if not self.create_index(index):
                success = False

        logger.info(f"Created {len(indexes)} fulltext indexes for legal knowledge graph")
        return success

    def create_vector_indexes(self) -> bool:
        """Create vector indexes explicitly for hybrid retrieval"""
        indexes = [
            Index(
                name="verdict_embedding_idx",
                label="Verdict",
                properties=["embedding"],
                index_type="vector",
            ),
            Index(
                name="article_embedding_idx",
                label="Article",
                properties=["embedding"],
                index_type="vector",
            ),
        ]

        success = True
        for index in indexes:
            if not self.create_index(index):
                success = False

        logger.info(f"Created {len(indexes)} vector indexes for hybrid retrieval")
        return success

    def validate_schema(self) -> Dict[str, bool]:
        """Validate that all required constraints and indexes exist"""
        validation_results = {
            "constraints": False,
            "indexes": False,
            "fulltext_indexes": False,
        }

        try:
            # Check constraints
            existing_constraints = self.get_constraints()
            constraint_names = {c.get("name") for c in existing_constraints}

            required_constraints = {
                "unique_law_id",
                "unique_article_id",
                "unique_note_id",
                "unique_clause_id",
                "unique_court_id",
                "unique_branch_id",
                "unique_verdict_id",
                "unique_case_id",
                "unique_person_id",
                "unique_party_id",
            }

            validation_results["constraints"] = required_constraints.issubset(constraint_names)

            # Check indexes
            existing_indexes = self.get_indexes()
            index_names = {idx.get("name") for idx in existing_indexes}

            required_indexes = {
                "law_name_idx",
                "law_year_idx",
                "article_number_idx",
                "court_name_idx",
                "verdict_case_number_idx",
                "verdict_date_idx",
            }

            validation_results["indexes"] = required_indexes.issubset(index_names)

            # Check fulltext indexes
            required_fulltext = {
                "law_fulltext_idx",
                "article_fulltext_idx",
                "verdict_fulltext_idx",
            }

            validation_results["fulltext_indexes"] = required_fulltext.issubset(index_names)

            logger.info(f"Schema validation results: {validation_results}")

        except Exception as e:
            logger.error(f"Schema validation failed: {e}")

        return validation_results


# Default schema for RAG system
DEFAULT_CONSTRAINTS = [
    Constraint(
        name="unique_document_id",
        label="Document",
        properties=["id"],
        constraint_type="unique",
    ),
    Constraint(
        name="unique_chunk_id",
        label="Chunk",
        properties=["id"],
        constraint_type="unique",
    ),
    Constraint(
        name="unique_entity_id",
        label="Entity",
        properties=["id"],
        constraint_type="unique",
    ),
]

DEFAULT_INDEXES = [
    Index(
        name="document_title_index",
        label="Document",
        properties=["title"],
        index_type="btree",
    ),
    Index(
        name="chunk_content_fulltext",
        label="Chunk",
        properties=["content"],
        index_type="fulltext",
    ),
    Index(
        name="chunk_embedding_vector",
        label="Chunk",
        properties=["embedding"],
        index_type="vector",
    ),
    Index(
        name="entity_name_index",
        label="Entity",
        properties=["name"],
        index_type="btree",
    ),
]


def initialize_default_schema(runner: QueryRunner) -> bool:
    """Initialize the default RAG system schema"""
    manager = SchemaManager(runner)
    return manager.initialize_schema(DEFAULT_CONSTRAINTS, DEFAULT_INDEXES)
