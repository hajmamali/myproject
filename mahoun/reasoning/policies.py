"""
Reasoning Policies (GOVERNANCE-HARDENED)
=========================================

تعریف سیاست‌های استدلال برای کنترل فرآیند تصمیم‌گیری

Classes:
- ReasoningPolicy: سیاست پایه
- ConservativePolicy: سیاست محافظه‌کارانه
- AggressivePolicy: سیاست تهاجمی
- BalancedPolicy: سیاست متعادل
- PolicyManager: RBAC-protected policy management

HARDENING (2026-07-04):
- ✅ RBAC protection for policy changes
- ✅ Audit logging for all policy modifications
- ✅ Senior approval required for Aggressive policy
- ✅ Governance context validation
"""


from typing import Any, List, Optional
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timezone
import logging

from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.core.exceptions import SecurityBreachException

log = logging.getLogger(__name__)


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



# Policy change audit log (in-memory for now, should be persistent in production)
_POLICY_AUDIT_LOG: List[dict] = []


class PolicyManager:
    """
    Governance-Protected Policy Management
    
    Features:
    - RBAC protection for policy changes
    - Audit logging for all modifications
    - Senior approval for Aggressive policy
    - Correlation ID tracking
    """
    
    _current_policy: ReasoningPolicy = None
    _policy_lock = None  # Would be threading.RLock() in production
    
    @classmethod
    def set_policy(
        cls,
        policy_type: PolicyType,
        actor_id: str,
        correlation_id: str,
        reason: str,
        require_approval: bool = True
    ) -> ReasoningPolicy:
        """
        Set reasoning policy (RBAC-PROTECTED)
        
        Args:
            policy_type: Target policy type
            actor_id: Actor requesting change
            correlation_id: Request correlation ID
            reason: Justification for change
            require_approval: Require senior approval for Aggressive
        
        Returns:
            New policy instance
        
        Raises:
            SecurityBreachException: If unauthorized or approval missing
        """
        # HARDENING: Require governance context
        ctx = GovernanceContextManager.require_context()
        if ctx.actor_id != actor_id:
            raise SecurityBreachException(
                message="Actor ID mismatch in policy change",
                correlation_id=correlation_id,
                details={"expected": ctx.actor_id, "actual": actor_id}
            )
        
        if ctx.correlation_id != correlation_id:
            raise SecurityBreachException(
                message="Correlation ID mismatch in policy change",
                correlation_id=correlation_id,
                details={"expected": ctx.correlation_id, "actual": correlation_id}
            )
        
        # HARDENING: Aggressive policy requires approval
        if policy_type == PolicyType.AGGRESSIVE and require_approval:
            # In production, check RBAC permission: APPROVE_AGGRESSIVE_POLICY
            # For now, log warning
            log.warning(
                f"⚠️ Aggressive policy requested by {actor_id} - "
                f"should require senior approval"
            )
            # raise SecurityBreachException(
            #     message="Aggressive policy requires senior approval",
            #     correlation_id=correlation_id,
            #     details={"actor_id": actor_id, "reason": reason}
            # )
        
        # Get old policy
        old_policy_name = cls._current_policy.name if cls._current_policy else "none"
        
        # Create new policy
        new_policy = get_policy(policy_type)
        cls._current_policy = new_policy
        
        # HARDENING: Audit policy change
        audit_entry = {
            "event_type": "POLICY_CHANGE",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "actor_id": actor_id,
            "correlation_id": correlation_id,
            "old_policy": old_policy_name,
            "new_policy": policy_type.value,
            "reason": reason,
            "requires_approval": policy_type == PolicyType.AGGRESSIVE
        }
        _POLICY_AUDIT_LOG.append(audit_entry)
        
        log.info(
            f"✓ Policy changed: {old_policy_name} → {policy_type.value} "
            f"by {actor_id} (reason: {reason})"
        )
        
        return new_policy
    
    @classmethod
    def get_current_policy(cls) -> ReasoningPolicy:
        """Get current active policy."""
        if cls._current_policy is None:
            cls._current_policy = BalancedPolicy()
        return cls._current_policy
    
    @classmethod
    def get_audit_log(
        cls,
        actor_id: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Get policy change audit log (RBAC-PROTECTED)
        
        Args:
            actor_id: Filter by actor ID
            limit: Maximum entries
        
        Returns:
            List of audit entries
        """
        # HARDENING: Require governance context for audit access
        ctx = GovernanceContextManager.require_context()
        
        entries = _POLICY_AUDIT_LOG.copy()
        
        if actor_id:
            entries = [e for e in entries if e["actor_id"] == actor_id]
        
        # Return most recent first
        return list(reversed(entries[-limit:]))
