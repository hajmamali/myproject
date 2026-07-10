"""
Reasoning Policies
==================

تعریف سیاست‌های استدلال برای کنترل فرآیند تصمیم‌گیری

Classes:
- ReasoningPolicy: سیاست پایه
- ConservativePolicy: سیاست محافظه‌کارانه
- AggressivePolicy: سیاست تهاجمی
- BalancedPolicy: سیاست متعادل
"""


from typing import Any, List, Optional
from dataclasses import dataclass
from enum import Enum


class PolicyType(str, Enum):
    """نوع سیاست استدلال"""
    CONSERVATIVE = "conservative"  # محافظه‌کارانه
    BALANCED = "balanced"          # متعادل
    AGGRESSIVE = "aggressive"      # تهاجمی
    CUSTOM = "custom"              # سفارشی


@dataclass
class ReasoningPolicy:
    """
    سیاست استدلال برای کنترل فرآیند تصمیم‌گیری
    
    Attributes:
        min_evidence_count: حداقل تعداد شواهد مورد نیاز
        min_confidence: حداقل اطمینان برای پذیرش
        max_reasoning_steps: حداکثر گام‌های استدلال
        uncertainty_threshold: آستانه عدم قطعیت
        require_causal_chain: نیاز به زنجیره علّی
        enable_fallback: فعال‌سازی fallback
        temperature: دمای softmax برای نرمال‌سازی
    """
    
    # Evidence requirements
    min_evidence_count: int = 2
    min_evidence_strength: float = 0.3
    
    # Confidence thresholds
    min_confidence: float = 0.5
    high_confidence_threshold: float = 0.8
    
    # Reasoning control
    max_reasoning_steps: int = 6
    min_reasoning_steps: int = 3
    
    # Uncertainty
    uncertainty_threshold: float = 0.2
    max_uncertainty: float = 0.5
    
    # Causal reasoning
    require_causal_chain: bool = False
    min_causal_strength: float = 0.4
    
    # Fallback behavior
    enable_fallback: bool = True
    fallback_confidence: float = 0.3
    
    # Scoring
    temperature: float = 1.0
    score_weights: Optional[dict] = None
    
    # Policy metadata
    name: str = "default"
    description: str = "Default reasoning policy"
    
    def __post_init__(self):
        """Initialize score weights if not provided"""
        if self.score_weights is None:
            self.score_weights = {
                'evidence': 0.4,
                'confidence': 0.3,
                'causal': 0.2,
                'consistency': 0.1
            }
    
    def validate_evidence(self, evidence_count: int, evidence_strength: float) -> bool:
        """
        اعتبارسنجی شواهد
        
        Args:
            evidence_count: تعداد شواهد
            evidence_strength: قدرت شواهد
            
        Returns:
            True اگر شواهد کافی باشند
        """
        return (
            evidence_count >= self.min_evidence_count and
            evidence_strength >= self.min_evidence_strength
        )
    
    def validate_confidence(self, confidence: float) -> bool:
        """
        اعتبارسنجی اطمینان
        
        Args:
            confidence: سطح اطمینان
            
        Returns:
            True اگر اطمینان کافی باشد
        """
        return confidence >= self.min_confidence
    
    def validate_uncertainty(self, uncertainty: float) -> bool:
        """
        اعتبارسنجی عدم قطعیت
        
        Args:
            uncertainty: میزان عدم قطعیت
            
        Returns:
            True اگر عدم قطعیت قابل قبول باشد
        """
        return uncertainty <= self.uncertainty_threshold
    
    def is_high_confidence(self, confidence: float) -> bool:
        """بررسی اطمینان بالا"""
        return confidence >= self.high_confidence_threshold
    
    def should_continue_reasoning(self, step: int, confidence: float) -> bool:
        """
        تصمیم به ادامه استدلال
        
        Args:
            step: گام فعلی
            confidence: اطمینان فعلی
            
        Returns:
            True اگر باید ادامه داد
        """
        # حداقل گام‌ها را طی کن
        if step < self.min_reasoning_steps:
            return True
        
        # اگر اطمینان بالا رسید، متوقف شو
        if self.is_high_confidence(confidence):
            return False
        
        # حداکثر گام‌ها را رعایت کن
        return step < self.max_reasoning_steps
    
    def compute_final_score(self, scores: dict) -> float:
        """
        محاسبه امتیاز نهایی
        
        Args:
            scores: دیکشنری امتیازها
            
        Returns:
            امتیاز نهایی وزن‌دار
        """
        from mahoun.reasoning.utils import weighted_average, clamp
        
        values: List[Any] = []
        weights: List[Any] = []
        for key, weight in self.score_weights.items():
            if key in scores:
                values.append(scores[key])
                weights.append(weight)
        
        if not values:
            return 0.0
        
        final_score = weighted_average(values, weights)
        return clamp(final_score, 0.0, 1.0)


class ConservativePolicy(ReasoningPolicy):
    """
    سیاست محافظه‌کارانه
    
    - شواهد بیشتر نیاز دارد
    - اطمینان بالاتر می‌خواهد
    - عدم قطعیت کمتری می‌پذیرد
    """
    
    def __init__(self):
        super().__init__(
            name="conservative",
            description="Conservative reasoning with high evidence requirements",
            min_evidence_count=3,
            min_evidence_strength=0.5,
            min_confidence=0.7,
            high_confidence_threshold=0.9,
            uncertainty_threshold=0.15,
            max_uncertainty=0.3,
            require_causal_chain=True,
            min_causal_strength=0.6,
            max_reasoning_steps=8,
            min_reasoning_steps=4,
            temperature=0.5,  # More focused
            score_weights={
                'evidence': 0.5,
                'confidence': 0.3,
                'causal': 0.15,
                'consistency': 0.05
            }
        )


class AggressivePolicy(ReasoningPolicy):
    """
    سیاست تهاجمی
    
    - شواهد کمتر نیاز دارد
    - اطمینان پایین‌تر می‌پذیرد
    - عدم قطعیت بیشتری می‌پذیرد
    """
    
    def __init__(self):
        super().__init__(
            name="aggressive",
            description="Aggressive reasoning with lower evidence requirements",
            min_evidence_count=1,
            min_evidence_strength=0.2,
            min_confidence=0.3,
            high_confidence_threshold=0.6,
            uncertainty_threshold=0.3,
            max_uncertainty=0.7,
            require_causal_chain=False,
            min_causal_strength=0.3,
            max_reasoning_steps=4,
            min_reasoning_steps=2,
            temperature=1.5,  # More exploratory
            score_weights={
                'evidence': 0.3,
                'confidence': 0.2,
                'causal': 0.3,
                'consistency': 0.2
            }
        )


class BalancedPolicy(ReasoningPolicy):
    """
    سیاست متعادل (پیش‌فرض)
    
    - تعادل بین محافظه‌کاری و تهاجم
    - مناسب برای اکثر موارد
    """
    
    def __init__(self):
        super().__init__(
            name="balanced",
            description="Balanced reasoning policy for general use",
            min_evidence_count=2,
            min_evidence_strength=0.3,
            min_confidence=0.5,
            high_confidence_threshold=0.8,
            uncertainty_threshold=0.2,
            max_uncertainty=0.5,
            require_causal_chain=False,
            min_causal_strength=0.4,
            max_reasoning_steps=6,
            min_reasoning_steps=3,
            temperature=1.0,
            score_weights={
                'evidence': 0.4,
                'confidence': 0.3,
                'causal': 0.2,
                'consistency': 0.1
            }
        )


def get_policy(policy_type: PolicyType = PolicyType.BALANCED) -> ReasoningPolicy:
    """
    دریافت سیاست بر اساس نوع
    
    Args:
        policy_type: نوع سیاست
        
    Returns:
        شیء سیاست
        
    Example:
        >>> policy = get_policy(PolicyType.CONSERVATIVE)
        >>> policy.min_confidence
        0.7
    """
    policies = {
        PolicyType.CONSERVATIVE: ConservativePolicy(),
        PolicyType.BALANCED: BalancedPolicy(),
        PolicyType.AGGRESSIVE: AggressivePolicy()
    }
    
    return policies.get(policy_type, BalancedPolicy())


def create_custom_policy(
    name: str,
    **kwargs
) -> ReasoningPolicy:
    """
    ساخت سیاست سفارشی
    
    Args:
        name: نام سیاست
        **kwargs: پارامترهای سیاست
        
    Returns:
        سیاست سفارشی
        
    Example:
        >>> policy = create_custom_policy(
        ...     name="my_policy",
        ...     min_confidence=0.6,
        ...     max_reasoning_steps=10
        ... )
    """
    return ReasoningPolicy(name=name, **kwargs)
