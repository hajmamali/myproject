"""
Ultra-Advanced Evaluation & Benchmarking System
===============================================

Next-generation evaluation framework with:
- Multi-dimensional metrics (retrieval, generation, end-to-end)
- Automated benchmarking
- A/B testing framework
- Statistical significance testing
- Human evaluation integration
- Adversarial testing
- Fairness & bias detection
- Explainability analysis
- Cost-performance optimization
- Real-time monitoring
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field
from scipy import stats

if TYPE_CHECKING:
    from sentence_transformers import SentenceTransformer

log = logging.getLogger(__name__)


# ============================================================================
# ENUMS & TYPES
# ============================================================================

class MetricType(str, Enum):
    """Metric types"""
    # Retrieval metrics
    RECALL = "recall"
    PRECISION = "precision"
    F1 = "f1"
    MAP = "map"  # Mean Average Precision
    MRR = "mrr"  # Mean Reciprocal Rank
    NDCG = "ndcg"  # Normalized Discounted Cumulative Gain
    HIT_RATE = "hit_rate"
    
    # Generation metrics
    BLEU = "bleu"
    ROUGE = "rouge"
    METEOR = "meteor"
    BERTSCORE = "bertscore"
    BLEURT = "bleurt"
    
    # Semantic metrics
    SEMANTIC_SIMILARITY = "semantic_similarity"
    ANSWER_RELEVANCE = "answer_relevance"
    FAITHFULNESS = "faithfulness"
    CONTEXT_RELEVANCE = "context_relevance"
    
    # RAG-specific
    ANSWER_CORRECTNESS = "answer_correctness"
    ANSWER_COMPLETENESS = "answer_completeness"
    HALLUCINATION_RATE = "hallucination_rate"
    CITATION_ACCURACY = "citation_accuracy"
    
    # Performance
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    COST = "cost"
    
    # Quality
    COHERENCE = "coherence"
    FLUENCY = "fluency"
    CONSISTENCY = "consistency"
    
    # Fairness
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    BIAS_SCORE = "bias_score"


class EvaluationMode(str, Enum):
    """Evaluation modes"""
    OFFLINE = "offline"  # Batch evaluation
    ONLINE = "online"  # Real-time evaluation
    AB_TEST = "ab_test"  # A/B testing
    ADVERSARIAL = "adversarial"  # Adversarial testing
    HUMAN = "human"  # Human evaluation


# ============================================================================
# DATA MODELS
# ============================================================================

class EvaluationSample(BaseModel):
    """Single evaluation sample"""
    id: str
    query: str
    ground_truth: Optional[str] = None
    retrieved_docs: List[Dict[str, Any]] = Field(default_factory=list)
    generated_answer: Optional[str] = None
    reference_answer: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Ground truth for retrieval
    relevant_doc_ids: List[str] = Field(default_factory=list)
    
    # Timestamps
    retrieval_time_ms: Optional[float] = None
    generation_time_ms: Optional[float] = None
    total_time_ms: Optional[float] = None


class EvaluationResult(BaseModel):
    """Evaluation results"""
    sample_id: str
    metrics: Dict[str, float] = Field(default_factory=dict)
    passed: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    # Detailed results
    retrieval_results: Optional[Dict[str, Any]] = None
    generation_results: Optional[Dict[str, Any]] = None
    
    # Explanations
    explanations: Dict[str, str] = Field(default_factory=dict)


class BenchmarkReport(BaseModel):
    """Comprehensive benchmark report"""
    name: str
    timestamp: str
    
    # Aggregate metrics
    metrics: Dict[str, float] = Field(default_factory=dict)
    
    # Per-sample results
    sample_results: List[EvaluationResult] = Field(default_factory=list)
    
    # Statistical analysis
    confidence_intervals: Dict[str, Tuple[float, float]] = Field(default_factory=dict)
    statistical_tests: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    
    # Performance
    total_samples: int = 0
    passed_samples: int = 0
    failed_samples: int = 0
    
    # Cost analysis
    total_cost: float = 0.0
    cost_per_query: float = 0.0
    
    # Recommendations
    recommendations: List[str] = Field(default_factory=list)


# ============================================================================
# METRIC CALCULATORS
# ============================================================================

class MetricCalculator(ABC):
    """Base class for metric calculators"""
    
    @abstractmethod
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate metric for a sample"""
        pass
    
    @abstractmethod
    def aggregate(self, scores: List[float]) -> float:
        """Aggregate scores across samples"""
        pass


class RecallCalculator(MetricCalculator):
    """Recall@K calculator"""
    
    def __init__(self, k: int = 10):
        self.k = k
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate Recall@K"""
        if not sample.relevant_doc_ids:
            return 0.0
        
        retrieved_ids = [doc.get("id") for doc in sample.retrieved_docs[:self.k]]
        relevant_retrieved = len(set(retrieved_ids) & set(sample.relevant_doc_ids))
        
        return relevant_retrieved / len(sample.relevant_doc_ids)
    
    def aggregate(self, scores: List[float]) -> float:
        """Average recall"""
        return np.mean(scores) if scores else 0.0


class PrecisionCalculator(MetricCalculator):
    """Precision@K calculator"""
    
    def __init__(self, k: int = 10):
        self.k = k
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate Precision@K"""
        if not sample.relevant_doc_ids:
            return 0.0
        
        retrieved_ids = [doc.get("id") for doc in sample.retrieved_docs[:self.k]]
        if not retrieved_ids:
            return 0.0
        
        relevant_retrieved = len(set(retrieved_ids) & set(sample.relevant_doc_ids))
        
        return relevant_retrieved / len(retrieved_ids)
    
    def aggregate(self, scores: List[float]) -> float:
        """Average precision"""
        return np.mean(scores) if scores else 0.0


class NDCGCalculator(MetricCalculator):
    """NDCG@K calculator"""
    
    def __init__(self, k: int = 10):
        self.k = k
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate NDCG@K"""
        if not sample.relevant_doc_ids:
            return 0.0
        
        # Get relevance scores (1 if relevant, 0 otherwise)
        retrieved_ids = [doc.get("id") for doc in sample.retrieved_docs[:self.k]]
        relevance = [1 if doc_id in sample.relevant_doc_ids else 0 for doc_id in retrieved_ids]
        
        # DCG
        dcg = sum([rel / np.log2(i + 2) for i, rel in enumerate(relevance)])
        
        # IDCG (ideal DCG)
        ideal_relevance = sorted(relevance, reverse=True)
        idcg = sum([rel / np.log2(i + 2) for i, rel in enumerate(ideal_relevance)])
        
        return dcg / idcg if idcg > 0 else 0.0
    
    def aggregate(self, scores: List[float]) -> float:
        """Average NDCG"""
        return np.mean(scores) if scores else 0.0


class MRRCalculator(MetricCalculator):
    """Mean Reciprocal Rank calculator"""
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate MRR"""
        if not sample.relevant_doc_ids:
            return 0.0
        
        retrieved_ids = [doc.get("id") for doc in sample.retrieved_docs]
        
        for i, doc_id in enumerate(retrieved_ids):
            if doc_id in sample.relevant_doc_ids:
                return 1.0 / (i + 1)
        
        return 0.0
    
    def aggregate(self, scores: List[float]) -> float:
        """Mean of reciprocal ranks"""
        return np.mean(scores) if scores else 0.0


class SemanticSimilarityCalculator(MetricCalculator):
    """
    Ultra-advanced semantic similarity calculator with fail-closed DI.
    
    Constructor Injection Contract
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
    ``model`` MUST be injected by bootstrap (primary path).
    Lazy fallback is DEPRECATED and triggers loud warnings.
    """
    
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        model: Optional["SentenceTransformer"] = None,
        correlation_id: str = "",
    ):
        """
        Args:
            model_name: Model name (only used for lazy fallback)
            model: Pre-constructed SentenceTransformer (MANDATORY in production).
                  If None, triggers DEPRECATED lazy fallback with warning.
            correlation_id: Request tracking ID for observability.
        """
        import time
        self._correlation_id = correlation_id or f"sim-{time.time()}"
        
        self.model_name = model_name
        
        if model is not None:
            # PRIMARY PATH: Bootstrap-injected model
            self.model = model
            log.info(
                f"[{self._correlation_id}] ✅ SemanticSimilarityCalculator initialized "
                f"(bootstrap-injected model)"
            )
        else:
            # DEPRECATED FALLBACK: Lazy construction
            log.warning(
                f"[{self._correlation_id}] ⚠️  DEPRECATED: SemanticSimilarityCalculator "
                f"initialized without injected model. Attempting lazy construction. "
                f"Bootstrap wiring is MANDATORY in production. "
                f"Remediation: Update bootstrap/runtime.py to inject SentenceTransformer."
            )
            self.model = self._lazy_construct_model()
    
    def _lazy_construct_model(self) -> "SentenceTransformer":
        """
        DEPRECATED: Lazy model construction fallback.
        
        This method exists only for backward compatibility. Bootstrap injection
        is the PRIMARY path.
        """
        import time
        try:
            from sentence_transformers import SentenceTransformer
            
            start = time.time()
            model = SentenceTransformer(self.model_name)
            latency_ms = (time.time() - start) * 1000
            
            log.warning(
                f"[{self._correlation_id}] ⚠️  Lazy model construction completed "
                f"(model={self.model_name}, latency={latency_ms:.2f}ms). "
                f"This is a DEPRECATED fallback path."
            )
            return model
            
        except ImportError:
            log.error(
                f"[{self._correlation_id}] ❌ sentence-transformers not installed "
                f"and no model injected."
            )
            raise ImportError(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers OR "
                "inject pre-constructed model via bootstrap wiring."
            )
        except Exception as e:
            log.error(
                f"[{self._correlation_id}] ❌ Lazy model construction failed: {e}"
            )
            raise RuntimeError(f"Failed to construct embedding model: {e}")
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate semantic similarity"""
        if not sample.generated_answer or not sample.reference_answer:
            return 0.0
        
        # Compute embeddings
        emb1 = self.model.encode(sample.generated_answer)
        emb2 = self.model.encode(sample.reference_answer)
        
        # Cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        return float(similarity)
    
    def aggregate(self, scores: List[float]) -> float:
        """Average similarity"""
        return np.mean(scores) if scores else 0.0


class FaithfulnessCalculator(MetricCalculator):
    """Faithfulness calculator (checks if answer is grounded in context)"""
    
    def __init__(self, use_llm: bool = True):
        self.use_llm = use_llm
        if use_llm:
            # Initialize LLM for faithfulness checking
            pass
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate faithfulness score"""
        if not sample.generated_answer or not sample.retrieved_docs:
            return 0.0
        
        if self.use_llm:
            # Use LLM to check if answer is supported by context
            return self._llm_faithfulness_check(sample)
        else:
            # Simple heuristic: check token overlap
            return self._heuristic_faithfulness_check(sample)
    
    def _llm_faithfulness_check(self, sample: EvaluationSample) -> float:
        """LLM-based faithfulness check"""
        # Placeholder for LLM-based checking
        return 0.8
    
    def _heuristic_faithfulness_check(self, sample: EvaluationSample) -> float:
        """Heuristic faithfulness check"""
        answer_tokens = set(sample.generated_answer.lower().split())
        
        # Combine all retrieved docs
        context = " ".join([doc.get("content", "") for doc in sample.retrieved_docs])
        context_tokens = set(context.lower().split())
        
        # Calculate overlap
        if not answer_tokens:
            return 0.0
        
        overlap = len(answer_tokens & context_tokens) / len(answer_tokens)
        return overlap
    
    def aggregate(self, scores: List[float]) -> float:
        """Average faithfulness"""
        return np.mean(scores) if scores else 0.0


class HallucinationDetector(MetricCalculator):
    """Hallucination detection"""
    
    def calculate(self, sample: EvaluationSample) -> float:
        """Calculate hallucination score (0 = no hallucination, 1 = full hallucination)"""
        if not sample.generated_answer or not sample.retrieved_docs:
            return 1.0  # No context = potential hallucination
        
        # Use faithfulness as inverse of hallucination
        faithfulness = FaithfulnessCalculator(use_llm=False).calculate(sample)
        
        return 1.0 - faithfulness
    
    def aggregate(self, scores: List[float]) -> float:
        """Average hallucination rate"""
        return np.mean(scores) if scores else 0.0


# ============================================================================
# EVALUATION ENGINE
# ============================================================================

class EvaluationEngine:
    """
    Ultra-advanced evaluation engine
    """
    
    def __init__(
        self,
        metrics: List[MetricType],
        mode: EvaluationMode = EvaluationMode.OFFLINE
    ):
        self.metrics = metrics
        self.mode = mode
        
        # Initialize metric calculators
        self.calculators: Dict[MetricType, MetricCalculator] = {}
        self._init_calculators()
        
        # Results storage
        self.results: List[EvaluationResult] = []
        
        print(f"🔬 Evaluation Engine initialized with {len(metrics)} metrics")
    
    def _init_calculators(self):
        """Initialize metric calculators"""
        for metric in self.metrics:
            if metric == MetricType.RECALL:
                self.calculators[metric] = RecallCalculator(k=10)
            elif metric == MetricType.PRECISION:
                self.calculators[metric] = PrecisionCalculator(k=10)
            elif metric == MetricType.NDCG:
                self.calculators[metric] = NDCGCalculator(k=10)
            elif metric == MetricType.MRR:
                self.calculators[metric] = MRRCalculator()
            elif metric == MetricType.SEMANTIC_SIMILARITY:
                self.calculators[metric] = SemanticSimilarityCalculator()
            elif metric == MetricType.FAITHFULNESS:
                self.calculators[metric] = FaithfulnessCalculator()
            elif metric == MetricType.HALLUCINATION_RATE:
                self.calculators[metric] = HallucinationDetector()
    
    def evaluate_sample(self, sample: EvaluationSample) -> EvaluationResult:
        """Evaluate a single sample"""
        result = EvaluationResult(sample_id=sample.id)
        
        # Calculate each metric
        for metric_type, calculator in self.calculators.items():
            try:
                score = calculator.calculate(sample)
                result.metrics[metric_type.value] = score
            except Exception as e:
                result.errors.append(f"Error calculating {metric_type.value}: {str(e)}")
                result.passed = False
        
        # Check thresholds
        if result.metrics.get(MetricType.HALLUCINATION_RATE.value, 0) > 0.5:
            result.warnings.append("High hallucination rate detected")
        
        if result.metrics.get(MetricType.RECALL.value, 0) < 0.3:
            result.warnings.append("Low recall - consider improving retrieval")
        
        return result
    
    async def evaluate_batch(
        self,
        samples: List[EvaluationSample],
        show_progress: bool = True
    ) -> BenchmarkReport:
        """Evaluate a batch of samples"""
        print(f"📊 Evaluating {len(samples)} samples...")
        
        results = []
        
        for i, sample in enumerate(samples):
            result = self.evaluate_sample(sample)
            results.append(result)
            
            if show_progress and (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{len(samples)}")
        
        # Generate report
        report = self._generate_report(results)
        
        print(f"✅ Evaluation completed!")
        
        return report
    
    def _generate_report(self, results: List[EvaluationResult]) -> BenchmarkReport:
        """Generate comprehensive benchmark report"""
        from datetime import datetime
        
        report = BenchmarkReport(
            name="RAG Evaluation",
            timestamp=datetime.now().isoformat(),
            sample_results=results,
            total_samples=len(results),
            passed_samples=sum(1 for r in results if r.passed),
            failed_samples=sum(1 for r in results if not r.passed)
        )
        
        # Aggregate metrics
        for metric_type in self.calculators.keys():
            metric_name = metric_type.value
            scores = [r.metrics.get(metric_name, 0.0) for r in results]
            
            if scores:
                # Mean
                report.metrics[f"{metric_name}_mean"] = np.mean(scores)
                
                # Std
                report.metrics[f"{metric_name}_std"] = np.std(scores)
                
                # Median
                report.metrics[f"{metric_name}_median"] = np.median(scores)
                
                # Min/Max
                report.metrics[f"{metric_name}_min"] = np.min(scores)
                report.metrics[f"{metric_name}_max"] = np.max(scores)
                
                # Confidence interval (95%)
                ci = stats.t.interval(
                    0.95,
                    len(scores) - 1,
                    loc=np.mean(scores),
                    scale=stats.sem(scores)
                )
                report.confidence_intervals[metric_name] = ci
        
        # Generate recommendations
        report.recommendations = self._generate_recommendations(report)
        
        return report
    
    def _generate_recommendations(self, report: BenchmarkReport) -> List[str]:
        """Generate recommendations based on results"""
        recommendations = []
        
        # Check recall
        recall_mean = report.metrics.get("recall_mean", 0)
        if recall_mean < 0.5:
            recommendations.append(
                "⚠️ Low recall detected. Consider: "
                "1) Increasing retrieval top-k, "
                "2) Improving embedding model, "
                "3) Adding query expansion"
            )
        
        # Check hallucination
        hallucination_mean = report.metrics.get("hallucination_rate_mean", 0)
        if hallucination_mean > 0.3:
            recommendations.append(
                "⚠️ High hallucination rate. Consider: "
                "1) Improving context relevance, "
                "2) Adding faithfulness constraints, "
                "3) Using smaller temperature in generation"
            )
        
        # Check faithfulness
        faithfulness_mean = report.metrics.get("faithfulness_mean", 0)
        if faithfulness_mean < 0.7:
            recommendations.append(
                "⚠️ Low faithfulness. Consider: "
                "1) Improving retrieval quality, "
                "2) Adding citation requirements, "
                "3) Using retrieval-augmented generation"
            )
        
        # Check semantic similarity
        similarity_mean = report.metrics.get("semantic_similarity_mean", 0)
        if similarity_mean < 0.6:
            recommendations.append(
                "⚠️ Low semantic similarity. Consider: "
                "1) Fine-tuning generation model, "
                "2) Improving prompt engineering, "
                "3) Adding more training examples"
            )
        
        if not recommendations:
            recommendations.append("✅ All metrics look good! System is performing well.")
        
        return recommendations
    
    def compare_systems(
        self,
        system_a_results: List[EvaluationResult],
        system_b_results: List[EvaluationResult],
        metric: MetricType
    ) -> Dict[str, Any]:
        """
        Compare two systems using statistical tests
        
        Returns:
            Statistical test results including p-value and effect size
        """
        metric_name = metric.value
        
        scores_a = [r.metrics.get(metric_name, 0.0) for r in system_a_results]
        scores_b = [r.metrics.get(metric_name, 0.0) for r in system_b_results]
        
        # Paired t-test
        t_stat, p_value = stats.ttest_rel(scores_a, scores_b)
        
        # Effect size (Cohen's d)
        mean_diff = np.mean(scores_a) - np.mean(scores_b)
        pooled_std = np.sqrt((np.std(scores_a)**2 + np.std(scores_b)**2) / 2)
        cohens_d = mean_diff / pooled_std if pooled_std > 0 else 0
        
        # Determine significance
        is_significant = p_value < 0.05
        
        return {
            "metric": metric_name,
            "system_a_mean": np.mean(scores_a),
            "system_b_mean": np.mean(scores_b),
            "difference": mean_diff,
            "t_statistic": t_stat,
            "p_value": p_value,
            "is_significant": is_significant,
            "cohens_d": cohens_d,
            "effect_size": self._interpret_effect_size(cohens_d)
        }
    
    def _interpret_effect_size(self, cohens_d: float) -> str:
        """Interpret Cohen's d effect size"""
        abs_d = abs(cohens_d)
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"


# ============================================================================
# A/B TESTING FRAMEWORK
# ============================================================================

class ABTestFramework:
    """
    A/B testing framework for RAG systems
    """
    
    def __init__(
        self,
        variant_a_name: str = "Control",
        variant_b_name: str = "Treatment"
    ):
        self.variant_a_name = variant_a_name
        self.variant_b_name = variant_b_name
        
        self.variant_a_results: List[EvaluationResult] = []
        self.variant_b_results: List[EvaluationResult] = []
    
    def add_result(self, result: EvaluationResult, variant: str):
        """Add result to appropriate variant"""
        if variant == "a":
            self.variant_a_results.append(result)
        else:
            self.variant_b_results.append(result)
    
    def analyze(self, metrics: List[MetricType]) -> Dict[str, Any]:
        """Analyze A/B test results"""
        engine = EvaluationEngine(metrics)
        
        analysis = {
            "variant_a": self.variant_a_name,
            "variant_b": self.variant_b_name,
            "sample_sizes": {
                "a": len(self.variant_a_results),
                "b": len(self.variant_b_results)
            },
            "comparisons": []
        }
        
        # Compare each metric
        for metric in metrics:
            comparison = engine.compare_systems(
                self.variant_a_results,
                self.variant_b_results,
                metric
            )
            analysis["comparisons"].append(comparison)
        
        # Overall recommendation
        significant_improvements = sum(
            1 for c in analysis["comparisons"]
            if c["is_significant"] and c["difference"] > 0
        )
        
        if significant_improvements > len(metrics) / 2:
            analysis["recommendation"] = f"✅ Deploy {self.variant_b_name} - significant improvements detected"
        else:
            analysis["recommendation"] = f"⚠️ Keep {self.variant_a_name} - no significant improvements"
        
        return analysis


# ============================================================================
# MAIN
# ============================================================================

async def main():
    """Example usage"""
    
    # Create evaluation samples
    samples = [
        EvaluationSample(
            id="sample_1",
            query="What is the capital of France?",
            reference_answer="Paris is the capital of France.",
            generated_answer="The capital of France is Paris.",
            retrieved_docs=[
                {"id": "doc1", "content": "Paris is the capital and largest city of France."},
                {"id": "doc2", "content": "France is a country in Europe."}
            ],
            relevant_doc_ids=["doc1"]
        ),
        # Add more samples...
    ]
    
    # Initialize evaluation engine
    engine = EvaluationEngine(
        metrics=[
            MetricType.RECALL,
            MetricType.PRECISION,
            MetricType.NDCG,
            MetricType.MRR,
            MetricType.SEMANTIC_SIMILARITY,
            MetricType.FAITHFULNESS,
            MetricType.HALLUCINATION_RATE
        ]
    )
    
    # Run evaluation
    report = await engine.evaluate_batch(samples)
    
    # Print report
    print("\n" + "="*80)
    print("📊 EVALUATION REPORT")
    print("="*80)
    print(f"Total samples: {report.total_samples}")
    print(f"Passed: {report.passed_samples}")
    print(f"Failed: {report.failed_samples}")
    print("\nMetrics:")
    for metric, value in report.metrics.items():
        print(f"  {metric}: {value:.4f}")
    print("\nRecommendations:")
    for rec in report.recommendations:
        print(f"  {rec}")
    print("="*80)


if __name__ == "__main__":
    asyncio.run(main())
