"""
Data Quality Metrics
====================

Comprehensive data quality analysis and drift detection.

Features:
- Quality score calculation
- Data drift detection
- Outlier and anomaly detection
- Completeness and consistency checks
- Quality reports
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from scipy import stats
import logging

logger = logging.getLogger(__name__)


@dataclass
class QualityReport:
    """Data quality report."""
    dataset_name: str
    total_samples: int
    quality_score: float  # 0-1
    completeness_score: float  # 0-1
    consistency_score: float  # 0-1
    validity_score: float  # 0-1
    issues: List[Dict[str, Any]]
    recommendations: List[str]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "total_samples": self.total_samples,
            "quality_score": self.quality_score,
            "completeness_score": self.completeness_score,
            "consistency_score": self.consistency_score,
            "validity_score": self.validity_score,
            "issues": self.issues,
            "recommendations": self.recommendations
        }


@dataclass
class DriftReport:
    """Data drift report."""
    reference_dataset: str
    current_dataset: str
    drift_detected: bool
    drift_score: float  # 0-1, higher = more drift
    feature_drifts: Dict[str, float]
    statistical_tests: Dict[str, Dict[str, Any]]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "reference_dataset": self.reference_dataset,
            "current_dataset": self.current_dataset,
            "drift_detected": self.drift_detected,
            "drift_score": self.drift_score,
            "feature_drifts": self.feature_drifts,
            "statistical_tests": self.statistical_tests
        }


class DataQualityAnalyzer:
    """
    Comprehensive data quality analyzer.
    
    Calculates quality metrics and detects data drift.
    """
    
    def __init__(
        self,
        completeness_threshold: float = 0.95,
        consistency_threshold: float = 0.90,
        drift_threshold: float = 0.1
    ):
        """
        Initialize quality analyzer.
        
        Args:
            completeness_threshold: Minimum completeness score
            consistency_threshold: Minimum consistency score
            drift_threshold: Maximum acceptable drift score
        """
        self.completeness_threshold = completeness_threshold
        self.consistency_threshold = consistency_threshold
        self.drift_threshold = drift_threshold
    
    def analyze_quality(
        self,
        dataset_name: str,
        data: Dict[str, np.ndarray],
        schema: Optional[Dict[str, Any]] = None
    ) -> QualityReport:
        """
        Analyze dataset quality.
        
        Args:
            dataset_name: Name of dataset
            data: Dictionary mapping feature names to arrays
            schema: Optional schema for validation
            
        Returns:
            QualityReport object
        """
        logger.info(f"Analyzing quality for dataset: {dataset_name}")
        
        total_samples = len(next(iter(data.values())))
        issues = []
        recommendations = []
        
        # Completeness check
        completeness_score = self._check_completeness(data, issues, recommendations)
        
        # Consistency check
        consistency_score = self._check_consistency(data, issues, recommendations)
        
        # Validity check
        validity_score = self._check_validity(data, schema, issues, recommendations)
        
        # Overall quality score (weighted average)
        quality_score = (
            0.4 * completeness_score +
            0.3 * consistency_score +
            0.3 * validity_score
        )
        
        report = QualityReport(
            dataset_name=dataset_name,
            total_samples=total_samples,
            quality_score=quality_score,
            completeness_score=completeness_score,
            consistency_score=consistency_score,
            validity_score=validity_score,
            issues=issues,
            recommendations=recommendations
        )
        
        logger.info(f"Quality analysis complete. Score: {quality_score:.3f}")
        return report
    
    def _check_completeness(
        self,
        data: Dict[str, np.ndarray],
        issues: List[Dict[str, Any]],
        recommendations: List[str]
    ) -> float:
        """Check data completeness (missing values)."""
        total_values = 0
        missing_values = 0
        
        for feature, values in data.items():
            total_values += len(values)
            
            # Count None, NaN, empty strings
            if values.dtype == object:
                missing = sum(1 for v in values if v is None or v == "" or (isinstance(v, float) and np.isnan(v)))
            else:
                missing = np.isnan(values).sum()
            
            missing_values += missing
            
            if missing > 0:
                missing_pct = (missing / len(values)) * 100
                if missing_pct > 5:  # More than 5% missing
                    issues.append({
                        "type": "missing_values",
                        "feature": feature,
                        "count": int(missing),
                        "percentage": missing_pct,
                        "severity": "high" if missing_pct > 20 else "medium"
                    })
                    recommendations.append(
                        f"Impute or remove missing values in {feature} ({missing_pct:.1f}% missing)"
                    )
        
        if total_values == 0:
            return 1.0
        
        completeness = 1.0 - (missing_values / total_values)
        return max(0.0, completeness)
    
    def _check_consistency(
        self,
        data: Dict[str, np.ndarray],
        issues: List[Dict[str, Any]],
        recommendations: List[str]
    ) -> float:
        """Check data consistency (duplicates, outliers)."""
        consistency_scores = []
        
        for feature, values in data.items():
            # Check for duplicates
            if values.dtype == object:
                unique_ratio = len(set(values)) / len(values)
            else:
                unique_ratio = len(np.unique(values)) / len(values)
            
            if unique_ratio < 0.1:  # Less than 10% unique
                issues.append({
                    "type": "low_diversity",
                    "feature": feature,
                    "unique_ratio": unique_ratio,
                    "severity": "medium"
                })
                recommendations.append(
                    f"Feature {feature} has low diversity ({unique_ratio:.1%} unique values)"
                )
            
            # Check for outliers (numeric features only)
            if values.dtype in [np.float32, np.float64, np.int32, np.int64]:
                outliers = self._detect_outliers(values)
                outlier_pct = (outliers.sum() / len(values)) * 100
                
                if outlier_pct > 5:
                    issues.append({
                        "type": "outliers",
                        "feature": feature,
                        "count": int(outliers.sum()),
                        "percentage": outlier_pct,
                        "severity": "low"
                    })
                
                consistency_scores.append(1.0 - (outlier_pct / 100))
            else:
                consistency_scores.append(1.0)
        
        return np.mean(consistency_scores) if consistency_scores else 1.0
    
    def _detect_outliers(self, values: np.ndarray) -> np.ndarray:
        """Detect outliers using IQR method."""
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        return (values < lower_bound) | (values > upper_bound)
    
    def _check_validity(
        self,
        data: Dict[str, np.ndarray],
        schema: Optional[Dict[str, Any]],
        issues: List[Dict[str, Any]],
        recommendations: List[str]
    ) -> float:
        """Check data validity against schema."""
        if not schema:
            return 1.0  # No schema to validate against
        
        validity_scores = []
        
        for feature, values in data.items():
            if feature not in schema:
                continue
            
            feature_schema = schema[feature]
            valid_count = len(values)
            
            # Check type
            expected_type = feature_schema.get("type")
            if expected_type:
                # Type checking logic here
                pass
            
            # Check range
            if "min" in feature_schema or "max" in feature_schema:
                min_val = feature_schema.get("min", -np.inf)
                max_val = feature_schema.get("max", np.inf)
                
                if values.dtype in [np.float32, np.float64, np.int32, np.int64]:
                    out_of_range = ((values < min_val) | (values > max_val)).sum()
                    if out_of_range > 0:
                        issues.append({
                            "type": "out_of_range",
                            "feature": feature,
                            "count": int(out_of_range),
                            "severity": "high"
                        })
                        valid_count -= out_of_range
            
            validity_scores.append(valid_count / len(values))
        
        return np.mean(validity_scores) if validity_scores else 1.0
    
    def detect_drift(
        self,
        reference_data: Dict[str, np.ndarray],
        current_data: Dict[str, np.ndarray],
        reference_name: str = "reference",
        current_name: str = "current"
    ) -> DriftReport:
        """
        Detect data drift between reference and current datasets.
        
        Args:
            reference_data: Reference dataset
            current_data: Current dataset
            reference_name: Name of reference dataset
            current_name: Name of current dataset
            
        Returns:
            DriftReport object
        """
        logger.info(f"Detecting drift: {reference_name} vs {current_name}")
        
        feature_drifts = {}
        statistical_tests = {}
        
        for feature in reference_data.keys():
            if feature not in current_data:
                continue
            
            ref_values = reference_data[feature]
            cur_values = current_data[feature]
            
            # Kolmogorov-Smirnov test for numeric features
            if ref_values.dtype in [np.float32, np.float64, np.int32, np.int64]:
                ks_stat, p_value = stats.ks_2samp(ref_values, cur_values)
                feature_drifts[feature] = ks_stat
                statistical_tests[feature] = {
                    "test": "kolmogorov_smirnov",
                    "statistic": float(ks_stat),
                    "p_value": float(p_value),
                    "drift_detected": p_value < 0.05
                }
            else:
                # Chi-square test for categorical features
                ref_counts = np.unique(ref_values, return_counts=True)[1]
                cur_counts = np.unique(cur_values, return_counts=True)[1]
                
                # Normalize to same length
                min_len = min(len(ref_counts), len(cur_counts))
                ref_counts = ref_counts[:min_len]
                cur_counts = cur_counts[:min_len]
                
                if len(ref_counts) > 1:
                    chi2_stat, p_value = stats.chisquare(cur_counts, ref_counts)
                    feature_drifts[feature] = chi2_stat / len(ref_counts)  # Normalize
                    statistical_tests[feature] = {
                        "test": "chi_square",
                        "statistic": float(chi2_stat),
                        "p_value": float(p_value),
                        "drift_detected": p_value < 0.05
                    }
        
        # Overall drift score (average of feature drifts)
        drift_score = np.mean(list(feature_drifts.values())) if feature_drifts else 0.0
        drift_detected = drift_score > self.drift_threshold
        
        report = DriftReport(
            reference_dataset=reference_name,
            current_dataset=current_name,
            drift_detected=drift_detected,
            drift_score=float(drift_score),
            feature_drifts=feature_drifts,
            statistical_tests=statistical_tests
        )
        
        logger.info(f"Drift detection complete. Score: {drift_score:.3f}, Detected: {drift_detected}")
        return report
