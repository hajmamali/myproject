"""
Deep Legal Reasoning Engine
============================

Main reasoning engine combining:
- Chain of Thought (CoT)
- Causal Inference
- Knowledge Graph
- Planner / Thought / Executor pattern

Extracted from legacy code with full implementation.
"""


from typing import Any, Dict, List, Optional, Tuple

from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.reasoning.chain_of_thought import ChainOfThoughtReasoner
from mahoun.reasoning.causal_inference import CausalInferenceEngine
from mahoun.core.models import ReasoningResult
from mahoun.core.logging import setup_logger
from mahoun.graph.ultra_graph_builder import UltraGraphBuilder

log = setup_logger("reasoning_engine")


class DeepLegalReasoningEngine:
    """
    Main deep reasoning engine combining all components
    
    Features:
    - Chain of thought reasoning (6-step process)
    - Causal inference
    - Knowledge graph integration
    - Evidence assessment
    - Planner / Thought / Executor pattern
    
    Upgraded from legacy code with:
    - Pydantic models
    - Better structure
    - Type hints
    - Complete implementation from legacy
    """
    
    def __init__(self):
        """Initialize deep reasoning engine with full legacy implementation"""
        self.knowledge_graph = LegalKnowledgeGraph()
        self.graph_builder = UltraGraphBuilder(
            enable_quality_assessment=False,
            enable_analytics=False
        )
        self.chain_reasoner = ChainOfThoughtReasoner(
            self.knowledge_graph,
            graph=self.graph_builder
        )
        self.causal_engine = CausalInferenceEngine()
        
        # Initialize with basic legal knowledge
        self._initialize_legal_knowledge()
        
        log.info("Initialized DeepLegalReasoningEngine with full reasoning capabilities")
    
    def _initialize_legal_knowledge(self):
        """Initialize with basic legal knowledge"""
        
        # Add basic legal rules
        self.knowledge_graph.add_legal_rule(
            "contract_breach",
            "عدم انجام تعهدات قراردادی",
            "طرف متخلف موظف به جبران خسارت است",
            0.9
        )
        self._register_rule_with_graph(
            "contract_breach",
            "عدم انجام تعهدات قراردادی",
            "طرف متخلف موظف به جبران خسارت است"
        )
        
        self.knowledge_graph.add_legal_rule(
            "criminal_liability",
            "ارتکاب جرم عمدی",
            "مرتکب مستحق مجازات قانونی است",
            0.95
        )
        self._register_rule_with_graph(
            "criminal_liability",
            "ارتکاب جرم عمدی",
            "مرتکب مستحق مجازات قانونی است"
        )
        
        # Add causal relationships
        self.causal_engine.add_causal_relationship(
            "نقض قرارداد",
            "خسارت مالی",
            0.8
        )
        
        self.causal_engine.add_causal_relationship(
            "ارتکاب جرم",
            "مجازات قانونی",
            0.9
        )
        
        log.debug("Initialized basic legal knowledge")
    
    def _register_rule_with_graph(
        self,
        rule_id: str,
        condition: str,
        conclusion: str
    ):
        """Mirror knowledge-graph rules into the UltraGraphBuilder"""
        if not hasattr(self, "graph_builder") or self.graph_builder is None:
            return
        
        entities = [
            {"id": condition, "label": condition, "type": "Condition"},
            {"id": conclusion, "label": conclusion, "type": "Conclusion"},
        ]
        relationships = [
            {
                "source_id": condition,
                "target_id": conclusion,
                "type": "IMPLIES",
                "properties": {"rule_id": rule_id}
            }
        ]
        self.graph_builder.build_graph(entities, relationships)
    
    def deep_reason(
        self,
        question: str,
        context: str,
        facts: Optional[List[str]] = None
    ) -> ReasoningResult:
        """
        Perform deep legal reasoning with full 6-step Chain of Thought
        
        Process (from legacy code):
        1. Analyze question type
        2. Extract legal concepts
        3. Find applicable rules
        4. Find precedents
        5. Apply logical reasoning
        6. Generate conclusion
        
        Then combine with causal inference for final answer.
        
        Args:
            question: Legal question
            context: Context text
            facts: Extracted facts (auto-extract if None)
            
        Returns:
            ReasoningResult with complete analysis
        """
        if facts is None:
            facts = self._extract_facts_from_context(context)
        
        log.info(f"Starting deep reasoning for question: {question[:50]}...")
        log.debug(f"Extracted {len(facts)} facts from context")
        
        # Step 1-6: Chain of thought reasoning (full implementation)
        cot_result = self.chain_reasoner.reason(question, context, facts)
        log.debug(f"CoT completed with {len(cot_result['reasoning_chain'])} steps")
        
        # Causal inference (parallel analysis)
        causal_result = self.causal_engine.infer_causality(facts, question)
        log.debug(f"Causal inference found {len(causal_result['causal_chain'])} relationships")
        
        # Synthesize final answer (combine CoT + Causal)
        final_answer = self._synthesize_answer(cot_result, causal_result)
        
        # Calculate overall confidence
        confidence = (
            cot_result["confidence"] + causal_result["confidence"]
        ) / 2
        
        # Assess evidence strength
        evidence_strength = self._assess_evidence_strength(
            cot_result,
            causal_result
        )
        
        # Create Pydantic result model
        result = ReasoningResult(
            question=question,
            context=context,
            facts=facts,
            reasoning_chain=cot_result["reasoning_chain"],
            causal_chain=causal_result["causal_chain"],
            primary_cause=causal_result["primary_cause"],
            final_answer=final_answer,
            confidence=confidence,
            supporting_evidence=cot_result["supporting_evidence"],
            evidence_strength=evidence_strength,
             visited_nodes=cot_result.get("visited_nodes", []),
             graph_edges_used=cot_result.get("graph_edges_used", []),
             used_rule_ids=cot_result.get("used_rule_ids", []),
             limitations=cot_result.get("limitations"),
             graph_dependency_proof=cot_result.get("graph_dependency_proof", False),
            reasoning_depth="deep"
        )
        
        log.info(
            f"✅ Deep reasoning completed: "
            f"confidence={confidence:.2%}, "
            f"evidence={evidence_strength}, "
            f"steps={len(cot_result['reasoning_chain'])}"
        )
        
        return result
    
    def _extract_facts_from_context(self, context: str) -> List[str]:
        """
        Extract facts from context
        
        Simple sentence splitting (can be enhanced with NLP)
        """
        sentences = context.split(".")
        facts = [s.strip() for s in sentences if len(s.strip()) > 10]
        return facts
    
    def _synthesize_answer(
        self,
        cot_result: Dict,
        causal_result: Dict
    ) -> str:
        """Synthesize final answer from all reasoning"""
        
        base_answer = cot_result["answer"]
        
        # Add causal insights if available
        if causal_result["primary_cause"]:
            causal_insight = (
                f" علت اصلی: {causal_result['primary_cause'].explanation}"
            )
            base_answer += causal_insight
        
        if causal_result["causal_chain"]:
            base_answer += (
                f" | تحلیل علّی شامل {len(causal_result['causal_chain'])} رابطه است."
            )
        
        # Add confidence qualifier
        confidence = (
            cot_result["confidence"] + causal_result["confidence"]
        ) / 2
        
        if confidence < 0.7:
            base_answer += " (نیاز به بررسی بیشتر)"
        elif confidence > 0.9:
            base_answer += " (با اطمینان بالا)"
        
        if cot_result.get("contradictions_detected"):
            base_answer += " ⚠️ تعارض بین قوانین شناسایی شد."
        
        if cot_result.get("limitations"):
            base_answer += f" [حالت محدود: {cot_result['limitations']}]"
        
        if not cot_result.get("graph_dependency_proof", False):
            base_answer += " (گزارش بدون اثبات وابستگی کامل به گراف)"
        
        return base_answer
    
    def _assess_evidence_strength(
        self,
        cot_result: Dict,
        causal_result: Dict
    ) -> str:
        """Assess overall evidence strength"""
        
        evidence_count = len(cot_result.get("supporting_evidence", []))
        causal_strength = causal_result.get("confidence", 0)
        
        if evidence_count >= 3 and causal_strength > 0.8:
            return "قوی"
        elif evidence_count >= 2 and causal_strength > 0.6:
            return "متوسط"
        else:
            return "ضعیف"
    
    def explain_reasoning(self, reasoning_result: ReasoningResult) -> str:
        """
        Generate human-readable explanation of reasoning
        
        Full implementation from legacy code with enhancements.
        
        Args:
            reasoning_result: Reasoning result
            
        Returns:
            Formatted explanation with:
            - Reasoning steps
            - Causal analysis
            - Supporting evidence
            - Confidence metrics
        """
        explanation = "🧠 مراحل استدلال عمیق:\n"
        explanation += "=" * 50 + "\n\n"
        
        # Chain of thought steps
        for i, step in enumerate(reasoning_result.reasoning_chain, 1):
            explanation += f"{i}. **{step.step}**\n"
            explanation += f"   {step.reasoning}\n"
            explanation += f"   اطمینان: {step.confidence:.1%}\n"
            
            if step.evidence:
                explanation += f"   شواهد: {', '.join(step.evidence[:3])}\n"
            
            explanation += "\n"
        
        # Causal analysis
        if reasoning_result.primary_cause:
            explanation += "🔗 **تحلیل علت و معلول:**\n"
            explanation += f"   {reasoning_result.primary_cause.explanation}\n"
            explanation += f"   قدرت رابطه: {reasoning_result.primary_cause.strength:.1%}\n\n"
        
        if reasoning_result.causal_chain:
            explanation += f"   زنجیره علّی: {len(reasoning_result.causal_chain)} رابطه\n\n"
        
        # Supporting evidence
        if reasoning_result.supporting_evidence:
            explanation += "📚 **شواهد پشتیبان:**\n"
            for i, evidence in enumerate(reasoning_result.supporting_evidence, 1):
                explanation += f"   {i}. {evidence}\n"
            explanation += "\n"
        
        # Overall assessment
        explanation += "📊 **ارزیابی کلی:**\n"
        explanation += f"   سطح اطمینان: {reasoning_result.confidence:.1%}\n"
        explanation += f"   قدرت شواهد: {reasoning_result.evidence_strength}\n"
        explanation += f"   عمق استدلال: {reasoning_result.reasoning_depth}\n"
        
        # Confidence interpretation
        if reasoning_result.confidence > 0.9:
            explanation += "\n✅ **نتیجه با اطمینان بالا**"
        elif reasoning_result.confidence > 0.7:
            explanation += "\n⚠️  **نتیجه با اطمینان متوسط - توصیه به بررسی بیشتر**"
        else:
            explanation += "\n❌ **نتیجه با اطمینان پایین - نیاز به اطلاعات بیشتر**"
        
        return explanation
    
    def add_legal_rule(
        self,
        rule_id: str,
        condition: str,
        conclusion: str,
        confidence: float = 1.0
    ):
        """Add legal rule to knowledge base"""
        self.knowledge_graph.add_legal_rule(
            rule_id,
            condition,
            conclusion,
            confidence
        )
        self._register_rule_with_graph(rule_id, condition, conclusion)
    
    def add_precedent(
        self,
        case_id: str,
        facts: List[str],
        decision: str,
        court: str
    ):
        """Add legal precedent"""
        self.knowledge_graph.add_precedent(
            case_id,
            facts,
            decision,
            court
        )
    
    def add_causal_relationship(
        self,
        cause: str,
        effect: str,
        strength: float
    ):
        """Add causal relationship"""
        self.causal_engine.add_causal_relationship(cause, effect, strength)
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        return {
            "knowledge_graph": self.knowledge_graph.get_statistics(),
            "causal_engine": self.causal_engine.get_statistics(),
        }
