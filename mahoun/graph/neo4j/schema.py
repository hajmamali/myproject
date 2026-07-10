"""
Neo4j Schema Management
Handles constraints, indexes, and schema migrations
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set
import logging
from neo4j import Session

logger = logging.getLogger(__name__)


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

    def __init__(self, session: Session):
        self.session = session

    def create_constraint(self, constraint: Constraint) -> bool:
        """Create a constraint in the database"""
        try:
            if constraint.constraint_type == "unique":
                query = f"""
                CREATE CONSTRAINT {constraint.name} IF NOT EXISTS
                FOR (n:{constraint.label})
                REQUIRE n.{constraint.properties[0]} IS UNIQUE
                """
            elif constraint.constraint_type == "exists":
                query = f"""
                CREATE CONSTRAINT {constraint.name} IF NOT EXISTS
                FOR (n:{constraint.label})
                REQUIRE n.{constraint.properties[0]} IS NOT NULL
                """
            elif constraint.constraint_type == "node_key":
                props = ", ".join([f"n.{p}" for p in constraint.properties])
                query = f"""
                CREATE CONSTRAINT {constraint.name} IF NOT EXISTS
                FOR (n:{constraint.label})
                REQUIRE ({props}) IS NODE KEY
                """
            else:
                logger.error(f"Unknown constraint type: {constraint.constraint_type}")
                return False

            self.session.run(query)
            logger.info(f"Created constraint: {constraint.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create constraint {constraint.name}: {e}")
            return False

    def create_index(self, index: Index) -> bool:
        """Create an index in the database"""
        try:
            if index.index_type == "btree":
                props = ", ".join([f"n.{p}" for p in index.properties])
                query = f"""
                CREATE INDEX {index.name} IF NOT EXISTS
                FOR (n:{index.label})
                ON ({props})
                """
            elif index.index_type == "fulltext":
                props = ", ".join([f"n.{p}" for p in index.properties])
                query = f"""
                CREATE FULLTEXT INDEX {index.name} IF NOT EXISTS
                FOR (n:{index.label})
                ON EACH [{props}]
                """
            elif index.index_type == "vector":
                # Vector index for embeddings (Neo4j 5.11+)
                query = f"""
                CREATE VECTOR INDEX {index.name} IF NOT EXISTS
                FOR (n:{index.label})
                ON n.{index.properties[0]}
                OPTIONS {{indexConfig: {{
                    `vector.dimensions`: 768,
                    `vector.similarity_function`: 'cosine'
                }}}}
                """
            else:
                logger.error(f"Unknown index type: {index.index_type}")
                return False

            self.session.run(query)
            logger.info(f"Created index: {index.name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create index {index.name}: {e}")
            return False

    def drop_constraint(self, constraint_name: str) -> bool:
        """Drop a constraint from the database"""
        try:
            query = f"DROP CONSTRAINT {constraint_name} IF EXISTS"
            self.session.run(query)
            logger.info(f"Dropped constraint: {constraint_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop constraint {constraint_name}: {e}")
            return False

    def drop_index(self, index_name: str) -> bool:
        """Drop an index from the database"""
        try:
            query = f"DROP INDEX {index_name} IF EXISTS"
            self.session.run(query)
            logger.info(f"Dropped index: {index_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to drop index {index_name}: {e}")
            return False

    def get_constraints(self) -> List[Dict]:
        """Get all constraints in the database"""
        try:
            result = self.session.run("SHOW CONSTRAINTS")
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Failed to get constraints: {e}")
            return []

    def get_indexes(self) -> List[Dict]:
        """Get all indexes in the database"""
        try:
            result = self.session.run("SHOW INDEXES")
            return [dict(record) for record in result]
        except Exception as e:
            logger.error(f"Failed to get indexes: {e}")
            return []

    def get_node_labels(self) -> Set[str]:
        """Get all node labels in the database"""
        try:
            result = self.session.run("CALL db.labels()")
            return {record["label"] for record in result}
        except Exception as e:
            logger.error(f"Failed to get node labels: {e}")
            return set()

    def get_relationship_types(self) -> Set[str]:
        """Get all relationship types in the database"""
        try:
            result = self.session.run("CALL db.relationshipTypes()")
            return {record["relationshipType"] for record in result}
        except Exception as e:
            logger.error(f"Failed to get relationship types: {e}")
            return set()

    def initialize_schema(
        self, constraints: List[Constraint], indexes: List[Index]
    ) -> bool:
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

        logger.info(
            f"Created {len(indexes)} fulltext indexes for legal knowledge graph"
        )
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

            validation_results["constraints"] = required_constraints.issubset(
                constraint_names
            )

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

            validation_results["fulltext_indexes"] = required_fulltext.issubset(
                index_names
            )

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


def initialize_default_schema(session: Session) -> bool:
    """Initialize the default RAG system schema"""
    manager = SchemaManager(session)
    return manager.initialize_schema(DEFAULT_CONSTRAINTS, DEFAULT_INDEXES)
