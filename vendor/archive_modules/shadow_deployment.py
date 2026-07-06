"""
Advanced Shadow Deployment System
==================================

Production-grade shadow deployment with:
- Multi-policy parallel testing
- Statistical comparison and analysis
- Automatic promotion/demotion
- Performance profiling
- Traffic shaping and sampling
- Real-time metrics and alerting
"""


import time
import asyncio
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple, Callable
from dataclasses import dataclass, field
from enum import Enum
from threading import Thread, Lock
from concurrent.futures import ThreadPoolExecutor, Future
from collections import defaultdict, deque

from self_improve.integration.rl_bandit_bridge import RLBanditBridge, HierarchicalDecision
from self_improve.rl.environment import QueryContext, RetrievalResult
from self_improve.logging_utils import get_logger, log_metric

logger = get_logger(__name__)


class ShadowMode(Enum):
    """Shadow deployment modes"""
    DISABLED = "disabled"
    LOGGING_ONLY = "logging_only"  # Log decisions only, no comparison
    COMPARISON = "comparison"  # Compare decisions and results
    FULL_SHADOW = "full_shadow"  # Full parallel execution with metrics
    CANARY = "canary"  # Gradual traffic shift


class PolicyStatus(Enum):
    """Shadow policy status"""
    DRAFT = "draft"
    TESTING = "testing"
    VALIDATED = "validated"
    PROMOTED = "promoted"
    FAILED = "failed"
    ARCHIVED = "archived"


@dataclass
class ShadowResult:
    """Result of shadow execution"""
    query_id: str
    production_decision: HierarchicalDecision
    shadow_decision: HierarchicalDecision
    production_result: Optional[RetrievalResult]
    shadow_result: Optional[RetrievalResult]
    comparison_metrics: Dict[str, float]
    execution_time_ms: float
    timestamp: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ShadowPolicy:
    """Shadow policy configuration"""
    policy_id: str
    name: str
    version: str
    description: str
    bridge: RLBanditBridge
    traffic_percentage: float
    status: PolicyStatus = PolicyStatus.DRAFT
    enabled: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    
    # Performance metrics
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    
    # Comparison metrics
    decision_agreement_rate: float = 0.0
    performance_improvement: float = 0.0
    error_rate: float = 0.0
    
    # Promotion criteria
    min_requests_for_promotion: int = 1000
    min_agreement_rate: float = 0.8
    max_error_rate: float = 0.05
    min_performance_improvement: float = 0.0
    
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ComparisonReport:
    """Detailed comparison report"""
    policy_id: str
    total_comparisons: int
    decision_agreement_rate: float
    strategy_agreement_rate: float
    avg_latency_diff_ms: float
    latency_improvement_pct: float
    accuracy_diff: float
    diversity_diff: float
    statistical_significance: Dict[str, float]
    recommendation: str
    confidence: float
    timestamp: float


class ShadowDeploymentManager:
    """
    Advanced Shadow Deployment Manager
    
    Features:
    - Multi-policy parallel testing
    - Statistical comparison and validation
    - Automatic promotion based on metrics
    - Traffic shaping and sampling strategies
    - Real-time performance monitoring
    - Detailed comparison reports
    - Rollback capabilities
    """
    
    def __init__(
        self,
        production_bridge: RLBanditBridge,
        max_shadow_policies: int = 5,
        comparison_timeout: float = 5.0,
        enable_async: bool = True,
        max_results_buffer: int = 50000,
        statistical_confidence: float = 0.95,
        enable_auto_promotion: bool = False,
    ):
        """
        Initialize shadow deployment manager
        
        Args:
            production_bridge: Production RL-Bandit bridge
            max_shadow_policies: Maximum concurrent shadow policies
            comparison_timeout: Timeout for shadow execution (seconds)
            enable_async: Enable async execution
            max_results_buffer: Maximum results to keep in memory
            statistical_confidence: Confidence level for statistical tests
            enable_auto_promotion: Enable automatic policy promotion
        """
        self.production_bridge = production_bridge
        self.max_shadow_policies = max_shadow_policies
        self.comparison_timeout = comparison_timeout
        self.enable_async = enable_async
        self.max_results_buffer = max_results_buffer
        self.statistical_confidence = statistical_confidence
        self.enable_auto_promotion = enable_auto_promotion
        
        # Policy management
        self.shadow_policies: Dict[str, ShadowPolicy] = {}
        self.shadow_lock = Lock()
        
        # Results storage
        self.shadow_results: deque = deque(maxlen=max_results_buffer)
        self.results_lock = Lock()
        
        # Per-policy results for analysis
        self.policy_results: Dict[str, List[ShadowResult]] = defaultdict(list)
        
        # Mode and traffic control
        self.mode = ShadowMode.DISABLED
        self.global_traffic_percentage = 0.0
        
        # Sampling strategies
        self.sampling_strategies = {
            "random": self._random_sampling,
            "stratified": self._stratified_sampling,
            "importance": self._importance_sampling,
        }
        self.current_sampling_strategy = "random"
        
        # Async execution
        if enable_async:
            self.executor = ThreadPoolExecutor(
                max_workers=max_shadow_policies * 4,
                thread_name_prefix="shadow_"
            )
        else:
            self.executor = None
            
        # Statistics
        self.total_requests = 0
        self.shadow_requests = 0
        self.comparison_count = 0
        self.error_count = 0
        self.timeout_count = 0
        
        # Performance tracking
        self.latency_samples = deque(maxlen=10000)
        self.comparison_latency_samples = deque(maxlen=10000)
        
        # Callbacks
        self.promotion_callbacks: List[Callable] = []
        self.failure_callbacks: List[Callable] = []
        
        logger.info(
            f"Initialized ShadowDeploymentManager: "
            f"max_policies={max_shadow_policies}, async={enable_async}"
        )
        
    def add_shadow_policy(
        self,
        policy_id: str,
        name: str,
        bridge: RLBanditBridge,
        traffic_percentage: float = 0.0,
        description: str = ""
    ) -> ShadowPolicy:
        with self.shadow_lock:
            if len(self.shadow_policies) >= self.max_shadow_policies:
                raise ValueError(f"Maximum {self.max_shadow_policies} shadow policies allowed")
                
            if policy_id in self.shadow_policies:
                raise ValueError(f"Policy {policy_id} already exists")
                
            policy = ShadowPolicy(
                policy_id=policy_id,
                name=name,
                description=description,
                bridge=bridge,
                traffic_percentage=traffic_percentage
            )
            
            self.shadow_policies[policy_id] = policy
            
        logger.info(f"Added shadow policy: {policy_id} ({name})")
        return policy
        
    def process_request(
        self,
        query: str,
        query_type: str,
        query_context: QueryContext,
        user_context: Optional[Dict] = None,
        system_metrics: Optional[Dict] = None
    ) -> Tuple[HierarchicalDecision, Optional[List[ShadowResult]]]:
        self.total_requests += 1
        
        production_decision = self.production_bridge.select_strategy(
            query=query,
            query_type=query_type,
            query_context=query_context,
            user_context=user_context,
            system_metrics=system_metrics
        )
        
        if self.mode == ShadowMode.DISABLED:
            return production_decision, None
            
        if not self._should_shadow_test():
            return production_decision, None
            
        self.shadow_requests += 1
        active_policies = self._get_active_policies()
        
        if not active_policies:
            return production_decision, None
            
        shadow_results = []
        for policy in active_policies:
            try:
                result = self._execute_shadow_policy(
                    policy, query, query_type, query_context,
                    user_context, system_metrics, production_decision
                )
                if result:
                    shadow_results.append(result)
            except Exception as e:
                logger.error(f"Shadow policy execution failed: {e}")
                self.error_count += 1
                
        return production_decision, shadow_results
        
    def _should_shadow_test(self) -> bool:
        import random
        if self.mode == ShadowMode.DISABLED:
            return False
        return random.random() * 100 <= self.global_traffic_percentage
        
    def _get_active_policies(self) -> List[ShadowPolicy]:
        with self.shadow_lock:
            active = []
            for policy in self.shadow_policies.values():
                if policy.enabled:
                    import random
                    if random.random() * 100 <= policy.traffic_percentage:
                        active.append(policy)
            return active
            
    def _execute_shadow_policy(
        self,
        policy: ShadowPolicy,
        query: str,
        query_type: str,
        query_context: QueryContext,
        user_context: Optional[Dict],
        system_metrics: Optional[Dict],
        production_decision: HierarchicalDecision
    ) -> Optional[ShadowResult]:
        try:
            shadow_decision = policy.bridge.select_strategy(
                query=query,
                query_type=query_type,
                query_context=query_context,
                user_context=user_context,
                system_metrics=system_metrics
            )
            
            production_result = self._simulate_retrieval_result(production_decision)
            shadow_result = self._simulate_retrieval_result(shadow_decision)
            
            comparison_metrics = self._compare_results(
                production_decision, shadow_decision,
                production_result, shadow_result
            )
            
            result = ShadowResult(
                query_id=f"query_{time.time()}_{hash(query) % 10000}",
                production_decision=production_decision,
                shadow_decision=shadow_decision,
                production_result=production_result,
                shadow_result=shadow_result,
                comparison_metrics=comparison_metrics,
                timestamp=time.time(),
                metadata={"policy_id": policy.policy_id}
            )
            
            with self.results_lock:
                self.shadow_results.append(result)
                if len(self.shadow_results) > 10000:
                    self.shadow_results = self.shadow_results[-5000:]
                    
            self.comparison_count += 1
            return result
            
        except Exception as e:
            logger.error(f"Shadow policy {policy.policy_id} failed: {e}")
            return None
            
    def _simulate_retrieval_result(self, decision: HierarchicalDecision) -> RetrievalResult:
        import numpy as np
        return RetrievalResult(
            documents=[{"id": i, "score": 0.8 - i*0.1} for i in range(5)],
            relevance_scores=np.array([0.8, 0.7, 0.6, 0.5, 0.4]),
            diversity_score=0.7,
            latency=100.0 + np.random.normal(0, 20),
            strategy_used=decision.final_strategy["name"]
        )
        
    def _compare_results(
        self,
        prod_decision: HierarchicalDecision,
        shadow_decision: HierarchicalDecision,
        prod_result: RetrievalResult,
        shadow_result: RetrievalResult
    ) -> Dict[str, float]:
        metrics = {}
        metrics["decision_agreement"] = 1.0 if prod_decision.rl_action == shadow_decision.rl_action else 0.0
        metrics["bandit_agreement"] = 1.0 if prod_decision.bandit_arm == shadow_decision.bandit_arm else 0.0
        metrics["latency_diff"] = shadow_result.latency - prod_result.latency
        metrics["latency_ratio"] = shadow_result.latency / max(prod_result.latency, 1.0)
        metrics["diversity_diff"] = shadow_result.diversity_score - prod_result.diversity_score
        return metrics
        
    def get_statistics(self) -> Dict[str, Any]:
        with self.shadow_lock:
            active_policies = sum(1 for p in self.shadow_policies.values() if p.enabled)
            
        return {
            "mode": self.mode.value,
            "global_traffic_percentage": self.global_traffic_percentage,
            "total_policies": len(self.shadow_policies),
            "active_policies": active_policies,
            "total_requests": self.total_requests,
            "shadow_requests": self.shadow_requests,
            "comparison_count": self.comparison_count,
            "error_count": self.error_count,
            "shadow_rate": self.shadow_requests / max(self.total_requests, 1) * 100,
        }
        

    def add_shadow_policy(
        self,
        policy_id: str,
        name: str,
        version: str,
        bridge: RLBanditBridge,
        traffic_percentage: float = 0.0,
        description: str = "",
        **kwargs
    ) -> ShadowPolicy:
        """
        Add new shadow policy
        
        Args:
            policy_id: Unique policy identifier
            name: Policy name
            version: Policy version
            bridge: RL-Bandit bridge for shadow policy
            traffic_percentage: Initial traffic percentage
            description: Policy description
            **kwargs: Additional policy parameters
            
        Returns:
            Created shadow policy
        """
        with self.shadow_lock:
            if len(self.shadow_policies) >= self.max_shadow_policies:
                raise ValueError(
                    f"Maximum {self.max_shadow_policies} shadow policies reached"
                )
                
            if policy_id in self.shadow_policies:
                raise ValueError(f"Policy {policy_id} already exists")
                
            policy = ShadowPolicy(
                policy_id=policy_id,
                name=name,
                version=version,
                description=description,
                bridge=bridge,
                traffic_percentage=traffic_percentage,
                **kwargs
            )
            
            self.shadow_policies[policy_id] = policy
            self.policy_results[policy_id] = []
            
        logger.info(
            f"Added shadow policy: {policy_id} (v{version}) - {name}, "
            f"traffic={traffic_percentage}%"
        )
        
        log_metric(
            measurement="shadow_policy_added",
            fields={"traffic_percentage": traffic_percentage},
            tags={"policy_id": policy_id, "version": version}
        )
        
        return policy
        
    def remove_shadow_policy(self, policy_id: str):
        """Remove shadow policy"""
        with self.shadow_lock:
            if policy_id not in self.shadow_policies:
                raise ValueError(f"Policy {policy_id} not found")
                
            policy = self.shadow_policies.pop(policy_id)
            
        logger.info(f"Removed shadow policy: {policy_id}")
        
        log_metric(
            measurement="shadow_policy_removed",
            fields={"count": 1.0},
            tags={"policy_id": policy_id}
        )
        
    def update_policy_traffic(self, policy_id: str, traffic_percentage: float):
        """Update policy traffic percentage"""
        with self.shadow_lock:
            if policy_id not in self.shadow_policies:
                raise ValueError(f"Policy {policy_id} not found")
                
            old_traffic = self.shadow_policies[policy_id].traffic_percentage
            self.shadow_policies[policy_id].traffic_percentage = traffic_percentage
            self.shadow_policies[policy_id].updated_at = time.time()
            
        logger.info(
            f"Updated policy {policy_id} traffic: {old_traffic}% → {traffic_percentage}%"
        )
        
    def process_request(
        self,
        query: str,
        query_type: str,
        query_context: QueryContext,
        user_context: Optional[Dict] = None,
        system_metrics: Optional[Dict] = None,
        execute_retrieval: Optional[Callable] = None
    ) -> Tuple[HierarchicalDecision, Optional[RetrievalResult], Optional[List[ShadowResult]]]:
        """
        Process request with shadow testing
        
        Args:
            query: Query text
            query_type: Query type
            query_context: Query context
            user_context: User context
            system_metrics: System metrics
            execute_retrieval: Optional function to execute actual retrieval
            
        Returns:
            (production_decision, production_result, shadow_results)
        """
        start_time = time.time()
        self.total_requests += 1
        
        # Execute production decision
        production_decision = self.production_bridge.select_strategy(
            query=query,
            query_type=query_type,
            query_context=query_context,
            user_context=user_context,
            system_metrics=system_metrics
        )
        
        # Execute production retrieval if function provided
        production_result = None
        if execute_retrieval:
            try:
                production_result = execute_retrieval(production_decision)
            except Exception as e:
                logger.error(f"Production retrieval failed: {e}")
                
        production_latency = (time.time() - start_time) * 1000
        self.latency_samples.append(production_latency)
        
        # Check if shadow testing should be performed
        if not self._should_shadow_test(query_type):
            return production_decision, production_result, None
            
        self.shadow_requests += 1
        
        # Get active shadow policies
        active_policies = self._get_active_policies()
        
        if not active_policies:
            return production_decision, production_result, None
            
        # Execute shadow policies
        shadow_results = []
        
        if self.enable_async and self.executor:
            # Async execution
            futures = []
            for policy in active_policies:
                future = self.executor.submit(
                    self._execute_shadow_policy,
                    policy, query, query_type, query_context,
                    user_context, system_metrics, production_decision,
                    production_result, execute_retrieval
                )
                futures.append((policy, future))
                
            # Collect results with timeout
            for policy, future in futures:
                try:
                    result = future.result(timeout=self.comparison_timeout)
                    if result:
                        shadow_results.append(result)
                except TimeoutError:
                    logger.warning(f"Shadow policy {policy.policy_id} timed out")
                    self.timeout_count += 1
                    policy.failed_requests += 1
                except Exception as e:
                    logger.error(f"Shadow policy {policy.policy_id} failed: {e}")
                    self.error_count += 1
                    policy.failed_requests += 1
        else:
            # Sync execution
            for policy in active_policies:
                try:
                    result = self._execute_shadow_policy(
                        policy, query, query_type, query_context,
                        user_context, system_metrics, production_decision,
                        production_result, execute_retrieval
                    )
                    if result:
                        shadow_results.append(result)
                except Exception as e:
                    logger.error(f"Shadow policy {policy.policy_id} failed: {e}")
                    self.error_count += 1
                    policy.failed_requests += 1
                    
        comparison_latency = (time.time() - start_time) * 1000
        self.comparison_latency_samples.append(comparison_latency)
        
        # Log metrics
        log_metric(
            measurement="shadow_request",
            fields={
                "production_latency_ms": production_latency,
                "comparison_latency_ms": comparison_latency,
                "shadow_policies_count": len(shadow_results),
            },
            tags={"query_type": query_type}
        )
        
        return production_decision, production_result, shadow_results
        
    def _should_shadow_test(self, query_type: str) -> bool:
        """Determine if request should be shadow tested"""
        if self.mode == ShadowMode.DISABLED:
            return False
            
        # Apply sampling strategy
        sampling_func = self.sampling_strategies.get(
            self.current_sampling_strategy,
            self._random_sampling
        )
        
        return sampling_func(query_type)
        
    def _random_sampling(self, query_type: str) -> bool:
        """Random sampling"""
        import random
        return random.random() * 100 <= self.global_traffic_percentage
        
    def _stratified_sampling(self, query_type: str) -> bool:
        """Stratified sampling by query type"""
        # Ensure each query type gets proportional sampling
        import random
        type_weights = {"legal": 1.0, "factual": 1.0, "procedural": 1.0}
        weight = type_weights.get(query_type, 1.0)
        return random.random() * 100 <= (self.global_traffic_percentage * weight)
        
    def _importance_sampling(self, query_type: str) -> bool:
        """Importance sampling - prioritize uncertain queries"""
        # In practice, would use uncertainty estimates
        import random
        return random.random() * 100 <= self.global_traffic_percentage
        
    def _get_active_policies(self) -> List[ShadowPolicy]:
        """Get active shadow policies for this request"""
        with self.shadow_lock:
            active = []
            for policy in self.shadow_policies.values():
                if not policy.enabled:
                    continue
                    
                # Check traffic percentage
                import random
                if random.random() * 100 <= policy.traffic_percentage:
                    active.append(policy)
                    
            return active
            
    def _execute_shadow_policy(
        self,
        policy: ShadowPolicy,
        query: str,
        query_type: str,
        query_context: QueryContext,
        user_context: Optional[Dict],
        system_metrics: Optional[Dict],
        production_decision: HierarchicalDecision,
        production_result: Optional[RetrievalResult],
        execute_retrieval: Optional[Callable]
    ) -> Optional[ShadowResult]:
        """Execute shadow policy and compare with production"""
        start_time = time.time()
        
        try:
            # Execute shadow decision
            shadow_decision = policy.bridge.select_strategy(
                query=query,
                query_type=query_type,
                query_context=query_context,
                user_context=user_context,
                system_metrics=system_metrics
            )
            
            # Execute shadow retrieval if function provided
            shadow_result = None
            if execute_retrieval and self.mode == ShadowMode.FULL_SHADOW:
                try:
                    shadow_result = execute_retrieval(shadow_decision)
                except Exception as e:
                    logger.error(f"Shadow retrieval failed: {e}")
                    
            execution_time = (time.time() - start_time) * 1000
            
            # Compare results
            comparison_metrics = self._compare_results(
                production_decision, shadow_decision,
                production_result, shadow_result
            )
            
            # Create result
            result = ShadowResult(
                query_id=f"query_{int(time.time()*1000)}_{hash(query) % 100000}",
                production_decision=production_decision,
                shadow_decision=shadow_decision,
                production_result=production_result,
                shadow_result=shadow_result,
                comparison_metrics=comparison_metrics,
                execution_time_ms=execution_time,
                timestamp=time.time(),
                metadata={
                    "policy_id": policy.policy_id,
                    "policy_version": policy.version,
                    "query_type": query_type,
                }
            )
            
            # Store result
            with self.results_lock:
                self.shadow_results.append(result)
                self.policy_results[policy.policy_id].append(result)
                
                # Keep only recent results per policy
                if len(self.policy_results[policy.policy_id]) > 10000:
                    self.policy_results[policy.policy_id] = \
                        self.policy_results[policy.policy_id][-5000:]
                        
            # Update policy metrics
            policy.total_requests += 1
            policy.successful_requests += 1
            policy.avg_latency_ms = (
                (policy.avg_latency_ms * (policy.total_requests - 1) + execution_time) /
                policy.total_requests
            )
            
            self.comparison_count += 1
            
            # Check for auto-promotion
            if self.enable_auto_promotion:
                self._check_auto_promotion(policy)
                
            return result
            
        except Exception as e:
            logger.error(f"Shadow policy {policy.policy_id} execution failed: {e}")
            policy.failed_requests += 1
            return None
            
    def _compare_results(
        self,
        prod_decision: HierarchicalDecision,
        shadow_decision: HierarchicalDecision,
        prod_result: Optional[RetrievalResult],
        shadow_result: Optional[RetrievalResult]
    ) -> Dict[str, float]:
        """Compare production and shadow results"""
        metrics = {}
        
        # Decision comparison
        metrics["rl_action_agreement"] = float(
            prod_decision.rl_action == shadow_decision.rl_action
        )
        metrics["bandit_arm_agreement"] = float(
            prod_decision.bandit_arm == shadow_decision.bandit_arm
        )
        metrics["strategy_agreement"] = float(
            prod_decision.final_strategy["name"] == shadow_decision.final_strategy["name"]
        )
        metrics["rl_confidence_diff"] = abs(
            prod_decision.rl_confidence - shadow_decision.rl_confidence
        )
        
        # Result comparison (if available)
        if prod_result and shadow_result:
            metrics["latency_diff_ms"] = shadow_result.latency - prod_result.latency
            metrics["latency_ratio"] = shadow_result.latency / max(prod_result.latency, 1.0)
            metrics["diversity_diff"] = shadow_result.diversity_score - prod_result.diversity_score
            
            # Document overlap
            if prod_result.documents and shadow_result.documents:
                prod_ids = {doc.get("id") for doc in prod_result.documents}
                shadow_ids = {doc.get("id") for doc in shadow_result.documents}
                overlap = len(prod_ids & shadow_ids) / max(len(prod_ids), 1)
                metrics["document_overlap"] = overlap
                
        return metrics
        
    def _check_auto_promotion(self, policy: ShadowPolicy):
        """Check if policy should be auto-promoted"""
        if policy.status != PolicyStatus.TESTING:
            return
            
        if policy.total_requests < policy.min_requests_for_promotion:
            return
            
        # Calculate metrics
        results = self.policy_results.get(policy.policy_id, [])
        if not results:
            return
            
        # Decision agreement rate
        agreement_rates = [
            r.comparison_metrics.get("strategy_agreement", 0.0)
            for r in results[-1000:]
        ]
        avg_agreement = np.mean(agreement_rates)
        
        # Error rate
        error_rate = policy.failed_requests / max(policy.total_requests, 1)
        
        # Performance improvement
        latency_diffs = [
            r.comparison_metrics.get("latency_diff_ms", 0.0)
            for r in results[-1000:]
            if "latency_diff_ms" in r.comparison_metrics
        ]
        avg_latency_improvement = -np.mean(latency_diffs) if latency_diffs else 0.0
        
        # Check promotion criteria
        if (avg_agreement >= policy.min_agreement_rate and
            error_rate <= policy.max_error_rate and
            avg_latency_improvement >= policy.min_performance_improvement):
            
            self._promote_policy(policy)
        elif error_rate > policy.max_error_rate * 2:
            self._fail_policy(policy)
            
    def _promote_policy(self, policy: ShadowPolicy):
        """Promote shadow policy"""
        policy.status = PolicyStatus.VALIDATED
        policy.updated_at = time.time()
        
        logger.info(f"Policy {policy.policy_id} promoted to VALIDATED")
        
        log_metric(
            measurement="shadow_policy_promoted",
            fields={"count": 1.0},
            tags={"policy_id": policy.policy_id}
        )
        
        # Trigger callbacks
        for callback in self.promotion_callbacks:
            try:
                callback(policy)
            except Exception as e:
                logger.error(f"Promotion callback failed: {e}")
                
    def _fail_policy(self, policy: ShadowPolicy):
        """Mark policy as failed"""
        policy.status = PolicyStatus.FAILED
        policy.enabled = False
        policy.updated_at = time.time()
        
        logger.warning(f"Policy {policy.policy_id} marked as FAILED")
        
        log_metric(
            measurement="shadow_policy_failed",
            fields={"count": 1.0},
            tags={"policy_id": policy.policy_id}
        )
        
        # Trigger callbacks
        for callback in self.failure_callbacks:
            try:
                callback(policy)
            except Exception as e:
                logger.error(f"Failure callback failed: {e}")
                
    def generate_comparison_report(
        self,
        policy_id: str,
        min_samples: int = 100
    ) -> Optional[ComparisonReport]:
        """
        Generate detailed comparison report for a policy
        
        Args:
            policy_id: Policy ID
            min_samples: Minimum samples required
            
        Returns:
            Comparison report or None
        """
        results = self.policy_results.get(policy_id, [])
        
        if len(results) < min_samples:
            logger.warning(
                f"Insufficient samples for report: {len(results)} < {min_samples}"
            )
            return None
            
        # Extract metrics
        decision_agreements = [
            r.comparison_metrics.get("strategy_agreement", 0.0)
            for r in results
        ]
        strategy_agreements = [
            r.comparison_metrics.get("strategy_agreement", 0.0)
            for r in results
        ]
        latency_diffs = [
            r.comparison_metrics.get("latency_diff_ms", 0.0)
            for r in results
            if "latency_diff_ms" in r.comparison_metrics
        ]
        
        # Calculate statistics
        decision_agreement_rate = np.mean(decision_agreements)
        strategy_agreement_rate = np.mean(strategy_agreements)
        avg_latency_diff = np.mean(latency_diffs) if latency_diffs else 0.0
        
        # Latency improvement percentage
        prod_latencies = [
            r.production_result.latency
            for r in results
            if r.production_result
        ]
        shadow_latencies = [
            r.shadow_result.latency
            for r in results
            if r.shadow_result
        ]
        
        if prod_latencies and shadow_latencies:
            latency_improvement_pct = (
                (np.mean(prod_latencies) - np.mean(shadow_latencies)) /
                np.mean(prod_latencies) * 100
            )
        else:
            latency_improvement_pct = 0.0
            
        # Statistical significance tests
        statistical_significance = {}
        
        if len(latency_diffs) > 30:
            # T-test for latency difference
            t_stat, p_value = stats.ttest_1samp(latency_diffs, 0)
            statistical_significance["latency_ttest_pvalue"] = p_value
            statistical_significance["latency_significant"] = float(
                p_value < (1 - self.statistical_confidence)
            )
            
        # Generate recommendation
        recommendation, confidence = self._generate_recommendation(
            decision_agreement_rate,
            latency_improvement_pct,
            statistical_significance
        )
        
        report = ComparisonReport(
            policy_id=policy_id,
            total_comparisons=len(results),
            decision_agreement_rate=decision_agreement_rate,
            strategy_agreement_rate=strategy_agreement_rate,
            avg_latency_diff_ms=avg_latency_diff,
            latency_improvement_pct=latency_improvement_pct,
            accuracy_diff=0.0,  # Would need actual accuracy data
            diversity_diff=0.0,  # Would need actual diversity data
            statistical_significance=statistical_significance,
            recommendation=recommendation,
            confidence=confidence,
            timestamp=time.time()
        )
        
        logger.info(
            f"Generated comparison report for {policy_id}: "
            f"agreement={decision_agreement_rate:.2%}, "
            f"latency_improvement={latency_improvement_pct:.1f}%, "
            f"recommendation={recommendation}"
        )
        
        return report
        
    def _generate_recommendation(
        self,
        agreement_rate: float,
        latency_improvement: float,
        statistical_significance: Dict[str, float]
    ) -> Tuple[str, float]:
        """Generate recommendation based on metrics"""
        confidence = 0.0
        
        # High agreement and improvement
        if agreement_rate > 0.9 and latency_improvement > 10:
            recommendation = "PROMOTE"
            confidence = 0.95
        elif agreement_rate > 0.8 and latency_improvement > 5:
            recommendation = "PROMOTE"
            confidence = 0.85
        # High agreement, neutral performance
        elif agreement_rate > 0.85 and abs(latency_improvement) < 5:
            recommendation = "CONTINUE_TESTING"
            confidence = 0.7
        # Low agreement
        elif agreement_rate < 0.7:
            recommendation = "REJECT"
            confidence = 0.9
        # Negative performance
        elif latency_improvement < -10:
            recommendation = "REJECT"
            confidence = 0.85
        else:
            recommendation = "CONTINUE_TESTING"
            confidence = 0.6
            
        return recommendation, confidence
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get comprehensive statistics"""
        with self.shadow_lock:
            active_policies = sum(1 for p in self.shadow_policies.values() if p.enabled)
            policy_stats = {
                pid: {
                    "status": p.status.value,
                    "total_requests": p.total_requests,
                    "success_rate": p.successful_requests / max(p.total_requests, 1),
                    "avg_latency_ms": p.avg_latency_ms,
                    "traffic_percentage": p.traffic_percentage,
                }
                for pid, p in self.shadow_policies.items()
            }
            
        return {
            "mode": self.mode.value,
            "global_traffic_percentage": self.global_traffic_percentage,
            "sampling_strategy": self.current_sampling_strategy,
            "total_policies": len(self.shadow_policies),
            "active_policies": active_policies,
            "total_requests": self.total_requests,
            "shadow_requests": self.shadow_requests,
            "comparison_count": self.comparison_count,
            "error_count": self.error_count,
            "timeout_count": self.timeout_count,
            "shadow_rate_pct": self.shadow_requests / max(self.total_requests, 1) * 100,
            "avg_production_latency_ms": np.mean(self.latency_samples) if self.latency_samples else 0,
            "avg_comparison_latency_ms": np.mean(self.comparison_latency_samples) if self.comparison_latency_samples else 0,
            "policies": policy_stats,
        }
        
    def register_promotion_callback(self, callback: Callable):
        """Register callback for policy promotion"""
        self.promotion_callbacks.append(callback)
        
    def register_failure_callback(self, callback: Callable):
        """Register callback for policy failure"""
        self.failure_callbacks.append(callback)
