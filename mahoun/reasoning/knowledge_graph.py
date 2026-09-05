"""
Legal Knowledge Graph
=====================

Store and query legal knowledge including:
- Legal rules
- Precedents
- Relationships

Features:
- Persistent storage (JSON files + Neo4j)
- Version history for rules/precedents
- CRUD operations
- Similarity-based search
- Batch loading support
- Governance context integration
"""


from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import asyncio
from concurrent.futures import ThreadPoolExecutor

from mahoun.core.logging import setup_logger
from mahoun.graph.batch import (
    BatchJob,
    JobPriority,
    PriorityQueue,
    Worker,
    ResourceLimits,
)

log = setup_logger("knowledge_graph")


@dataclass
class LegalRule:
    """Legal rule with condition and conclusion"""
    rule_id: str
    condition: str
    conclusion: str
    confidence: float = 1.0
    usage_count: int = 0
    source: str = "manual"
    metadata: Dict = field(default_factory=dict)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Optional[Any] = None


@dataclass
class LegalPrecedent:
    """Legal precedent case"""
    precedent_id: str  # Renamed from case_id for semantic clarity (external legal case reference)
    facts: List[str]
    decision: str
    court: str
    date: Optional[str] = None
    relevance_score: float = 0.0
    metadata: Dict = field(default_factory=dict)
    version: int = 1
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    provenance: Optional[Any] = None


class LegalKnowledgeGraph:
    """
    Legal knowledge graph for reasoning with persistent storage.
    
    Features:
    - Store legal rules with version history
    - Store precedents with version history
    - Find applicable rules
    - Find similar precedents
    - CRUD operations
    - JSON file persistence
    - Neo4j persistence
    - Batch loading with parallel processing
    - Governance context integration
    """
    
    def __init__(
        self,
        storage_path: Optional[Path] = None,
        enable_semantic: bool = True,
        enable_neo4j: bool = True,
        neo4j_write_governance: bool = True,
        batch_mode: bool = False,
    ):
        """
        Initialize knowledge graph with optional persistent storage.
        
        Args:
            storage_path: Path for persistent storage. If None, uses in-memory only.
            enable_semantic: Whether to enable semantic search (default: True)
            enable_neo4j: Whether to enable Neo4j persistence (default: True)
            neo4j_write_governance: Whether to use governance context for Neo4j writes (default: True)
            batch_mode: Whether to enable batch loading mode (default: False)
        """
        self.storage_path = storage_path
        self.entities: Dict[str, Any] = {}
        self.relationships: Dict[str, List] = {}
        self.legal_rules: Dict[str, LegalRule] = {}
        self.precedents: Dict[str, LegalPrecedent] = {}
        
        # Version history
        self._rule_versions: Dict[str, List[Dict]] = {}
        self._precedent_versions: Dict[str, List[Dict]] = {}
        
        # Semantic search (lazy initialization)
        self._semantic_searcher: Optional[Any] = None
        self._vector_index: Optional[Any] = None
        
        # Neo4j support
        self.enable_neo4j = enable_neo4j
        self.neo4j_write_governance = neo4j_write_governance
        self._neo4j_connection: Optional[Any] = None
        
        # Batch loading support
        self.batch_mode = batch_mode
        self._batch_queue: Optional[PriorityQueue] = None
        self._batch_workers: List[Worker] = []
        
        # Load from storage if path provided
        if self.storage_path:
            self.storage_path.mkdir(parents=True, exist_ok=True)
            self._load_from_storage()
        
        # Initialize Neo4j if enabled
        if self.enable_neo4j:
            self._init_neo4j()
        
        # Enable semantic search by default
        if enable_semantic:
            try:
                self.enable_semantic_search()
            except ImportError:
                log.warning(
                    "Semantic search not available (sentence-transformers not installed). "
                    "Falling back to keyword matching."
                )
        
        log.info(
            f"Initialized LegalKnowledgeGraph "
            f"(storage={storage_path}, semantic={enable_semantic}, "
            f"neo4j={enable_neo4j}, batch={batch_mode})"
        )
    
    def _init_neo4j(self) -> None:
        """Initialize Neo4j connection"""
        try:
            from mahoun.graph.neo4j.connection import get_connection
            self._neo4j_connection = get_connection()
            log.info("Neo4j connection initialized for LegalKnowledgeGraph")
        except Exception as e:
            log.warning(f"Failed to initialize Neo4j: {e}. Using in-memory storage only.")
            self.enable_neo4j = False
    
    def _write_to_neo4j_rule(self, rule: LegalRule) -> None:
        """Write rule to Neo4j"""
        if not self.enable_neo4j or not self._neo4j_connection:
            return
        
        try:
            query = """
            MERGE (r:LegalRule {rule_id: $rule_id})
            SET r.condition = $condition,
                r.conclusion = $conclusion,
                r.confidence = $confidence,
                r.usage_count = $usage_count,
                r.source = $source,
                r.version = $version,
                r.created_at = $created_at,
                r.updated_at = $updated_at,
                r.metadata = $metadata,
                r.provenance = $provenance
            RETURN r
            """
            
            self._neo4j_connection._raw_execute(query, {
                "rule_id": rule.rule_id,
                "condition": rule.condition,
                "conclusion": rule.conclusion,
                "confidence": rule.confidence,
                "usage_count": rule.usage_count,
                "source": rule.source,
                "version": rule.version,
                "created_at": rule.created_at,
                "updated_at": rule.updated_at,
                "metadata": json.dumps(rule.metadata, ensure_ascii=False),
                "provenance": json.dumps(
                    self._serialize_provenance(rule.provenance), 
                    ensure_ascii=False
                ) if rule.provenance else None,
            })
            
            log.debug(f"Wrote rule to Neo4j: {rule.rule_id}")
            
        except Exception as e:
            log.error(f"Failed to write rule to Neo4j: {e}")
    
    def _write_to_neo4j_precedent(self, prec: LegalPrecedent) -> None:
        """Write precedent to Neo4j"""
        if not self.enable_neo4j or not self._neo4j_connection:
            return
        
        try:
            query = """
            MERGE (p:LegalPrecedent {precedent_id: $precedent_id})
            SET p.facts = $facts,
                p.decision = $decision,
                p.court = $court,
                p.date = $date,
                p.relevance_score = $relevance_score,
                p.version = $version,
                p.created_at = $created_at,
                p.updated_at = $updated_at,
                p.metadata = $metadata,
                p.provenance = $provenance
            RETURN p
            """
            
            self._neo4j_connection._raw_execute(query, {
                "precedent_id": prec.precedent_id,
                "facts": prec.facts,
                "decision": prec.decision,
                "court": prec.court,
                "date": prec.date,
                "relevance_score": prec.relevance_score,
                "version": prec.version,
                "created_at": prec.created_at,
                "updated_at": prec.updated_at,
                "metadata": json.dumps(prec.metadata, ensure_ascii=False),
                "provenance": json.dumps(
                    self._serialize_provenance(prec.provenance),
                    ensure_ascii=False
                ) if prec.provenance else None,
            })
            
            log.debug(f"Wrote precedent to Neo4j: {prec.precedent_id}")
            
        except Exception as e:
            log.error(f"Failed to write precedent to Neo4j: {e}")

    def _resolve_entity_provenance(self, source: str, correlation_id: str, author: str, *, preserve_existing: Optional[Any] = None) -> Any:
        if preserve_existing is not None:
            return preserve_existing

        try:
            from mahoun.reasoning.evidence_linked_verdict import _resolve_provenance

            provenance = _resolve_provenance(
                source=source,
                correlation_id=correlation_id,
                author=author,
            )
        except Exception as exc:  # pragma: no cover - defensive fallback
            log.warning("Falling back to synthetic provenance for knowledge graph entity: %s", exc)
            provenance = None

        if provenance is None:
            return {
                "source": source,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "created_by": author,
                "correlation_id": correlation_id,
                "governance_scope_id": "development_synthetic_scope",
                "runtime_attestation_id": "development_synthetic_attestation",
            }

        if hasattr(provenance, "to_dict"):
            data = provenance.to_dict()
            data.setdefault("created_at", data.get("timestamp"))
            data.setdefault("created_by", data.get("author"))
            return data

        return provenance

    @staticmethod
    def _serialize_provenance(provenance: Optional[Any]) -> Optional[Any]:
        if provenance is None:
            return None
        if isinstance(provenance, dict):
            return provenance
        if hasattr(provenance, "to_dict"):
            return provenance.to_dict()
        return {"value": str(provenance)}
    
    def enable_semantic_search(
        self,
        model_name: Optional[str] = None,
        cache_size: int = 10000
    ):
        """
        Enable semantic search for rules and precedents.
        
        Args:
            model_name: SentenceTransformer model name
            cache_size: Cache size for embeddings
        """
        try:
            from mahoun.graph.semantic_search import PersianSemanticSearch
            
            self._semantic_searcher = PersianSemanticSearch(
                model_name=model_name,
                cache_size=cache_size
            )
            
            log.info("Semantic search enabled for knowledge graph")
            
        except ImportError as e:
            log.error(
                f"Failed to enable semantic search: {e}. "
                f"Install sentence-transformers: pip install sentence-transformers"
            )
            raise
    
    def _load_from_storage(self) -> None:
        """Load rules and precedents from storage."""
        if not self.storage_path:
            return
        
        # Load rules
        rules_file = self.storage_path / "rules.json"
        if rules_file.exists():
            try:
                with open(rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for r in data:
                        rule = LegalRule(**r)
                        self.legal_rules[rule.rule_id] = rule
                log.info(f"Loaded {len(self.legal_rules)} rules from storage")
            except (json.JSONDecodeError, TypeError) as e:
                log.error(f"Failed to load rules: {e}")
        
        # Load precedents
        precedents_file = self.storage_path / "precedents.json"
        if precedents_file.exists():
            try:
                with open(precedents_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for p in data:
                        prec = LegalPrecedent(**p)
                        self.precedents[prec.case_id] = prec
                log.info(f"Loaded {len(self.precedents)} precedents from storage")
            except (json.JSONDecodeError, TypeError) as e:
                log.error(f"Failed to load precedents: {e}")
        
        # Load version history
        versions_file = self.storage_path / "versions.json"
        if versions_file.exists():
            try:
                with open(versions_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._rule_versions = data.get("rules", {})
                    self._precedent_versions = data.get("precedents", {})
            except (json.JSONDecodeError, TypeError) as e:
                log.error(f"Failed to load versions: {e}")
    
    def _save_to_storage(self) -> None:
        """Save rules and precedents to storage."""
        if not self.storage_path:
            return
        
        # Save rules
        rules_file = self.storage_path / "rules.json"
        with open(rules_file, 'w', encoding='utf-8') as f:
            rules_data = []
            for rule in self.legal_rules.values():
                rules_data.append({
                    "rule_id": rule.rule_id,
                    "condition": rule.condition,
                    "conclusion": rule.conclusion,
                    "confidence": rule.confidence,
                    "usage_count": rule.usage_count,
                    "source": rule.source,
                    "metadata": rule.metadata,
                    "version": rule.version,
                    "created_at": rule.created_at,
                    "updated_at": rule.updated_at,
                    "provenance": self._serialize_provenance(rule.provenance),
                })
            json.dump(rules_data, f, ensure_ascii=False, indent=2)
        
        # Save precedents
        precedents_file = self.storage_path / "precedents.json"
        with open(precedents_file, 'w', encoding='utf-8') as f:
            prec_data = []
            for prec in self.precedents.values():
                prec_data.append({
                    "case_id": prec.case_id,
                    "facts": prec.facts,
                    "decision": prec.decision,
                    "court": prec.court,
                    "date": prec.date,
                    "relevance_score": prec.relevance_score,
                    "metadata": prec.metadata,
                    "version": prec.version,
                    "created_at": prec.created_at,
                    "updated_at": prec.updated_at,
                    "provenance": self._serialize_provenance(prec.provenance),
                })
            json.dump(prec_data, f, ensure_ascii=False, indent=2)
        
        # Save version history
        versions_file = self.storage_path / "versions.json"
        with open(versions_file, 'w', encoding='utf-8') as f:
            json.dump({
                "rules": self._rule_versions,
                "precedents": self._precedent_versions
            }, f, ensure_ascii=False, indent=2)
        
        log.debug("Saved knowledge graph to storage")
    
    def add_legal_rule(
        self,
        rule_id: str,
        condition: str,
        conclusion: str,
        confidence: float = 1.0,
        source: str = "manual",
        write_neo4j: bool = True
    ) -> LegalRule:
        """
        Add or update legal rule to knowledge base.
        
        If rule exists, creates new version and archives old one.
        
        Args:
            rule_id: Unique rule identifier
            condition: Rule condition
            conclusion: Rule conclusion
            confidence: Rule confidence (0-1)
            source: Source of rule
            write_neo4j: Whether to write to Neo4j (default: True)
            
        Returns:
            The created/updated LegalRule
        """
        now = datetime.now(timezone.utc).isoformat()
        old_rule = None
        
        # Check if rule exists (update with version history)
        if rule_id in self.legal_rules:
            old_rule = self.legal_rules[rule_id]
            
            # Archive old version
            if rule_id not in self._rule_versions:
                self._rule_versions[rule_id] = []
            self._rule_versions[rule_id].append({
                "version": old_rule.version,
                "condition": old_rule.condition,
                "conclusion": old_rule.conclusion,
                "confidence": old_rule.confidence,
                "archived_at": now
            })
            
            # Create new version
            new_version = old_rule.version + 1
            rule = LegalRule(
                rule_id=rule_id,
                condition=condition,
                conclusion=conclusion,
                confidence=confidence,
                source=source,
                usage_count=old_rule.usage_count,
                version=new_version,
                created_at=old_rule.created_at,
                updated_at=now
            )
            log.info(f"Updated legal rule: {rule_id} (v{new_version})")
        else:
            # Create new rule
            rule = LegalRule(
                rule_id=rule_id,
                condition=condition,
                conclusion=conclusion,
                confidence=confidence,
                source=source,
                version=1,
                created_at=now,
                updated_at=now
            )
            log.debug(f"Added legal rule: {rule_id}")
        
        # Set provenance
        rule.provenance = self._resolve_entity_provenance(
            source="knowledge_graph:add_legal_rule",
            correlation_id=rule_id,
            author="mahoun_knowledge_graph",
            preserve_existing=old_rule.provenance if old_rule else None,
        )
        self.legal_rules[rule_id] = rule
        
        # Save to storage
        self._save_to_storage()
        
        # Write to Neo4j if enabled
        if write_neo4j:
            self._write_to_neo4j_rule(rule)
        
        return rule
    
    def add_precedent(
        self,
        precedent_id: str,  # Renamed from case_id for semantic clarity
        facts: List[str],
        decision: str,
        court: str,
        date: Optional[str] = None,
        write_neo4j: bool = True
    ) -> LegalPrecedent:
        """
        Add or update legal precedent.
        
        If precedent exists, creates new version and archives old one.
        
        Args:
            precedent_id: Unique precedent identifier (external legal case reference)
            facts: List of case facts
            decision: Court decision
            court: Court name
            date: Decision date
            write_neo4j: Whether to write to Neo4j (default: True)
            
        Returns:
            The created/updated LegalPrecedent
        """
        now = datetime.now(timezone.utc).isoformat()
        old_prec = None
        
        # Check if precedent exists (update with version history)
        if precedent_id in self.precedents:
            old_prec = self.precedents[precedent_id]
            
            # Archive old version
            if precedent_id not in self._precedent_versions:
                self._precedent_versions[precedent_id] = []
            self._precedent_versions[precedent_id].append({
                "version": old_prec.version,
                "facts": old_prec.facts,
                "decision": old_prec.decision,
                "archived_at": now
            })
            
            # Create new version
            new_version = old_prec.version + 1
            prec = LegalPrecedent(
                precedent_id=precedent_id,
                facts=facts,
                decision=decision,
                court=court,
                date=date,
                relevance_score=old_prec.relevance_score,
                version=new_version,
                created_at=old_prec.created_at,
                updated_at=now
            )
            log.info(f"Updated precedent: {precedent_id} (v{new_version})")
        else:
            # Create new precedent
            prec = LegalPrecedent(
                precedent_id=precedent_id,
                facts=facts,
                decision=decision,
                court=court,
                date=date,
                version=1,
                created_at=now,
                updated_at=now
            )
            log.debug(f"Added precedent: {precedent_id}")
        
        prec.provenance = self._resolve_entity_provenance(
            source="knowledge_graph:add_precedent",
            correlation_id=precedent_id,
            author="mahoun_knowledge_graph",
            preserve_existing=old_prec.provenance if old_prec else None,
        )

        self.precedents[precedent_id] = prec
        
        # Save to storage
        self._save_to_storage()
        
        # Write to Neo4j if enabled
        if write_neo4j:
            self._write_to_neo4j_precedent(prec)
        
        return prec
    
    def find_applicable_rules(
        self,
        facts: List[str],
        use_semantic: bool = True,
        semantic_threshold: float = 0.6
    ) -> List[Dict]:
        """
        Find applicable legal rules based on facts.
        
        Uses hybrid approach:
        1. Semantic similarity (if available and enabled)
        2. Fallback to keyword matching
        
        Args:
            facts: List of facts
            use_semantic: Whether to use semantic search
            semantic_threshold: Minimum semantic similarity score
            
        Returns:
            List of applicable rules with match scores
        """
        applicable_rules: List[Any] = []
        
        # Try semantic search first
        if use_semantic and hasattr(self, '_semantic_searcher') and self._semantic_searcher:
            try:
                fact_text = " ".join(facts)
                rule_conditions = [rule.condition for rule in self.legal_rules.values()]
                rule_ids = list(self.legal_rules.keys())
                
                # Semantic similarity search
                results = self._semantic_searcher.semantic_similarity(
                    query=fact_text,
                    candidates=rule_conditions,
                    top_k=len(rule_conditions),
                    threshold=semantic_threshold
                )
                
                for result in results:
                    rule_id = rule_ids[rule_conditions.index(result.text)]
                    rule = self.legal_rules[rule_id]
                    
                    applicable_rules.append({
                        "rule_id": rule_id,
                        "rule": rule,
                        "match_score": result.score,
                        "match_type": "semantic"
                    })
                    
                    # Update usage count
                    rule.usage_count += 1
                
                log.debug(
                    f"Found {len(applicable_rules)} applicable rules "
                    f"(semantic search)"
                )
                
                return applicable_rules
                
            except Exception as e:
                log.warning(f"Semantic search failed, falling back to keyword: {e}")
        
        # Fallback: Keyword matching
        for rule_id, rule in self.legal_rules.items():
            # Simple keyword matching
            condition_keywords = rule.condition.lower().split()
            fact_text = " ".join(facts).lower()
            
            # Calculate match score
            match_score = sum(
                1 for keyword in condition_keywords 
                if keyword in fact_text
            )
            
            if match_score > 0:
                applicable_rules.append({
                    "rule_id": rule_id,
                    "rule": rule,
                    "match_score": match_score / len(condition_keywords),
                    "match_type": "keyword"
                })
                
                # Update usage count
                rule.usage_count += 1
        
        # Sort by match score
        applicable_rules.sort(key=lambda x: x["match_score"], reverse=True)
        
        log.debug(
            f"Found {len(applicable_rules)} applicable rules "
            f"(keyword matching)"
        )
        
        return applicable_rules
    
    def find_similar_precedents(
        self,
        current_facts: List[str],
        top_k: int = 5,
        use_semantic: bool = True,
        semantic_threshold: float = 0.5
    ) -> List[Dict]:
        """
        Find similar legal precedents.
        
        Uses hybrid approach:
        1. Semantic similarity (if available and enabled)
        2. Fallback to Jaccard word overlap
        
        Args:
            current_facts: Current case facts
            top_k: Number of precedents to return
            use_semantic: Whether to use semantic search
            semantic_threshold: Minimum semantic similarity score
            
        Returns:
            List of similar precedents with similarity scores
        """
        similar_cases: List[Any] = []
        
        # Try semantic search first
        if use_semantic and hasattr(self, '_semantic_searcher') and self._semantic_searcher:
            try:
                current_text = " ".join(current_facts)
                precedent_texts = [
                    " ".join(prec.facts) for prec in self.precedents.values()
                ]
                case_ids = list(self.precedents.keys())
                
                # Semantic similarity search
                results = self._semantic_searcher.semantic_similarity(
                    query=current_text,
                    candidates=precedent_texts,
                    top_k=top_k,
                    threshold=semantic_threshold
                )
                
                for result in results:
                    case_id = case_ids[precedent_texts.index(result.text)]
                    precedent = self.precedents[case_id]
                    
                    similar_cases.append({
                        "case_id": case_id,
                        "precedent": precedent,
                        "similarity": result.score,
                        "match_type": "semantic"
                    })
                    
                    # Update relevance score
                    precedent.relevance_score = result.score
                
                log.debug(
                    f"Found {len(similar_cases)} similar precedents "
                    f"(semantic search)"
                )
                
                return similar_cases
                
            except Exception as e:
                log.warning(f"Semantic search failed, falling back to Jaccard: {e}")
        
        # Fallback: Jaccard similarity
        current_text = " ".join(current_facts).lower()
        current_words = set(current_text.split())
        
        for case_id, precedent in self.precedents.items():
            precedent_text = " ".join(precedent.facts).lower()
            precedent_words = set(precedent_text.split())
            
            # Calculate similarity (Jaccard)
            common_words = current_words & precedent_words
            all_words = current_words | precedent_words
            
            if len(all_words) > 0:
                similarity = len(common_words) / len(all_words)
            else:
                similarity = 0.0
            
            # Threshold for relevance
            if similarity > 0.1:
                similar_cases.append({
                    "case_id": case_id,
                    "precedent": precedent,
                    "similarity": similarity,
                    "match_type": "jaccard"
                })
                
                # Update relevance score
                precedent.relevance_score = similarity
        
        # Sort by similarity
        similar_cases.sort(key=lambda x: x["similarity"], reverse=True)
        
        log.debug(
            f"Found {len(similar_cases)} similar precedents "
            f"(Jaccard similarity)"
        )
        
        return similar_cases[:top_k]
    
    def get_rule(self, rule_id: str) -> Optional[LegalRule]:
        """Get rule by ID"""
        return self.legal_rules.get(rule_id)
    
    def get_precedent(self, case_id: str) -> Optional[LegalPrecedent]:
        """Get precedent by ID"""
        return self.precedents.get(case_id)
    
    def delete_rule(self, rule_id: str) -> bool:
        """
        Delete a rule by ID.
        
        Args:
            rule_id: Rule to delete
            
        Returns:
            True if deleted, False if not found
        """
        if rule_id in self.legal_rules:
            del self.legal_rules[rule_id]
            self._save_to_storage()
            log.info(f"Deleted rule: {rule_id}")
            return True
        return False
    
    def delete_precedent(self, case_id: str) -> bool:
        """
        Delete a precedent by ID.
        
        Args:
            case_id: Precedent to delete
            
        Returns:
            True if deleted, False if not found
        """
        if case_id in self.precedents:
            del self.precedents[case_id]
            self._save_to_storage()
            log.info(f"Deleted precedent: {case_id}")
            return True
        return False
    
    def get_rule_history(self, rule_id: str) -> List[Dict]:
        """Get version history for a rule."""
        return self._rule_versions.get(rule_id, [])
    
    def get_precedent_history(self, case_id: str) -> List[Dict]:
        """Get version history for a precedent."""
        return self._precedent_versions.get(case_id, [])
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get knowledge graph statistics"""
        return {
            "num_rules": len(self.legal_rules),
            "num_precedents": len(self.precedents),
            "num_entities": len(self.entities),
            "num_relationships": len(self.relationships),
            "num_rule_versions": sum(len(v) for v in self._rule_versions.values()),
            "num_precedent_versions": sum(len(v) for v in self._precedent_versions.values()),
            "storage_path": str(self.storage_path) if self.storage_path else None
        }
    
    # Batch loading support
    async def start_batch_loader(
        self,
        num_rule_workers: int = 4,
        num_precedent_workers: int = 4,
        max_queue_size: int = 5000
    ) -> None:
        """
        Start batch loader with worker pools.
        
        Args:
            num_rule_workers: Number of workers for rule loading
            num_precedent_workers: Number of workers for precedent loading
            max_queue_size: Maximum queue size
        """
        if not self.batch_mode:
            log.warning("Batch mode not enabled. Call with batch_mode=True on init.")
            return
        
        # Create queue
        self._batch_queue = PriorityQueue(max_size=max_queue_size)
        log.info(f"Created batch queue (max size: {max_queue_size})")
        
        # Create resource limits
        limits = ResourceLimits(max_memory_mb=2048)
        
        # Create rule workers
        for i in range(num_rule_workers):
            worker = Worker(
                worker_id=f"rule_loader_{i}",
                task_handler=self._batch_load_rule,
                resource_limits=limits,
                heartbeat_interval=30.0,
            )
            self._batch_workers.append(worker)
            await worker.start(self._batch_queue)
        
        # Create precedent workers
        for i in range(num_precedent_workers):
            worker = Worker(
                worker_id=f"precedent_loader_{i}",
                task_handler=self._batch_load_precedent,
                resource_limits=limits,
                heartbeat_interval=30.0,
            )
            self._batch_workers.append(worker)
            await worker.start(self._batch_queue)
        
        log.info(
            f"Started batch loader with {num_rule_workers} rule workers "
            f"and {num_precedent_workers} precedent workers"
        )
    
    async def _batch_load_rule(self, job: BatchJob) -> Dict[str, Any]:
        """Load rule from batch job"""
        try:
            data = job.data
            rule = self.add_legal_rule(
                rule_id=data["rule_id"],
                condition=data["condition"],
                conclusion=data["conclusion"],
                confidence=data.get("confidence", 1.0),
                source=data.get("source", "batch_loader"),
                write_neo4j=self.enable_neo4j
            )
            return {
                "status": "success",
                "rule_id": rule.rule_id,
                "version": rule.version
            }
        except Exception as e:
            log.error(f"Failed to load rule: {e}")
            raise
    
    async def _batch_load_precedent(self, job: BatchJob) -> Dict[str, Any]:
        """Load precedent from batch job"""
        try:
            data = job.data
            prec = self.add_precedent(
                case_id=data["case_id"],
                facts=data["facts"],
                decision=data["decision"],
                court=data["court"],
                date=data.get("date"),
                write_neo4j=self.enable_neo4j
            )
            return {
                "status": "success",
                "case_id": prec.case_id,
                "version": prec.version
            }
        except Exception as e:
            log.error(f"Failed to load precedent: {e}")
            raise
    
    async def enqueue_rule_batch(
        self,
        rules: List[Dict[str, Any]],
        priority: JobPriority = JobPriority.NORMAL
    ) -> int:
        """
        Enqueue rules for batch loading.
        
        Args:
            rules: List of rule data dicts
            priority: Job priority for queue
            
        Returns:
            Number of jobs enqueued
        """
        if not self._batch_queue:
            raise RuntimeError("Batch queue not initialized. Call start_batch_loader first.")
        
        count = 0
        for rule_data in rules:
            job = BatchJob(
                task_name="load_rule",
                data=rule_data,
                priority=priority,
                timeout=300.0,
                max_retries=2,
            )
            await self._batch_queue.enqueue(job)
            count += 1
        
        log.info(f"Enqueued {count} rule jobs")
        return count
    
    async def enqueue_precedent_batch(
        self,
        precedents: List[Dict[str, Any]],
        priority: JobPriority = JobPriority.NORMAL
    ) -> int:
        """
        Enqueue precedents for batch loading.
        
        Args:
            precedents: List of precedent data dicts
            priority: Job priority for queue
            
        Returns:
            Number of jobs enqueued
        """
        if not self._batch_queue:
            raise RuntimeError("Batch queue not initialized. Call start_batch_loader first.")
        
        count = 0
        for prec_data in precedents:
            job = BatchJob(
                task_name="load_precedent",
                data=prec_data,
                priority=priority,
                timeout=300.0,
                max_retries=2,
            )
            await self._batch_queue.enqueue(job)
            count += 1
        
        log.info(f"Enqueued {count} precedent jobs")
        return count
    
    async def stop_batch_loader(self, timeout: float = 30.0) -> None:
        """Stop batch loader workers"""
        for worker in self._batch_workers:
            await worker.stop(graceful=True, timeout=timeout)
        
        self._batch_workers.clear()
        log.info("Stopped batch loader")
    
    def clear(self):
        """Clear all knowledge"""
        self.entities.clear()
        self.relationships.clear()
        self.legal_rules.clear()
        self.precedents.clear()
        self._rule_versions.clear()
        self._precedent_versions.clear()
        self._save_to_storage()
        log.info("Cleared knowledge graph")
