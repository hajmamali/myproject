import pytest
pytest.importorskip("jwt")
"""
Comprehensive tests for rate limiter.

Tests cover:
- Sliding window algorithm correctness
- Concurrent access safety
- Redis backend integration
- Custom limits per identifier
- Burst handling
- Edge cases and error conditions
"""

import pytest
import time
import threading
from unittest.mock import Mock, patch, MagicMock
from mahoun.security.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitExceeded,
    SlidingWindowCounter
)


class TestSlidingWindowCounter:
    """Test sliding window counter implementation."""
    
    def test_basic_counting(self):
        """Test basic request counting."""
        config = RateLimitConfig(requests_per_window=5, window_seconds=10)
        counter = SlidingWindowCounter(config)
        
        current_time = time.time()
        
        # Should allow first 5 requests
        for i in range(5):
            allowed, retry_after = counter.check_and_increment(current_time + i * 0.1)
            assert allowed, f"Request {i+1} should be allowed"
            assert retry_after == 0.0
    
    def test_burst_limit(self):
        """Test burst multiplier enforcement."""
        config = RateLimitConfig(
            requests_per_window=10,
            window_seconds=60,
            burst_multiplier=1.5
        )
        counter = SlidingWindowCounter(config)
        
        current_time = time.time()
        
        # Should allow up to 15 requests (10 * 1.5)
        for i in range(15):
            allowed, _ = counter.check_and_increment(current_time)
            assert allowed, f"Request {i+1} should be allowed (burst)"
        
        # 16th request should be denied
        allowed, retry_after = counter.check_and_increment(current_time)
        assert not allowed
        assert retry_after > 0
    
    def test_sliding_window_expiry(self):
        """Test that old requests expire correctly."""
        config = RateLimitConfig(requests_per_window=3, window_seconds=5)
        counter = SlidingWindowCounter(config)
        
        current_time = 1000.0
        
        # Fill up the limit
        for i in range(3):
            allowed, _ = counter.check_and_increment(current_time + i)
            assert allowed
        
        # Should be blocked
        allowed, _ = counter.check_and_increment(current_time + 3)
        assert not allowed
        
        # After window expires, should be allowed again
        allowed, _ = counter.check_and_increment(current_time + 6)
        assert allowed
    
    def test_get_current_count(self):
        """Test current count retrieval."""
        config = RateLimitConfig(requests_per_window=10, window_seconds=60)
        counter = SlidingWindowCounter(config)
        
        current_time = time.time()
        
        assert counter.get_current_count(current_time) == 0
        
        counter.check_and_increment(current_time)
        counter.check_and_increment(current_time + 1)
        
        assert counter.get_current_count(current_time + 2) == 2
    
    def test_thread_safety(self):
        """Test thread-safe concurrent access."""
        config = RateLimitConfig(requests_per_window=100, window_seconds=10)
        counter = SlidingWindowCounter(config)
        
        current_time = time.time()
        results = []
        
        def make_request():
            allowed, _ = counter.check_and_increment(current_time)
            results.append(allowed)
        
        # Spawn 150 threads (should allow 150 with burst)
        threads = [threading.Thread(target=make_request) for _ in range(150)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have exactly 150 allowed (100 * 1.5)
        assert sum(results) == 150


class TestRateLimiter:
    """Test rate limiter with memory backend."""
    
    def test_default_config(self):
        """Test rate limiter with default configuration."""
        limiter = RateLimiter()
        
        # Should allow 100 requests
        for i in range(100):
            limiter.check_rate_limit("user1")
        
        # 101st should fail (with burst it's 150)
        for i in range(50):
            limiter.check_rate_limit("user1")
        
        with pytest.raises(RateLimitExceeded) as exc_info:
            limiter.check_rate_limit("user1")
        
        assert exc_info.value.limit == 100
        assert exc_info.value.window == 60
        assert exc_info.value.retry_after > 0
    
    def test_custom_limit_per_identifier(self):
        """Test custom limits for specific identifiers."""
        limiter = RateLimiter()
        
        # Set custom limit for premium user
        limiter.set_custom_limit("premium_user", requests_per_window=1000, window_seconds=60)
        
        # Premium user should have higher limit
        for i in range(1000):
            limiter.check_rate_limit("premium_user")
        
        # Regular user should have default limit
        for i in range(100):
            limiter.check_rate_limit("regular_user")
    
    def test_request_cost(self):
        """Test request cost multiplier."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10, window_seconds=60)
        )
        
        # Expensive operation costs 5 requests
        limiter.check_rate_limit("user1", cost=5)
        
        # Should only allow 1 more expensive operation (5 + 5 = 10)
        limiter.check_rate_limit("user1", cost=5)
        
        # Next one should fail
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user1", cost=5)
    
    def test_get_remaining_requests(self):
        """Test remaining requests calculation."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10, window_seconds=60)
        )
        
        assert limiter.get_remaining_requests("user1") == 10
        
        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user1")
        
        assert limiter.get_remaining_requests("user1") == 8
    
    def test_reset_limit(self):
        """Test limit reset."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=5, window_seconds=60)
        )
        
        # Use up limit
        for i in range(5):
            limiter.check_rate_limit("user1")
        
        # Should be blocked
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user1")
        
        # Reset
        limiter.reset_limit("user1")
        
        # Should work again
        limiter.check_rate_limit("user1")
    
    def test_cleanup_expired(self):
        """Test cleanup of expired counters."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=5, window_seconds=1)
        )
        
        # Create some counters
        limiter.check_rate_limit("user1")
        limiter.check_rate_limit("user2")
        limiter.check_rate_limit("user3")
        
        # Wait for expiry
        time.sleep(1.5)
        
        # Cleanup
        removed = limiter.cleanup_expired()
        assert removed == 3
    
    def test_multiple_identifiers_isolated(self):
        """Test that different identifiers have isolated limits."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=5, window_seconds=60)
        )
        
        # User1 uses up their limit
        for i in range(5):
            limiter.check_rate_limit("user1")
        
        # User2 should still have full limit
        for i in range(5):
            limiter.check_rate_limit("user2")
        
        # User1 blocked
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user1")
        
        # User2 blocked
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user2")


class TestRateLimiterRedis:
    """Test rate limiter with Redis backend."""
    
    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('mahoun.security.rate_limiter.redis') as mock:
            redis_client = MagicMock()
            mock.from_url.return_value = redis_client
            yield redis_client
    
    def test_redis_backend_enabled(self, mock_redis):
        """Test Redis backend initialization."""
        limiter = RateLimiter(redis_url="redis://localhost:6379")
        
        assert limiter.redis_client is not None
    
    def test_redis_rate_limiting(self, mock_redis):
        """Test rate limiting with Redis backend."""
        mock_redis.pipeline.return_value.execute.return_value = [None, 5, None, None]
        
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10, window_seconds=60),
            redis_url="redis://localhost:6379"
        )
        
        # Should use Redis
        limiter.check_rate_limit("user1")
        
        # Verify Redis calls
        assert mock_redis.pipeline.called
    
    def test_redis_fallback_on_error(self, mock_redis):
        """Test fallback to memory when Redis fails."""
        mock_redis.pipeline.side_effect = Exception("Redis connection failed")
        
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10, window_seconds=60),
            redis_url="redis://localhost:6379"
        )
        
        # Should fallback to memory backend
        limiter.check_rate_limit("user1")
        
        # Should still work
        assert limiter.get_remaining_requests("user1") == 9
    
    def test_redis_limit_exceeded(self, mock_redis):
        """Test rate limit exceeded with Redis."""
        # Simulate limit exceeded (count = 150, limit = 100)
        mock_redis.pipeline.return_value.execute.return_value = [None, 150, None, None]
        mock_redis.zrange.return_value = [(b"1000.0", 1000.0)]
        
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=100, window_seconds=60),
            redis_url="redis://localhost:6379"
        )
        
        with pytest.raises(RateLimitExceeded):
            limiter.check_rate_limit("user1")


class TestRateLimitExceeded:
    """Test RateLimitExceeded exception."""
    
    def test_exception_message(self):
        """Test exception message formatting."""
        exc = RateLimitExceeded(limit=100, window=60, retry_after=30.5)
        
        assert "100 requests per 60s" in str(exc)
        assert "30.5s" in str(exc)
    
    def test_exception_attributes(self):
        """Test exception attributes."""
        exc = RateLimitExceeded(limit=50, window=120, retry_after=45.0)
        
        assert exc.limit == 50
        assert exc.window == 120
        assert exc.retry_after == 45.0


class TestRateLimitConfig:
    """Test rate limit configuration."""
    
    def test_default_burst_multiplier(self):
        """Test default burst multiplier."""
        config = RateLimitConfig(requests_per_window=100, window_seconds=60)
        
        assert config.burst_multiplier == 1.5
    
    def test_custom_burst_multiplier(self):
        """Test custom burst multiplier."""
        config = RateLimitConfig(
            requests_per_window=100,
            window_seconds=60,
            burst_multiplier=2.0
        )
        
        assert config.burst_multiplier == 2.0


@pytest.mark.slow
class TestRateLimiterPerformance:
    """Performance and stress tests."""
    
    def test_high_throughput(self):
        """Test high throughput scenario."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10000, window_seconds=60)
        )
        
        start = time.time()
        
        for i in range(1000):
            limiter.check_rate_limit(f"user{i % 10}")
        
        elapsed = time.time() - start
        
        # Should handle 1000 requests quickly
        assert elapsed < 1.0, f"Too slow: {elapsed}s"
    
    def test_many_identifiers(self):
        """Test with many different identifiers."""
        limiter = RateLimiter(
            default_config=RateLimitConfig(requests_per_window=10, window_seconds=60)
        )
        
        # Create 1000 different identifiers
        for i in range(1000):
            limiter.check_rate_limit(f"user{i}")
        
        # Cleanup should remove none (all active)
        removed = limiter.cleanup_expired()
        assert removed == 0
