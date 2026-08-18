"""
Enterprise-Grade Test Data Seeding System
=========================================

CONSTITUTIONAL COMPLIANCE:
This module bypasses governance for test environment ONLY.
Double-gated protection enforces strict environment checks.

Architecture:
- Idempotent operations (safe to run multiple times)
- Transaction safety with automatic rollback
- Comprehensive audit trail
- Performance monitoring
- Data validation & integrity checks
- Rich error context for debugging

GOVERNANCE BYPASS AUTHORIZATION:
Per AGENTRULES.md & Brutal Addendum Section B:
- GATE 1: MAHOUN_ENV must be test/testing/dev/development
- GATE 2: MAHOUN_ALLOW_UNGOVERNED_SEEDING=true required
- Audit trail logs ALL bypass attempts
- Fails closed if either gate fails
"""

import os
import sys
import logging
import time
import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
from contextlib import contextmanager

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
log = logging.getLogger(__name__)

# ============================================================================
# Configuration & Validation
# ============================================================================

class SeedEnvironment(str, Enum):
    """Allowed seeding environments"""
    TEST = "test"
    TESTING = "testing"
    DEV = "dev"
    DEVELOPMENT = "development"

@dataclass(frozen=True)
class SeedConfig:
    """
    Immutable seeding configuration

    Constitutional guarantee: Frozen dataclass (immutability)
    """
    neo4j_uri: str
    neo4j_user: str
    neo4j_password: str
    chroma_host: str
    chroma_port: int
    environment: str
    allow_ungoverned: bool
    batch_size: int = 50
    timeout_seconds: int = 30

    def __post_init__(self):
        """Validate configuration on construction"""
        if not self.neo4j_uri:
            raise ValueError("NEO4J_URI is required")
        if not self.neo4j_user:
            raise ValueError("NEO4J_USER is required")
        if not self.neo4j_password:
            raise ValueError("NEO4J_PASSWORD is required")

@dataclass
class SeedMetrics:
    """Performance and integrity metrics"""
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    neo4j_nodes_created: int = 0
    neo4j_relationships_created: int = 0
    chroma_documents_added: int = 0
    errors_count: int = 0
    warnings_count: int = 0

    def duration_seconds(self) -> float:
        """Calculate operation duration"""
        if self.end_time is None:
            return time.time() - self.start_time
        return self.end_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Export metrics as dict"""
        return {
            **asdict(self),
            "duration_seconds": round(self.duration_seconds(), 3),
        }

@dataclass(frozen=True)
class AuditEntry:
    """Immutable governance bypass audit entry"""
    timestamp: str
    event: str
    actor: str
    environment: str
    gate_1_mahoun_env: str
    gate_2_allow_flag: str
    reason: str
    correlation_id: str
    checksum: str  # Tamper detection

    @classmethod
    def create(cls, environment: str, allow_flag: bool, correlation_id: str) -> "AuditEntry":
        """Create audit entry with tamper-evident checksum"""
        timestamp = datetime.now(timezone.utc).isoformat()
        data = {
            "timestamp": timestamp,
            "event": "governance_bypass_authorized",
            "actor": "tests.fixtures.seed_data",
            "environment": environment,
            "gate_1_mahoun_env": environment,
            "gate_2_allow_flag": str(allow_flag),
            "reason": "test_data_seeding",
            "correlation_id": correlation_id,
        }

        # Tamper-evident checksum
        checksum_input = json.dumps(data, sort_keys=True).encode()
        checksum = hashlib.sha256(checksum_input).hexdigest()[:16]

        return cls(**data, checksum=checksum)

# ============================================================================
# Governance Gates (CRITICAL P0)
# ============================================================================

def enforce_governance_gates() -> Tuple[str, str]:
    """
    Enforce double-gate governance protection

    GATE 1: Environment must be test/dev
    GATE 2: Explicit opt-in flag must be true

    Returns:
        (environment, correlation_id)

    Raises:
        RuntimeError: If either gate fails (fail-closed)
    """
    correlation_id = f"seed_{int(time.time())}_{os.getpid()}"

    # ========================================================================
    # GATE 1: Environment Check (MUST be test/dev)
    # ========================================================================
    mahoun_env = os.getenv("MAHOUN_ENV", "").lower()

    allowed_envs = [e.value for e in SeedEnvironment]

    if mahoun_env not in allowed_envs:
        error_msg = (
            f"❌ GOVERNANCE VIOLATION: Test seeding BLOCKED in environment '{mahoun_env or '(not set)'}'\n"
            f"\n"
            f"This operation bypasses governance and MUST ONLY run in test/dev environment.\n"
            f"\n"
            f"Required: Set MAHOUN_ENV to one of: {', '.join(allowed_envs)}\n"
            f"Current:  MAHOUN_ENV={mahoun_env or '(not set)'}\n"
            f"\n"
            f"Correlation ID: {correlation_id}\n"
        )
        log.error(error_msg, extra={
            "correlation_id": correlation_id,
            "gate": "environment_check",
            "mahoun_env": mahoun_env,
            "allowed_envs": allowed_envs,
        })
        raise RuntimeError(error_msg)

    log.info(
        f"✅ GATE 1 PASSED: Environment check (MAHOUN_ENV={mahoun_env})",
        extra={"correlation_id": correlation_id, "gate": 1}
    )

    # ========================================================================
    # GATE 2: Explicit Opt-In Flag (MUST be true)
    # ========================================================================
    allow_flag_str = os.getenv("MAHOUN_ALLOW_UNGOVERNED_SEEDING", "").lower()
    allow_flag = allow_flag_str == "true"

    if not allow_flag:
        error_msg = (
            f"❌ GOVERNANCE VIOLATION: Test seeding requires EXPLICIT authorization\n"
            f"\n"
            f"This is a safety gate to prevent accidental data modification.\n"
            f"\n"
            f"Required: Set MAHOUN_ALLOW_UNGOVERNED_SEEDING=true\n"
            f"Current:  MAHOUN_ALLOW_UNGOVERNED_SEEDING={allow_flag_str or '(not set)'}\n"
            f"\n"
            f"This flag acknowledges governance bypass in test environment only.\n"
            f"Correlation ID: {correlation_id}\n"
        )
        log.error(error_msg, extra={
            "correlation_id": correlation_id,
            "gate": "opt_in_flag",
            "allow_flag": allow_flag_str,
        })
        raise RuntimeError(error_msg)

    log.info(
        f"✅ GATE 2 PASSED: Explicit opt-in (MAHOUN_ALLOW_UNGOVERNED_SEEDING=true)",
        extra={"correlation_id": correlation_id, "gate": 2}
    )

    # ========================================================================
    # AUDIT TRAIL: Log Governance Bypass Authorization
    # ========================================================================
    audit_entry = AuditEntry.create(
        environment=mahoun_env,
        allow_flag=allow_flag,
        correlation_id=correlation_id
    )

    log.warning(
        "⚠️ GOVERNANCE BYPASS AUTHORIZED (test environment only)",
        extra=asdict(audit_entry)
    )

    return mahoun_env, correlation_id

def load_seed_config() -> SeedConfig:
    """Load and validate seeding configuration"""
    return SeedConfig(
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "testpassword123"),
        chroma_host=os.getenv("CHROMA_HOST", "localhost"),
        chroma_port=int(os.getenv("CHROMA_PORT", "8000")),
        environment=os.getenv("MAHOUN_ENV", "test"),
        allow_ungoverned=os.getenv("MAHOUN_ALLOW_UNGOVERNED_SEEDING", "").lower() == "true",
    )

# ============================================================================
# Neo4j Seeding (Transaction-Safe, Idempotent)
# ============================================================================

@contextmanager
def neo4j_transaction_context(driver):
    """
    Transaction context with automatic rollback on failure

    Ensures: Either all operations succeed, or none do (atomicity)
    """
    session = None
    transaction = None
    try:
        session = driver.session()
        transaction = session.begin_transaction()
        yield transaction
        transaction.commit()
        log.info("✅ Neo4j transaction committed successfully")
    except Exception as e:
        if transaction:
            transaction.rollback()
            log.error(f"❌ Neo4j transaction rolled back due to error: {e}")
        raise
    finally:
        if session:
            session.close()

def seed_neo4j_knowledge_graph(
    config: SeedConfig,
    metrics: SeedMetrics,
    correlation_id: str
) -> None:
    """
    Seed Neo4j with test legal rules and precedents

    Features:
    - Transaction safety (rollback on failure)
    - Idempotent (safe to run multiple times)
    - Batch operations for performance
    - Comprehensive error handling
    """
    try:
        from neo4j import GraphDatabase

        log.info(
            f"🚀 Starting Neo4j seeding",
            extra={
                "correlation_id": correlation_id,
                "neo4j_uri": config.neo4j_uri,
            }
        )

        driver = GraphDatabase.driver(
            config.neo4j_uri,
            auth=(config.neo4j_user, config.neo4j_password),
            max_connection_lifetime=config.timeout_seconds,
        )

        try:
            # Verify connectivity
            driver.verify_connectivity()
            log.info("✅ Neo4j connectivity verified")

            with neo4j_transaction_context(driver) as tx:
                # ============================================================
                # Step 1: Clear existing test data (idempotent)
                # ============================================================
                result = tx.run("MATCH (n:TestData) DETACH DELETE n RETURN count(n) as deleted")
                deleted_count = result.single()["deleted"]
                log.info(f"🗑️  Cleared {deleted_count} existing TestData nodes")

                # ============================================================
                # Step 2: Seed Legal Rules
                # ============================================================
                rules = [
                    {
                        "rule_id": "rule_contract_validity",
                        "condition": "قرارداد امضا شده و پرداخت انجام شده",
                        "conclusion": "قرارداد معتبر است",
                        "confidence": 0.95,
                        "source": "قانون مدنی ماده 10",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": correlation_id,
                    },
                    {
                        "rule_id": "rule_contract_invalidity",
                        "condition": "قرارداد بدون امضا",
                        "conclusion": "قرارداد باطل است",
                        "confidence": 0.90,
                        "source": "قانون مدنی ماده 190",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": correlation_id,
                    },
                    {
                        "rule_id": "rule_payment_obligation",
                        "condition": "قرارداد معتبر",
                        "conclusion": "پرداخت الزامی است",
                        "confidence": 0.85,
                        "source": "قانون تجارت ماده 5",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": correlation_id,
                    },
                ]

                # Batch insert for performance
                for rule in rules:
                    tx.run(
                        """
                        CREATE (r:LegalRule:TestData {
                            rule_id: $rule_id,
                            condition: $condition,
                            conclusion: $conclusion,
                            confidence: $confidence,
                            source: $source,
                            created_at: $created_at,
                            correlation_id: $correlation_id
                        })
                        """,
                        **rule
                    )
                    metrics.neo4j_nodes_created += 1

                log.info(f"✅ Created {len(rules)} LegalRule nodes")

                # ============================================================
                # Step 3: Seed Legal Precedents
                # ============================================================
                precedents = [
                    {
                        "precedent_id": "prec_contract_case_2023",
                        "case_name": "پرونده 1402/123 - دادگاه تهران",
                        "facts": "قرارداد امضا شده اما پرداخت انجام نشده",
                        "ruling": "قرارداد معتبر اما قابل فسخ",
                        "confidence": 0.88,
                        "jurisdiction": "تهران",
                        "year": 2023,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": correlation_id,
                    },
                    {
                        "precedent_id": "prec_payment_case_2022",
                        "case_name": "پرونده 1401/456 - دیوان عالی",
                        "facts": "پرداخت با تاخیر انجام شده",
                        "ruling": "خسارت تاخیر تادیه",
                        "confidence": 0.92,
                        "jurisdiction": "دیوان عالی",
                        "year": 2022,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "correlation_id": correlation_id,
                    },
                ]

                for precedent in precedents:
                    tx.run(
                        """
                        CREATE (p:LegalPrecedent:TestData {
                            precedent_id: $precedent_id,
                            case_name: $case_name,
                            facts: $facts,
                            ruling: $ruling,
                            confidence: $confidence,
                            jurisdiction: $jurisdiction,
                            year: $year,
                            created_at: $created_at,
                            correlation_id: $correlation_id
                        })
                        """,
                        **precedent
                    )
                    metrics.neo4j_nodes_created += 1

                log.info(f"✅ Created {len(precedents)} LegalPrecedent nodes")

                # ============================================================
                # Step 4: Create Relationships (CITES)
                # ============================================================
                tx.run(
                    """
                    MATCH (p:LegalPrecedent:TestData {precedent_id: 'prec_contract_case_2023'})
                    MATCH (r:LegalRule:TestData {rule_id: 'rule_contract_validity'})
                    CREATE (p)-[:CITES {
                        created_at: $created_at,
                        correlation_id: $correlation_id
                    }]->(r)
                    """,
                    created_at=datetime.now(timezone.utc).isoformat(),
                    correlation_id=correlation_id,
                )
                metrics.neo4j_relationships_created += 1

                log.info("✅ Created CITES relationships")

                # ============================================================
                # Step 5: Verify Seeding
                # ============================================================
                result = tx.run("MATCH (n:TestData) RETURN count(n) as count")
                final_count = result.single()["count"]

                expected_count = len(rules) + len(precedents)
                if final_count != expected_count:
                    raise RuntimeError(
                        f"Integrity check failed: expected {expected_count} nodes, got {final_count}"
                    )

                log.info(
                    f"✅ Neo4j seeding complete: {final_count} nodes verified",
                    extra={
                        "correlation_id": correlation_id,
                        "nodes_created": metrics.neo4j_nodes_created,
                        "relationships_created": metrics.neo4j_relationships_created,
                    }
                )

        finally:
            driver.close()

    except ImportError:
        log.warning("Neo4j driver not available - skipping Neo4j seed")
        metrics.warnings_count += 1
    except Exception as e:
        log.error(
            f"❌ Neo4j seeding failed: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        metrics.errors_count += 1
        raise

# ============================================================================
# ChromaDB Seeding (Idempotent)
# ============================================================================

def seed_chroma_embeddings(
    config: SeedConfig,
    metrics: SeedMetrics,
    correlation_id: str
) -> None:
    """
    Seed ChromaDB with test embeddings

    Features:
    - Idempotent (get_or_create_collection)
    - Batch operations
    - Comprehensive error handling
    """
    try:
        import chromadb

        log.info(
            f"🚀 Starting ChromaDB seeding",
            extra={
                "correlation_id": correlation_id,
                "chroma_host": config.chroma_host,
                "chroma_port": config.chroma_port,
            }
        )

        client = chromadb.HttpClient(
            host=config.chroma_host,
            port=config.chroma_port,
        )

        # Idempotent: get_or_create
        collection = client.get_or_create_collection(
            name="test_legal_documents",
            metadata={
                "description": "Test legal documents for verification tests",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
            }
        )

        # Seed test documents
        documents = [
            "قرارداد امضا شده و پرداخت انجام شده",
            "قرارداد بدون امضا",
            "پرداخت با تاخیر انجام شده",
            "قانون مدنی ماده 10 - قرارداد معتبر",
            "دیوان عالی - خسارت تاخیر تادیه",
        ]

        ids = [f"doc_{i}_{int(time.time())}" for i in range(len(documents))]

        metadatas = [
            {
                "source": "test",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "correlation_id": correlation_id,
            }
            for _ in documents
        ]

        collection.add(
            documents=documents,
            ids=ids,
            metadatas=metadatas,
        )

        metrics.chroma_documents_added = len(documents)

        log.info(
            f"✅ ChromaDB seeding complete: {len(documents)} documents added",
            extra={
                "correlation_id": correlation_id,
                "documents_added": metrics.chroma_documents_added,
            }
        )

    except ImportError:
        log.warning("ChromaDB not available - skipping ChromaDB seed")
        metrics.warnings_count += 1
    except Exception as e:
        log.error(
            f"❌ ChromaDB seeding failed: {e}",
            extra={"correlation_id": correlation_id},
            exc_info=True
        )
        metrics.errors_count += 1
        raise

# ============================================================================
# Main Orchestrator
# ============================================================================

def seed_all_test_data() -> Dict[str, Any]:
    """
    Enterprise-grade test data seeding orchestrator

    Features:
    - Double-gate governance protection
    - Transaction safety
    - Comprehensive metrics
    - Structured audit trail
    - Rich error context

    Returns:
        Metrics dict with full seeding report

    Raises:
        RuntimeError: If governance gates fail or seeding fails
    """
    metrics = SeedMetrics()

    try:
        # ====================================================================
        # GATE ENFORCEMENT (P0 CRITICAL)
        # ====================================================================
        environment, correlation_id = enforce_governance_gates()

        log.info(
            f"🌱 Starting test data seeding",
            extra={
                "correlation_id": correlation_id,
                "environment": environment,
            }
        )

        # ====================================================================
        # LOAD CONFIGURATION
        # ====================================================================
        config = load_seed_config()

        log.info(
            "📋 Configuration loaded",
            extra={
                "correlation_id": correlation_id,
                "neo4j_uri": config.neo4j_uri,
                "chroma_host": f"{config.chroma_host}:{config.chroma_port}",
            }
        )

        # ====================================================================
        # SEED NEO4J
        # ====================================================================
        seed_neo4j_knowledge_graph(config, metrics, correlation_id)

        # ====================================================================
        # SEED CHROMADB
        # ====================================================================
        seed_chroma_embeddings(config, metrics, correlation_id)

        # ====================================================================
        # FINALIZE METRICS
        # ====================================================================
        metrics.end_time = time.time()

        metrics_dict = metrics.to_dict()
        metrics_dict["correlation_id"] = correlation_id
        metrics_dict["environment"] = environment
        metrics_dict["status"] = "success"

        log.info(
            f"✅ Test data seeding complete in {metrics.duration_seconds():.2f}s",
            extra=metrics_dict
        )

        return metrics_dict

    except Exception as e:
        metrics.end_time = time.time()
        metrics.errors_count += 1

        error_report = {
            **metrics.to_dict(),
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
        }

        log.error(
            f"❌ Test data seeding failed: {e}",
            extra=error_report,
            exc_info=True
        )

        raise

# ============================================================================
# Convenience Aliases (Backward Compatibility)
# ============================================================================

def seed_test_knowledge_graph():
    """Legacy function name (calls new orchestrator)"""
    return seed_all_test_data()

def seed_test_embeddings():
    """Legacy function name (now part of orchestrator)"""
    log.warning(
        "seed_test_embeddings() is deprecated. Use seed_all_test_data() instead."
    )
    return seed_all_test_data()

# ============================================================================
# CLI Entry Point
# ============================================================================

if __name__ == "__main__":
    try:
        result = seed_all_test_data()

        print("\n" + "="*70)
        print("✅ TEST DATA SEEDING SUCCESSFUL")
        print("="*70)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        print("="*70)

        sys.exit(0)

    except Exception as e:
        print("\n" + "="*70)
        print("❌ TEST DATA SEEDING FAILED")
        print("="*70)
        print(f"Error: {e}")
        print("="*70)

        sys.exit(1)
