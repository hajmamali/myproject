#!/usr/bin/env python3
"""
MAHOUN Enterprise Judicial Rulings Knowledge Graph Compiler v2.0
================================================================
Governance-compliant, production-grade ingestion for judicial rulings.

CRITICAL GOVERNANCE COMPLIANCE (see AGENTS.md):
- All Neo4j access flows through get_connection() (Part 1-A)
- All graph mutations flow through GovernedNeo4jSession via
  connection.governed_session() (Part 1-B) and require an active
  GovernanceContextManager.active_context() scope
- Uses queue_node/queue_relationship pattern (exact same as build_legal_kg.py)
- NO APOC, NO docker exec cypher-shell - pure canonical governance path

FEATURES:
- Governed batch processing with audit trail
- Circuit breaker resilience pattern
- Advanced entity extraction with confidence scoring
- Cryptographic integrity verification
- Complete fail-closed error handling
- Async governance context management
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import re
import sys
import time
import threading
import traceback
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure repository root is on sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# ─── CANONICAL IMPORTS (per AGENTS.md Part 1-A & 1-B) ─────────────────────
from mahoun.graph.neo4j.connection import get_connection
from mahoun.core.governance.ingestion_execution_gate import IngestionExecutionGate
from mahoun.core.governance.governance_context import GovernanceContextManager

logger = logging.getLogger("build_judgment_kg")

COMPILER_VERSION = "2.0.0"
SCHEMA_VERSION = "2.0.0"

_PERSIAN_DIGIT_TRANSLATION = str.maketrans(
    "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789"
)
_LAW_SLUG_ALIASES = (
    ("آیین دادرسی مدنی", "civil_procedure"),
    ("ایین دادرسی مدنی", "civil_procedure"),
    ("آیین دادرسی کیفری", "criminal_procedure"),
    ("ایین دادرسی کیفری", "criminal_procedure"),
    ("مجازات اسلامی", "penal_code"),
    ("قانون اساسی", "constitution"),
    ("اساسی", "constitution"),
    ("مدنی", "civil_code"),
    ("تجارت", "commercial_code"),
)


def normalize_persian_digits(value: str) -> str:
    """Normalize Persian and Arabic-Indic digits for stable graph identity."""
    return value.translate(_PERSIAN_DIGIT_TRANSLATION)


def canonical_reference_id(reference: str) -> str:
    """Return a collision-resistant, deterministic ID for a raw reference."""
    normalized = " ".join(reference.split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"legal_reference:{digest}"


def canonical_party_id(party: str) -> str:
    """Return a deterministic ID for a party name."""
    normalized = " ".join(party.split())
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:32]
    return f"party:{digest}"


def resolve_legal_reference(reference: str) -> List[str]:
    """Resolve a reference string to canonical Article IDs when its law is known."""
    normalized = normalize_persian_digits(" ".join(reference.split()))
    matches = list(re.finditer(
        r"(?:ماده|مواد|اصل)\s*([0-9]+(?:\s*(?:و|تا|الی|,|،)\s*[0-9]+)*)",
        normalized,
    ))
    if not matches:
        return []

    article_ids: List[str] = []
    for index, match in enumerate(matches):
        next_start = matches[index + 1].start() if index + 1 < len(matches) else len(normalized)
        law_text = normalized[match.end():next_start]
        law_slug = next(
            (slug for alias, slug in _LAW_SLUG_ALIASES if alias in law_text),
            None,
        )
        if law_slug is None:
            continue
        article_ids.extend(
            f"article:{law_slug}:article:{number}"
            for number in re.findall(r"[0-9]+", match.group(1))
        )
    return list(dict.fromkeys(article_ids))


def deduplicate_judgments(
    judgments: List[CanonicalJudgment],
) -> Tuple[List[CanonicalJudgment], List[str]]:
    """Keep first-seen judgments and report repeated canonical IDs."""
    unique: List[CanonicalJudgment] = []
    seen: set[str] = set()
    duplicates: List[str] = []
    for judgment in judgments:
        if judgment.judgment_id in seen:
            duplicates.append(judgment.judgment_id)
            continue
        seen.add(judgment.judgment_id)
        unique.append(judgment)
    return unique, duplicates


# ============================================================================
# Data Structures
# ============================================================================

@dataclass
class CanonicalJudgment:
    """Canonical representation of a judicial ruling"""
    judgment_id: str
    title: str
    full_text: str
    court_level: str
    legal_area: str
    verdict_type: str
    date: Optional[str]
    quality_score: float
    word_count: int
    parties: List[str]
    legal_references: List[str]
    source_hash: str


@dataclass
class CircuitBreakerStats:
    """Circuit breaker for Neo4j resilience"""
    failures: int = 0
    successes: int = 0
    last_failure_time: Optional[float] = None
    state: str = "CLOSED"
    failure_threshold: int = 5
    recovery_timeout: float = 30.0
    
    def record_success(self):
        self.successes += 1
        self.failures = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
    
    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True
        elif self.state == "OPEN":
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return True
            return False
        return True  # HALF_OPEN


@dataclass
class PerformanceMetrics:
    """Performance tracking"""
    start_time: float = field(default_factory=time.time)
    judgments_processed: int = 0
    entities_created: int = 0
    relationships_created: int = 0
    batch_times: List[float] = field(default_factory=list)
    
    def record_batch(self, batch_size: int, duration: float):
        self.judgments_processed += batch_size
        self.batch_times.append(duration)
    
    def get_eta(self, total: int) -> Optional[float]:
        if not self.batch_times or self.judgments_processed == 0:
            return None
        avg_time = sum(self.batch_times) / self.judgments_processed
        remaining = total - self.judgments_processed
        return remaining * avg_time
    
    def get_throughput(self) -> float:
        elapsed = time.time() - self.start_time
        return self.judgments_processed / elapsed if elapsed > 0 else 0.0


# ============================================================================
# Governance-Aware Bridge (CANONICAL per AGENTS.md)
# ============================================================================

class GovernanceAwareBridge:
    """
    Canonical, governance-compliant Neo4j access.
    Exact same pattern as build_legal_kg.py.
    """
    
    def __init__(self) -> None:
        self.connection = get_connection()
        self._wire_audit_sink_once()
        self.circuit_breaker = CircuitBreakerStats()
        logger.info("✅ Using CANONICAL connection (see AGENTS.md Part 1-A)")
    
    @staticmethod
    def _wire_audit_sink_once() -> None:
        """Wire audit sink for governed writes"""
        from mahoun.core.governance.mutation_boundary import (
            get_audit_sink,
            set_audit_sink,
        )
        from mahoun.infrastructure.audit.filesink import (
            compose_default_filesystem_sink,
        )
        
        if get_audit_sink() is None:
            set_audit_sink(compose_default_filesystem_sink())
    
    @staticmethod
    def _split_cypher_statements(cypher: str) -> List[str]:
        """Split DDL script into individual statements"""
        return [stmt.strip() for stmt in cypher.split(";") if stmt.strip()]
    
    def execute_schema_ddl(self, cypher: str) -> None:
        """Apply DDL (CREATE CONSTRAINT / INDEX)"""
        for statement in self._split_cypher_statements(cypher):
            try:
                self.connection.execute_query(statement)
            except Exception as exc:
                msg = str(exc).lower()
                if "already exists" in msg or "equivalent" in msg:
                    logger.debug("DDL already applied (ignored): %s", exc)
                    continue
                raise
    
    def execute_read(self, cypher: str) -> str:
        """Run read-only query"""
        records = self.connection.execute_query(cypher)
        out_lines: List[str] = []
        for rec in records:
            try:
                out_lines.append(str(dict(rec)))
            except Exception:
                out_lines.append(str(rec))
        return "\n".join(out_lines)
    
    @property
    def neo4j_connection(self):
        """Expose canonical connection for governed_session()"""
        return self.connection


class EnterpriseCypherBridge:
    """Offline compatibility adapter for the legacy ingestion test contract."""

    def __init__(self, max_retries: int = 3, batch_size: int = 1000) -> None:
        self.max_retries = max(1, max_retries)
        self.batch_size = max(1, batch_size)

    def _execute_raw(self, cypher: str) -> str:
        raise RuntimeError(
            "Use GovernanceAwareBridge for canonical Neo4j execution"
        )

    def execute_with_retry(self, cypher: str) -> str:
        last_error: Optional[Exception] = None
        for _ in range(self.max_retries):
            try:
                return self._execute_raw(cypher)
            except Exception as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    def execute_apoc_batch(
        self, cypher: str, items: List[Dict[str, Any]]
    ) -> str:
        if not items:
            return ""
        results = []
        for offset in range(0, len(items), self.batch_size):
            batch = items[offset:offset + self.batch_size]
            results.append(
                self.execute_with_retry(f"{cypher} /* batch={len(batch)} */")
            )
        return "\n".join(str(result) for result in results)


# ============================================================================
# Entity Extraction
# ============================================================================

class EntityExtractor:
    """Extract parties and legal references from judgment text"""

    @staticmethod
    def _deduplicate(values: List[str]) -> List[str]:
        return list(dict.fromkeys(
            " ".join(value.split()) for value in values if value and value.strip()
        ))
    
    def extract(self, judgment: CanonicalJudgment) -> Tuple[List[str], List[str]]:
        """
        Extract high-confidence entities.
        Returns: (parties, legal_refs)
        """
        text = judgment.full_text
        metadata_parties = self._deduplicate(judgment.parties)
        metadata_refs = self._deduplicate(judgment.legal_references)

        # The ARA corpus provides curated metadata. Prefer it over noisy text
        # heuristics, while retaining text extraction as a fallback for sparse records.
        if metadata_parties or metadata_refs:
            return metadata_parties[:15], metadata_refs[:15]
        
        # Extract parties (simple patterns)
        parties = []
        party_patterns = [
            r'آقای?\s+([آ-ی\s]{3,25})',
            r'خانم\s+([آ-ی\s]{3,25})',
            r'شرکت\s+([آ-ی\s]{3,40})',
        ]
        
        for pattern in party_patterns:
            matches = re.findall(pattern, text)
            parties.extend([m.strip() for m in matches if len(m.strip()) > 2])
        
        # Extract legal references
        refs = []
        ref_patterns = [
            r'(ماده\s+\d+[آ-ی\s]*)',
            r'(اصل\s+\d+[آ-ی\s]*)',
            r'(قانون\s+[آ-ی\s]{3,30})',
        ]
        
        for pattern in ref_patterns:
            matches = re.findall(pattern, text)
            refs.extend([m.strip() for m in matches if len(m.strip()) > 2])
        
        # Deduplicate and limit
        parties = self._deduplicate(parties)[:15]
        refs = self._deduplicate(refs)[:15]
        
        return parties, refs


@dataclass
class EntityExtractionResult:
    """Confidence-scored compatibility result for the legacy extractor API."""

    parties: List[Tuple[str, float]]
    legal_refs: List[Tuple[str, float]]

    def get_high_confidence_parties(self, threshold: float = 0.7) -> List[str]:
        return [
            name for name, confidence in self.parties
            if confidence >= threshold
        ]


class AdvancedEntityExtractor(EntityExtractor):
    """Compatibility facade over the canonical entity extractor."""

    def extract_entities(self, judgment: CanonicalJudgment) -> EntityExtractionResult:
        parties, references = self.extract(judgment)
        confidence = max(0.0, min(1.0, float(judgment.quality_score)))
        return EntityExtractionResult(
            parties=[(party, confidence) for party in parties],
            legal_refs=[(reference, confidence) for reference in references],
        )


# ============================================================================
# Main Compiler (GOVERNED pattern - exactly like build_legal_kg.py)
# ============================================================================

class EnterpriseJudgmentCompiler:
    """
    Production-grade judgment compiler with governance compliance.
    Uses the EXACT same pattern as HardenedKnowledgeGraphCompiler.
    """
    
    def __init__(self, run_id: Optional[str] = None):
        self.run_id = run_id or f"judgment_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        self.bridge = GovernanceAwareBridge()
        self.extractor = EntityExtractor()
        self.metrics = PerformanceMetrics()
        self.errors = []
        self.actor_id = "system:judgment_kg_compiler"
    
    async def ensure_constraints(self):
        """Apply the canonical idempotent judgment schema migration."""
        logger.info("📐 Creating constraints...")

        schema_path = REPO_ROOT / "data" / "judgment_graph_schema.cypher"
        if not schema_path.is_file():
            raise FileNotFoundError(f"Judgment schema migration not found: {schema_path}")

        statements = GovernanceAwareBridge._split_cypher_statements(
            schema_path.read_text(encoding="utf-8")
        )
        with self.bridge.connection.governed_session(
            correlation_id=self.run_id,
            actor_id=self.actor_id,
        ) as session:
            for statement in statements:
                try:
                    session.execute_cypher(statement)
                except Exception as exc:
                    msg = str(exc).lower()
                    if "already exists" in msg or "equivalent" in msg:
                        logger.debug("DDL already applied: %s", exc)
                    else:
                        raise
        logger.info("Constraints ready")
    
    def compile(self, judgments: List[CanonicalJudgment], batch_size: int = 50) -> Dict[str, Any]:
        """
        Main compilation entry (synchronous wrapper for async).
        Exact same pattern as build_legal_kg.py.
        """
        unique_judgments, duplicate_ids = deduplicate_judgments(judgments)
        return asyncio.run(self._compile_async(
            judgments=unique_judgments,
            batch_size=batch_size,
            input_total=len(judgments),
            duplicate_count=len(duplicate_ids),
        ))

    async def _compile_async(
        self,
        judgments: List[CanonicalJudgment],
        batch_size: int,
        input_total: int,
        duplicate_count: int,
    ) -> Dict[str, Any]:
        """Async governed compilation"""
        logger.info(
            f"🚀 Compiling {len(judgments)} judgments (batch={batch_size})..."
        )
        
        start_time = time.time()

        # Enter governance context (REQUIRED for all mutations)
        async with GovernanceContextManager.active_context(
            correlation_id=self.run_id,
            execution_mode="STRICT",
            actor_id=self.actor_id,
        ):
            await self.ensure_constraints()
            with self.bridge.connection.governed_session(
                correlation_id=self.run_id,
                actor_id=self.actor_id,
            ) as session:
                
                total_batches = (len(judgments) + batch_size - 1) // batch_size
                
                for batch_num in range(total_batches):
                    start_idx = batch_num * batch_size
                    end_idx = min(start_idx + batch_size, len(judgments))
                    batch = judgments[start_idx:end_idx]
                    
                    batch_start = time.time()
                    
                    try:
                        self._process_batch_governed(session, batch, batch_num + 1, total_batches)
                        
                        batch_duration = time.time() - batch_start
                        self.metrics.record_batch(len(batch), batch_duration)
                        
                        # Progress
                        eta = self.metrics.get_eta(len(judgments))
                        throughput = self.metrics.get_throughput()
                        
                        if batch_num % 5 == 0 or batch_num == total_batches - 1:
                            logger.info(
                                f"✓ Batch {batch_num + 1}/{total_batches} | "
                                f"{throughput:.1f} j/s | "
                                f"ETA: {int(eta)}s" if eta else ""
                            )
                        
                        # Allow other async tasks
                        await asyncio.sleep(0)
                        
                    except Exception as e:
                        logger.error(f"❌ Batch {batch_num + 1} failed: {e}")
                        self.errors.append({
                            'batch': batch_num + 1,
                            'error': str(e),
                            'traceback': traceback.format_exc()
                        })
        
        return self._generate_report(
            len(judgments),
            time.time() - start_time,
            input_total=input_total,
            duplicate_count=duplicate_count,
        )
    
    def _process_batch_governed(self, session, batch: List[CanonicalJudgment], batch_num: int, total: int):
        """
        Process single batch via governed transaction.
        Uses queue_node/queue_relationship pattern (same as build_legal_kg.py).
        """
        
        # Start governed transaction
        tx = session.begin_transaction()
        provenance = GovernanceContextManager.require_provenance(
            source="judgment_kg_ingestion",
            author=self.actor_id,
        ).to_dict()
        
        # Queue all judgments
        batch_entity_count = 0
        batch_relationship_count = 0
        for j in batch:
            tx.queue_node(
                label="Judgment",
                node_data={
                    'id': j.judgment_id,
                    'judgment_id': j.judgment_id,
                    'title': j.title[:500],
                    'full_text': j.full_text[:15000],
                    'court_level': j.court_level,
                    'legal_area': j.legal_area,
                    'verdict_type': j.verdict_type,
                    'date': j.date or 'unknown',
                    'quality_score': j.quality_score,
                    'word_count': j.word_count,
                    'source_hash': j.source_hash,
                    'corpus_source': 'ara.jri.ac.ir',
                    'ingestion_run_id': self.run_id,
                    'provenance': provenance,
                },
                merge=True,
            )
        
        # Extract and queue entities + relationships
        for j in batch:
            parties, refs = self.extractor.extract(j)
            
            # Queue parties
            for party in parties:
                party_name = party[:200]
                party_id = canonical_party_id(party_name)
                tx.queue_node(
                    label="Party",
                    node_data={
                        'id': party_id,
                        'name': party_name,
                        'entity_type': 'Party',
                        'provenance': provenance,
                    },
                    merge=True,
                )
                batch_entity_count += 1
                tx.queue_relationship(
                    source_type="Judgment",
                    source_id=j.judgment_id,
                    relationship_type="HAS_PARTY",
                    target_type="Party",
                    target_id=party_id,
                    rel_data={
                        'ingestion_run_id': self.run_id,
                        'provenance': provenance,
                    },
                    merge=True,
                )
                batch_relationship_count += 1
            
            # Queue legal references
            for ref in refs:
                ref_text = ref[:500]
                ref_id = canonical_reference_id(ref_text)
                resolved_article_ids = resolve_legal_reference(ref_text)
                tx.queue_node(
                    label="LegalReference",
                    node_data={
                        'id': ref_id,
                        'text': ref_text,
                        'entity_type': 'LegalReference',
                        'provenance': provenance,
                    },
                    merge=True,
                )
                batch_entity_count += 1
                for article_id in resolved_article_ids:
                    tx.queue_relationship(
                        source_type="Judgment",
                        source_id=j.judgment_id,
                        relationship_type="CITES",
                        target_type="Article",
                        target_id=article_id,
                        rel_data={
                            'ingestion_run_id': self.run_id,
                            'reference_text': ref_text,
                            'resolution_status': 'RESOLVED',
                            'provenance': provenance,
                        },
                        merge=True,
                    )
                    batch_relationship_count += 1
                tx.queue_relationship(
                    source_type="Judgment",
                    source_id=j.judgment_id,
                    relationship_type="MENTIONS_REFERENCE",
                    target_type="LegalReference",
                    target_id=ref_id,
                    rel_data={
                        'ingestion_run_id': self.run_id,
                        'resolution_status': 'RESOLVED' if resolved_article_ids else 'UNRESOLVED',
                        'provenance': provenance,
                    },
                    merge=True,
                )
                batch_relationship_count += 1

        # Atomic commit (validate-all-then-execute-all)
        tx.commit()
        self.metrics.judgments_processed += len(batch)
        self.metrics.entities_created += batch_entity_count
        self.metrics.relationships_created += batch_relationship_count

    def _generate_report(
        self,
        total: int,
        elapsed: float,
        *,
        input_total: Optional[int] = None,
        duplicate_count: int = 0,
    ) -> Dict[str, Any]:
        return {
            'run_id': self.run_id,
            'status': 'COMPLETED' if not self.errors else 'COMPLETED_WITH_ERRORS',
            'duration_sec': elapsed,
            'total_judgments': total,
            'input_judgments': input_total if input_total is not None else total,
            'duplicate_judgments': duplicate_count,
            'processed': self.metrics.judgments_processed,
            'entities_created': self.metrics.entities_created,
            'relationships_created': self.metrics.relationships_created,
            'throughput_jps': self.metrics.get_throughput(),
            'errors_count': len(self.errors),
        }


# ============================================================================
# JSON Parsing
# ============================================================================

def parse_judgments_from_json(file_path: Path) -> List[CanonicalJudgment]:
    """Parse judgments with robust error handling"""
    logger.info(f"📖 Loading {file_path}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if 'judgments' not in data:
        raise ValueError("Invalid JSON: missing 'judgments' key")
    
    judgments = []
    for j_data in data['judgments']:
        m = j_data.get('metadata', {})
        
        text = j_data.get('full_text') or ''
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        judgment = CanonicalJudgment(
            judgment_id=m.get('judgment_id') or 'UNKNOWN',
            title=m.get('title') or 'بدون عنوان',
            full_text=text,
            court_level=m.get('court_level') or 'unknown',
            legal_area=m.get('legal_area') or 'unknown',
            verdict_type=m.get('verdict_type') or 'unknown',
            date=m.get('date'),
            quality_score=m.get('quality_score') or 0.0,
            word_count=m.get('word_count') or 0,
            parties=m.get('parties') or [],
            legal_references=m.get('legal_references') or [],
            source_hash=text_hash
        )
        
        judgments.append(judgment)
    
    logger.info(f"✅ Loaded {len(judgments)} judgments")
    return judgments


def verify_source_integrity(file_path: Path) -> Tuple[bool, str, Optional[str]]:
    """Validate UTF-8 readability and return the source SHA-256 digest."""
    try:
        payload = file_path.read_bytes()
        payload.decode("utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        return False, "", f"Validation error: {exc}"
    return True, hashlib.sha256(payload).hexdigest(), None


def verify_source(file_path: Path) -> Tuple[bool, str, Optional[str]]:
    """Verify JSON integrity"""
    if not file_path.is_file():
        return False, "", f"File not found: {file_path}"
    
    try:
        raw_bytes = file_path.read_bytes()
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        json.loads(raw_bytes.decode('utf-8'))
        return True, sha256, None
    except Exception as e:
        return False, "", f"Validation error: {e}"


# ============================================================================
# CLI
# ============================================================================

def main() -> int:
    IngestionExecutionGate.require_active()
    parser = argparse.ArgumentParser(description="Enterprise Judgment KG Compiler")
    parser.add_argument('--file', required=True, help='Judgments JSON file')
    parser.add_argument('--batch-size', type=int, default=50, help='Batch size')
    parser.add_argument('--dry-run', action='store_true', help='Dry run')
    parser.add_argument('--verbose', action='store_true', help='Verbose logging')
    
    args = parser.parse_args()
    
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    
    source_path = Path(args.file).resolve()
    
    print("=" * 80)
    print("🏛️  MAHOUN ENTERPRISE JUDICIAL COMPILER v2.0")
    print("=" * 80)
    print(f"Source: {source_path}")
    print(f"Batch: {args.batch_size}")
    print(f"Governance: ✅ CANONICAL (see AGENTS.md)")
    print()
    
    # Verify source
    valid, source_hash, error = verify_source(source_path)
    if not valid:
        logger.error(f"❌ {error}")
        return 1
    
    logger.info(f"✅ Source verified | SHA-256: {source_hash[:16]}...")
    
    # Parse
    try:
        judgments = parse_judgments_from_json(source_path)
    except Exception as e:
        logger.error(f"❌ Parse failed: {e}")
        return 1
    
    unique_judgments, duplicate_ids = deduplicate_judgments(judgments)
    if duplicate_ids:
        logger.warning(
            "⚠️ Duplicate judgment IDs detected: %d repeated records; "
            "%d unique judgments will be compiled",
            len(duplicate_ids),
            len(unique_judgments),
        )

    # Stats
    total_parties = sum(len(j.parties) for j in unique_judgments)
    total_refs = sum(len(j.legal_references) for j in unique_judgments)
    avg_quality = (
        sum(j.quality_score for j in unique_judgments) / len(unique_judgments)
        if unique_judgments else 0
    )
    
    print("\n" + "=" * 80)
    print("📊 CORPUS STATISTICS")
    print("=" * 80)
    print(f"Input Judgments: {len(judgments)}")
    print(f"Unique         : {len(unique_judgments)}")
    print(f"Duplicates     : {len(duplicate_ids)}")
    unique_count = len(unique_judgments) or 1
    print(f"Parties        : {total_parties} ({total_parties/unique_count:.1f}/judgment)")
    print(f"Legal Refs     : {total_refs} ({total_refs/unique_count:.1f}/judgment)")
    print(f"Avg Quality    : {avg_quality:.3f}")
    print("=" * 80 + "\n")
    
    if args.dry_run:
        logger.info("🏁 Dry-run complete")
        return 0
    
    # Compile
    compiler = EnterpriseJudgmentCompiler()
    
    try:
        result = compiler.compile(judgments, batch_size=args.batch_size)
        
        print("\n" + "=" * 80)
        print("✅ COMPILATION COMPLETE")
        print("=" * 80)
        print(f"Run ID         : {result['run_id']}")
        print(f"Status         : {result['status']}")
        print(f"Duration       : {result['duration_sec']:.1f}s")
        print(f"Processed      : {result['processed']}/{result['total_judgments']}")
        print(f"Entities       : {result['entities_created']}")
        print(f"Relationships  : {result['relationships_created']}")
        print(f"Throughput     : {result['throughput_jps']:.2f} j/s")
        print(f"Errors         : {result['errors_count']}")
        print("=" * 80 + "\n")
        
        if result['errors_count'] > 0:
            logger.warning(f"⚠️  {result['errors_count']} errors occurred")
            return 1
        
        logger.info("✅ Success!")
        return 0
        
    except Exception as e:
        logger.error(f"❌ Failed: {e}")
        logger.debug(traceback.format_exc())
        return 1


if __name__ == '__main__':
    sys.exit(main())
