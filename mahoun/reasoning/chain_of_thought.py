"""
Chain of Thought Reasoning
===========================

Step-by-step reasoning for legal problems.

Extracted from legacy code with upgrades.
"""


from collections import deque, defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from mahoun.core.models import ReasoningStep
from mahoun.reasoning.knowledge_graph import LegalKnowledgeGraph
from mahoun.core.logging import setup_logger

log = setup_logger("chain_of_thought")


class ChainOfThoughtReasoner:
    """
    Chain of thought reasoning for legal problems
    
    Steps:
    1. Analyze question
    2. Extract legal concepts
    3. Find applicable rules
    4. Find precedents
    5. Apply logical reasoning
    6. Generate conclusion
    
    Upgraded from legacy code with:
    - Pydantic models
    - Better structure
    - Type hints
    """
    
    def __init__(
        self,
        knowledge_graph: LegalKnowledgeGraph,
        graph: Any = None
    ):
        """
        Initialize reasoner
        
        Args:
            knowledge_graph: Legal knowledge graph
            graph: Optional graph adapter providing adjacency info
        """
        self.knowledge_graph = knowledge_graph
        self.graph = graph
        self.reasoning_steps: List[ReasoningStep] = []
        self.graph_edges_used: List[Tuple[str, str]] = []
        self.graph_reachable_nodes: set[str] = set()
        self.graph_entry_points: List[str] = []
        self.graph_paths_used: List[List[str]] = []
        self.rule_applications: List[Dict[str, Any]] = []
        self.graph_dependency_proof: bool = False
        self.limitations: Optional[str] = None
        self.graph_available: bool = False
        self._contradictory_sources: Dict[str, set] = {}
        
        log.info("Initialized ChainOfThoughtReasoner")
    
    def reason(
        self,
        question: str,
        context: str,
        facts: List[str]
    ) -> Dict[str, Any]:
        """
        Perform chain of thought reasoning
        
        Args:
            question: Legal question
            context: Context text
            facts: Extracted facts
            
        Returns:
            Reasoning result with steps and conclusion
        """
        self.reasoning_steps = []
        self.graph_edges_used = []
        self.graph_paths_used = []
        self.graph_entry_points = list(facts)
        self.graph_reachable_nodes = set(facts)
        self.rule_applications = []
        self.graph_dependency_proof = False
        self.limitations = None
        self._contradictory_sources = {}
        self.graph_available = self._graph_is_available()
        if not self.graph_available:
            self.limitations = "graph_missing_or_empty"
        if self.graph_available:
            self._expand_graph_reachability(facts)
        
        # Step 1: Analyze question
        step1 = self._analyze_question(question)
        self.reasoning_steps.append(step1)
        
        # Step 2: Extract legal concepts
        step2 = self._extract_legal_concepts(context, facts)
        self.reasoning_steps.append(step2)
        
        # Step 3: Find applicable rules
        step3 = self._find_applicable_rules(facts)
        self.reasoning_steps.append(step3)
        
        # Step 4: Find precedents
        step4 = self._find_precedents(facts)
        self.reasoning_steps.append(step4)
        
        # Step 5: Apply logical reasoning
        step5 = self._apply_logical_reasoning(
            step3.get("rules", []),
            step4.get("precedents", [])
        )
        self.reasoning_steps.append(step5)
        
        # Step 6: Generate conclusion
        step6 = self._generate_conclusion(question, step5.get("reasoning", []))
        self.reasoning_steps.append(step6)
        
        contradictions_detected = self._detect_contradictions()
        
        return {
            "answer": step6["conclusion"],
            "reasoning_chain": [
                ReasoningStep(
                    step=s["step"],
                    reasoning=s.get("reasoning", ""),
                    confidence=s.get("confidence", 0.5),
                    evidence=s.get("evidence", [])
                )
                for s in self.reasoning_steps
            ],
            "confidence": self._calculate_confidence(),
            "supporting_evidence": self._gather_evidence(),
            "graph_edges_used": list(self.graph_edges_used),
            "reachable_nodes": sorted(self.graph_reachable_nodes),
            "graph_paths_used": self.graph_paths_used,
            "visited_nodes": sorted(self.graph_reachable_nodes),
            "used_rule_ids": [entry["rule_id"] for entry in self.rule_applications],
            "graph_dependency_proof": self.graph_dependency_proof,
            "limitations": self.limitations,
            "contradictions_detected": contradictions_detected,
            "rule_applications": list(self.rule_applications),
        }
    
    def _analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze the legal question"""
        
        question_types = {
            "liability": ["مسئول", "مسئولیت", "متعهد"],
            "procedure": ["آیین", "روند", "مراحل", "چگونه"],
            "definition": ["چیست", "تعریف", "معنی"],
            "consequence": ["عواقب", "نتیجه", "مجازات"],
            "requirement": ["شرایط", "الزامات", "ضروری"],
        }
        
        question_lower = question.lower()
        detected_type = "general"
        
        for q_type, keywords in question_types.items():
            if any(keyword in question_lower for keyword in keywords):
                detected_type = q_type
                break
        
        key_terms = [term for term in question.split() if len(term) > 3]
        
        return {
            "step": "question_analysis",
            "question_type": detected_type,
            "key_terms": key_terms,
            "reasoning": f"سوال از نوع {detected_type} تشخیص داده شد",
            "confidence": 0.8,
        }
    
    def _extract_legal_concepts(
        self,
        context: str,
        facts: List[str]
    ) -> Dict[str, Any]:
        """Extract legal concepts from context"""
        
        legal_concepts = {
            "entities": [],
            "relationships": [],
            "legal_terms": []
        }
        
        # Legal keywords
        legal_keywords = [
            "دادگاه", "قاضی", "متهم", "شاکی", "وکیل",
            "قانون", "ماده", "حکم", "رأی", "دادنامه",
            "پرونده", "جرم", "مجازات", "قرارداد", "تعهد"
        ]
        
        all_text = (context + " " + " ".join(facts)).lower()
        
        for keyword in legal_keywords:
            if keyword in all_text:
                legal_concepts["legal_terms"].append(keyword)
        
        return {
            "step": "concept_extraction",
            "concepts": legal_concepts,
            "reasoning": f"{len(legal_concepts['legal_terms'])} مفهوم حقوقی شناسایی شد",
            "confidence": 0.7,
        }
    
    def _find_applicable_rules(self, facts: List[str]) -> Dict[str, Any]:
        """Find applicable legal rules"""
        
        fact_inputs = facts
        if self.graph and self.graph_reachable_nodes:
            merged = list(dict.fromkeys(list(facts) + list(self.graph_reachable_nodes)))
            fact_inputs = merged
        
        rules = self.knowledge_graph.find_applicable_rules(fact_inputs)
        
        return {
            "step": "rule_identification",
            "rules": rules[:3],  # Top 3 rules
            "reasoning": f"{len(rules)} قانون قابل اعمال یافت شد",
            "confidence": 0.8 if rules else 0.3,
        }
    
    def _find_precedents(self, facts: List[str]) -> Dict[str, Any]:
        """Find relevant precedents"""
        
        precedents = self.knowledge_graph.find_similar_precedents(facts)
        
        return {
            "step": "precedent_analysis",
            "precedents": precedents,
            "reasoning": f"{len(precedents)} سابقه مشابه یافت شد",
            "confidence": 0.7 if precedents else 0.3,
        }
    
    def _apply_logical_reasoning(
        self,
        rules: List[Dict],
        precedents: List[Dict]
    ) -> Dict[str, Any]:
        """Apply logical reasoning"""
        
        reasoning_logic: List[Any] = []
        # Rule-based reasoning
        for rule in rules:
            if rule["match_score"] > 0.5 and self._graph_allows_rule(rule["rule"], rule["rule_id"]):
                reasoning_logic.append({
                    "type": "rule_application",
                    "content": f"بر اساس {rule['rule_id']}: {rule['rule'].conclusion}",
                    "confidence": rule["match_score"],
                    "rule_id": rule["rule_id"],
                })
        
        # Precedent-based reasoning
        for precedent in precedents:
            if precedent["similarity"] > 0.3:
                reasoning_logic.append({
                    "type": "precedent_application",
                    "content": f"مطابق سابقه {precedent['case_id']}: {precedent['precedent'].decision}",
                    "confidence": precedent["similarity"],
                })
        
        return {
            "step": "logical_reasoning",
            "reasoning": reasoning_logic,
            "reasoning_text": f"{len(reasoning_logic)} استدلال منطقی تولید شد",
            "confidence": 0.75 if reasoning_logic else 0.4,
        }
    
    def _generate_conclusion(
        self,
        question: str,
        reasoning: List[Dict]
    ) -> Dict[str, Any]:
        """Generate final conclusion"""
        
        if not reasoning:
            conclusion = "بر اساس اطلاعات موجود، نمی‌توان نتیجه‌گیری قطعی ارائه داد."
        else:
            # Combine reasoning
            rule_conclusions = [
                r["content"] for r in reasoning 
                if r["type"] == "rule_application"
            ]
            precedent_conclusions = [
                r["content"] for r in reasoning 
                if r["type"] == "precedent_application"
            ]
            
            conclusion_parts: List[Any] = []
            if rule_conclusions:
                conclusion_parts.append(
                    "بر اساس قوانین: " + "; ".join(rule_conclusions)
                )
            if precedent_conclusions:
                conclusion_parts.append(
                    "بر اساس سوابق: " + "; ".join(precedent_conclusions)
                )
            
            conclusion = " و ".join(conclusion_parts) if conclusion_parts else "نتیجه‌گیری نامشخص"
        
        return {
            "step": "conclusion_generation",
            "conclusion": conclusion,
            "reasoning": "نتیجه‌گیری نهایی بر اساس استدلالات انجام شد",
            "confidence": 0.8 if reasoning else 0.3,
        }
    
    def _calculate_confidence(self) -> float:
        """Calculate overall confidence"""
        
        if not self.reasoning_steps:
            return 0.0
        
        # Find rule and precedent steps
        rule_step = next(
            (s for s in self.reasoning_steps if s.get("step") == "rule_identification"),
            None
        )
        precedent_step = next(
            (s for s in self.reasoning_steps if s.get("step") == "precedent_analysis"),
            None
        )
        
        # Base confidence
        confidence = 0.5
        
        # Add confidence from rules
        if rule_step and rule_step.get("rules"):
            confidence += 0.3 * len(rule_step["rules"]) / 3  # Max 0.3
        
        # Add confidence from precedents
        if precedent_step and precedent_step.get("precedents"):
            confidence += 0.2 * len(precedent_step["precedents"]) / 5  # Max 0.2
        
        return min(confidence, 1.0)
    
    def _gather_evidence(self) -> List[str]:
        """Gather supporting evidence"""
        
        evidence: List[Any] = []
        for step in self.reasoning_steps:
            if step.get("step") == "rule_identification" and step.get("rules"):
                for rule in step["rules"]:
                    evidence.append(
                        f"قانون: {rule['rule'].condition} → {rule['rule'].conclusion}"
                    )
            
            if step.get("step") == "precedent_analysis" and step.get("precedents"):
                for precedent in step["precedents"]:
                    evidence.append(
                        f"سابقه: {precedent['precedent'].decision}"
                    )
        
        return evidence
    
    def _graph_is_available(self) -> bool:
        """Check whether a usable graph has been provided"""
        if self.graph is None:
            return False
        get_edges = getattr(self.graph, "get_edges", None)
        if callable(get_edges):
            try:
                return bool(self.graph.get_edges())
            except Exception:
                return False
        return False
    
    def _record_rule_application(
        self,
        rule_id: str,
        condition: str,
        conclusion: str,
        edge: Optional[Tuple[str, str]]
    ):
        """Store metadata for each applied rule"""
        self.rule_applications.append({
            "rule_id": rule_id,
            "source": condition,
            "target": conclusion,
            "graph_edge_used": edge,
        })
    
    def _detect_contradictions(self) -> bool:
        """Detect if multiple conflicting conclusions were reached"""
        condition_targets = defaultdict(set)
        for entry in self.rule_applications:
            condition_targets[entry["source"]].add(entry["target"])
        
        self._contradictory_sources = {
            source: targets
            for source, targets in condition_targets.items()
            if len(targets) > 1
        }
        return bool(self._contradictory_sources)
    # ------------------------------------------------------------------
    # Graph helpers
    # ------------------------------------------------------------------
    
    def _graph_allows_rule(self, rule, rule_id: str) -> bool:
        """
        Ensure graph connectivity requirements are met for a rule.
        Records rule application metadata for auditing.
        """
        condition = rule.condition
        conclusion = rule.conclusion
        
        if not self.graph_available:
            if condition in self.graph_entry_points:
                self._record_rule_application(rule_id, condition, conclusion, None)
                return True
            return False
        
        if condition not in self.graph_reachable_nodes:
            if not self._graph_path_from_facts(condition):
                return False
        
        if not self._graph_has_edge(condition, conclusion):
            return False
        
        edge = (condition, conclusion)
        self.graph_edges_used.append(edge)
        self.graph_dependency_proof = True
        self.graph_reachable_nodes.add(conclusion)
        self._record_rule_application(rule_id, condition, conclusion, edge)
        return True
    
    def _expand_graph_reachability(self, facts: Iterable[str], max_depth: int = 5):
        """Populate reachable nodes from provided facts"""
        queue = deque([(fact, 0) for fact in facts])
        visited = set(facts)
        
        while queue:
            node, depth = queue.popleft()
            if depth >= max_depth:
                continue
            for neighbor in self._graph_get_neighbors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))
        self.graph_reachable_nodes = visited
    
    def _graph_get_neighbors(self, node_id: str) -> List[str]:
        if self.graph is None:
            return []
        if hasattr(self.graph, "get_neighbors"):
            return self.graph.get_neighbors(node_id)
        
        edge_index = getattr(self.graph, "edge_index", None)
        if edge_index:
            return [
                edge.target_id for edge in edge_index.get(node_id, [])
            ]
        return []
    
    def _graph_has_edge(self, source: str, target: str) -> bool:
        if self.graph is None:
            return False
        if hasattr(self.graph, "has_edge"):
            return self.graph.has_edge(source, target)
        
        edge_index = getattr(self.graph, "edge_index", None)
        if edge_index:
            return any(
                edge.target_id == target
                for edge in edge_index.get(source, [])
            )
        return False
    
    def _graph_path_from_facts(self, target: str, max_depth: int = 5) -> bool:
        """Try to reach a target node from any fact"""
        if self.graph is None:
            return False
        
        for fact in self.graph_entry_points:
            path = self._graph_find_path(fact, target, max_depth)
            if path:
                self.graph_paths_used.append(path)
                for node in path:
                    self.graph_reachable_nodes.add(node)
                return True
        return False
    
    def _graph_find_path(self, start: str, target: str, max_depth: int = 5):
        if self.graph is None:
            return None
        if hasattr(self.graph, "find_path"):
            return self.graph.find_path(start, target, max_depth)
        
        queue = deque([(start, [start])])
        visited = set([start])
        
        while queue:
            node, path = queue.popleft()
            if len(path) > max_depth:
                continue
            for neighbor in self._graph_get_neighbors(node):
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == target:
                    return new_path
                visited.add(neighbor)
                queue.append((neighbor, new_path))
        return None
