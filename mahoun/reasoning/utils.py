"""
Reasoning Utilities
===================

توابع کمکی ریاضی و نرمال‌سازی برای موتور استدلال

Functions:
- softmax: نرمال‌سازی احتمالاتی
- clamp: محدود کردن مقادیر
- safe_mean: میانگین امن
- normalize_scores: نرمال‌سازی امتیازها
- weighted_average: میانگین وزن‌دار
"""


import math
from typing import List, Optional, Union

def softmax(scores: List[float], temperature: float = 1.0) -> List[float]:
    """
    Softmax normalization
    
    Args:
        scores: لیست امتیازها
        temperature: دمای softmax (کمتر = تمرکز بیشتر)
        
    Returns:
        احتمالات نرمال‌شده
        
    Example:
        >>> softmax([1.0, 2.0, 3.0])
        [0.09, 0.24, 0.67]
    """
    if not scores:
        return []
    
    # Scale by temperature
    scaled = [s / temperature for s in scores]
    
    # Subtract max for numerical stability
    max_score = max(scaled)
    exp_scores = [math.exp(s - max_score) for s in scaled]
    
    # Normalize
    total = sum(exp_scores)
    if total == 0:
        return [1.0 / len(scores)] * len(scores)
    
    return [e / total for e in exp_scores]


def clamp(
    value: float,
    min_value: float = 0.0,
    max_value: float = 1.0
) -> float:
    """
    محدود کردن مقدار به بازه [min, max]
    
    Args:
        value: مقدار ورودی
        min_value: حداقل
        max_value: حداکثر
        
    Returns:
        مقدار محدود شده
        
    Example:
        >>> clamp(1.5, 0, 1)
        1.0
        >>> clamp(-0.5, 0, 1)
        0.0
    """
    return max(min_value, min(value, max_value))


def safe_mean(values: List[float], default: float = 0.0) -> float:
    """
    میانگین امن (بدون خطا برای لیست خالی)
    
    Args:
        values: لیست مقادیر
        default: مقدار پیش‌فرض برای لیست خالی
        
    Returns:
        میانگین یا مقدار پیش‌فرض
        
    Example:
        >>> safe_mean([1, 2, 3])
        2.0
        >>> safe_mean([])
        0.0
    """
    if not values:
        return default
    
    return sum(values) / len(values)


def safe_max(values: List[float], default: float = 0.0) -> float:
    """
    حداکثر امن
    
    Args:
        values: لیست مقادیر
        default: مقدار پیش‌فرض
        
    Returns:
        حداکثر یا مقدار پیش‌فرض
    """
    if not values:
        return default
    
    return max(values)


def safe_min(values: List[float], default: float = 0.0) -> float:
    """
    حداقل امن
    
    Args:
        values: لیست مقادیر
        default: مقدار پیش‌فرض
        
    Returns:
        حداقل یا مقدار پیش‌فرض
    """
    if not values:
        return default
    
    return min(values)


def normalize_scores(
    scores: List[float],
    method: str = "minmax"
) -> List[float]:
    """
    نرمال‌سازی امتیازها
    
    Args:
        scores: لیست امتیازها
        method: روش نرمال‌سازی ("minmax", "zscore", "sum")
        
    Returns:
        امتیازهای نرمال‌شده
        
    Example:
        >>> normalize_scores([1, 2, 3], method="minmax")
        [0.0, 0.5, 1.0]
    """
    if not scores:
        return []
    
    if method == "minmax":
        # Min-Max normalization [0, 1]
        min_score = min(scores)
        max_score = max(scores)
        
        if max_score == min_score:
            return [1.0] * len(scores)
        
        return [(s - min_score) / (max_score - min_score) for s in scores]
    
    elif method == "zscore":
        # Z-score normalization
        mean = safe_mean(scores)
        std = math.sqrt(safe_mean([(s - mean) ** 2 for s in scores]))
        
        if std == 0:
            return [0.0] * len(scores)
        
        return [(s - mean) / std for s in scores]
    
    elif method == "sum":
        # Sum normalization
        total = sum(scores)
        
        if total == 0:
            return [1.0 / len(scores)] * len(scores)
        
        return [s / total for s in scores]
    
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def weighted_average(
    values: List[float],
    weights: Optional[List[float]] = None,
    default: float = 0.0
) -> float:
    """
    میانگین وزن‌دار
    
    Args:
        values: لیست مقادیر
        weights: لیست وزن‌ها (اختیاری)
        default: مقدار پیش‌فرض
        
    Returns:
        میانگین وزن‌دار
        
    Example:
        >>> weighted_average([1, 2, 3], [0.5, 0.3, 0.2])
        1.7
    """
    if not values:
        return default
    
    if weights is None:
        return safe_mean(values, default)
    
    if len(values) != len(weights):
        raise ValueError("values and weights must have same length")
    
    total_weight = sum(weights)
    if total_weight == 0:
        return safe_mean(values, default)
    
    weighted_sum = sum(v * w for v, w in zip(values, weights))
    return weighted_sum / total_weight


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    شباهت کسینوسی بین دو بردار
    
    Args:
        vec1: بردار اول
        vec2: بردار دوم
        
    Returns:
        شباهت کسینوسی [-1, 1]
        
    Example:
        >>> cosine_similarity([1, 0, 0], [1, 0, 0])
        1.0
    """
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must have same length")
    
    if not vec1 or not vec2:
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    
    norm1 = math.sqrt(sum(a * a for a in vec1))
    norm2 = math.sqrt(sum(b * b for b in vec2))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def entropy(probabilities: List[float]) -> float:
    """
    محاسبه آنتروپی (عدم قطعیت)
    
    Args:
        probabilities: لیست احتمالات
        
    Returns:
        آنتروپی (بیشتر = عدم قطعیت بیشتر)
        
    Example:
        >>> entropy([0.5, 0.5])  # Maximum uncertainty
        1.0
        >>> entropy([1.0, 0.0])  # No uncertainty
        0.0
    """
    if not probabilities:
        return 0.0
    
    # Filter out zero probabilities
    probs = [p for p in probabilities if p > 0]
    
    if not probs:
        return 0.0
    
    return -sum(p * math.log2(p) for p in probs)


def confidence_interval(
    mean: float,
    std: float,
    confidence_level: float = 0.95
) -> tuple[float, float]:
    """
    محاسبه بازه اطمینان
    
    Args:
        mean: میانگین
        std: انحراف معیار
        confidence_level: سطح اطمینان (0.95 یا 0.99)
        
    Returns:
        (lower_bound, upper_bound)
        
    Example:
        >>> confidence_interval(0.8, 0.1, 0.95)
        (0.604, 0.996)
    """
    # Z-scores for common confidence levels
    z_scores = {
        0.90: 1.645,
        0.95: 1.96,
        0.99: 2.576
    }
    
    z = z_scores.get(confidence_level, 1.96)
    margin = z * std
    
    return (mean - margin, mean + margin)


def exponential_decay(
    initial_value: float,
    decay_rate: float,
    time: float
) -> float:
    """
    کاهش نمایی (برای وزن‌دهی زمانی)
    
    Args:
        initial_value: مقدار اولیه
        decay_rate: نرخ کاهش
        time: زمان
        
    Returns:
        مقدار کاهش‌یافته
        
    Example:
        >>> exponential_decay(1.0, 0.1, 5)
        0.606
    """
    return initial_value * math.exp(-decay_rate * time)


def sigmoid(x: float) -> float:
    """
    تابع سیگموید
    
    Args:
        x: ورودی
        
    Returns:
        خروجی در بازه [0, 1]
        
    Example:
        >>> sigmoid(0)
        0.5
        >>> sigmoid(10)
        0.9999
    """
    return 1 / (1 + math.exp(-x))


def linear_interpolation(
    x: float,
    x1: float,
    y1: float,
    x2: float,
    y2: float
) -> float:
    """
    درون‌یابی خطی
    
    Args:
        x: نقطه مورد نظر
        x1, y1: نقطه اول
        x2, y2: نقطه دوم
        
    Returns:
        مقدار درون‌یاب شده
    """
    if x2 == x1:
        return y1
    
    return y1 + (x - x1) * (y2 - y1) / (x2 - x1)


# Aliases for convenience
normalize = normalize_scores
avg = safe_mean
clip = clamp
