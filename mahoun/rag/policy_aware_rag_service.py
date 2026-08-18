"""
Policy-Aware RAG Service - Governance-Enhanced Retrieval
========================================================

Enterprise-grade RAG wrapper with:
- Full Governance Kernel integration
- Policy-based filtering (privacy, sensitivity, authority)
- Intelligent caching with TTL
- Query rewriting
- Multi-stage reranking
- Comprehensive observability

CRITICAL: This is a COMPOSITION WRAPPER over HybridRAGService.
Per AGENTS.md Part 3: Never create duplicate implementations.

Architecture:
    PolicyAwareRAGService (governance + policy + caching)
      ↓ composition
    HybridRAGService (multi-mode retrieval)
      ↓ composition
    UltraHybridSearch + VectorStore + GraphRetriever

Created: 2026-08-01
Part of: Phase 4 - Architecture Integration Mission
"""

import logging
import time
import hashlib
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import OrderedDict

from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.governance.governance_context import GovernanceScopeEnforcer
from mahoun.rag.hybrid_rag_service import (
    HybridRAGService,
    HybridRAGResult,
    RetrievalResult,
    RAGMode
)
from mahoun.reasoning.rag_evidence import RAGEvidenceNode

logger = logging.getLogger(__name__)


# ============================================================================
# Policy Models
# ============================================================================

class PrivacyLevel(str, Enum):
    """Privacy levels for document filtering"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class SourceAuthority(str, Enum):
    """Source authority levels"""
    PRIMARY = "primary"       # Original legislation, court verdicts
    SECONDARY = "secondary"   # Legal commentary, analysis
    TERTIARY = "tertiary"     # General legal information
    UNKNOWN = "unknown"


@dataclass
class RetrievalPolicy:
    """Policy constraints for retrieval"""
    min_privacy_level: PrivacyLevel = PrivacyLevel.PUBLIC
    max_privacy_level: PrivacyLevel = PrivacyLevel.RESTRICTED
    allowed_sources: Optional[List[SourceAuthority]] = None
    min_confidence_score: float = 0.0
    max_result_age_days: Optional[int] = None
    require_governance_approval: bool = True
    
    def __post_init__(self):
        """Validate policy constraints"""
        if self.min_confidence_score < 0.0 or self.min_confidence_score > 1.0:
            raise ValueError(f"min_confidence_score must be in [0, 1], got {self.min_confidence_score}")


@dataclass
class CacheEntry:
    """Cached retrieval result with metadata"""
    query_hash: str
    result: HybridRAGResult
    cached_at: datetime
    ttl_seconds: int
    hit_count: int = 0
    last_access: datetime = field(default_factory=datetime.now)
    
    @property
    def is_expired(self) -> bool:
        """Check if cache entry has expired"""
        age = (datetime.now() - self.cached_at).total_seconds()
        return age > self.ttl_seconds
    
    @property
    def is_hot(self) -> bool:
        """Check if entry is frequently accessed (hot)"""
        return self.hit_count >= 3


# ============================================================================
# Policy-Aware RAG Service
# ============================================================================

class PolicyAwareRAGService:
    """
    Enterprise RAG service with governance, policy filtering, and caching.
    
    Features:
    - ✅ Governance context enforcement
    - ✅ Policy-based result filtering
    - ✅ Intelligent LRU cache with TTL
    - ✅ Query rewriting for better results
    - ✅ Multi-stage reranking
    - ✅ Confidence scoring
    - ✅ Comprehensive metrics
    
    Usage:
        service = PolicyAwareRAGService(
            base_service=HybridRAGService(...),
            default_policy=RetrievalPolicy(
                min_privacy_level=PrivacyLevel.PUBLIC,
                min_confidence_score=0.5
            ),
            enable_governance=True,
            enable_cache=True
        )
        
        # Retrieval with policy filtering
        # NOTE: GovernanceContext is received from middleware, NOT created here
        result = await service.retrieve(
            query="قانون مدنی ماده 10",
            mode=RAGMode.AUTO,
            top_k=10,
            policy=custom_policy  # Optional override
        )
    """
    
    def __init__(
        self,
        base_service: HybridRAGService,
        default_policy: Optional[RetrievalPolicy] = None,
        enable_governance: bool = True,
        enable_cache: bool = True,
        enable_query_rewriting: bool = True,
        enable_reranking: bool = True,
        cache_ttl_seconds: int = 3600,  # 1 hour
        cache_max_size: int = 1000,
        query_rewriter=None,  # Optional QueryRewriter instance
    ):
        """
        Initialize Policy-Aware RAG Service.
        
        Args:
            base_service: HybridRAGService instance to wrap
            default_policy: Default retrieval policy
            enable_governance: Enable governance context enforcement
            enable_cache: Enable intelligent caching
            enable_query_rewriting: Enable query rewriting
            enable_reranking: Enable multi-stage reranking
            cache_ttl_seconds: Default TTL for cached entries
            cache_max_size: Maximum cache size (LRU eviction)
            query_rewriter: Optional QueryRewriter instance
        """
        # Core components
        self.base_service = base_service
        self.default_policy = default_policy or RetrievalPolicy()
        
        # Feature flags
        self.enable_governance = enable_governance
        self.enable_cache = enable_cache
        self.enable_query_rewriting = enable_query_rewriting
        self.enable_reranking = enable_reranking
        
        # Cache configuration
        self.cache_ttl_seconds = cache_ttl_seconds
        self.cache_max_size = cache_max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        
        # Query rewriter (lazy load if needed)
        self._query_rewriter = query_rewriter
        
        # Metrics
        self.metrics = {
            "total_requests": 0,
            "cache_hits": 0,
            "cache_misses": 0,
            "governance_blocks": 0,
            "policy_filtered_results": 0,
            "query_rewrites": 0,
            "reranking_operations": 0,
            "avg_latency_ms": 0.0,
        }
        
        logger.info(
            f"PolicyAwareRAGService initialized "
            f"(governance: {enable_governance}, cache: {enable_cache}, "
            f"rewriting: {enable_query_rewriting}, reranking: {enable_reranking})"
        )
    
    # ========================================================================
    # Public API
    # ========================================================================
    
    @GovernanceScopeEnforcer.enforce()
    async def retrieve(
        self,
        query: str,
        mode: RAGMode = RAGMode.AUTO,
        top_k: int = 10,
        policy: Optional[RetrievalPolicy] = None,
        query_embedding: Optional[List[float]] = None,
        skip_cache: bool = False,
    ) -> HybridRAGResult:
        """
        Retrieve documents with governance and policy enforcement.
        
        Args:
            query: Search query
            mode: RAG retrieval mode
            top_k: Number of results to return
            policy: Optional policy override (uses default if None)
            query_embedding: Optional pre-computed embedding
            skip_cache: Force cache bypass
            
        Returns:
            HybridRAGResult with filtered, reranked results
            
        Raises:
            GovernanceError: If governance context not available
            PolicyViolationError: If policy constraints violated
        """
        start_time = time.time()
        self.metrics["total_requests"] += 1
        
        # Governance check
        if self.enable_governance:
            governance_ctx = GovernanceContextManager.require_context()
            logger.debug(
                f"Governance context verified: {governance_ctx.context_id}"
            )
        
        # Use provided policy or default
        active_policy = policy or self.default_policy
        
        # Step 1: Check cache
        if self.enable_cache and not skip_cache:
            cached_result = self._check_cache(query, mode, top_k, active_policy)
            if cached_result is not None:
                self.metrics["cache_hits"] += 1
                logger.debug(f"Cache hit for query: {query[:50]}...")
                return cached_result
            self.metrics["cache_misses"] += 1
        
        # Step 2: Query rewriting
        rewritten_query = query
        if self.enable_query_rewriting:
            rewritten_query = await self._rewrite_query(query)
            if rewritten_query != query:
                self.metrics["query_rewrites"] += 1
                logger.debug(f"Query rewritten: '{query}' → '{rewritten_query}'")
        
        # Step 3: Base retrieval
        base_result = await self.base_service.retrieve(
            query=rewritten_query,
            mode=mode,
            top_k=top_k * 2,  # Retrieve more for filtering
            query_embedding=query_embedding
        )
        
        # Step 4: Policy filtering
        filtered_results = self._apply_policy_filter(
            base_result.results,
            active_policy
        )
        
        if len(filtered_results) < len(base_result.results):
            filtered_count = len(base_result.results) - len(filtered_results)
            self.metrics["policy_filtered_results"] += filtered_count
            logger.debug(f"Policy filtered {filtered_count} results")
        
        # Step 5: Reranking
        if self.enable_reranking and len(filtered_results) > 0:
            filtered_results = await self._rerank_results(
                query=rewritten_query,
                results=filtered_results
            )
            self.metrics["reranking_operations"] += 1
        
        # Step 6: Limit to top_k
        final_results = filtered_results[:top_k]
        
        # Build final result
        total_time_ms = (time.time() - start_time) * 1000
        final_result = HybridRAGResult(
            query=query,  # Original query for consistency
            mode_used=base_result.mode_used,
            results=final_results,
            retrieval_time_ms=total_time_ms,
            metadata={
                **base_result.metadata,
                "policy_applied": True,
                "governance_enforced": self.enable_governance,
                "rewritten_query": rewritten_query if rewritten_query != query else None,
                "results_filtered": len(base_result.results) - len(filtered_results),
                "cache_enabled": self.enable_cache,
            }
        )
        
        # Step 7: Cache result
        if self.enable_cache:
            self._cache_result(query, mode, top_k, active_policy, final_result)
        
        # Update metrics
        self._update_metrics(total_time_ms)
        
        return final_result
    
    async def retrieve_with_evidence(
        self,
        query: str,
        mode: RAGMode = RAGMode.AUTO,
        top_k: int = 10,
        policy: Optional[RetrievalPolicy] = None,
    ) -> Tuple[HybridRAGResult, List[RAGEvidenceNode]]:
        """
        Retrieve documents and convert to evidence nodes for verdict engine.
        
        Args:
            query: Search query
            mode: RAG mode
            top_k: Number of results
            policy: Optional policy
            
        Returns:
            Tuple of (HybridRAGResult, List[RAGEvidenceNode])
        """
        # Get retrieval results
        result = await self.retrieve(
            query=query,
            mode=mode,
            top_k=top_k,
            policy=policy
        )
        
        # Convert to evidence nodes
        evidence_nodes = []
        for rank, retrieval_result in enumerate(result.results, start=1):
            evidence_node = RAGEvidenceNode(
                fact=retrieval_result.content,
                source=retrieval_result.metadata.get("source", "unknown"),
                confidence=retrieval_result.score,
                provenance={
                    "doc_id": retrieval_result.doc_id,
                    "rank": rank,
                    "retrieval_mode": result.mode_used,
                    "query": query,
                    **retrieval_result.metadata
                }
            )
            evidence_nodes.append(evidence_node)
        
        return result, evidence_nodes
    
    def enable_governance_enforcement(self):
        """Enable governance enforcement (for testing/rollout)"""
        self.enable_governance = True
        logger.info("Governance enforcement ENABLED")
    
    def disable_governance_enforcement(self):
        """Disable governance enforcement (for testing/rollout)"""
        self.enable_governance = False
        logger.warning("⚠️ Governance enforcement DISABLED")
    
    def clear_cache(self):
        """Clear all cached entries"""
        cache_size = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared ({cache_size} entries removed)")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get service metrics"""
        cache_hit_rate = 0.0
        if self.metrics["total_requests"] > 0:
            cache_hit_rate = (
                self.metrics["cache_hits"] / self.metrics["total_requests"]
            )
        
        return {
            **self.metrics,
            "cache_hit_rate": cache_hit_rate,
            "cache_size": len(self._cache),
            "governance_enabled": self.enable_governance,
            "cache_enabled": self.enable_cache,
            "query_rewriting_enabled": self.enable_query_rewriting,
            "reranking_enabled": self.enable_reranking,
        }
    
    # ========================================================================
    # Private Methods
    # ========================================================================
    
    def _check_cache(
        self,
        query: str,
        mode: RAGMode,
        top_k: int,
        policy: RetrievalPolicy
    ) -> Optional[HybridRAGResult]:
        """Check cache for existing result"""
        cache_key = self._generate_cache_key(query, mode, top_k, policy)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            
            # Check expiration
            if entry.is_expired:
                del self._cache[cache_key]
                logger.debug(f"Cache entry expired: {cache_key}")
                return None
            
            # Update access stats
            entry.hit_count += 1
            entry.last_access = datetime.now()
            
            # Move to end (LRU)
            self._cache.move_to_end(cache_key)
            
            return entry.result
        
        return None
    
    def _cache_result(
        self,
        query: str,
        mode: RAGMode,
        top_k: int,
        policy: RetrievalPolicy,
        result: HybridRAGResult
    ):
        """Cache retrieval result"""
        cache_key = self._generate_cache_key(query, mode, top_k, policy)
        
        # Evict oldest entry if cache full
        if len(self._cache) >= self.cache_max_size:
            # Try to evict cold entries first
            evicted = False
            for key, entry in list(self._cache.items()):
                if not entry.is_hot:
                    del self._cache[key]
                    evicted = True
                    logger.debug(f"Evicted cold cache entry: {key}")
                    break
            
            # If all entries are hot, evict oldest (LRU)
            if not evicted:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug(f"Evicted oldest cache entry (all hot): {oldest_key}")
        
        # Add to cache
        entry = CacheEntry(
            query_hash=cache_key,
            result=result,
            cached_at=datetime.now(),
            ttl_seconds=self.cache_ttl_seconds
        )
        self._cache[cache_key] = entry
        logger.debug(f"Cached result: {cache_key}")
    
    def _generate_cache_key(
        self,
        query: str,
        mode: RAGMode,
        top_k: int,
        policy: RetrievalPolicy
    ) -> str:
        """Generate unique cache key from parameters"""
        # Create deterministic string representation
        policy_str = (
            f"{policy.min_privacy_level.value}:"
            f"{policy.max_privacy_level.value}:"
            f"{policy.min_confidence_score}:"
            f"{policy.allowed_sources}"
        )
        
        key_components = f"{query}|{mode.value}|{top_k}|{policy_str}"
        
        # Hash to fixed length
        return hashlib.sha256(key_components.encode()).hexdigest()[:16]
    
    async def _rewrite_query(self, query: str) -> str:
        """
        Rewrite query for better retrieval results.
        
        Uses QueryRewriter if available, otherwise returns original.
        """
        if self._query_rewriter is None:
            # Lazy load query rewriter
            try:
                from mahoun.pipelines.query_rewriter import QueryRewriter
                self._query_rewriter = QueryRewriter()
                logger.debug("QueryRewriter loaded")
            except Exception as e:
                logger.warning(f"Could not load QueryRewriter: {e}")
                return query
        
        try:
            rewritten = await self._query_rewriter.rewrite(query)
            return rewritten
        except Exception as e:
            logger.warning(f"Query rewriting failed: {e}")
            return query
    
    def _apply_policy_filter(
        self,
        results: List[RetrievalResult],
        policy: RetrievalPolicy
    ) -> List[RetrievalResult]:
        """
        Filter results based on policy constraints.
        
        Filters by:
        - Privacy level
        - Source authority
        - Confidence score
        - Result age
        """
        filtered = []
        
        for result in results:
            # Extract metadata
            metadata = result.metadata
            
            # Privacy level check
            privacy_level_str = metadata.get("privacy_level", "public")
            try:
                privacy_level = PrivacyLevel(privacy_level_str.lower())
            except ValueError:
                privacy_level = PrivacyLevel.PUBLIC
            
            if not self._is_privacy_level_allowed(privacy_level, policy):
                continue
            
            # Source authority check
            if policy.allowed_sources is not None:
                source_authority_str = metadata.get("source_authority", "unknown")
                try:
                    source_authority = SourceAuthority(source_authority_str.lower())
                except ValueError:
                    source_authority = SourceAuthority.UNKNOWN
                
                if source_authority not in policy.allowed_sources:
                    continue
            
            # Confidence score check
            if result.score < policy.min_confidence_score:
                continue
            
            # Age check
            if policy.max_result_age_days is not None:
                created_at = metadata.get("created_at")
                if created_at is not None:
                    try:
                        if isinstance(created_at, str):
                            created_date = datetime.fromisoformat(created_at)
                        else:
                            created_date = created_at
                        
                        age_days = (datetime.now() - created_date).days
                        if age_days > policy.max_result_age_days:
                            continue
                    except Exception:
                        pass  # If date parsing fails, include result
            
            filtered.append(result)
        
        return filtered
    
    def _is_privacy_level_allowed(
        self,
        level: PrivacyLevel,
        policy: RetrievalPolicy
    ) -> bool:
        """Check if privacy level is within policy bounds"""
        level_order = {
            PrivacyLevel.PUBLIC: 0,
            PrivacyLevel.INTERNAL: 1,
            PrivacyLevel.CONFIDENTIAL: 2,
            PrivacyLevel.RESTRICTED: 3,
        }
        
        level_value = level_order[level]
        min_value = level_order[policy.min_privacy_level]
        max_value = level_order[policy.max_privacy_level]
        
        return min_value <= level_value <= max_value
    
    async def _rerank_results(
        self,
        query: str,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """
        Multi-stage reranking with confidence scoring.
        
        Strategies:
        1. Semantic similarity reranking (if model available)
        2. Diversity-aware reranking
        3. Recency boost
        """
        if len(results) <= 1:
            return results
        
        # Stage 1: Semantic reranking (placeholder - would use cross-encoder)
        # In production, this would use a reranking model
        reranked = results.copy()
        
        # Stage 2: Diversity penalty (avoid too similar results)
        reranked = self._apply_diversity_penalty(reranked)
        
        # Stage 3: Recency boost
        reranked = self._apply_recency_boost(reranked)
        
        # Re-sort by adjusted score
        reranked.sort(key=lambda x: x.score, reverse=True)
        
        # Update ranks
        for rank, result in enumerate(reranked, start=1):
            result.rank = rank
        
        return reranked
    
    def _apply_diversity_penalty(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Apply diversity penalty to avoid redundant results"""
        # Simplified: penalize results with very similar content
        seen_content_hashes = set()
        
        for result in results:
            # Hash first 100 chars for similarity check
            content_snippet = result.content[:100].strip()
            content_hash = hashlib.md5(content_snippet.encode()).hexdigest()[:8]
            
            if content_hash in seen_content_hashes:
                # Apply penalty
                result.score *= 0.9
            else:
                seen_content_hashes.add(content_hash)
        
        return results
    
    def _apply_recency_boost(
        self,
        results: List[RetrievalResult]
    ) -> List[RetrievalResult]:
        """Boost more recent results"""
        for result in results:
            created_at = result.metadata.get("created_at")
            if created_at is not None:
                try:
                    if isinstance(created_at, str):
                        created_date = datetime.fromisoformat(created_at)
                    else:
                        created_date = created_at
                    
                    age_days = (datetime.now() - created_date).days
                    
                    # Boost recent results (decay over 365 days)
                    if age_days < 365:
                        boost_factor = 1.0 + (0.2 * (1.0 - age_days / 365.0))
                        result.score *= boost_factor
                except Exception:
                    pass  # Skip boost if date parsing fails
        
        return results
    
    def _update_metrics(self, latency_ms: float):
        """Update average latency metric"""
        n = self.metrics["total_requests"]
        self.metrics["avg_latency_ms"] = (
            (self.metrics["avg_latency_ms"] * (n - 1) + latency_ms) / n
        )


# ============================================================================
# Factory Functions
# ============================================================================

async def create_policy_aware_rag_service(
    base_service: Optional[HybridRAGService] = None,
    default_policy: Optional[RetrievalPolicy] = None,
    enable_governance: bool = True,
    enable_cache: bool = True,
    **kwargs
) -> PolicyAwareRAGService:
    """
    Create PolicyAwareRAGService with defaults.
    
    Args:
        base_service: Optional HybridRAGService (creates if None)
        default_policy: Default retrieval policy
        enable_governance: Enable governance enforcement
        enable_cache: Enable caching
        **kwargs: Additional arguments for PolicyAwareRAGService
        
    Returns:
        Initialized PolicyAwareRAGService
    """
    # Create base service if not provided
    if base_service is None:
        from mahoun.rag.hybrid_rag_service import create_hybrid_rag_service
        base_service = await create_hybrid_rag_service()
        logger.info("Created default HybridRAGService")
    
    # Create policy-aware service
    service = PolicyAwareRAGService(
        base_service=base_service,
        default_policy=default_policy,
        enable_governance=enable_governance,
        enable_cache=enable_cache,
        **kwargs
    )
    
    logger.info("PolicyAwareRAGService created successfully")
    return service
