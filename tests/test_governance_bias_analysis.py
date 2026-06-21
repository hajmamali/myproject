"""
Comprehensive tests for bias analysis.

Tests cover:
- Fairness metrics calculation
- Protected attribute detection
- Bias report generation
- Mitigation strategy generation
- Edge cases and error handling
"""

import pytest
import numpy as np
from mahoun.governance.bias_analysis import (
    BiasAnalyzer,
    FairnessMetrics,
    BiasReport,
    ProtectedAttribute,
    FairnessMetric
)


class TestFairnessMetrics:
    """Test fairness metrics calculations."""
    
    def test_demographic_parity_perfect(self):
        """Test demographic parity with perfect parity."""
        predictions = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.demographic_parity(predictions, protected_attr)
        
        # Both groups have 50% positive rate
        assert score == 1.0
    
    def test_demographic_parity_disparity(self):
        """Test demographic parity with disparity."""
        predictions = np.array([1, 1, 1, 1, 0, 0, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.demographic_parity(predictions, protected_attr)
        
        # Group 0: 100%, Group 1: 0% -> disparity = 1.0
        assert score == 0.0
    
    def test_demographic_parity_single_group(self):
        """Test demographic parity with single group."""
        predictions = np.array([1, 0, 1, 0])
        protected_attr = np.array([0, 0, 0, 0])
        
        score = FairnessMetrics.demographic_parity(predictions, protected_attr)
        
        # No disparity with single group
        assert score == 1.0
    
    def test_equalized_odds_perfect(self):
        """Test equalized odds with perfect equality."""
        predictions = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        labels = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.equalized_odds(predictions, labels, protected_attr)
        
        # Perfect predictions -> TPR=1, FPR=0 for both groups
        assert score == 1.0
    
    def test_equalized_odds_disparity(self):
        """Test equalized odds with disparity."""
        # Group 0: perfect predictions
        # Group 1: all wrong
        predictions = np.array([1, 1, 0, 0, 0, 0, 1, 1])
        labels = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.equalized_odds(predictions, labels, protected_attr)
        
        # Should have low score due to disparity
        assert score < 0.5
    
    def test_disparate_impact_no_bias(self):
        """Test disparate impact with no bias."""
        predictions = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        ratio = FairnessMetrics.disparate_impact(predictions, protected_attr, privileged_group=0)
        
        # Both groups have 50% positive rate -> ratio = 1.0
        assert ratio == 1.0
    
    def test_disparate_impact_bias(self):
        """Test disparate impact with bias."""
        predictions = np.array([1, 1, 1, 1, 0, 0, 1, 1])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        ratio = FairnessMetrics.disparate_impact(predictions, protected_attr, privileged_group=0)
        
        # Privileged: 100%, Unprivileged: 50% -> ratio = 0.5
        assert ratio == 0.5
    
    def test_disparate_impact_edge_cases(self):
        """Test disparate impact edge cases."""
        # All zeros
        predictions = np.array([0, 0, 0, 0])
        protected_attr = np.array([0, 0, 1, 1])
        
        ratio = FairnessMetrics.disparate_impact(predictions, protected_attr, privileged_group=0)
        assert ratio == 1.0
        
        # Empty privileged group
        predictions = np.array([1, 1])
        protected_attr = np.array([1, 1])
        
        ratio = FairnessMetrics.disparate_impact(predictions, protected_attr, privileged_group=0)
        assert ratio == 1.0
    
    def test_equal_opportunity_perfect(self):
        """Test equal opportunity with perfect equality."""
        predictions = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        labels = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.equal_opportunity(predictions, labels, protected_attr)
        
        # Both groups have TPR = 1.0
        assert score == 1.0
    
    def test_equal_opportunity_disparity(self):
        """Test equal opportunity with disparity."""
        predictions = np.array([1, 1, 0, 0, 0, 0, 0, 0])
        labels = np.array([1, 1, 0, 0, 1, 1, 0, 0])
        protected_attr = np.array([0, 0, 0, 0, 1, 1, 1, 1])
        
        score = FairnessMetrics.equal_opportunity(predictions, labels, protected_attr)
        
        # Group 0: TPR=1.0, Group 1: TPR=0.0 -> disparity=1.0
        assert score == 0.0


class TestBiasAnalyzer:
    """Test bias analyzer."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset."""
        np.random.seed(42)
        return {
            "gender": np.array([0, 0, 0, 0, 1, 1, 1, 1] * 10),
            "age": np.random.randint(18, 65, 80),
            "feature1": np.random.randn(80),
            "feature2": np.random.randn(80)
        }
    
    @pytest.fixture
    def sample_predictions(self):
        """Create sample predictions."""
        np.random.seed(42)
        return np.random.randint(0, 2, 80)
    
    @pytest.fixture
    def sample_labels(self):
        """Create sample labels."""
        np.random.seed(42)
        return np.random.randint(0, 2, 80)
    
    def test_analyze_dataset_basic(self, sample_data, sample_predictions, sample_labels):
        """Test basic dataset analysis."""
        analyzer = BiasAnalyzer(fairness_threshold=0.8)
        
        report = analyzer.analyze_dataset(
            dataset_name="test_dataset",
            data=sample_data,
            protected_attributes=["gender"],
            predictions=sample_predictions,
            labels=sample_labels
        )
        
        assert isinstance(report, BiasReport)
        assert report.dataset_name == "test_dataset"
        assert report.total_samples == 80
        assert "gender" in report.protected_attributes
        assert "gender_demographic_parity" in report.fairness_scores
        assert "gender_equalized_odds" in report.fairness_scores
    
    def test_analyze_dataset_no_predictions(self, sample_data):
        """Test analysis without predictions."""
        analyzer = BiasAnalyzer()
        
        report = analyzer.analyze_dataset(
            dataset_name="test_dataset",
            data=sample_data,
            protected_attributes=["gender"]
        )
        
        assert isinstance(report, BiasReport)
        assert len(report.fairness_scores) == 0  # No metrics without predictions
    
    def test_small_group_detection(self):
        """Test detection of small groups."""
        analyzer = BiasAnalyzer(min_group_size=10)
        
        data = {
            "gender": np.array([0] * 50 + [1] * 5)  # Group 1 has only 5 samples
        }
        
        report = analyzer.analyze_dataset(
            dataset_name="test",
            data=data,
            protected_attributes=["gender"]
        )
        
        # Should have violation for small group
        small_group_violations = [
            v for v in report.violations
            if v["type"] == "small_group_size"
        ]
        assert len(small_group_violations) > 0
    
    def test_fairness_violation_detection(self):
        """Test detection of fairness violations."""
        analyzer = BiasAnalyzer(fairness_threshold=0.8)
        
        # Create biased predictions
        data = {
            "gender": np.array([0] * 40 + [1] * 40)
        }
        predictions = np.array([1] * 40 + [0] * 40)  # All positive for group 0, all negative for group 1
        labels = np.array([1] * 40 + [1] * 40)
        
        report = analyzer.analyze_dataset(
            dataset_name="biased_dataset",
            data=data,
            protected_attributes=["gender"],
            predictions=predictions,
            labels=labels
        )
        
        # Should detect violations
        assert len(report.violations) > 0
        assert report.severity in ["high", "critical"]
    
    def test_severity_calculation(self):
        """Test severity level calculation."""
        analyzer = BiasAnalyzer(fairness_threshold=0.8)
        
        # No violations -> low severity
        report1 = BiasReport(
            dataset_name="test",
            total_samples=100,
            protected_attributes=["gender"],
            fairness_scores={"gender_dp": 0.9},
            violations=[],
            recommendations=[],
            severity="low"
        )
        assert report1.severity == "low"
        
        # Critical violations
        violations = [
            {"type": "demographic_parity_violation", "score": 0.3},
            {"type": "equalized_odds_violation", "score": 0.2}
        ]
        severity = analyzer._calculate_severity(violations, {})
        assert severity == "critical"
    
    def test_detect_protected_attributes(self):
        """Test automatic detection of protected attributes."""
        analyzer = BiasAnalyzer()
        
        data = {
            "user_gender": np.array([0, 1, 0, 1]),
            "age_group": np.array([1, 2, 3, 1]),
            "ethnicity_code": np.array([0, 1, 2, 0]),
            "feature_x": np.array([1.0, 2.0, 3.0, 4.0])
        }
        
        detected = analyzer.detect_protected_attributes(data)
        
        assert "user_gender" in detected
        assert "age_group" in detected
        assert "ethnicity_code" in detected
        assert "feature_x" not in detected
    
    def test_generate_mitigation_strategy(self):
        """Test mitigation strategy generation."""
        analyzer = BiasAnalyzer()
        
        report = BiasReport(
            dataset_name="test",
            total_samples=100,
            protected_attributes=["gender"],
            fairness_scores={"gender_dp": 0.5},
            violations=[
                {
                    "type": "demographic_parity_violation",
                    "attribute": "gender",
                    "score": 0.5
                },
                {
                    "type": "small_group_size",
                    "attribute": "age",
                    "groups": ["65+"]
                }
            ],
            recommendations=[],
            severity="high"
        )
        
        strategy = analyzer.generate_mitigation_strategy(report)
        
        assert strategy["severity"] == "high"
        assert strategy["priority"] == "high"
        assert len(strategy["strategies"]) > 0
        
        # Should have reweighting/resampling for demographic parity
        methods = [s["method"] for s in strategy["strategies"]]
        assert "reweighting" in methods or "resampling" in methods
        assert "data_collection" in methods
    
    def test_multiple_protected_attributes(self, sample_data, sample_predictions, sample_labels):
        """Test analysis with multiple protected attributes."""
        analyzer = BiasAnalyzer()
        
        report = analyzer.analyze_dataset(
            dataset_name="test",
            data=sample_data,
            protected_attributes=["gender", "age"],
            predictions=sample_predictions,
            labels=sample_labels
        )
        
        assert "gender_demographic_parity" in report.fairness_scores
        assert "age_demographic_parity" in report.fairness_scores
    
    def test_missing_protected_attribute(self, sample_data, sample_predictions):
        """Test handling of missing protected attribute."""
        analyzer = BiasAnalyzer()
        
        report = analyzer.analyze_dataset(
            dataset_name="test",
            data=sample_data,
            protected_attributes=["nonexistent_attr"],
            predictions=sample_predictions
        )
        
        # Should not crash, just skip missing attribute
        assert isinstance(report, BiasReport)
    
    def test_report_to_dict(self):
        """Test report serialization."""
        report = BiasReport(
            dataset_name="test",
            total_samples=100,
            protected_attributes=["gender"],
            fairness_scores={"gender_dp": 0.85},
            violations=[],
            recommendations=["Collect more data"],
            severity="low"
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["dataset_name"] == "test"
        assert report_dict["total_samples"] == 100
        assert report_dict["fairness_scores"]["gender_dp"] == 0.85


class TestProtectedAttribute:
    """Test protected attribute enum."""
    
    def test_enum_values(self):
        """Test enum values."""
        assert ProtectedAttribute.GENDER == "gender"
        assert ProtectedAttribute.AGE == "age"
        assert ProtectedAttribute.ETHNICITY == "ethnicity"
        assert ProtectedAttribute.RELIGION == "religion"


class TestFairnessMetric:
    """Test fairness metric enum."""
    
    def test_enum_values(self):
        """Test enum values."""
        assert FairnessMetric.DEMOGRAPHIC_PARITY == "demographic_parity"
        assert FairnessMetric.EQUALIZED_ODDS == "equalized_odds"
        assert FairnessMetric.DISPARATE_IMPACT == "disparate_impact"


@pytest.mark.slow
class TestBiasAnalysisPerformance:
    """Performance tests for bias analysis."""
    
    def test_large_dataset_analysis(self):
        """Test analysis on large dataset."""
        np.random.seed(42)
        
        data = {
            "gender": np.random.randint(0, 2, 10000),
            "age": np.random.randint(18, 65, 10000),
            "feature1": np.random.randn(10000)
        }
        predictions = np.random.randint(0, 2, 10000)
        labels = np.random.randint(0, 2, 10000)
        
        analyzer = BiasAnalyzer()
        
        import time
        start = time.time()
        
        report = analyzer.analyze_dataset(
            dataset_name="large_dataset",
            data=data,
            protected_attributes=["gender", "age"],
            predictions=predictions,
            labels=labels
        )
        
        elapsed = time.time() - start
        
        assert isinstance(report, BiasReport)
        assert elapsed < 5.0, f"Analysis too slow: {elapsed}s"
