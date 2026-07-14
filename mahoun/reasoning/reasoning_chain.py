"""
Reasoning Chain - Multi-Stage Legal Reasoning Pipeline
========================================================

Integrates NLI verification, citation auditing, and uncertainty estimation
into a unified reasoning pipeline.

Pipeline Stages:
1. Answer Generation (from retrieved context)
2. NLI Verification (answer ⊢ context)
3. Citation Auditing (citations valid and accurate)
4. Uncertainty Estimation (epistemic + aleatoric)
5. Transparency Trace (how answer was reached)

Modes:
- strict: Full verification (production/legal compliance)
- fast: Lightweight verification (desktop development)
"""

import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ReasoningMode(str, Enum):
    """Reasoning execution modes"""
    STRICT = "strict"  # Production: mandatory verification
    FAST = "fast"      # Desktop: lightweight verification
    DISABLED = "disabled"  # Skip reasoning (not recommended)


@dataclass
class ReasoningConfig:
    """Configuration for reasoning chain"""
    enabled: bool = True
    mode: ReasoningMode = ReasoningMode.FAST
    nli_enabled: bool = True
    citation_audit_enabled: bool = True
    uncertainty_enabled: bool = True
    nli_threshold: float = 0.5  # Minimum entailment score
    citation_min_accuracy: float = 0.8  # Minimum citation accuracy
    

@dataclass
class ReasoningResult:
    """Output of complete reasoning chain"""
    # Input
    query: str
    answer: str
    
    # Verification Results
    nli_verified: bool
    nli_entailment_score: float
    nli_contradiction_score: float
    
    citations_valid: bool
    citation_accuracy_score: float
    citation_details: Dict[str, Any]
    
    uncertainty_score: float
    epistemic_uncertainty: float
    aleatoric_uncertainty: float
    confidence: float
    
    # Transparency
    transparency_trace: Dict[str, Any]
    reasoning_chain: List[str]
    hop_trace: List[Dict[str, Any]]
    citation_trace: List[Dict[str, Any]]
    
    # Metadata
    processing_time_ms: float
    mode_used: str
    warnings: List[str] = field(default_factory=list)


class ReasoningChain:
    """
    Multi-stage reasoning pipeline for MAHOUN.
    
    This is architecturally mandatory for legal compliance.
    Execution mode is configurable (strict vs fast).
    
    Usage:
        # Create with default components
        chain = ReasoningChain(config=ReasoningConfig(mode="strict"))
        await chain.initialize()
        
        # Process answer through reasoning pipeline
        result = await chain.process(
            query="سابقه دخالت ثالث چیست؟",
            retrieved_docs=[{...}, {...}],
            generated_answer="بر اساس رأی دادگاه..."
        )
        
        # Check verification
        if result.nli_verified and result.citations_valid:
            print(f"Answer verified (confidence: {result.confidence:.2f})")
    """
    
    def __init__(
        self,
        config: Optional[ReasoningConfig] = None,
        nli_verifier=None,
        citation_auditor=None,
        uncertainty_service=None
    ):
        """
        Initialize Reasoning Chain.
        
        Args:
            config: Reasoning configuration
            nli_verifier: Optional NLIVerifier instance
            citation_auditor: Optional CitationAuditor instance
            uncertainty_service: Optional UncertaintyService instance
        """
        self.config = config or ReasoningConfig()
        self._nli_verifier = nli_verifier
        self._citation_auditor = citation_auditor
        self._uncertainty_service = uncertainty_service
        
        self._initialized = False
        
        # Track module availability (PUBLIC for reporting)
        self.nli_available = False
        self.citation_available = False
        self.uncertainty_available = False
        
        # Statistics
        self.stats = {
            "total_processed": 0,
            "nli_verified_count": 0,
            "citations_valid_count": 0,
            "avg_processing_time_ms": 0.0
        }
        
        logger.info(
            f"ReasoningChain initialized "
            f"(mode: {self.config.mode.value}, enabled: {self.config.enabled})"
        )
    
    async def initialize(self):
        """Initialize reasoning components"""
        if self._initialized:
            return
        
        if not self.config.enabled:
            logger.warning("Reasoning chain disabled - NOT RECOMMENDED for production")
            self._initialized = True
            return
        
        # Initialize NLI Verifier
        if self.config.nli_enabled and self._nli_verifier is None:
            try:
                # from mahoun.guardrails.ultra_nli_verifier import UltraNLIVerifier as NLIVerifier
                self._nli_verifier = NLIVerifier(threshold=self.config.nli_threshold)
                self.nli_available = True
                logger.info("✅ NLI Verifier initialized")
            except Exception as e:
                logger.warning(f"NLI Verifier unavailable: {e}")
                self.nli_available = False
                if self.config.mode == ReasoningMode.STRICT:
                    raise
        elif self._nli_verifier is not None:
            self.nli_available = True
        
        # Initialize Citation Auditor
        if self.config.citation_audit_enabled and self._citation_auditor is None:
            try:
                # from mahoun.guardrails.ultra_citation_auditor import UltraCitationAuditor as CitationAuditor
                self._citation_auditor = CitationAuditor(
                    min_accuracy=self.config.citation_min_accuracy
                )
                self.citation_available = True
                logger.info("✅ Citation Auditor initialized")
            except Exception as e:
                logger.warning(f"Citation Auditor unavailable: {e}")
                self.citation_available = False
                if self.config.mode == ReasoningMode.STRICT:
                    raise
        elif self._citation_auditor is not None:
            self.citation_available = True
        
        # Initialize Uncertainty Service
        if self.config.uncertainty_enabled and self._uncertainty_service is None:
            try:
                # from mahoun.uncertainty.service import UncertaintyService, UncertaintyConfig
                # from mahoun.uncertainty.service import UncertaintyMethod
                uncertainty_config = UncertaintyConfig(
                    default_method=UncertaintyMethod.ENSEMBLE
                )
                self._uncertainty_service = UncertaintyService(uncertainty_config)
                self.uncertainty_available = True
                logger.info("✅ Uncertainty Service initialized")
            except Exception as e:
                logger.warning(f"Uncertainty Service unavailable: {e}")
                self.uncertainty_available = False
                if self.config.mode == ReasoningMode.STRICT:
                    raise
        elif self._uncertainty_service is not None:
            self.uncertainty_available = True
        
        self._initialized = True
        logger.info("Reasoning chain fully initialized")
    
    async def process(
        self,
        query: str,
        retrieved_docs: List[Dict[str, Any]],
        generated_answer: str,
        retrieval_metadata: Optional[Dict[str, Any]] = None
    ) -> ReasoningResult:
        """
        Process answer through full reasoning chain.
        
        Args:
            query: Original query
            retrieved_docs: Retrieved source documents
            generated_answer: Generated answer to verify
            retrieval_metadata: Optional retrieval metadata
            
        Returns:
            ReasoningResult with verification and transparency info
        """
        start_time = time.time()
        
        if not self._initialized:
            await self.initialize()
        
        if not self.config.enabled:
            return self._create_disabled_result(query, generated_answer, start_time)
        
        warnings: List[Any] = []
        reasoning_chain: List[Any] = []
        # Prepare context from retrieved documents
        context = self._build_context(retrieved_docs)
        sources = [doc.get('content', doc.get('text', '')) for doc in retrieved_docs]
        
        # Stage 1: NLI Verification
        nli_result = await self._verify_nli(generated_answer, context, reasoning_chain)
        if not nli_result['verified']:
            warnings.append(f"NLI verification failed (score: {nli_result['entailment_score']:.3f})")
        
        # Stage 2: Citation Auditing
        citation_result = await self._audit_citations(generated_answer, sources, reasoning_chain)
        if not citation_result['valid']:
            warnings.append(f"Citation audit failed (accuracy: {citation_result['accuracy']:.3f})")
        
        # Stage 3: Uncertainty Estimation
        uncertainty_result = await self._estimate_uncertainty(
            generated_answer,
            retrieved_docs,
            nli_result,
            citation_result,
            reasoning_chain
        )
        
        # Stage 4: Build Transparency Trace
        transparency_trace = self._build_transparency_trace(
            query,
            generated_answer,
            retrieved_docs,
            nli_result,
            citation_result,
            uncertainty_result,
            retrieval_metadata
        )
        
        # Build hop trace and citation trace
        hop_trace = self._build_hop_trace(retrieved_docs, retrieval_metadata)
        citation_trace = citation_result.get('citation_details', [])
        
        processing_time_ms = (time.time() - start_time) * 1000
        
        # Update statistics
        self._update_stats(nli_result['verified'], citation_result['valid'], processing_time_ms)
        
        return ReasoningResult(
            query=query,
            answer=generated_answer,
            nli_verified=nli_result['verified'],
            nli_entailment_score=nli_result['entailment_score'],
            nli_contradiction_score=nli_result['contradiction_score'],
            citations_valid=citation_result['valid'],
            citation_accuracy_score=citation_result['accuracy'],
            citation_details=citation_result,
            uncertainty_score=uncertainty_result['total'],
            epistemic_uncertainty=uncertainty_result['epistemic'],
            aleatoric_uncertainty=uncertainty_result['aleatoric'],
            confidence=1.0 - uncertainty_result['total'],
            transparency_trace=transparency_trace,
            reasoning_chain=reasoning_chain,
            hop_trace=hop_trace,
            citation_trace=citation_trace,
            processing_time_ms=processing_time_ms,
            mode_used=self.config.mode.value,
            warnings=warnings
        )
    
    def _build_context(self, retrieved_docs: List[Dict[str, Any]]) -> str:
        """Build concatenated context from retrieved documents"""
        context_parts: List[Any] = []
        for doc in retrieved_docs:
            text = doc.get('content', doc.get('text', ''))
            if text:
                context_parts.append(text)
        return '\n\n'.join(context_parts)
    
    async def _verify_nli(
        self,
        answer: str,
        context: str,
        reasoning_chain: List[str]
    ) -> Dict[str, Any]:
        """Run NLI verification"""
        if not self.nli_available:
            reasoning_chain.append("NLI verification: UNAVAILABLE (torch/dependencies not installed)")
            return {
                'verified': False,
                'entailment_score': 0.0,
                'contradiction_score': 0.0,
                'neutral_score': 0.0,
                'available': False
            }
        
        if not self.config.nli_enabled:
            reasoning_chain.append("NLI verification: SKIPPED (disabled in config)")
            return {
                'verified': False,
                'entailment_score': 0.0,
                'contradiction_score': 0.0,
                'neutral_score': 0.0,
                'skipped': True
            }
        
        try:
            nli_result = self._nli_verifier.verify(context=context, answer=answer)
            
            reasoning_chain.append(
                f"NLI verification: {'PASS' if nli_result.is_supported else 'FAIL'} "
                f"(entailment: {nli_result.entailment_score:.3f}, "
                f"contradiction: {nli_result.contradiction_score:.3f})"
            )
            
            return {
                'verified': nli_result.is_supported,
                'entailment_score': nli_result.entailment_score,
                'contradiction_score': nli_result.contradiction_score,
                'neutral_score': nli_result.neutral_score
            }
        except Exception as e:
            logger.error(f"NLI verification failed: {e}")
            reasoning_chain.append(f"NLI verification: ERROR - {str(e)[:50]}")
            
            # In strict mode, failures are critical
            if self.config.mode == ReasoningMode.STRICT:
                raise
            
            # In fast mode, continue with warning
            return {
                'verified': False,
                'entailment_score': 0.5,
                'contradiction_score': 0.0,
                'neutral_score': 0.5,
                'error': str(e)
            }
    
    async def _audit_citations(
        self,
        answer: str,
        sources: List[str],
        reasoning_chain: List[str]
    ) -> Dict[str, Any]:
        """Run citation auditing"""
        if not self.citation_available:
            reasoning_chain.append("Citation audit: UNAVAILABLE (torch/dependencies not installed)")
            return {
                'valid': False,
                'accuracy': 0.0,
                'citation_details': [],
                'available': False
            }
        
        if not self.config.citation_audit_enabled:
            reasoning_chain.append("Citation audit: SKIPPED (disabled in config)")
            return {
                'valid': False,
                'accuracy': 0.0,
                'citation_details': [],
                'skipped': True
            }
        
        try:
            audit_result = self._citation_auditor.audit(
                answer=answer,
                sources=sources
            )
            
            reasoning_chain.append(
                f"Citation audit: {'PASS' if audit_result.is_valid else 'FAIL'} "
                f"({audit_result.valid_citations}/{audit_result.total_citations} valid, "
                f"accuracy: {audit_result.accuracy_score:.3f})"
            )
            
            return {
                'valid': audit_result.is_valid,
                'accuracy': audit_result.accuracy_score,
                'total_citations': audit_result.total_citations,
                'valid_citations': audit_result.valid_citations,
                'invalid_citations': audit_result.invalid_citations,
                'citation_details': [
                    {'citation': c, 'valid': True} 
                    for c in audit_result.invalid_citations  # Track invalid ones
                ]
            }
        except Exception as e:
            logger.error(f"Citation audit failed: {e}")
            reasoning_chain.append(f"Citation audit: ERROR - {str(e)[:50]}")
            
            if self.config.mode == ReasoningMode.STRICT:
                raise
            
            return {
                'valid': False,
                'accuracy': 0.5,
                'citation_details': [],
                'error': str(e)
            }
    
    async def _estimate_uncertainty(
        self,
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        nli_result: Dict[str, Any],
        citation_result: Dict[str, Any],
        reasoning_chain: List[str]
    ) -> Dict[str, float]:
        """Estimate uncertainty"""
        if not self.uncertainty_available:
            reasoning_chain.append("Uncertainty estimation: UNAVAILABLE (torch/dependencies not installed)")
            return {
                'epistemic': 1.0,  # Maximum uncertainty when unavailable
                'aleatoric': 0.0,
                'total': 1.0,
                'available': False
            }
        
        if not self.config.uncertainty_enabled:
            reasoning_chain.append("Uncertainty estimation: SKIPPED (disabled in config)")
            return {
                'epistemic': 1.0,
                'aleatoric': 0.0,
                'total': 1.0,
                'skipped': True
            }
        
        try:
            # Use retrieval scores + verification scores as basis
            scores: List[Any] = []
            # Add retrieval scores
            for doc in retrieved_docs:
                score = doc.get('score', 0.5)
                scores.append(float(score))
            
            # Add verification scores
            scores.append(nli_result.get('entailment_score', 0.5))
            scores.append(citation_result.get('accuracy', 0.5))
            
            # Estimate uncertainty
            uncertainty_estimate = self._uncertainty_service.estimate(
                scores=scores,
                method="ensemble"
            )
            
            reasoning_chain.append(
                f"Uncertainty: {uncertainty_estimate.total_uncertainty:.3f} "
                f"(epistemic: {uncertainty_estimate.epistemic_uncertainty:.3f}, "
                f"aleatoric: {uncertainty_estimate.aleatoric_uncertainty:.3f})"
            )
            
            return {
                'epistemic': uncertainty_estimate.epistemic_uncertainty,
                'aleatoric': uncertainty_estimate.aleatoric_uncertainty,
                'total': uncertainty_estimate.total_uncertainty
            }
        except Exception as e:
            logger.error(f"Uncertainty estimation failed: {e}")
            reasoning_chain.append(f"Uncertainty estimation: ERROR - {str(e)[:50]}")
            
            if self.config.mode == ReasoningMode.STRICT:
                raise
            
            return {
                'epistemic': 0.5,
                'aleatoric': 0.3,
                'total': 0.8,
                'error': str(e)
            }
    
    def _build_transparency_trace(
        self,
        query: str,
        answer: str,
        retrieved_docs: List[Dict[str, Any]],
        nli_result: Dict[str, Any],
        citation_result: Dict[str, Any],
        uncertainty_result: Dict[str, float],
        retrieval_metadata: Optional[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Build comprehensive transparency trace"""
        return {
            "query": query,
            "answer_length": len(answer),
            "retrieval": {
                "method": retrieval_metadata.get('mode_used', 'unknown') if retrieval_metadata else 'unknown',
                "num_sources": len(retrieved_docs),
                "top_scores": [doc.get('score', 0.0) for doc in retrieved_docs[:5]]
            },
            "verification": {
                "nli_verified": nli_result.get('verified', False),
                "nli_entailment_score": nli_result.get('entailment_score', 0.0),
                "citations_valid": citation_result.get('valid', False),
                "citation_accuracy": citation_result.get('accuracy', 0.0)
            },
            "uncertainty": {
                "epistemic": uncertainty_result['epistemic'],
                "aleatoric": uncertainty_result['aleatoric'],
                "total": uncertainty_result['total'],
                "confidence": 1.0 - uncertainty_result['total']
            },
            "reasoning_mode": self.config.mode.value
        }
    
    def _build_hop_trace(
        self,
        retrieved_docs: List[Dict[str, Any]],
        retrieval_metadata: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Build hop trace showing retrieval path"""
        hop_trace: List[Any] = []
        for idx, doc in enumerate(retrieved_docs):
            hop_trace.append({
                "hop": idx + 1,
                "doc_id": doc.get('doc_id', doc.get('id', f'doc_{idx}')),
                "score": doc.get('score', 0.0),
                "source": doc.get('source', 'unknown'),
                "metadata": {
                    k: v for k, v in doc.get('metadata', {}).items()
                    if k in ['section', 'case_type', 'court_level']  # Relevant fields only
                }
            })
        
        return hop_trace
    
    def _create_disabled_result(
        self,
        query: str,
        answer: str,
        start_time: float
    ) -> ReasoningResult:
        """Create result when reasoning is disabled or unavailable"""
        return ReasoningResult(
            query=query,
            answer=answer,
            nli_verified=False,  # HONEST: not verified
            nli_entailment_score=0.0,  # HONEST: not 1.0
            nli_contradiction_score=0.0,
            citations_valid=False,  # HONEST: not verified
            citation_accuracy_score=0.0,  # HONEST: not 1.0
            citation_details={},
            uncertainty_score=1.0,  # Maximum uncertainty when disabled
            epistemic_uncertainty=1.0,
            aleatoric_uncertainty=0.0,
            confidence=0.0,  # HONEST: no confidence, not 1.0
            transparency_trace={'reasoning_disabled': True},
            reasoning_chain=["Reasoning: DISABLED or UNAVAILABLE"],
            hop_trace=[],
            citation_trace=[],
            processing_time_ms=(time.time() - start_time) * 1000,
            mode_used="disabled",
            warnings=["Reasoning modules disabled or unavailable"]
        )
    
    def _update_stats(self, nli_verified: bool, citations_valid: bool, time_ms: float):
        """Update statistics"""
        self.stats["total_processed"] += 1
        if nli_verified:
            self.stats["nli_verified_count"] += 1
        if citations_valid:
            self.stats["citations_valid_count"] += 1
        
        n = self.stats["total_processed"]
        self.stats["avg_processing_time_ms"] = (
            (self.stats["avg_processing_time_ms"] * (n - 1) + time_ms) / n
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get reasoning statistics"""
        stats = self.stats.copy()
        if stats["total_processed"] > 0:
            stats["nli_pass_rate"] = stats["nli_verified_count"] / stats["total_processed"]
            stats["citation_pass_rate"] = stats["citations_valid_count"] / stats["total_processed"]
        return stats
