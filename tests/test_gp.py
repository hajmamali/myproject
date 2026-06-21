#!/usr/bin/env python3
"""
Unit Tests for Gaussian Process Uncertainty

این تست‌ها باید قبل از استفاده در production اجرا شوند.
اجرا: python -m pytest tests/test_gp.py -v
"""

import pytest
import numpy as np
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from mahoun.uncertainty.gaussian_process import (
    GaussianProcessUncertainty,
    GPConfig,
    KernelType,
    UncertaintyEstimate,
    CalibrationMetrics,
    ThreadSafeCache,
    create_gp_uncertainty,
    create_features_from_scores,
    HAS_GPYTORCH,
    HAS_SKLEARN,
)


# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def sample_data():
    """داده نمونه برای تست"""
    np.random.seed(42)
    X_train = np.random.randn(100, 5)
    y_train = np.sin(X_train[:, 0]) + 0.1 * np.random.randn(100)
    X_test = np.random.randn(20, 5)
    y_test = np.sin(X_test[:, 0]) + 0.1 * np.random.randn(20)
    return X_train, y_train, X_test, y_test


@pytest.fixture
def gp_config():
    """تنظیمات پیش‌فرض برای تست"""
    return GPConfig(
        num_inducing_points=20, num_epochs=10, use_cuda=False, mc_samples=20
    )


@pytest.fixture
def fitted_gp(sample_data, gp_config):
    """GP آموزش‌دیده"""
    X_train, y_train, _, _ = sample_data
    gp = GaussianProcessUncertainty(gp_config)
    gp.fit(X_train, y_train)
    return gp


# =============================================================================
# Test: Configuration
# =============================================================================


class TestGPConfig:
    """تست‌های تنظیمات"""

    def test_default_config(self):
        """تست تنظیمات پیش‌فرض"""
        config = GPConfig()
        assert config.kernel_type == KernelType.MATERN_52
        assert config.num_inducing_points == 100
        assert config.learning_rate == 0.01

    def test_invalid_inducing_points(self):
        """تست رد کردن inducing points نامعتبر"""
        with pytest.raises(ValueError, match="حداقل 10"):
            GPConfig(num_inducing_points=5)

    def test_invalid_learning_rate(self):
        """تست رد کردن learning rate نامعتبر"""
        with pytest.raises(ValueError, match="بین 0 و 1"):
            GPConfig(learning_rate=2.0)


# =============================================================================
# Test: Basic Functionality
# =============================================================================


class TestBasicFunctionality:
    """تست‌های عملکرد پایه"""

    def test_fit_and_predict(self, sample_data, gp_config):
        """تست آموزش و پیش‌بینی"""
        X_train, y_train, X_test, _ = sample_data

        gp = GaussianProcessUncertainty(gp_config)
        gp.fit(X_train, y_train)

        mean, std = gp.predict(X_test)

        assert mean.shape == (20,)
        assert std.shape == (20,)
        assert np.all(std > 0), "std باید مثبت باشد"

    def test_predict_without_fit(self, gp_config):
        """تست پیش‌بینی بدون آموزش"""
        gp = GaussianProcessUncertainty(gp_config)

        with pytest.raises(ValueError, match="not fitted"):
            gp.predict(np.random.randn(10, 5))

    def test_uncertainty_estimation(self, fitted_gp, sample_data):
        """تست تخمین عدم قطعیت"""
        _, _, X_test, _ = sample_data

        estimate = fitted_gp.estimate_uncertainty(X_test[0:1])

        assert isinstance(estimate, UncertaintyEstimate)
        assert estimate.epistemic_std >= 0
        assert estimate.aleatoric_std >= 0
        assert estimate.total_std >= 0
        assert estimate.confidence_interval_lower < estimate.confidence_interval_upper

    def test_legal_explanation_generated(self, fitted_gp, sample_data):
        """تست تولید توضیح حقوقی"""
        _, _, X_test, _ = sample_data

        estimate = fitted_gp.estimate_uncertainty(X_test[0:1])

        assert len(estimate.explanation_fa) > 0
        assert len(estimate.explanation_en) > 0
        assert "عدم قطعیت" in estimate.explanation_fa
        assert "Uncertainty" in estimate.explanation_en


# =============================================================================
# Test: Input Validation
# =============================================================================


class TestInputValidation:
    """تست‌های اعتبارسنجی ورودی"""

    def test_nan_rejection(self, fitted_gp):
        """تست رد کردن NaN"""
        X_nan = np.array([[1, 2, np.nan, 4, 5]])

        with pytest.raises(ValueError, match="NaN"):
            fitted_gp.predict(X_nan)

    def test_inf_rejection(self, fitted_gp):
        """تست رد کردن Inf"""
        X_inf = np.array([[1, 2, np.inf, 4, 5]])

        with pytest.raises(ValueError, match="Inf"):
            fitted_gp.predict(X_inf)

    def test_shape_mismatch(self, gp_config):
        """تست عدم تطابق شکل"""
        gp = GaussianProcessUncertainty(gp_config)

        X = np.random.randn(100, 5)
        y = np.random.randn(50)  # Wrong size

        with pytest.raises(ValueError, match="same number of samples"):
            gp.fit(X, y)

    def test_minimum_samples(self, gp_config):
        """تست حداقل نمونه"""
        gp = GaussianProcessUncertainty(gp_config)

        X = np.random.randn(5, 5)  # Too few
        y = np.random.randn(5)

        with pytest.raises(ValueError, match="at least"):
            gp.fit(X, y)


# =============================================================================
# Test: Calibration
# =============================================================================


class TestCalibration:
    """تست‌های کالیبراسیون"""

    def test_calibration(self, fitted_gp, sample_data):
        """تست کالیبراسیون"""
        _, _, X_test, y_test = sample_data

        metrics = fitted_gp.calibrate(X_test, y_test)

        assert isinstance(metrics, CalibrationMetrics)
        assert 0 <= metrics.expected_calibration_error <= 1
        assert 0 <= metrics.maximum_calibration_error <= 1

    def test_calibration_temperature(self, fitted_gp, sample_data):
        """تست temperature scaling"""
        _, _, X_test, y_test = sample_data

        fitted_gp.calibrate(X_test, y_test)

        assert fitted_gp._calibration_temperature > 0


# =============================================================================
# Test: Cache
# =============================================================================


class TestCache:
    """تست‌های کش"""

    def test_cache_hit(self, fitted_gp, sample_data):
        """تست hit کش"""
        _, _, X_test, _ = sample_data

        # First call
        _ = fitted_gp.predict(X_test)

        # Second call (should hit cache)
        _ = fitted_gp.predict(X_test)

        assert fitted_gp._cache._hits > 0

    def test_cache_clear(self, fitted_gp, sample_data):
        """تست پاک کردن کش"""
        _, _, X_test, _ = sample_data

        _ = fitted_gp.predict(X_test)
        fitted_gp.clear_cache()

        assert fitted_gp._cache._hits == 0
        assert fitted_gp._cache._misses == 0

    def test_thread_safe_cache(self):
        """تست thread-safety کش"""
        cache = ThreadSafeCache(max_size=100, ttl_seconds=60)

        # Concurrent access simulation
        import threading

        def writer():
            for i in range(100):
                cache.set(f"key_{i}", f"value_{i}")

        def reader():
            for i in range(100):
                cache.get(f"key_{i}")

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should not raise any exceptions


# =============================================================================
# Test: Metrics
# =============================================================================


class TestMetrics:
    """تست‌های معیارها"""

    def test_get_metrics(self, fitted_gp, sample_data):
        """تست دریافت معیارها"""
        _, _, X_test, _ = sample_data

        _ = fitted_gp.predict(X_test)
        metrics = fitted_gp.get_metrics()

        assert "latency" in metrics
        assert "cache" in metrics
        assert "calibration" in metrics
        assert metrics["is_fitted"] == True

    def test_latency_tracking(self, fitted_gp, sample_data):
        """تست ردیابی تأخیر"""
        _, _, X_test, _ = sample_data

        for _ in range(10):
            _ = fitted_gp.predict(X_test)

        metrics = fitted_gp.get_metrics()
        assert metrics["latency"]["count"] >= 10


# =============================================================================
# Test: Utility Functions
# =============================================================================


class TestUtilityFunctions:
    """تست‌های توابع کمکی"""

    def test_create_features_from_scores(self):
        """تست ساخت ویژگی از امتیازات"""
        scores = np.array([0.5, 0.7, 0.9])
        features = create_features_from_scores(scores)

        assert features.shape[0] == 3
        assert features.shape[1] > 1  # Should have multiple features

    def test_factory_function(self):
        """تست factory function"""
        gp = create_gp_uncertainty(
            kernel_type="matern_52", num_inducing_points=50, use_cuda=False
        )

        assert isinstance(gp, GaussianProcessUncertainty)
        assert gp.config.kernel_type == KernelType.MATERN_52
        assert gp.config.num_inducing_points == 50


# =============================================================================
# Test: Edge Cases
# =============================================================================


class TestEdgeCases:
    """تست‌های موارد لبه‌ای"""

    def test_single_sample_prediction(self, fitted_gp):
        """تست پیش‌بینی تک نمونه"""
        X_single = np.random.randn(1, 5)

        mean, std = fitted_gp.predict(X_single)

        assert mean.shape == (1,)
        assert std.shape == (1,)

    def test_1d_input(self, gp_config):
        """تست ورودی یک‌بعدی"""
        gp = GaussianProcessUncertainty(gp_config)

        X = np.random.randn(100)  # 1D
        y = np.sin(X) + 0.1 * np.random.randn(100)

        gp.fit(X, y)

        X_test = np.random.randn(10)
        mean, std = gp.predict(X_test)

        assert mean.shape == (10,)


# =============================================================================
# Benchmark
# =============================================================================


class TestBenchmark:
    """بنچمارک‌ها"""

    def test_prediction_latency(self, fitted_gp, sample_data):
        """تست تأخیر پیش‌بینی"""
        import time

        _, _, X_test, _ = sample_data

        # Warm up
        _ = fitted_gp.predict(X_test)
        fitted_gp.clear_cache()

        # Measure
        start = time.time()
        for _ in range(100):
            fitted_gp.clear_cache()
            _ = fitted_gp.predict(X_test)
        elapsed = (time.time() - start) * 1000 / 100  # ms per prediction

        print(f"\n📊 Average prediction latency: {elapsed:.2f}ms")

        # Should be under 200ms for 20 samples
        assert elapsed < 200, f"Prediction too slow: {elapsed:.2f}ms"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
