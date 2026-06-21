"""
Comprehensive tests for data quality metrics.

Tests cover:
- Quality score calculation
- Completeness, consistency, validity checks
- Data drift detection
- Statistical tests
- Edge cases
"""

import pytest
import numpy as np
from scipy import stats
from mahoun.governance.quality_metrics import (
    DataQualityAnalyzer,
    QualityReport,
    DriftReport
)


class TestDataQualityAnalyzer:
    """Test data quality analyzer."""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample dataset."""
        np.random.seed(42)
        return {
            "feature1": np.random.randn(100),
            "feature2": np.random.randint(0, 10, 100),
            "feature3": np.array(["a", "b", "c"] * 33 + ["a"])
        }
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return DataQualityAnalyzer(
            completeness_threshold=0.95,
            consistency_threshold=0.90,
            drift_threshold=0.1
        )
    
    def test_analyze_quality_basic(self, analyzer, sample_data):
        """Test basic quality analysis."""
        report = analyzer.analyze_quality(
            dataset_name="test_dataset",
            data=sample_data
        )
        
        assert isinstance(report, QualityReport)
        assert report.dataset_name == "test_dataset"
        assert report.total_samples == 100
        assert 0.0 <= report.quality_score <= 1.0
        assert 0.0 <= report.completeness_score <= 1.0
        assert 0.0 <= report.consistency_score <= 1.0
        assert 0.0 <= report.validity_score <= 1.0
    
    def test_completeness_perfect(self, analyzer):
        """Test completeness with no missing values."""
        data = {
            "feature1": np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            "feature2": np.array([10, 20, 30, 40, 50])
        }
        
        report = analyzer.analyze_quality("test", data)
        
        assert report.completeness_score == 1.0
        assert len([i for i in report.issues if i["type"] == "missing_values"]) == 0
    
    def test_completeness_with_missing(self, analyzer):
        """Test completeness with missing values."""
        data = {
            "feature1": np.array([1.0, np.nan, 3.0, np.nan, 5.0]),
            "feature2": np.array([10, 20, 30, 40, 50])
        }
        
        report = analyzer.analyze_quality("test", data)
        
        assert report.completeness_score < 1.0
        missing_issues = [i for i in report.issues if i["type"] == "missing_values"]
        assert len(missing_issues) > 0
        assert missing_issues[0]["feature"] == "feature1"
        assert missing_issues[0]["percentage"] == 40.0  # 2 out of 5
    
    def test_completeness_with_empty_strings(self, analyzer):
        """Test completeness with empty strings."""
        data = {
            "feature1": np.array(["a", "", "c", "", "e"], dtype=object)
        }
        
        report = analyzer.analyze_quality("test", data)
        
        assert report.completeness_score < 1.0
        missing_issues = [i for i in report.issues if i["type"] == "missing_values"]
        assert len(missing_issues) > 0
    
    def test_consistency_low_diversity(self, analyzer):
        """Test consistency with low diversity."""
        data = {
            "feature1": np.array([1, 1, 1, 1, 1, 1, 1, 1, 1, 2])  # 90% same value
        }
        
        report = analyzer.analyze_quality("test", data)
        
        low_diversity_issues = [i for i in report.issues if i["type"] == "low_diversity"]
        assert len(low_diversity_issues) > 0
        assert low_diversity_issues[0]["unique_ratio"] < 0.1
    
    def test_consistency_outliers(self, analyzer):
        """Test consistency with outliers."""
        np.random.seed(42)
        data = {
            "feature1": np.concatenate([
                np.random.randn(95),  # Normal data
                np.array([100, 200, 300, 400, 500])  # Outliers
            ])
        }
        
        report = analyzer.analyze_quality("test", data)
        
        outlier_issues = [i for i in report.issues if i["type"] == "outliers"]
        assert len(outlier_issues) > 0
    
    def test_outlier_detection_iqr(self, analyzer):
        """Test IQR-based outlier detection."""
        values = np.array([1, 2, 3, 4, 5, 6, 7, 8, 9, 100])
        
        outliers = analyzer._detect_outliers(values)
        
        assert outliers[-1] == True  # 100 is an outlier
        assert outliers[0] == False  # 1 is not an outlier
    
    def test_validity_with_schema(self, analyzer):
        """Test validity checking with schema."""
        data = {
            "age": np.array([25, 30, 35, 150, 40]),  # 150 is out of range
            "score": np.array([0.5, 0.7, 0.9, 1.2, 0.8])  # 1.2 is out of range
        }
        
        schema = {
            "age": {"type": "int", "min": 0, "max": 120},
            "score": {"type": "float", "min": 0.0, "max": 1.0}
        }
        
        report = analyzer.analyze_quality("test", data, schema=schema)
        
        out_of_range_issues = [i for i in report.issues if i["type"] == "out_of_range"]
        assert len(out_of_range_issues) > 0
    
    def test_report_to_dict(self):
        """Test report serialization."""
        report = QualityReport(
            dataset_name="test",
            total_samples=100,
            quality_score=0.85,
            completeness_score=0.90,
            consistency_score=0.85,
            validity_score=0.80,
            issues=[{"type": "missing_values", "count": 5}],
            recommendations=["Fix missing values"]
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["dataset_name"] == "test"
        assert report_dict["quality_score"] == 0.85
        assert len(report_dict["issues"]) == 1


class TestDriftDetection:
    """Test data drift detection."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return DataQualityAnalyzer(drift_threshold=0.1)
    
    def test_detect_drift_no_drift(self, analyzer):
        """Test drift detection with no drift."""
        np.random.seed(42)
        
        reference_data = {
            "feature1": np.random.randn(1000),
            "feature2": np.random.randint(0, 10, 1000)
        }
        
        # Same distribution
        np.random.seed(42)
        current_data = {
            "feature1": np.random.randn(1000),
            "feature2": np.random.randint(0, 10, 1000)
        }
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        assert isinstance(report, DriftReport)
        assert report.drift_detected == False
        assert report.drift_score < analyzer.drift_threshold
    
    def test_detect_drift_with_drift(self, analyzer):
        """Test drift detection with significant drift."""
        np.random.seed(42)
        
        reference_data = {
            "feature1": np.random.randn(1000)  # Mean=0, Std=1
        }
        
        current_data = {
            "feature1": np.random.randn(1000) + 5  # Mean=5, Std=1 (shifted)
        }
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        assert report.drift_detected == True
        assert report.drift_score > analyzer.drift_threshold
        assert "feature1" in report.feature_drifts
    
    def test_kolmogorov_smirnov_test(self, analyzer):
        """Test KS test for numeric features."""
        np.random.seed(42)
        
        reference_data = {
            "feature1": np.random.normal(0, 1, 1000)
        }
        
        current_data = {
            "feature1": np.random.normal(2, 1, 1000)  # Different mean
        }
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        assert "feature1" in report.statistical_tests
        test_result = report.statistical_tests["feature1"]
        assert test_result["test"] == "kolmogorov_smirnov"
        assert test_result["drift_detected"] == True
        assert test_result["p_value"] < 0.05
    
    def test_chi_square_test(self, analyzer):
        """Test chi-square test for categorical features."""
        np.random.seed(42)
        
        reference_data = {
            "category": np.array(["a"] * 500 + ["b"] * 300 + ["c"] * 200)
        }
        
        current_data = {
            "category": np.array(["a"] * 200 + ["b"] * 300 + ["c"] * 500)  # Different distribution
        }
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        assert "category" in report.statistical_tests
        test_result = report.statistical_tests["category"]
        assert test_result["test"] == "chi_square"
    
    def test_drift_report_to_dict(self):
        """Test drift report serialization."""
        report = DriftReport(
            reference_dataset="ref",
            current_dataset="cur",
            drift_detected=True,
            drift_score=0.25,
            feature_drifts={"feature1": 0.3},
            statistical_tests={"feature1": {"test": "ks", "p_value": 0.01}}
        )
        
        report_dict = report.to_dict()
        
        assert report_dict["drift_detected"] == True
        assert report_dict["drift_score"] == 0.25
    
    def test_drift_missing_features(self, analyzer):
        """Test drift detection with missing features."""
        reference_data = {
            "feature1": np.random.randn(100),
            "feature2": np.random.randn(100)
        }
        
        current_data = {
            "feature1": np.random.randn(100)
            # feature2 missing
        }
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        # Should only analyze feature1
        assert "feature1" in report.feature_drifts
        assert "feature2" not in report.feature_drifts
    
    def test_drift_with_identical_data(self, analyzer):
        """Test drift detection with identical data."""
        data = {
            "feature1": np.array([1, 2, 3, 4, 5])
        }
        
        report = analyzer.detect_drift(data, data)
        
        assert report.drift_detected == False
        assert report.drift_score == 0.0


class TestEdgeCases:
    """Test edge cases and error handling."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance."""
        return DataQualityAnalyzer()
    
    def test_empty_dataset(self, analyzer):
        """Test with empty dataset."""
        data = {
            "feature1": np.array([])
        }
        
        # Should not crash
        report = analyzer.analyze_quality("empty", data)
        assert isinstance(report, QualityReport)
    
    def test_single_value_dataset(self, analyzer):
        """Test with single value."""
        data = {
            "feature1": np.array([42])
        }
        
        report = analyzer.analyze_quality("single", data)
        assert report.total_samples == 1
    
    def test_all_missing_values(self, analyzer):
        """Test with all missing values."""
        data = {
            "feature1": np.array([np.nan, np.nan, np.nan])
        }
        
        report = analyzer.analyze_quality("all_missing", data)
        assert report.completeness_score == 0.0
    
    def test_all_same_values(self, analyzer):
        """Test with all same values."""
        data = {
            "feature1": np.array([42] * 100)
        }
        
        report = analyzer.analyze_quality("same_values", data)
        
        # Should detect low diversity
        low_diversity_issues = [i for i in report.issues if i["type"] == "low_diversity"]
        assert len(low_diversity_issues) > 0
    
    def test_mixed_types(self, analyzer):
        """Test with mixed data types."""
        data = {
            "numeric": np.array([1.0, 2.0, 3.0]),
            "categorical": np.array(["a", "b", "c"]),
            "integer": np.array([10, 20, 30])
        }
        
        report = analyzer.analyze_quality("mixed", data)
        assert isinstance(report, QualityReport)
    
    def test_very_small_dataset(self, analyzer):
        """Test with very small dataset."""
        data = {
            "feature1": np.array([1, 2])
        }
        
        report = analyzer.analyze_quality("tiny", data)
        assert report.total_samples == 2


@pytest.mark.slow
class TestQualityMetricsPerformance:
    """Performance tests for quality metrics."""
    
    def test_large_dataset_analysis(self):
        """Test analysis on large dataset."""
        np.random.seed(42)
        
        data = {
            "feature1": np.random.randn(100000),
            "feature2": np.random.randint(0, 100, 100000),
            "feature3": np.random.choice(["a", "b", "c", "d"], 100000)
        }
        
        analyzer = DataQualityAnalyzer()
        
        import time
        start = time.time()
        
        report = analyzer.analyze_quality("large_dataset", data)
        
        elapsed = time.time() - start
        
        assert isinstance(report, QualityReport)
        assert elapsed < 5.0, f"Analysis too slow: {elapsed}s"
    
    def test_drift_detection_performance(self):
        """Test drift detection performance."""
        np.random.seed(42)
        
        reference_data = {
            "feature1": np.random.randn(10000),
            "feature2": np.random.randint(0, 100, 10000)
        }
        
        current_data = {
            "feature1": np.random.randn(10000),
            "feature2": np.random.randint(0, 100, 10000)
        }
        
        analyzer = DataQualityAnalyzer()
        
        import time
        start = time.time()
        
        report = analyzer.detect_drift(reference_data, current_data)
        
        elapsed = time.time() - start
        
        assert isinstance(report, DriftReport)
        assert elapsed < 2.0, f"Drift detection too slow: {elapsed}s"


class TestQualityScoreCalculation:
    """Test quality score calculation logic."""
    
    def test_weighted_average(self):
        """Test that quality score is weighted average."""
        analyzer = DataQualityAnalyzer()
        
        # Perfect scores
        data = {
            "feature1": np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        }
        
        report = analyzer.analyze_quality("test", data)
        
        # Quality = 0.4*completeness + 0.3*consistency + 0.3*validity
        expected = 0.4 * report.completeness_score + \
                   0.3 * report.consistency_score + \
                   0.3 * report.validity_score
        
        assert abs(report.quality_score - expected) < 0.01
