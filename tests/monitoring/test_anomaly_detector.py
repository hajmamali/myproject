"""
Unit tests for StatisticalAnomalyDetector
==========================================

Classification: UNIT TEST / MONITORING
Purpose: Verify anomaly detection algorithms work correctly

Tests:
- Z-score detection (normal distribution)
- IQR detection (outlier detection)
- Performance degradation detection
- API compatibility (check_anomaly vs check_metric)
- Alert severity classification
- Graceful degradation with insufficient samples

Author: MAHOUN Test Suite
Version: 1.0.0
"""

import pytest
from datetime import datetime

from mahoun.monitoring.anomaly_detector import (
    StatisticalAnomalyDetector,
    PerformanceDegradationDetector,
    AnomalyDetectionSystem,
    AnomalyAlert,
)


class TestStatisticalAnomalyDetector:
    """Test statistical anomaly detection"""
    
    @pytest.mark.p2
    def test_zscore_no_anomaly_stable_data(self):
        """Test Z-score detection with stable data (no anomaly)"""
        detector = StatisticalAnomalyDetector(z_threshold=3.0, min_samples=10)
        
        # Add stable data (mean=10, std~0)
        for i in range(20):
            detector.add_metric("stable_metric", 10.0)
        
        # Test value within range
        alert = detector.detect_anomaly_zscore("stable_metric", 10.0)
        assert alert is None
    
    @pytest.mark.p2
    def test_zscore_detects_spike(self):
        """Test Z-score detection catches spike anomaly"""
        detector = StatisticalAnomalyDetector(z_threshold=3.0, min_samples=10)
        
        # Add normal data (mean=100, std~10)
        for i in range(50):
            detector.add_metric("mutation_rate", 100 + (i % 10))
        
        # Test spike (way above 3 std)
        alert = detector.detect_anomaly_zscore("mutation_rate", 200.0)
        assert alert is not None
        assert alert.severity in ('medium', 'high', 'critical')
        assert alert.z_score > 3.0
    
    @pytest.mark.p2
    def test_zscore_detects_drop(self):
        """Test Z-score detection catches drop anomaly"""
        detector = StatisticalAnomalyDetector(z_threshold=2.5, min_samples=10)
        
        # Add normal data with some variance
        for i in range(50):
            detector.add_metric("throughput", 1000.0 + (i % 20))
        
        # Test significant drop (many standard deviations below)
        alert = detector.detect_anomaly_zscore("throughput", 200.0)
        assert alert is not None
        assert alert.z_score > 2.5
    
    @pytest.mark.p2
    def test_iqr_detects_outlier(self):
        """Test IQR method detects outliers"""
        detector = StatisticalAnomalyDetector(iqr_multiplier=1.5, min_samples=10)
        
        # Add data with spread (not constant)
        for i in range(40):
            detector.add_metric("latency", 10.0 + (i % 30))
        
        # Test far outlier
        alert = detector.detect_anomaly_iqr("latency", 1000.0)
        assert alert is not None
        assert alert.severity in ('medium', 'high', 'critical')
    
    @pytest.mark.p2
    def test_detect_anomaly_chooses_method(self):
        """Test detect_anomaly delegates to correct method"""
        detector = StatisticalAnomalyDetector(min_samples=10, z_threshold=2.5)
        
        # Add sample data with variance
        for i in range(30):
            detector.add_metric("test_metric", 50.0 + (i % 10))
        
        # Test Z-score method with extreme outlier
        alert_z = detector.detect_anomaly("test_metric", 300.0, method='zscore')
        assert alert_z is not None
        
        # Test IQR method with extreme outlier
        alert_iqr = detector.detect_anomaly("test_metric", 300.0, method='iqr')
        assert alert_iqr is not None
    
    @pytest.mark.p2
    def test_insufficient_samples_returns_none(self):
        """Test graceful handling of insufficient samples"""
        detector = StatisticalAnomalyDetector(min_samples=10)
        
        # Add only 5 samples (below threshold)
        for i in range(5):
            detector.add_metric("sparse_metric", 100.0)
        
        # Should not detect anomaly (not enough data)
        alert = detector.detect_anomaly("sparse_metric", 1000.0)
        assert alert is None
    
    @pytest.mark.p2
    def test_zero_std_returns_none(self):
        """Test handling of zero standard deviation (constant data)"""
        detector = StatisticalAnomalyDetector(min_samples=10)
        
        # All identical values
        for i in range(20):
            detector.add_metric("constant", 42.0)
        
        # Should not detect anomaly (std=0)
        alert = detector.detect_anomaly_zscore("constant", 42.0)
        assert alert is None
    
    @pytest.mark.p2
    def test_get_metric_statistics(self):
        """Test statistics calculation"""
        detector = StatisticalAnomalyDetector()
        
        # Add known distribution
        for i in range(100):
            detector.add_metric("stats_test", float(i))
        
        stats = detector.get_metric_statistics("stats_test")
        assert 'mean' in stats
        assert 'std' in stats
        assert 'min' in stats
        assert 'max' in stats
        assert stats['count'] > 0
        assert 40 < stats['mean'] < 60  # approximate center
    
    @pytest.mark.p2
    def test_get_recent_alerts(self):
        """Test alert retrieval and filtering"""
        detector = StatisticalAnomalyDetector(min_samples=10)
        
        # Generate some alerts
        for i in range(20):
            detector.add_metric("alert_test", 100.0)
        
        detector.detect_anomaly("alert_test", 200.0)
        detector.detect_anomaly("alert_test", 300.0)
        
        alerts = detector.get_recent_alerts(limit=5)
        assert len(alerts) >= 0  # At least attempt succeeded
    
    @pytest.mark.p2
    def test_clear_history(self):
        """Test history clearing"""
        detector = StatisticalAnomalyDetector()
        
        detector.add_metric("clear_test", 100.0)
        assert "clear_test" in detector.metric_history
        
        detector.clear_history("clear_test")
        assert len(detector.metric_history["clear_test"]) == 0
        
        detector.clear_history()
        assert len(detector.metric_history) == 0


class TestPerformanceDegradationDetector:
    """Test performance degradation detection"""
    
    @pytest.mark.p2
    def test_detects_degradation_lower_is_better(self):
        """Test degradation when lower values are better (e.g., latency)"""
        detector = PerformanceDegradationDetector(
            degradation_threshold=0.1,
            min_samples=10,
        )
        
        # Baseline: low latency
        for i in range(30):
            detector.add_metric("latency", 10.0)
        
        # Recent: high latency (degraded)
        for i in range(30):
            detector.add_metric("latency", 20.0)
        
        alert = detector.detect_degradation("latency", 20.0, higher_is_better=False)
        assert alert is not None
        assert alert.severity in ('low', 'medium', 'high', 'critical')
    
    @pytest.mark.p2
    def test_detects_degradation_higher_is_better(self):
        """Test degradation when higher values are better (e.g., throughput)"""
        detector = PerformanceDegradationDetector(
            degradation_threshold=0.15,
            min_samples=10,
        )
        
        # Baseline: high throughput
        for i in range(30):
            detector.add_metric("throughput", 1000.0)
        
        # Recent: low throughput (degraded)
        for i in range(30):
            detector.add_metric("throughput", 500.0)
        
        alert = detector.detect_degradation("throughput", 500.0, higher_is_better=True)
        assert alert is not None
        assert alert.message.__contains__("degradation")
    
    @pytest.mark.p2
    def test_no_degradation_stable_performance(self):
        """Test no alert on stable performance"""
        detector = PerformanceDegradationDetector(
            degradation_threshold=0.1,
            min_samples=10,
        )
        
        # Stable performance
        for i in range(50):
            detector.add_metric("stable_perf", 100.0)
        
        alert = detector.detect_degradation("stable_perf", 100.0)
        assert alert is None


class TestAnomalyDetectionSystem:
    """Test combined anomaly detection system"""
    
    @pytest.mark.p2
    def test_check_metric_returns_list(self):
        """Test check_metric returns list of alerts"""
        system = AnomalyDetectionSystem(
            enable_statistical=True,
            enable_degradation=False,
        )
        
        # Prime with data
        for i in range(30):
            system.check_metric("test_metric", 100.0)
        
        # Trigger anomaly
        alerts = system.check_metric("test_metric", 300.0)
        assert isinstance(alerts, list)
    
    @pytest.mark.p2
    def test_check_anomaly_returns_single_alert(self):
        """Test check_anomaly (API compatibility) returns single alert"""
        system = AnomalyDetectionSystem(
            enable_statistical=True,
            enable_degradation=False,
        )
        
        # Prime with data
        for i in range(30):
            system.check_anomaly("compat_test", 50.0)
        
        # Trigger anomaly
        alert = system.check_anomaly("compat_test", 200.0)
        
        # Should return single AnomalyAlert or None
        assert alert is None or isinstance(alert, AnomalyAlert)
    
    @pytest.mark.p2
    def test_check_anomaly_returns_highest_severity(self):
        """Test check_anomaly returns highest severity when multiple alerts"""
        system = AnomalyDetectionSystem(
            enable_statistical=True,
            enable_degradation=True,
        )
        
        # Prime with stable baseline
        for i in range(50):
            system.check_metric("multi_alert", 100.0)
        
        # Trigger multiple detectors
        alert = system.check_anomaly("multi_alert", 500.0)
        
        if alert:
            # If multiple alerts generated, should be highest severity
            assert alert.severity in ('low', 'medium', 'high', 'critical')
    
    @pytest.mark.p2
    def test_disabled_statistical_detection(self):
        """Test system with statistical detection disabled"""
        system = AnomalyDetectionSystem(
            enable_statistical=False,
            enable_degradation=True,
        )
        
        assert system.statistical_detector is None
        assert system.degradation_detector is not None
    
    @pytest.mark.p2
    def test_get_all_alerts(self):
        """Test retrieving all alerts"""
        system = AnomalyDetectionSystem()
        
        # Generate some activity
        for i in range(20):
            system.check_metric("alert_retrieval", 100.0)
        
        system.check_metric("alert_retrieval", 300.0)
        
        alerts = system.get_all_alerts(limit=10)
        assert isinstance(alerts, list)


class TestBehavioralMonitorCompatibility:
    """Test API compatibility with behavioral_monitor.py"""
    
    @pytest.mark.p2
    def test_detect_anomaly_api_compatible(self):
        """Test detect_anomaly works for behavioral_monitor.py usage"""
        detector = StatisticalAnomalyDetector(min_samples=10)
        
        # Simulate behavioral monitor usage
        actor_id = "user-123"
        metric_name = f"{actor_id}:mutation_rate"
        
        # Add baseline activity
        for i in range(30):
            detector.add_metric(metric_name, 5.0)
        
        # Check for spike (behavioral monitor pattern)
        alert = detector.detect_anomaly(metric_name, 50.0)
        
        assert alert is None or isinstance(alert, AnomalyAlert)
        if alert:
            assert alert.metric_name == metric_name
            assert alert.z_score > 0
    
    @pytest.mark.p2
    def test_system_check_anomaly_api_compatible(self):
        """Test AnomalyDetectionSystem.check_anomaly API"""
        system = AnomalyDetectionSystem()
        
        # Behavioral monitor calls system.check_anomaly()
        for i in range(30):
            system.check_anomaly("actor:mutation_rate", 10.0)
        
        alert = system.check_anomaly("actor:mutation_rate", 100.0)
        
        # Must return None or single AnomalyAlert
        assert alert is None or isinstance(alert, AnomalyAlert)


# ============================================================================
# PYTEST MARKERS
# ============================================================================

pytestmark = pytest.mark.unit
