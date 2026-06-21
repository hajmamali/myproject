"""
Tests for Metrics Collection
=============================
Unit tests for the metrics collection system.

Tests both the old API (via migration layer) and new Prometheus-style API.
"""

import pytest
import time
import asyncio
from mahoun.infrastructure.observability.metrics_migration import (
    MetricsCollector,
    get_metrics_collector
)


def test_metrics_collector_counter():
    """Test counter metrics (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_counter("test.counter", 1)
    collector.record_counter("test.counter", 5)
    
    metrics = collector.get_metrics("test.counter")
    assert metrics["counter"] == 6
    assert metrics["history_count"] == 2


def test_metrics_collector_gauge():
    """Test gauge metrics (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_gauge("test.gauge", 42.5)
    collector.record_gauge("test.gauge", 50.0)
    
    metrics = collector.get_metrics("test.gauge")
    assert metrics["gauge"] == 50.0  # Latest value
    assert metrics["history_count"] == 2


def test_metrics_collector_timing():
    """Test timing metrics (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_timing("test.function", 150.5)
    
    metrics = collector.get_metrics("test.function")
    assert "percentiles" in metrics
    assert metrics["history_count"] == 1


def test_metrics_collector_get_all():
    """Test getting all metrics (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_counter("counter1", 10)
    collector.record_counter("counter2", 20)
    collector.record_gauge("gauge1", 100.0)
    
    all_metrics = collector.get_metrics()
    
    assert "counters" in all_metrics
    assert "gauges" in all_metrics
    assert all_metrics["counters"]["counter1"] == 10
    assert all_metrics["counters"]["counter2"] == 20
    assert all_metrics["gauges"]["gauge1"] == 100.0


def test_metrics_collector_summary():
    """Test metrics summary (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_counter("test1", 5)
    collector.record_gauge("test2", 10.0)
    
    summary = collector.get_summary()
    
    assert "total_counters" in summary
    assert "total_gauges" in summary
    assert "total_data_points" in summary
    assert summary["total_counters"] >= 1
    assert summary["total_gauges"] >= 1


def test_metrics_collector_reset():
    """Test resetting metrics (OLD API)"""
    collector = MetricsCollector()
    
    collector.record_counter("test", 10)
    assert collector.get_metrics("test")["counter"] == 10
    
    # Reset specific metric
    collector.reset("test")
    metrics = collector.get_metrics("test")
    assert metrics["counter"] == 0
    assert metrics["history_count"] == 0


def test_metrics_collector_reset_all():
    """Test resetting all metrics (OLD API)"""
    # Disable system metrics for clean test
    collector = MetricsCollector(enable_system_metrics=False)
    
    collector.record_counter("test1", 10)
    collector.record_gauge("test2", 20.0)
    
    # Reset all
    collector.reset()
    
    all_metrics = collector.get_metrics()
    assert len(all_metrics["counters"]) == 0
    assert len(all_metrics["gauges"]) == 0

def test_get_metrics_collector_singleton():
    """Test that get_metrics_collector returns singleton"""
    collector1 = get_metrics_collector()
    collector2 = get_metrics_collector()
    
    assert collector1 is collector2


def test_prometheus_export():
    """Test Prometheus metrics export (NEW API)"""
    collector = MetricsCollector()
    
    # Register and use metrics (NEW API)
    counter = collector.register_counter("test_counter")
    counter.inc(5)
    
    gauge = collector.register_gauge("test_gauge")
    gauge.set(42.0)
    
    # Export to Prometheus format
    prometheus_output = collector.to_prometheus()
    
    assert "test_counter" in prometheus_output
    assert "test_gauge" in prometheus_output
    assert "42.0" in prometheus_output


def test_new_api_counter():
    """Test NEW Prometheus-style counter API"""
    collector = MetricsCollector()
    
    counter = collector.register_counter("new_counter")
    counter.inc(1)
    counter.inc(5)
    
    # Verify via new API
    all_metrics = collector.get_all_metrics()
    assert all_metrics["counters"]["new_counter"]["value"] == 6


def test_new_api_gauge():
    """Test NEW Prometheus-style gauge API"""
    collector = MetricsCollector()
    
    gauge = collector.register_gauge("new_gauge")
    gauge.set(100.0)
    gauge.inc(10.0)
    gauge.dec(5.0)
    
    # Verify via new API
    all_metrics = collector.get_all_metrics()
    assert all_metrics["gauges"]["new_gauge"]["value"] == 105.0


def test_new_api_histogram():
    """Test NEW Prometheus-style histogram API"""
    collector = MetricsCollector()
    
    histogram = collector.register_histogram("new_histogram")
    histogram.observe(100.0)
    histogram.observe(200.0)
    histogram.observe(150.0)
    
    # Verify via new API
    all_metrics = collector.get_all_metrics()
    assert all_metrics["histograms"]["new_histogram"]["count"] == 3
    
    percentiles = all_metrics["histograms"]["new_histogram"]["percentiles"]
    assert percentiles["p50"] == 150.0  # Median


def test_mixed_api_usage():
    """Test that OLD and NEW APIs work together"""
    collector = MetricsCollector()
    
    # Use OLD API
    collector.record_counter("old_counter", 10)
    collector.record_gauge("old_gauge", 50.0)
    
    # Use NEW API
    new_counter = collector.register_counter("new_counter")
    new_counter.inc(20)
    
    new_gauge = collector.register_gauge("new_gauge")
    new_gauge.set(75.0)
    
    # Verify both work
    old_metrics = collector.get_metrics()
    assert old_metrics["counters"]["old_counter"] == 10
    assert old_metrics["counters"]["new_counter"] == 20
    assert old_metrics["gauges"]["old_gauge"] == 50.0
    assert old_metrics["gauges"]["new_gauge"] == 75.0


def test_histogram_percentiles():
    """Test histogram percentile calculations"""
    collector = MetricsCollector()
    
    histogram = collector.register_histogram("latency")
    
    # Add values
    for value in [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]:
        histogram.observe(value)
    
    all_metrics = collector.get_all_metrics()
    percentiles = all_metrics["histograms"]["latency"]["percentiles"]
    
    assert percentiles["p50"] == 50  # Median
    assert percentiles["p95"] == 95  # 95th percentile
    assert percentiles["p99"] == 99  # 99th percentile


def test_counter_with_labels():
    """Test counter with labels (NEW API)"""
    collector = MetricsCollector()
    
    counter = collector.register_counter("http_requests", labels={"method": "GET", "status": "200"})
    counter.inc(10)
    
    prometheus_output = collector.to_prometheus()
    assert 'http_requests{method="GET",status="200"}' in prometheus_output


def test_gauge_with_labels():
    """Test gauge with labels (NEW API)"""
    collector = MetricsCollector()
    
    gauge = collector.register_gauge("temperature", labels={"location": "server1"})
    gauge.set(75.5)
    
    prometheus_output = collector.to_prometheus()
    assert 'temperature{location="server1"}' in prometheus_output


def test_timing_to_histogram_conversion():
    """Test that OLD timing API converts to histogram"""
    collector = MetricsCollector()
    
    # Use OLD timing API
    collector.record_timing("api_call", 100.0)
    collector.record_timing("api_call", 200.0)
    collector.record_timing("api_call", 150.0)
    
    # Verify it's stored as histogram
    all_metrics = collector.get_all_metrics()
    assert "api_call.duration_ms" in all_metrics["histograms"]
    assert all_metrics["histograms"]["api_call.duration_ms"]["count"] == 3
