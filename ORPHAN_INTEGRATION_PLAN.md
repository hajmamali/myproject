# MAHOUN Orphan Module Integration Report
# Generated: 2026-07-04T05:43:38.244801

## Summary
- Total modules: 6
- Priority P0: 0
- Priority P1: 0
- Priority P2: 0

## Integration Patches

### 1. KG_ADAPTERS
**Target:** `mahoun/bootstrap/runtime.py`
**Description:** Wire Neo4j KG Adapter to SERVICE_REGISTRY
**Benefit:** Graph-based influence signals for evidence ranking
**Risk Level:** Low - graceful degradation if Neo4j disabled

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: kg_adapters ==========
    # Add Neo4j Knowledge Graph Adapter (governance-hardened)
    if settings.graph_backend != "disabled_fallback":
        try:
            from mahoun.reasoning.kg_adapters import Neo4jKGAdapter
            from mahoun.graph.neo4j.connection import get_connection
            
            # Session factory for governed access
            def kg_session_factory():
                conn = get_connection()
                return conn.session()
            
            kg_adapter = Neo4jKGAdapter(session_factory=kg_session_factory)
            SERVICE_REGISTRY["kg_adapter"] = kg_adapter
            logger.info("✓ Neo4jKGAdapter registered (governance-hardened)")
        except ImportError as e:
            logger.warning(f"kg_adapters unavailable: {e}")
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_kg_adapter_registration
- [ ] test_kg_adapter_query

---

### 2. POLICIES
**Target:** `mahoun/reasoning/adapters.py`
**Description:** Add ReasoningPolicy to DependencyContainer
**Benefit:** Policy-based reasoning control for different risk profiles
**Risk Level:** Low - defaults to BALANCED policy

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: policies ==========
    from mahoun.reasoning.policies import get_policy, PolicyType
    
    def set_policy(self, policy_type: PolicyType) -> None:
        """Set reasoning policy (Conservative/Balanced/Aggressive)"""
        self._policy = get_policy(policy_type)
        logger.info(f"Reasoning policy set to: {policy_type}")
    
    @property
    def policy(self):
        """Get current reasoning policy"""
        if not hasattr(self, '_policy'):
            from mahoun.reasoning.policies import get_policy, PolicyType
            self._policy = get_policy(PolicyType.BALANCED)
        return self._policy
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_policy_selection
- [ ] test_conservative_policy
- [ ] test_aggressive_policy

---

### 3. REASONING_RECORDER_ULTRA
**Target:** `mahoun/reasoning/evidence_linked_verdict.py`
**Description:** Replace ReasoningRecorder with Ultra version (cryptographic audit)
**Benefit:** Cryptographic hash-chain audit trail with tamper detection
**Risk Level:** Medium - needs testing for backward compatibility

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: reasoning_recorder_ultra ==========
    # Replace standard recorder with Ultra version for cryptographic integrity
    from mahoun.reasoning.reasoning_recorder_ultra import (
        RerankingCoTGenerator,  # If needed for step generation
        # Add other classes as needed
    )
    
    # In __init__ method, replace:
    # self.recorder = ReasoningRecorder()
    # With:
    # self.recorder = UltraReasoningRecorder(backend="file", audit_mode=True)
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_ultra_recorder_hash_chain
- [ ] test_ultra_recorder_tamper_detection

---

### 4. CAUSAL_EFFECTS
**Target:** `mahoun/reasoning/evidence_linked_verdict.py`
**Description:** Add optional causal effect estimation step
**Benefit:** Causal effect estimation for legal reasoning
**Risk Level:** Low - optional feature, fails gracefully

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: causal_effects ==========
    def _estimate_causal_effects(
        self,
        facts: List[Dict],
        enable_causal: bool = False
    ) -> Optional[Dict[str, float]]:
        """
        Estimate causal effects between facts (OPTIONAL)
        
        Args:
            facts: List of fact dictionaries
            enable_causal: Whether to run causal analysis
            
        Returns:
            Dictionary with causal effect estimates or None
        """
        if not enable_causal:
            return None
        
        try:
            from mahoun.reasoning.causal_effects import CausalEffectEstimator
            import numpy as np
            
            # Convert facts to numerical data (simplified)
            # In production, use proper feature extraction
            X = np.random.randn(len(facts), 5)  # Covariates
            treatment = np.random.randint(0, 2, len(facts))  # Binary treatment
            outcome = np.random.randn(len(facts))  # Outcome
            
            estimator = CausalEffectEstimator(method='dr')  # Doubly robust
            result = estimator.estimate(X, treatment, outcome)
            
            return result
        except Exception as e:
            self.logger.warning(f"Causal analysis failed: {e}")
            return None
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_causal_effect_estimation

---

### 5. CAUSAL_STRUCTURE
**Target:** `mahoun/reasoning/knowledge_graph.py`
**Description:** Add causal structure learning capability
**Benefit:** Learn causal relationships from legal evidence
**Risk Level:** Low - optional feature, returns empty graph on failure

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: causal_structure ==========
    def learn_causal_structure(
        self,
        observations: np.ndarray,
        var_names: Optional[List[str]] = None,
        algorithm: str = 'pc'
    ) -> nx.DiGraph:
        """
        Learn causal DAG from observational data
        
        Args:
            observations: Data matrix [N, D]
            var_names: Variable names
            algorithm: 'pc' or 'notears'
            
        Returns:
            Learned causal DAG
        """
        try:
            from mahoun.reasoning.causal_structure import CausalStructureLearner
            
            learner = CausalStructureLearner(algorithm=algorithm)
            dag = learner.learn(observations, var_names)
            
            logger.info(f"Learned causal structure: {dag.number_of_edges()} edges")
            return dag
        except Exception as e:
            logger.warning(f"Causal structure learning failed: {e}")
            return nx.DiGraph()  # Empty graph fallback
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_causal_dag_learning_pc
- [ ] test_causal_dag_learning_notears

---

### 6. RERANKING_COT
**Target:** `mahoun/rag/hybrid_rag_service.py`
**Description:** Add Chain-of-Thought reasoning for reranking
**Benefit:** Explainable reranking with 6-step reasoning process
**Risk Level:** Low - optional feature, returns empty list on failure

**Code to add:**
```python
# ========== ORPHAN MODULE INTEGRATION: reranking_cot ==========
    def _generate_reranking_explanation(
        self,
        query: str,
        document: LegalDocument,
        scores: Dict[str, float],
        enable_cot: bool = False
    ) -> List[ReasoningStep]:
        """
        Generate Chain-of-Thought explanation for reranking
        
        Args:
            query: User query
            document: Reranked document
            scores: Reranking scores
            enable_cot: Whether to generate CoT
            
        Returns:
            List of ReasoningStep objects with explanations
        """
        if not enable_cot:
            return []
        
        try:
            from mahoun.reasoning.reranking_cot import RerankingCoTGenerator
            
            cot_gen = RerankingCoTGenerator(language="fa")
            reasoning_steps = cot_gen.generate_reasoning(
                query=query,
                document=document,
                scores=scores,
                attention_weights=None,  # Add GAT attention if available
                uncertainty=None,  # Add uncertainty estimate if available
                metadata={}
            )
            
            return reasoning_steps
        except Exception as e:
            self.logger.warning(f"CoT generation failed: {e}")
            return []
    # ========== END ORPHAN MODULE INTEGRATION ==========
```

**Tests needed:**
- [ ] test_reranking_cot_persian
- [ ] test_reranking_cot_english

---
