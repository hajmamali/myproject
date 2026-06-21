#!/usr/bin/env python3
"""
Graph-Enhanced Reasoning - Memory-Centric Intelligence

This module implements memory-centric reasoning that prioritizes
knowledge graph and retrieval quality over raw AI model size.

Design Philosophy:
- Graph + Retrieval Quality > Model Parameter Count
- Evidence-driven reasoning chains
- AI model used only for final reasoning step
- Full proof tree generation for auditability

Version: 1.0.0
Dependencies: AIRuntimeProtocol (G-0 frozen), Knowledge Graph, Retrieval Service
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging
import time
import uuid

from mahoun.core.protocols.ai_runtime import AIRuntimeProtocol
from mahoun.core.models import (
    AIResponse,
    PromptTemplate,
    EvidenceSlot,
    EvidenceSlotType,
    create_audit_event,
    AuditEventType,
    AuditContext
)

logger = logging.getLogger(__name__)


@dataclass
class Evidence:
    """
    Evidence retrieved from knowledge graph or retrieval system
    """
    source: str  # Source identifier
    content: str  # Evidence content
    confidence: float  # Confidence score (0.0-1.0)
    provenance_hash: str  # SHA-256 hash for integrity
    metadata: Dict[str, Any]  # Additional metadata
    
    def __post_init__(self):
        """Validate evidence"""
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("confidence must be between 0.0 and 1.0")
        if len(self.provenance_hash) != 64:
            raise ValueError("provenance_hash must be SHA-256 hash")


@dataclass
class ReasoningContext:
    """
    Context for reasoning operation
    """
    query: str  # Original query
    evidence_items: List[Evidence]  # Retrieved evidence
    graph_context: Dict[str, Any]  # Graph-derived context
    retrieval_context: Dict[str, Any]  # Retrieval-derived context
    correlation_id: str  # Request correlation ID
    
    def get_total_evidence_confidence(self) -> float:
        """Calculate average evidence confidence"""
        if not self.evidence_items:
            return 0.0
        return sum(e.confidence for e in self.evidence_items) / len(self.evidence_items)
    
    def get_evidence_sources(self) -> List[str]:
        """Get list of evidence source identifiers"""
        return [e.source for e in self.evidence_items]


@dataclass
class ProofTreeNode:
    """
    Node in proof tree for auditability
    """
    node_id: str
    node_type: str  # "evidence", "inference", "conclusion"
    content: str
    confidence: float
    children: List['ProofTreeNode']
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert proof tree node to dictionary"""
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "content": self.content,
            "confidence": self.confidence,
            "children": [child.to_dict() for child in self.children],
            "metadata": self.metadata
        }


@dataclass
class ReasoningResponse:
    """
    Complete reasoning response with evidence and proof tree
    """
    query: str
    answer: str
    confidence: float
    evidence: List[Evidence]
    proof_tree: ProofTreeNode
    ai_response: AIResponse
    reasoning_time_ms: float
    metadata: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format"""
        return {
            "query": self.query,
            "answer": self.answer,
            "confidence": self.confidence,
            "evidence_count": len(self.evidence),
            "evidence_sources": [e.source for e in self.evidence],
            "proof_tree": self.proof_tree.to_dict(),
            "ai_response": self.ai_response.to_audit_dict(),
            "reasoning_time_ms": self.reasoning_time_ms,
            "metadata": self.metadata
        }


class GraphService:
    """
    Abstract interface for knowledge graph operations
    
    This is a placeholder interface - implementations should
    integrate with existing MAHOUN graph infrastructure.
    """
    
    def find_evidence(
        self,
        query: str,
        max_depth: int = 3,
        min_confidence: float = 0.7
    ) -> List[Evidence]:
        """
        Find evidence from knowledge graph
        
        Args:
            query: Query text
            max_depth: Maximum graph traversal depth
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of evidence items from graph
        """
        raise NotImplementedError("GraphService must be implemented")
    
    def get_context(
        self,
        evidence: List[Evidence]
    ) -> Dict[str, Any]:
        """
        Get graph context for evidence items
        
        Args:
            evidence: List of evidence items
            
        Returns:
            Dictionary with graph-derived context
        """
        raise NotImplementedError("GraphService must be implemented")


class RetrievalService:
    """
    Abstract interface for retrieval operations
    
    This is a placeholder interface - implementations should
    integrate with existing MAHOUN retrieval infrastructure.
    """
    
    def get_relevant_context(
        self,
        query: str,
        evidence: List[Evidence],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Get relevant context from retrieval system
        
        Args:
            query: Query text
            evidence: Existing evidence items
            top_k: Number of top results to retrieve
            
        Returns:
            Dictionary with retrieval context
        """
        raise NotImplementedError("RetrievalService must be implemented")


class GraphEnhancedReasoning:
    """
    Graph-Enhanced Reasoning Engine - Memory-Centric Intelligence
    
    This engine implements the core MAHOUN reasoning strategy:
    
    Priority Order:
    1. Knowledge Graph Evidence (highest priority)
    2. Retrieval System Context
    3. AI Model Reasoning (lowest priority - final step only)
    
    Design Principles:
    - Graph and retrieval quality determine reasoning quality
    - AI model used only for final synthesis
    - All reasoning steps are traceable via proof tree
    - Evidence-first approach ensures auditability
    
    Contract Guarantees:
    - Uses AIRuntimeProtocol (G-0 frozen interface)
    - Generates complete proof trees for audit
    - All evidence is traceable to sources
    - Resource usage respects deployment profile
    """
    
    # Standard prompt template for evidence-based reasoning
    EVIDENCE_REASONING_TEMPLATE = PromptTemplate(
        template_id="evidence_reasoning_v1",
        template_text="""Analyze the following query using the provided evidence:

Query: {query}

Evidence from Knowledge Graph:
{graph_evidence}

Additional Context from Retrieval:
{retrieval_context}

Instructions:
1. Base your answer strictly on the provided evidence
2. Reference specific evidence items in your reasoning
3. If evidence is insufficient, state that explicitly
4. Provide a confidence assessment based on evidence quality

Reasoning and Answer:""",
        template_version="1.0.0",
        evidence_slots=[
            EvidenceSlot(
                slot_name="query",
                slot_type=EvidenceSlotType.CUSTOM,
                required=True,
                max_length=1000
            ),
            EvidenceSlot(
                slot_name="graph_evidence",
                slot_type=EvidenceSlotType.GRAPH_CONTEXT,
                required=True,
                max_length=5000
            ),
            EvidenceSlot(
                slot_name="retrieval_context",
                slot_type=EvidenceSlotType.RETRIEVAL_CONTEXT,
                required=True,
                max_length=3000
            )
        ]
    )
    
    def __init__(
        self,
        graph_service: GraphService,
        retrieval_service: RetrievalService,
        ai_runtime: AIRuntimeProtocol
    ):
        """
        Initialize graph-enhanced reasoning engine
        
        Args:
            graph_service: Knowledge graph service
            retrieval_service: Retrieval service
            ai_runtime: AI runtime implementation
        """
        self.graph = graph_service
        self.retrieval = retrieval_service
        self.ai_runtime = ai_runtime
        
        logger.info("Initialized GraphEnhancedReasoning engine")
    
    def process_query(
        self,
        query: str,
        *,
        max_graph_depth: int = 3,
        min_evidence_confidence: float = 0.7,
        top_k_retrieval: int = 5,
        correlation_id: Optional[str] = None
    ) -> ReasoningResponse:
        """
        Process query with graph-enhanced reasoning
        
        This is the main entry point for reasoning operations.
        
        Priority flow:
        1. Graph Evidence Retrieval (primary)
        2. Retrieval Context Enhancement (secondary)
        3. AI Model Reasoning (final step only)
        4. Proof Tree Construction (auditability)
        
        Args:
            query: Query text
            max_graph_depth: Maximum graph traversal depth
            min_evidence_confidence: Minimum evidence confidence
            top_k_retrieval: Top K retrieval results
            correlation_id: Request correlation ID
            
        Returns:
            Complete reasoning response with proof tree
        """
        reasoning_start = time.time()
        correlation_id = correlation_id or str(uuid.uuid4())
        
        logger.info(f"Processing query: {query[:100]}... (corr_id={correlation_id})")
        
        try:
            # STEP 1: Retrieve evidence from knowledge graph (PRIMARY)
            logger.debug("Step 1: Retrieving evidence from knowledge graph...")
            evidence = self.graph.find_evidence(
                query=query,
                max_depth=max_graph_depth,
                min_confidence=min_evidence_confidence
            )
            
            logger.info(f"Retrieved {len(evidence)} evidence items from graph")
            
            # STEP 2: Get graph-derived context
            logger.debug("Step 2: Building graph context...")
            graph_context = self.graph.get_context(evidence)
            
            # STEP 3: Get retrieval context (SECONDARY)
            logger.debug("Step 3: Retrieving additional context...")
            retrieval_context = self.retrieval.get_relevant_context(
                query=query,
                evidence=evidence,
                top_k=top_k_retrieval
            )
            
            # Build reasoning context
            reasoning_context = ReasoningContext(
                query=query,
                evidence_items=evidence,
                graph_context=graph_context,
                retrieval_context=retrieval_context,
                correlation_id=correlation_id
            )
            
            # STEP 4: Build evidence-based prompt
            logger.debug("Step 4: Building evidence-based prompt...")
            prompt = self._build_evidence_prompt(reasoning_context)
            
            # STEP 5: AI reasoning (FINAL STEP - lowest priority)
            logger.debug("Step 5: Performing AI reasoning...")
            ai_response = self.ai_runtime.generate(
                prompt=prompt,
                max_tokens=512,
                temperature=0.3,  # Lower temperature for more deterministic reasoning
                context={
                    "evidence_count": len(evidence),
                    "graph_context": graph_context,
                    "retrieval_context": retrieval_context
                },
                correlation_id=correlation_id
            )
            
            # STEP 6: Build proof tree for auditability
            logger.debug("Step 6: Building proof tree...")
            proof_tree = self._build_proof_tree(
                reasoning_context=reasoning_context,
                ai_response=ai_response
            )
            
            reasoning_time_ms = (time.time() - reasoning_start) * 1000
            
            # Calculate overall confidence based on evidence and AI
            overall_confidence = self._calculate_confidence(
                evidence_confidence=reasoning_context.get_total_evidence_confidence(),
                ai_confidence=ai_response.confidence_score
            )
            
            # Create reasoning response
            response = ReasoningResponse(
                query=query,
                answer=ai_response.response_text,
                confidence=overall_confidence,
                evidence=evidence,
                proof_tree=proof_tree,
                ai_response=ai_response,
                reasoning_time_ms=reasoning_time_ms,
                metadata={
                    "graph_evidence_count": len(evidence),
                    "avg_evidence_confidence": reasoning_context.get_total_evidence_confidence(),
                    "ai_inference_time_ms": ai_response.generation_metadata.inference_time_ms,
                    "graph_retrieval_time_ms": reasoning_time_ms - ai_response.generation_metadata.inference_time_ms
                }
            )
            
            logger.info(
                f"Reasoning complete: {reasoning_time_ms:.0f}ms total, "
                f"{ai_response.generation_metadata.inference_time_ms:.0f}ms AI, "
                f"confidence={overall_confidence:.2f}"
            )
            
            # Audit event
            self._create_reasoning_audit_event(response)
            
            return response
            
        except Exception as e:
            logger.error(f"Reasoning failed: {e}")
            raise
    
    def _build_evidence_prompt(
        self,
        context: ReasoningContext
    ) -> str:
        """
        Build evidence-based prompt from context
        
        Args:
            context: Reasoning context with evidence
            
        Returns:
            Complete prompt with evidence integrated
        """
        # Format graph evidence
        graph_evidence_text = "\n\n".join([
            f"Evidence {i+1} (confidence: {e.confidence:.2f}):\n"
            f"Source: {e.source}\n"
            f"Content: {e.content}"
            for i, e in enumerate(context.evidence_items)
        ])
        
        # Format retrieval context
        retrieval_text = "\n".join([
            f"{key}: {value}"
            for key, value in context.retrieval_context.items()
        ])
        
        # Generate prompt from template
        prompt = self.EVIDENCE_REASONING_TEMPLATE.generate_prompt(
            evidence={
                "query": context.query,
                "graph_evidence": graph_evidence_text or "No evidence found",
                "retrieval_context": retrieval_text or "No additional context"
            }
        )
        
        return prompt
    
    def _build_proof_tree(
        self,
        reasoning_context: ReasoningContext,
        ai_response: AIResponse
    ) -> ProofTreeNode:
        """
        Build proof tree for auditability
        
        Args:
            reasoning_context: Reasoning context
            ai_response: AI response
            
        Returns:
            Root node of proof tree
        """
        # Create evidence nodes
        evidence_nodes = [
            ProofTreeNode(
                node_id=str(uuid.uuid4()),
                node_type="evidence",
                content=evidence.content,
                confidence=evidence.confidence,
                children=[],
                metadata={
                    "source": evidence.source,
                    "provenance_hash": evidence.provenance_hash
                }
            )
            for evidence in reasoning_context.evidence_items
        ]
        
        # Create inference node
        inference_node = ProofTreeNode(
            node_id=str(uuid.uuid4()),
            node_type="inference",
            content=ai_response.response_text,
            confidence=ai_response.confidence_score,
            children=[],
            metadata={
                "model_id": ai_response.generation_metadata.model_id,
                "inference_time_ms": ai_response.generation_metadata.inference_time_ms
            }
        )
        
        # Create root conclusion node
        root = ProofTreeNode(
            node_id=str(uuid.uuid4()),
            node_type="conclusion",
            content=f"Query: {reasoning_context.query}\nAnswer: {ai_response.response_text}",
            confidence=self._calculate_confidence(
                reasoning_context.get_total_evidence_confidence(),
                ai_response.confidence_score
            ),
            children=[*evidence_nodes, inference_node],
            metadata={
                "query": reasoning_context.query,
                "evidence_count": len(reasoning_context.evidence_items),
                "correlation_id": reasoning_context.correlation_id
            }
        )
        
        return root
    
    def _calculate_confidence(
        self,
        evidence_confidence: float,
        ai_confidence: float
    ) -> float:
        """
        Calculate overall confidence from evidence and AI
        
        Priority: Evidence confidence has higher weight than AI confidence
        
        Args:
            evidence_confidence: Average evidence confidence
            ai_confidence: AI model confidence
            
        Returns:
            Combined confidence score
        """
        # Weight evidence confidence more heavily (70/30 split)
        return (evidence_confidence * 0.7) + (ai_confidence * 0.3)
    
    def _create_reasoning_audit_event(
        self,
        response: ReasoningResponse
    ) -> None:
        """
        Create audit event for reasoning operation
        
        Args:
            response: Reasoning response
        """
        audit_context = AuditContext(
            correlation_id=response.ai_response.correlation_id,
            model_id=response.ai_response.generation_metadata.model_id,
            source_component="GraphEnhancedReasoning"
        )
        
        event = create_audit_event(
            event_type=AuditEventType.GENERATION_COMPLETED,
            payload={
                "query": response.query[:200],  # Truncate for audit
                "answer_length": len(response.answer),
                "confidence": response.confidence,
                "evidence_count": len(response.evidence),
                "reasoning_time_ms": response.reasoning_time_ms
            },
            context=audit_context,
            duration_ms=response.reasoning_time_ms
        )
        
        logger.debug(f"Created audit event: {event.event_id}")
