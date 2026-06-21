"""
Chain-of-Thought Reasoning for Document Reranking
==================================================

Generates explainable reasoning for GAT-based reranking decisions.

Provides 6-step reasoning process:
1. Query-Document Similarity
2. Graph Neighborhood Influence
3. Entity Relationship Analysis
4. PageRank Authority
5. Uncertainty Assessment
6. Final Score Synthesis
"""


from typing import Any, Dict, List, Optional, Tuple

# Optional torch import
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    torch: Optional[Any] = None
    nn: Optional[Any] = None
    F: Optional[Any] = None
import numpy as np
from mahoun.core.models import ReasoningStep, LegalDocument, LegalEntity, UncertaintyEstimate
from mahoun.core.logging import setup_logger
log = setup_logger("reranking_cot")


class RerankingCoTGenerator:
    """
    Generate chain-of-thought reasoning for reranking decisions
    
    Explains why a document received a specific ranking score by analyzing:
    - Content similarity to query
    - Graph structure influence
    - Entity relationships
    - Structural importance (PageRank)
    - Prediction confidence
    """
    
    def __init__(self, language: str = "fa"):
        """
        Initialize CoT generator
        
        Args:
            language: Output language ("fa" for Persian, "en" for English)
        """
        self.language = language
        log.info(f"Initialized RerankingCoTGenerator with language: {language}")
    
    def generate_reasoning(
        self,
        query: str,
        document: LegalDocument,
        scores: Dict[str, float],
        attention_weights: Optional[List[Tuple[torch.Tensor, torch.Tensor]]] = None,
        uncertainty: Optional[UncertaintyEstimate] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[ReasoningStep]:
        """
        Generate complete chain-of-thought reasoning
        
        Args:
            query: User query
            document: Document being ranked
            scores: Dictionary with retrieval_score, gat_score, pagerank_score, final_score
            attention_weights: GAT attention weights (list of (edge_index, alpha) per layer)
            uncertainty: Uncertainty estimate
            metadata: Additional metadata (node_degree, entity_types, etc.)
            
        Returns:
            List of ReasoningStep objects
        """
        reasoning_steps: List[Any] = []
        # Step 1: Query-Document Similarity
        step1 = self._generate_similarity_step(
            query, document, scores.get('retrieval_score', 0.0)
        )
        reasoning_steps.append(step1)
        
        # Step 2: Graph Neighborhood Influence
        if attention_weights and metadata:
            step2 = self._generate_neighborhood_step(attention_weights, metadata)
            reasoning_steps.append(step2)
        
        # Step 3: Entity Relationship Analysis
        step3 = self._generate_entity_step(document, query, metadata)
        reasoning_steps.append(step3)
        
        # Step 4: PageRank Authority
        if 'pagerank_score' in scores:
            step4 = self._generate_pagerank_step(
                scores['pagerank_score'],
                metadata.get('pagerank_percentile', 0.5) if metadata else 0.5
            )
            reasoning_steps.append(step4)
        
        # Step 5: Uncertainty Assessment
        if uncertainty:
            step5 = self._generate_uncertainty_step(uncertainty)
            reasoning_steps.append(step5)
        
        # Step 6: Final Score Synthesis
        step6 = self._generate_synthesis_step(scores, metadata)
        reasoning_steps.append(step6)
        
        log.debug(f"Generated {len(reasoning_steps)} reasoning steps for document {document.id}")
        
        return reasoning_steps
    
    def _generate_similarity_step(
        self,
        query: str,
        document: LegalDocument,
        score: float
    ) -> ReasoningStep:
        """
        Generate reasoning for query-document similarity
        
        Args:
            query: User query
            document: Document
            score: Similarity score
            
        Returns:
            ReasoningStep with similarity analysis
        """
        # Extract key terms from query
        query_terms = set(query.split())
        doc_terms = set(document.text.split())
        
        # Find matching terms
        matching_terms = query_terms.intersection(doc_terms)
        matching_terms = [t for t in matching_terms if len(t) > 2][:5]  # Top 5
        
        if self.language == "fa":
            step_name = "تشابه محتوایی"
            
            if score >= 0.8:
                reasoning = f"تشابه بسیار بالا ({score:.2f}) با پرسش. "
            elif score >= 0.6:
                reasoning = f"تشابه خوب ({score:.2f}) با پرسش. "
            elif score >= 0.4:
                reasoning = f"تشابه متوسط ({score:.2f}) با پرسش. "
            else:
                reasoning = f"تشابه ضعیف ({score:.2f}) با پرسش. "
            
            if matching_terms:
                reasoning += f"واژگان مشترک: {', '.join(matching_terms[:3])}"
            else:
                reasoning += "واژگان مشترک محدود"
        
        else:  # English
            step_name = "Content Similarity"
            
            if score >= 0.8:
                reasoning = f"Very high similarity ({score:.2f}) to query. "
            elif score >= 0.6:
                reasoning = f"Good similarity ({score:.2f}) to query. "
            elif score >= 0.4:
                reasoning = f"Moderate similarity ({score:.2f}) to query. "
            else:
                reasoning = f"Low similarity ({score:.2f}) to query. "
            
            if matching_terms:
                reasoning += f"Matching terms: {', '.join(matching_terms[:3])}"
            else:
                reasoning += "Limited matching terms"
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=score,
            evidence=matching_terms,
            metadata={"similarity_score": score}
        )
    
    def _generate_neighborhood_step(
        self,
        attention_weights: List[Tuple[torch.Tensor, torch.Tensor]],
        metadata: Dict[str, Any]
    ) -> ReasoningStep:
        """
        Generate reasoning for graph neighborhood influence
        
        Args:
            attention_weights: List of (edge_index, alpha) tuples from GAT layers
            metadata: Metadata with node information
            
        Returns:
            ReasoningStep with neighborhood analysis
        """
        # Analyze attention weights from last layer
        if attention_weights:
            edge_index, alpha = attention_weights[-1]
            
            # Get top attention weights
            top_k = min(5, alpha.shape[0])
            top_values, top_indices = torch.topk(alpha.squeeze(), k=top_k)
            
            avg_attention = alpha.mean().item()
            max_attention = alpha.max().item()
            
            num_neighbors = metadata.get('node_degree', 0)
        else:
            avg_attention = 0.0
            max_attention = 0.0
            num_neighbors = 0
        
        if self.language == "fa":
            step_name = "تأثیر همسایگان در گراف"
            
            if avg_attention >= 0.7:
                reasoning = f"تأثیر قوی از {num_neighbors} همسایه در گراف. "
            elif avg_attention >= 0.4:
                reasoning = f"تأثیر متوسط از {num_neighbors} همسایه در گراف. "
            else:
                reasoning = f"تأثیر ضعیف از {num_neighbors} همسایه در گراف. "
            
            reasoning += f"میانگین وزن توجه: {avg_attention:.2f}, "
            reasoning += f"حداکثر: {max_attention:.2f}"
        
        else:  # English
            step_name = "Graph Neighborhood Influence"
            
            if avg_attention >= 0.7:
                reasoning = f"Strong influence from {num_neighbors} neighbors in graph. "
            elif avg_attention >= 0.4:
                reasoning = f"Moderate influence from {num_neighbors} neighbors. "
            else:
                reasoning = f"Weak influence from {num_neighbors} neighbors. "
            
            reasoning += f"Avg attention: {avg_attention:.2f}, "
            reasoning += f"Max: {max_attention:.2f}"
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=float(avg_attention),
            evidence=[],
            metadata={
                "avg_attention": avg_attention,
                "max_attention": max_attention,
                "num_neighbors": num_neighbors
            }
        )
    
    def _generate_entity_step(
        self,
        document: LegalDocument,
        query: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReasoningStep:
        """
        Generate reasoning for entity relationships
        
        Args:
            document: Document with entities
            query: User query
            metadata: Additional metadata
            
        Returns:
            ReasoningStep with entity analysis
        """
        entities = document.entities
        
        # Count entity types
        entity_types: Dict[str, Any] = {}
        for entity in entities:
            entity_types[entity.label.value] = entity_types.get(entity.label.value, 0) + 1
        
        # Find key entities
        key_entities = [e.text for e in entities[:3]]  # Top 3
        
        # Check if query mentions entities
        query_lower = query.lower()
        matching_entities = [
            e.text for e in entities 
            if e.text.lower() in query_lower
        ][:3]
        
        if self.language == "fa":
            step_name = "تحلیل موجودیت‌ها"
            
            reasoning = f"سند شامل {len(entities)} موجودیت حقوقی است. "
            
            if entity_types:
                top_types = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:2]
                type_str = ", ".join([f"{t[0]} ({t[1]})" for t in top_types])
                reasoning += f"انواع اصلی: {type_str}. "
            
            if matching_entities:
                reasoning += f"موجودیت‌های مطابق با پرسش: {', '.join(matching_entities)}"
            else:
                reasoning += "موجودیت‌های کلیدی: " + ", ".join(key_entities[:2])
        
        else:  # English
            step_name = "Entity Analysis"
            
            reasoning = f"Document contains {len(entities)} legal entities. "
            
            if entity_types:
                top_types = sorted(entity_types.items(), key=lambda x: x[1], reverse=True)[:2]
                type_str = ", ".join([f"{t[0]} ({t[1]})" for t in top_types])
                reasoning += f"Main types: {type_str}. "
            
            if matching_entities:
                reasoning += f"Entities matching query: {', '.join(matching_entities)}"
            else:
                reasoning += "Key entities: " + ", ".join(key_entities[:2])
        
        confidence = 0.7 if matching_entities else 0.5
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=confidence,
            evidence=matching_entities if matching_entities else key_entities,
            metadata={
                "num_entities": len(entities),
                "entity_types": entity_types,
                "matching_entities": len(matching_entities)
            }
        )
    
    def _generate_pagerank_step(
        self,
        pagerank_score: float,
        percentile: float
    ) -> ReasoningStep:
        """
        Generate reasoning for PageRank authority
        
        Args:
            pagerank_score: PageRank score
            percentile: Percentile rank (0-1)
            
        Returns:
            ReasoningStep with PageRank analysis
        """
        if self.language == "fa":
            step_name = "اهمیت ساختاری"
            
            if percentile >= 0.9:
                reasoning = f"سند بسیار مهم (رتبه {percentile*100:.0f}٪). "
            elif percentile >= 0.7:
                reasoning = f"سند مهم (رتبه {percentile*100:.0f}٪). "
            elif percentile >= 0.5:
                reasoning = f"سند با اهمیت متوسط (رتبه {percentile*100:.0f}٪). "
            else:
                reasoning = f"سند با اهمیت کم (رتبه {percentile*100:.0f}٪). "
            
            reasoning += f"امتیاز PageRank: {pagerank_score:.4f}"
        
        else:  # English
            step_name = "Structural Importance"
            
            if percentile >= 0.9:
                reasoning = f"Very important document (top {percentile*100:.0f}%). "
            elif percentile >= 0.7:
                reasoning = f"Important document (top {percentile*100:.0f}%). "
            elif percentile >= 0.5:
                reasoning = f"Moderately important (top {percentile*100:.0f}%). "
            else:
                reasoning = f"Less important (top {percentile*100:.0f}%). "
            
            reasoning += f"PageRank score: {pagerank_score:.4f}"
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=float(percentile),
            evidence=[],
            metadata={
                "pagerank_score": pagerank_score,
                "percentile": percentile
            }
        )
    
    def _generate_uncertainty_step(
        self,
        uncertainty: UncertaintyEstimate
    ) -> ReasoningStep:
        """
        Generate reasoning for uncertainty assessment
        
        Args:
            uncertainty: Uncertainty estimate
            
        Returns:
            ReasoningStep with uncertainty analysis
        """
        # Classify confidence level
        if uncertainty.uncertainty < 0.1:
            confidence_level = "high"
            confidence_level_fa = "بالا"
        elif uncertainty.uncertainty < 0.2:
            confidence_level = "medium"
            confidence_level_fa = "متوسط"
        else:
            confidence_level = "low"
            confidence_level_fa = "پایین"
        
        if self.language == "fa":
            step_name = "ارزیابی اطمینان"
            
            reasoning = f"سطح اطمینان: {confidence_level_fa} "
            reasoning += f"(عدم قطعیت: {uncertainty.uncertainty:.3f}). "
            reasoning += f"بازه اطمینان 95٪: [{uncertainty.lower_bound:.2f}, {uncertainty.upper_bound:.2f}]"
        
        else:  # English
            step_name = "Uncertainty Assessment"
            
            reasoning = f"Confidence level: {confidence_level} "
            reasoning += f"(uncertainty: {uncertainty.uncertainty:.3f}). "
            reasoning += f"95% CI: [{uncertainty.lower_bound:.2f}, {uncertainty.upper_bound:.2f}]"
        
        # Higher confidence when uncertainty is low
        confidence = 1.0 - min(uncertainty.uncertainty, 1.0)
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=confidence,
            evidence=[],
            metadata={
                "uncertainty": uncertainty.uncertainty,
                "confidence_level": confidence_level,
                "ci_lower": uncertainty.lower_bound,
                "ci_upper": uncertainty.upper_bound
            }
        )
    
    def _generate_synthesis_step(
        self,
        scores: Dict[str, float],
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReasoningStep:
        """
        Generate reasoning for final score synthesis
        
        Args:
            scores: Dictionary with all scores
            metadata: Additional metadata with weights
            
        Returns:
            ReasoningStep with synthesis explanation
        """
        final_score = scores.get('final_score', 0.0)
        
        # Get individual scores
        retrieval_score = scores.get('retrieval_score', 0.0)
        gat_score = scores.get('gat_score', 0.0)
        pagerank_score = scores.get('pagerank_score', 0.0)
        
        # Get weights from metadata or use defaults
        if metadata and 'weights' in metadata:
            weights = metadata['weights']
        else:
            weights = {
                'retrieval': 0.4,
                'gat': 0.3,
                'pagerank': 0.2,
                'cross_encoder': 0.1
            }
        
        if self.language == "fa":
            step_name = "ترکیب نهایی امتیازات"
            
            reasoning = f"امتیاز نهایی: {final_score:.3f}. "
            reasoning += "ترکیب وزن‌دار از: "
            
            components: List[Any] = []
            if retrieval_score > 0:
                components.append(f"بازیابی ({retrieval_score:.2f})")
            if gat_score > 0:
                components.append(f"GAT ({gat_score:.2f})")
            if pagerank_score > 0:
                components.append(f"PageRank ({pagerank_score:.2f})")
            
            reasoning += ", ".join(components)
        
        else:  # English
            step_name = "Final Score Synthesis"
            
            reasoning = f"Final score: {final_score:.3f}. "
            reasoning += "Weighted combination of: "
            
            components: List[Any] = []
            if retrieval_score > 0:
                components.append(f"retrieval ({retrieval_score:.2f})")
            if gat_score > 0:
                components.append(f"GAT ({gat_score:.2f})")
            if pagerank_score > 0:
                components.append(f"PageRank ({pagerank_score:.2f})")
            
            reasoning += ", ".join(components)
        
        return ReasoningStep(
            step=step_name,
            reasoning=reasoning,
            confidence=final_score,
            evidence=[],
            metadata={
                "final_score": final_score,
                "component_scores": {
                    "retrieval": retrieval_score,
                    "gat": gat_score,
                    "pagerank": pagerank_score
                },
                "weights": weights
            }
        )
