"""
Bias Analysis and Fairness Metrics
===================================

Comprehensive bias detection and fairness analysis for training datasets.

Features:
- Protected attribute detection (gender, age, ethnicity, religion)
- Fairness metrics: demographic parity, equalized odds, disparate impact
- Bias mitigation strategies
- Visualization and reporting
"""

import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)


class ProtectedAttribute(str, Enum):
    """Protected attributes for bias analysis."""
    GENDER = "gender"
    AGE = "age"
    ETHNICITY = "ethnicity"
    RELIGION = "religion"
    NATIONALITY = "nationality"
    DISABILITY = "disability"


class FairnessMetric(str, Enum):
    """Fairness metrics."""
    DEMOGRAPHIC_PARITY = "demographic_parity"
    EQUALIZED_ODDS = "equalized_odds"
    EQUAL_OPPORTUNITY = "equal_opportunity"
    DISPARATE_IMPACT = "disparate_impact"
    CALIBRATION = "calibration"


@dataclass
class BiasReport:
    """Bias analysis report."""
    dataset_name: str
    total_samples: int
    protected_attributes: List[str]
    fairness_scores: Dict[str, float]
    violations: List[Dict[str, Any]]
    recommendations: List[str]
    severity: str  # "low", "medium", "high", "critical"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "dataset_name": self.dataset_name,
            "total_samples": self.total_samples,
            "protected_attributes": self.protected_attributes,
            "fairness_scores": self.fairness_scores,
            "violations": self.violations,
            "recommendations": self.recommendations,
            "severity": self.severity
        }


class FairnessMetrics:
    """
    Calculate fairness metrics for bias analysis.
    """
    
    @staticmethod
    def demographic_parity(
        predictions: np.ndarray,
        protected_attribute: np.ndarray
    ) -> float:
        """
        Calculate demographic parity.
        
        Measures whether positive prediction rate is equal across groups.
        Score of 1.0 = perfect parity, 0.0 = maximum disparity.
        
        Args:
            predictions: Binary predictions (0 or 1)
            protected_attribute: Protected attribute values
            
        Returns:
            Demographic parity score [0, 1]
        """
        unique_groups = np.unique(protected_attribute)
        
        if len(unique_groups) < 2:
            return 1.0  # No disparity if only one group
        
        positive_rates = []
        for group in unique_groups:
            mask = protected_attribute == group
            if mask.sum() > 0:
                positive_rate = predictions[mask].mean()
                positive_rates.append(positive_rate)
        
        if not positive_rates:
            return 1.0
        
        # Calculate disparity as 1 - (max_rate - min_rate)
        disparity = max(positive_rates) - min(positive_rates)
        return max(0.0, 1.0 - disparity)
    
    @staticmethod
    def equalized_odds(
        predictions: np.ndarray,
        labels: np.ndarray,
        protected_attribute: np.ndarray
    ) -> float:
        """
        Calculate equalized odds.
        
        Measures whether true positive rate and false positive rate
        are equal across groups.
        
        Args:
            predictions: Binary predictions
            labels: True labels
            protected_attribute: Protected attribute values
            
        Returns:
            Equalized odds score [0, 1]
        """
        unique_groups = np.unique(protected_attribute)
        
        if len(unique_groups) < 2:
            return 1.0
        
        tpr_list = []  # True positive rates
        fpr_list = []  # False positive rates
        
        for group in unique_groups:
            mask = protected_attribute == group
            if mask.sum() == 0:
                continue
            
            group_preds = predictions[mask]
            group_labels = labels[mask]
            
            # True positive rate
            positives = group_labels == 1
            if positives.sum() > 0:
                tpr = (group_preds[positives] == 1).mean()
                tpr_list.append(tpr)
            
            # False positive rate
            negatives = group_labels == 0
            if negatives.sum() > 0:
                fpr = (group_preds[negatives] == 1).mean()
                fpr_list.append(fpr)
        
        if not tpr_list or not fpr_list:
            return 1.0
        
        # Calculate disparity for both TPR and FPR
        tpr_disparity = max(tpr_list) - min(tpr_list)
        fpr_disparity = max(fpr_list) - min(fpr_list)
        
        # Average disparity
        avg_disparity = (tpr_disparity + fpr_disparity) / 2
        return max(0.0, 1.0 - avg_disparity)
    
    @staticmethod
    def disparate_impact(
        predictions: np.ndarray,
        protected_attribute: np.ndarray,
        privileged_group: Any
    ) -> float:
        """
        Calculate disparate impact ratio.
        
        Ratio of positive prediction rate for unprivileged group
        to privileged group. Ratio < 0.8 indicates bias.
        
        Args:
            predictions: Binary predictions
            protected_attribute: Protected attribute values
            privileged_group: Value representing privileged group
            
        Returns:
            Disparate impact ratio
        """
        privileged_mask = protected_attribute == privileged_group
        unprivileged_mask = ~privileged_mask
        
        if privileged_mask.sum() == 0 or unprivileged_mask.sum() == 0:
            return 1.0
        
        privileged_rate = predictions[privileged_mask].mean()
        unprivileged_rate = predictions[unprivileged_mask].mean()
        
        if privileged_rate == 0:
            return 1.0 if unprivileged_rate == 0 else 0.0
        
        return unprivileged_rate / privileged_rate
    
    @staticmethod
    def equal_opportunity(
        predictions: np.ndarray,
        labels: np.ndarray,
        protected_attribute: np.ndarray
    ) -> float:
        """
        Calculate equal opportunity.
        
        Measures whether true positive rate is equal across groups.
        
        Args:
            predictions: Binary predictions
            labels: True labels
            protected_attribute: Protected attribute values
            
        Returns:
            Equal opportunity score [0, 1]
        """
        unique_groups = np.unique(protected_attribute)
        
        if len(unique_groups) < 2:
            return 1.0
        
        tpr_list = []
        
        for group in unique_groups:
            mask = protected_attribute == group
            positives = (labels == 1) & mask
            
            if positives.sum() > 0:
                tpr = (predictions[positives] == 1).mean()
                tpr_list.append(tpr)
        
        if not tpr_list:
            return 1.0
        
        disparity = max(tpr_list) - min(tpr_list)
        return max(0.0, 1.0 - disparity)


class BiasAnalyzer:
    """
    Comprehensive bias analyzer for training datasets.
    
    Detects bias across protected attributes and calculates fairness metrics.
    """
    
    def __init__(
        self,
        fairness_threshold: float = 0.8,
        min_group_size: int = 10
    ):
        """
        Initialize bias analyzer.
        
        Args:
            fairness_threshold: Minimum fairness score (0-1)
            min_group_size: Minimum samples per group for analysis
        """
        self.fairness_threshold = fairness_threshold
        self.min_group_size = min_group_size
        self.metrics_calculator = FairnessMetrics()
    
    def analyze_dataset(
        self,
        dataset_name: str,
        data: Dict[str, np.ndarray],
        protected_attributes: List[str],
        predictions: Optional[np.ndarray] = None,
        labels: Optional[np.ndarray] = None
    ) -> BiasReport:
        """
        Analyze dataset for bias.
        
        Args:
            dataset_name: Name of dataset
            data: Dictionary mapping attribute names to arrays
            protected_attributes: List of protected attribute names
            predictions: Optional predictions for fairness metrics
            labels: Optional true labels for fairness metrics
            
        Returns:
            BiasReport object
        """
        logger.info(f"Analyzing bias in dataset: {dataset_name}")
        
        total_samples = len(next(iter(data.values())))
        fairness_scores = {}
        violations = []
        recommendations = []
        
        # Analyze each protected attribute
        for attr in protected_attributes:
            if attr not in data:
                logger.warning(f"Protected attribute {attr} not found in data")
                continue
            
            attr_data = data[attr]
            
            # Check group sizes
            unique_values, counts = np.unique(attr_data, return_counts=True)
            small_groups = [
                val for val, count in zip(unique_values, counts)
                if count < self.min_group_size
            ]
            
            if small_groups:
                violations.append({
                    "type": "small_group_size",
                    "attribute": attr,
                    "groups": [str(g) for g in small_groups],
                    "message": f"Groups with < {self.min_group_size} samples"
                })
                recommendations.append(
                    f"Collect more data for {attr} groups: {small_groups}"
                )
            
            # Calculate fairness metrics if predictions available
            if predictions is not None:
                # Demographic parity
                dp_score = self.metrics_calculator.demographic_parity(
                    predictions, attr_data
                )
                fairness_scores[f"{attr}_demographic_parity"] = dp_score
                
                if dp_score < self.fairness_threshold:
                    violations.append({
                        "type": "demographic_parity_violation",
                        "attribute": attr,
                        "score": dp_score,
                        "threshold": self.fairness_threshold,
                        "message": f"Demographic parity score {dp_score:.3f} below threshold"
                    })
                    recommendations.append(
                        f"Apply reweighting or resampling for {attr} to improve parity"
                    )
                
                # Equalized odds (if labels available)
                if labels is not None:
                    eo_score = self.metrics_calculator.equalized_odds(
                        predictions, labels, attr_data
                    )
                    fairness_scores[f"{attr}_equalized_odds"] = eo_score
                    
                    if eo_score < self.fairness_threshold:
                        violations.append({
                            "type": "equalized_odds_violation",
                            "attribute": attr,
                            "score": eo_score,
                            "threshold": self.fairness_threshold,
                            "message": f"Equalized odds score {eo_score:.3f} below threshold"
                        })
                        recommendations.append(
                            f"Apply post-processing calibration for {attr}"
                        )
        
        # Determine severity
        severity = self._calculate_severity(violations, fairness_scores)
        
        report = BiasReport(
            dataset_name=dataset_name,
            total_samples=total_samples,
            protected_attributes=protected_attributes,
            fairness_scores=fairness_scores,
            violations=violations,
            recommendations=recommendations,
            severity=severity
        )
        
        logger.info(f"Bias analysis complete. Severity: {severity}, Violations: {len(violations)}")
        return report
    
    def _calculate_severity(
        self,
        violations: List[Dict[str, Any]],
        fairness_scores: Dict[str, float]
    ) -> str:
        """Calculate overall severity level."""
        if not violations:
            return "low"
        
        # Count critical violations (score < 0.5)
        critical_count = sum(
            1 for v in violations
            if v.get("score", 1.0) < 0.5
        )
        
        if critical_count > 0:
            return "critical"
        elif len(violations) >= 5:
            return "high"
        elif len(violations) >= 2:
            return "medium"
        else:
            return "low"
    
    def detect_protected_attributes(
        self,
        data: Dict[str, np.ndarray],
        text_fields: Optional[List[str]] = None
    ) -> List[str]:
        """
        Automatically detect protected attributes in dataset.
        
        Args:
            data: Dataset dictionary
            text_fields: Optional list of text field names to scan
            
        Returns:
            List of detected protected attribute names
        """
        detected = []
        
        # Keywords for each protected attribute
        keywords = {
            "gender": ["gender", "sex", "male", "female"],
            "age": ["age", "birth", "dob"],
            "ethnicity": ["ethnicity", "race", "ethnic"],
            "religion": ["religion", "religious", "faith"],
            "nationality": ["nationality", "country", "citizen"],
            "disability": ["disability", "disabled", "handicap"]
        }
        
        # Check column names
        for attr, kws in keywords.items():
            for col_name in data.keys():
                if any(kw in col_name.lower() for kw in kws):
                    detected.append(col_name)
                    break
        
        # Check text fields if provided
        if text_fields:
            for field in text_fields:
                if field in data:
                    # Sample text to check for keywords
                    sample_text = " ".join(str(data[field][:100]))
                    for attr, kws in keywords.items():
                        if any(kw in sample_text.lower() for kw in kws):
                            if field not in detected:
                                detected.append(field)
        
        return detected
    
    def generate_mitigation_strategy(
        self,
        report: BiasReport
    ) -> Dict[str, Any]:
        """
        Generate bias mitigation strategy based on report.
        
        Args:
            report: BiasReport from analysis
            
        Returns:
            Mitigation strategy dictionary
        """
        strategies = []
        
        # Analyze violations and recommend strategies
        for violation in report.violations:
            if violation["type"] == "demographic_parity_violation":
                strategies.append({
                    "method": "reweighting",
                    "attribute": violation["attribute"],
                    "description": "Assign weights to balance positive prediction rates"
                })
                strategies.append({
                    "method": "resampling",
                    "attribute": violation["attribute"],
                    "description": "Oversample underrepresented groups"
                })
            
            elif violation["type"] == "equalized_odds_violation":
                strategies.append({
                    "method": "post_processing",
                    "attribute": violation["attribute"],
                    "description": "Calibrate predictions to equalize TPR/FPR"
                })
            
            elif violation["type"] == "small_group_size":
                strategies.append({
                    "method": "data_collection",
                    "attribute": violation["attribute"],
                    "description": "Collect more samples for underrepresented groups"
                })
        
        return {
            "severity": report.severity,
            "strategies": strategies,
            "priority": "high" if report.severity in ["high", "critical"] else "medium"
        }
