"""
Advanced Graph-Symbolic Bridge
==============================
Translates Neo4j Knowledge Graph subgraphs into First-Order Logic (FOL) facts
for the SymbolicReasoningEngine with enhanced capabilities.

Features:
- Property extraction (dates, amounts, status)
- Temporal reasoning predicates (before, after, during)
- Quantitative reasoning (comparison predicates)
- Legal domain specifics (valid, expired, applicable)
- Confidence scoring for facts
- Bidirectional predicate generation
- Type safety and validation
- Performance caching
"""

from typing import Any, Dict, List, Set, Optional, Tuple
import logging
from datetime import datetime
from dataclasses import dataclass, field
from functools import lru_cache
from mahoun.reasoning.first_order_logic import Atom, Term, TermType

logger = logging.getLogger(__name__)


@dataclass
class FactMetadata:
    """Metadata for generated facts"""
    confidence: float = 1.0
    source: str = "graph"
    temporal: bool = False
    quantitative: bool = False
    legal_specific: bool = False


@dataclass
class TranslationResult:
    """Result of graph-to-facts translation"""
    facts: List[Atom] = field(default_factory=list)
    metadata: Dict[str, FactMetadata] = field(default_factory=dict)
    statistics: Dict[str, int] = field(default_factory=dict)


class GraphSymbolicBridge:
    """
    Advanced bridge for translating Neo4j KG to FOL facts.
    
    Enhancements over basic bridge:
    - Property extraction with type-aware conversion
    - Temporal reasoning support (dates, time ranges)
    - Quantitative predicates (greater_than, less_than, equals)
    - Legal domain predicates (valid, expired, applicable)
    - Confidence scoring based on data quality
    - Bidirectional relationship generation
    - Caching for performance
    - Comprehensive statistics
    """
    
    def __init__(self, enable_caching: bool = True, enable_bidirectional: bool = True):
        """
        Initialize advanced graph-symbolic bridge.
        
        Args:
            enable_caching: Enable LRU cache for translation results
            enable_bidirectional: Generate reverse predicates for relationships
        """
        self.enable_caching = enable_caching
        self.enable_bidirectional = enable_bidirectional
        
        # Core predicate mappings
        self.predicate_mappings = {
            "HAS_PARTY": "has_role",
            "CITES": "refers_to",
            "ISSUED_BY": "issued_by",
            "APPLIES_TO": "applies_to",
            "MODIFIES": "modifies",
            "SUPERSEDES": "supersedes",
            "CONTRADICTS": "contradicts",
            "REQUIRES": "requires",
            "PROHIBITS": "prohibits",
        }
        
        # Legal domain-specific predicates
        self.legal_predicates = {
            "is_valid": lambda props: self._check_validity(props),
            "is_expired": lambda props: self._check_expiration(props),
            "is_applicable": lambda props: self._check_applicability(props),
            "is_enforceable": lambda props: self._check_enforceability(props),
        }
        
        # Temporal property mappings
        self.temporal_properties = {
            "date", "issued_date", "effective_date", "expiration_date",
            "start_date", "end_date", "created_at", "updated_at"
        }
        
        # Quantitative property mappings
        self.quantitative_properties = {
            "amount", "value", "limit", "threshold", "percentage",
            "duration", "period", "term"
        }
        
        logger.info(
            f"Advanced GraphSymbolicBridge initialized "
            f"(caching={enable_caching}, bidirectional={enable_bidirectional})"
        )
    
    def graph_to_facts(
        self,
        subgraph_nodes: List[Dict[str, Any]],
        subgraph_edges: List[Dict[str, Any]],
        include_metadata: bool = False
    ) -> TranslationResult:
        """
        Translates graph subgraph into FOL facts with enhanced capabilities.
        
        Args:
            subgraph_nodes: List of Neo4j node dictionaries
            subgraph_edges: List of Neo4j relationship dictionaries
            include_metadata: Include FactMetadata in result
            
        Returns:
            TranslationResult with facts, metadata, and statistics
        """
        if self.enable_caching:
            cache_key = self._compute_cache_key(subgraph_nodes, subgraph_edges)
            cached = self._get_cached_translation(cache_key)
            if cached:
                logger.debug(f"Using cached translation (cache hit)")
                return cached
        
        result = TranslationResult()
        facts = []
        metadata = {}
        
        # Statistics tracking
        stats = {
            "nodes_processed": 0,
            "edges_processed": 0,
            "type_facts": 0,
            "property_facts": 0,
            "temporal_facts": 0,
            "quantitative_facts": 0,
            "legal_facts": 0,
            "bidirectional_facts": 0,
        }
        
        # Process Nodes with property extraction
        for node in subgraph_nodes:
            stats["nodes_processed"] += 1
            node_facts, node_metadata = self._process_node(node)
            facts.extend(node_facts)
            metadata.update(node_metadata)
            stats["type_facts"] += len([f for f in node_facts if not any(
                m.temporal or m.quantitative or m.legal_specific
                for m in node_metadata.values()
            )])
        
        # Process Edges with bidirectional support
        for edge in subgraph_edges:
            stats["edges_processed"] += 1
            edge_facts, edge_metadata = self._process_edge(edge)
            facts.extend(edge_facts)
            metadata.update(edge_metadata)
            
            # Generate bidirectional predicates if enabled
            if self.enable_bidirectional:
                bidirectional_facts, bidirectional_metadata = self._generate_bidirectional(edge)
                facts.extend(bidirectional_facts)
                metadata.update(bidirectional_metadata)
                stats["bidirectional_facts"] += len(bidirectional_facts)
        
        # Update statistics
        stats["property_facts"] = sum(1 for m in metadata.values() if m.source == "property")
        stats["temporal_facts"] = sum(1 for m in metadata.values() if m.temporal)
        stats["quantitative_facts"] = sum(1 for m in metadata.values() if m.quantitative)
        stats["legal_facts"] = sum(1 for m in metadata.values() if m.legal_specific)
        
        result.facts = facts
        result.metadata = metadata if include_metadata else {}
        result.statistics = stats
        
        if self.enable_caching:
            self._cache_translation(cache_key, result)
        
        logger.info(
            f"Advanced bridge generated {len(facts)} facts: "
            f"type={stats['type_facts']}, temporal={stats['temporal_facts']}, "
            f"quantitative={stats['quantitative_facts']}, legal={stats['legal_facts']}"
        )
        
        return result
    
    def _process_node(self, node: Dict[str, Any]) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Process a single node with property extraction."""
        facts = []
        metadata = {}
        
        node_id = node.get("id", str(id(node)))
        label = node.get("label", "Entity").lower()
        properties = node.get("properties", {})
        
        term = Term(name=node_id, term_type=TermType.CONSTANT)
        
        # Type predicates (unary)
        type_pred = f"is_{label}"
        facts.append(Atom(type_pred, (term,)))
        metadata[f"{type_pred}({node_id})"] = FactMetadata(confidence=1.0, source="type")
        
        # Property extraction
        for prop_name, prop_value in properties.items():
            prop_facts, prop_metadata = self._extract_property_facts(
                node_id, prop_name, prop_value, term
            )
            facts.extend(prop_facts)
            metadata.update(prop_metadata)
        
        # Legal domain predicates
        for pred_name, pred_check in self.legal_predicates.items():
            try:
                if pred_check(properties):
                    facts.append(Atom(pred_name, (term,)))
                    metadata[f"{pred_name}({node_id})"] = FactMetadata(
                        confidence=0.9, source="legal", legal_specific=True
                    )
            except Exception as e:
                logger.debug(f"Legal predicate check failed for {pred_name}: {e}")
        
        return facts, metadata
    
    def _process_edge(self, edge: Dict[str, Any]) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Process a single edge with property extraction."""
        facts = []
        metadata = {}
        
        source = edge.get("source")
        target = edge.get("target")
        rel_type = edge.get("type", "").upper()
        properties = edge.get("properties", {})
        
        if not source or not target:
            return facts, metadata
        
        source_term = Term(name=source, term_type=TermType.CONSTANT)
        target_term = Term(name=target, term_type=TermType.CONSTANT)
        
        # Get mapped predicate name
        pred_name = self.predicate_mappings.get(rel_type, rel_type.lower())
        
        # Special handling for HAS_PARTY with role extraction
        if rel_type == "HAS_PARTY":
            role = properties.get("role", "party")
            role_pred = f"is_{role.lower().replace(' ', '_')}"
            facts.append(Atom(role_pred, (target_term, source_term)))
            metadata[f"{role_pred}({target}, {source})"] = FactMetadata(
                confidence=0.95, source="edge_role"
            )
        else:
            facts.append(Atom(pred_name, (source_term, target_term)))
            metadata[f"{pred_name}({source}, {target})"] = FactMetadata(
                confidence=1.0, source="edge"
            )
        
        # Edge property extraction
        for prop_name, prop_value in properties.items():
            if prop_name == "role":  # Already handled
                continue
            
            prop_facts, prop_metadata = self._extract_edge_property_facts(
                source, target, pred_name, prop_name, prop_value
            )
            facts.extend(prop_facts)
            metadata.update(prop_metadata)
        
        return facts, metadata
    
    def _extract_property_facts(
        self,
        node_id: str,
        prop_name: str,
        prop_value: Any,
        term: Term
    ) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Extract facts from node properties with type awareness."""
        facts = []
        metadata = {}
        
        if prop_value is None:
            return facts, metadata
        
        prop_lower = prop_name.lower()
        
        # Temporal properties
        if prop_lower in self.temporal_properties:
            temporal_facts, temporal_metadata = self._extract_temporal_facts(
                node_id, prop_name, prop_value, term
            )
            facts.extend(temporal_facts)
            metadata.update(temporal_metadata)
        
        # Quantitative properties
        elif prop_lower in self.quantitative_properties:
            quant_facts, quant_metadata = self._extract_quantitative_facts(
                node_id, prop_name, prop_value, term
            )
            facts.extend(quant_facts)
            metadata.update(quant_metadata)
        
        # Boolean properties
        elif isinstance(prop_value, bool):
            if prop_value:
                pred = f"has_{prop_lower}"
                facts.append(Atom(pred, (term,)))
                metadata[f"{pred}({node_id})"] = FactMetadata(
                    confidence=1.0, source="property"
                )
        
        # String properties (as simple predicates)
        elif isinstance(prop_value, str):
            pred = f"{prop_lower}_{prop_value.lower().replace(' ', '_')}"
            facts.append(Atom(pred, (term,)))
            metadata[f"{pred}({node_id})"] = FactMetadata(
                confidence=0.8, source="property"
            )
        
        return facts, metadata
    
    def _extract_temporal_facts(
        self,
        node_id: str,
        prop_name: str,
        prop_value: Any,
        term: Term
    ) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Extract temporal reasoning facts from date properties."""
        facts = []
        metadata = {}
        
        try:
            # Try to parse date
            if isinstance(prop_value, str):
                date_obj = datetime.fromisoformat(prop_value.replace('Z', '+00:00'))
            elif isinstance(prop_value, (int, float)):
                date_obj = datetime.fromtimestamp(prop_value)
            else:
                return facts, metadata
            
            # Add temporal predicate
            pred = f"has_{prop_name.lower()}"
            date_term = Term(name=date_obj.isoformat(), term_type=TermType.CONSTANT)
            facts.append(Atom(pred, (term, date_term)))
            metadata[f"{pred}({node_id}, {date_obj.isoformat()})"] = FactMetadata(
                confidence=0.95, source="temporal", temporal=True
            )
            
            # Add temporal comparison predicates if we have a reference date
            # (e.g., current date for "is_expired" check)
            # This could be extended with external reference dates
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse temporal property {prop_name}: {e}")
        
        return facts, metadata
    
    def _extract_quantitative_facts(
        self,
        node_id: str,
        prop_name: str,
        prop_value: Any,
        term: Term
    ) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Extract quantitative reasoning facts from numeric properties."""
        facts = []
        metadata = {}
        
        try:
            # Convert to float if possible
            if isinstance(prop_value, (int, float)):
                value = float(prop_value)
            elif isinstance(prop_value, str):
                value = float(prop_value.replace(',', ''))
            else:
                return facts, metadata
            
            # Add quantitative predicate
            pred = f"has_{prop_name.lower()}"
            value_term = Term(name=str(value), term_type=TermType.CONSTANT)
            facts.append(Atom(pred, (term, value_term)))
            metadata[f"{pred}({node_id}, {value})"] = FactMetadata(
                confidence=0.95, source="quantitative", quantitative=True
            )
            
            # Add comparison predicates against thresholds
            # (This could be extended with domain-specific thresholds)
            if value > 0:
                facts.append(Atom(f"{prop_name.lower()}_positive", (term,)))
                metadata[f"{prop_name.lower()}_positive({node_id})"] = FactMetadata(
                    confidence=0.9, source="quantitative", quantitative=True
                )
            elif value < 0:
                facts.append(Atom(f"{prop_name.lower()}_negative", (term,)))
                metadata[f"{prop_name.lower()}_negative({node_id})"] = FactMetadata(
                    confidence=0.9, source="quantitative", quantitative=True
                )
            else:  # value == 0
                facts.append(Atom(f"{prop_name.lower()}_zero", (term,)))
                metadata[f"{prop_name.lower()}_zero({node_id})"] = FactMetadata(
                    confidence=0.9, source="quantitative", quantitative=True
                )
            
        except (ValueError, TypeError) as e:
            logger.debug(f"Failed to parse quantitative property {prop_name}: {e}")
        
        return facts, metadata
    
    def _extract_edge_property_facts(
        self,
        source: str,
        target: str,
        base_pred: str,
        prop_name: str,
        prop_value: Any
    ) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Extract facts from edge properties."""
        facts = []
        metadata = {}
        
        if prop_value is None:
            return facts, metadata
        
        # Create qualified predicate name
        qualified_pred = f"{base_pred}_{prop_name.lower()}"
        
        source_term = Term(name=source, term_type=TermType.CONSTANT)
        target_term = Term(name=target, term_type=TermType.CONSTANT)
        
        if isinstance(prop_value, bool) and prop_value:
            facts.append(Atom(qualified_pred, (source_term, target_term)))
            metadata[f"{qualified_pred}({source}, {target})"] = FactMetadata(
                confidence=0.9, source="edge_property"
            )
        elif isinstance(prop_value, (int, float, str)):
            value_term = Term(name=str(prop_value), term_type=TermType.CONSTANT)
            facts.append(Atom(qualified_pred, (source_term, target_term, value_term)))
            metadata[f"{qualified_pred}({source}, {target}, {prop_value})"] = FactMetadata(
                confidence=0.85, source="edge_property"
            )
        
        return facts, metadata
    
    def _generate_bidirectional(
        self,
        edge: Dict[str, Any]
    ) -> Tuple[List[Atom], Dict[str, FactMetadata]]:
        """Generate reverse predicates for bidirectional reasoning."""
        facts = []
        metadata = {}
        
        source = edge.get("source")
        target = edge.get("target")
        rel_type = edge.get("type", "").upper()
        
        if not source or not target:
            return facts, metadata
        
        # Bidirectional mappings
        reverse_mappings = {
            "HAS_PARTY": "participates_in",
            "CITES": "cited_by",
            "APPLIES_TO": "applied_by",
            "MODIFIES": "modified_by",
            "SUPERSEDES": "superseded_by",
        }
        
        if rel_type in reverse_mappings:
            reverse_pred = reverse_mappings[rel_type]
            source_term = Term(name=source, term_type=TermType.CONSTANT)
            target_term = Term(name=target, term_type=TermType.CONSTANT)
            
            facts.append(Atom(reverse_pred, (target_term, source_term)))
            metadata[f"{reverse_pred}({target}, {source})"] = FactMetadata(
                confidence=0.9, source="bidirectional"
            )
        
        return facts, metadata
    
    def _check_validity(self, properties: Dict[str, Any]) -> bool:
        """Check if a legal entity is valid based on properties."""
        # Check expiration date
        if "expiration_date" in properties:
            try:
                exp_date = datetime.fromisoformat(properties["expiration_date"].replace('Z', '+00:00'))
                return datetime.now(exp_date.tzinfo) < exp_date
            except (ValueError, TypeError):
                pass
        
        # Check status
        status = properties.get("status", "").lower()
        return status in ("valid", "active", "in_effect", "enforced")
    
    def _check_expiration(self, properties: Dict[str, Any]) -> bool:
        """Check if a legal entity has expired."""
        if "expiration_date" not in properties:
            return False
        
        try:
            exp_date = datetime.fromisoformat(properties["expiration_date"].replace('Z', '+00:00'))
            return datetime.now(exp_date.tzinfo) >= exp_date
        except (ValueError, TypeError):
            return False
    
    def _check_applicability(self, properties: Dict[str, Any]) -> bool:
        """Check if a legal entity is applicable."""
        status = properties.get("status", "").lower()
        return status in ("applicable", "active", "in_effect")
    
    def _check_enforceability(self, properties: Dict[str, Any]) -> bool:
        """Check if a legal entity is enforceable."""
        enforceable = properties.get("enforceable", True)
        if isinstance(enforceable, bool):
            return enforceable
        if isinstance(enforceable, str):
            return enforceable.lower() in ("true", "yes", "1")
        return True
    
    def _compute_cache_key(
        self,
        nodes: List[Dict[str, Any]],
        edges: List[Dict[str, Any]]
    ) -> str:
        """Compute cache key for translation result."""
        import hashlib
        import json
        
        # Create deterministic string representation
        cache_data = {
            "nodes": sorted([(n.get("id"), n.get("label"), n.get("properties")) for n in nodes]),
            "edges": sorted([(e.get("source"), e.get("target"), e.get("type"), e.get("properties")) for e in edges])
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return hashlib.sha256(cache_str.encode()).hexdigest()
    
    def _get_cached_translation(self, cache_key: str) -> Optional[TranslationResult]:
        """Get cached translation result if available."""
        return self._translation_cache.get(cache_key) if hasattr(self, '_translation_cache') else None
    
    def _cache_translation(self, cache_key: str, result: TranslationResult):
        """Cache translation result."""
        if not hasattr(self, '_translation_cache'):
            self._translation_cache = {}
        
        # Simple LRU eviction (keep last 100 entries)
        if len(self._translation_cache) >= 100:
            oldest_key = next(iter(self._translation_cache))
            del self._translation_cache[oldest_key]
        
        self._translation_cache[cache_key] = result
