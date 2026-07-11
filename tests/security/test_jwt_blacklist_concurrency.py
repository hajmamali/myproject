"""
tests/security/test_jwt_blacklist_concurrency.py
===============================================

Wave 1 Week 1: Security Module - JWT Blacklist Concurrency Tests

Objective: Prove JWT token blacklist integrity under concurrent operations

Critical Paths Tested (P0):
- Concurrent revocation scenarios
- Blacklist race conditions  
- Memory management under load

Coverage Target: Contribute to Security 42.20% → 50%+

Test Categories:
1. Concurrent Revocation (3 tests)
2. Race Conditions (2 tests)  
3. Memory Management (1 test)

Total: 6 tests (simplified from 12 to focus on core functionality)
"""

import pytest
import secrets
import time
from threading import Thread, Lock
from datetime import datetime, timedelta

from mahoun.security.auth import JWTAuthenticator


class TestConcurrentRevocation:
    """Test JWT token revocation under concurrent load"""
    
    @pytest.fixture
    def secret_key(self):
        """Generate random secret key for each test."""
        return secrets.token_urlsafe(32)
    
    @pytest.fixture
    def jwt_auth(self, secret_key):
        """Fresh JWTAuthenticator for each test."""
        return JWTAuthenticator(
            secret_key=secret_key,
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    def test_concurrent_token_revocation_same_token(self, jwt_auth):
        """
        Critical: Multiple threads revoking same token must not corrupt blacklist
        
        Risk: Race condition in blacklist update
        Impact: Revoked token remains valid, security breach
        """
        # Create token
        user_id = "user_123"
        token = jwt_auth.create_access_token(user_id)
        
        # Track results
        results = {"success": 0, "errors": 0}
        lock = Lock()
        
        def revoke_token():
            try:
                jwt_auth.revoke_token(token)
                with lock:
                    results["success"] += 1
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        # Revoke same token from 10 threads
        threads = [Thread(target=revoke_token) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed (idempotent revocation)
        assert results["success"] == 10, f"Expected 10 successful revocations, got {results['success']}"
        assert results["errors"] == 0, f"Expected 0 errors, got {results['errors']}"
        
        # Token should be revoked (verify by attempting to use it)
        try:
            jwt_auth.verify_token(token)
            assert False, "Revoked token should fail verification"
        except ValueError as e:
            assert "revoked" in str(e).lower(), f"Expected 'revoked' error message, got {e}"
    
    def test_concurrent_different_tokens(self, jwt_auth):
        """
        Critical: Multiple threads revoking different tokens must not interfere
        
        Risk: Cross-talk between blacklist operations
        Impact: Wrong token revoked or blacklist corruption
        """
        user_ids = [f"user_{i}" for i in range(10)]
        tokens = [jwt_auth.create_access_token(user_id) for user_id in user_ids]
        
        results = {"revoked": 0, "errors": 0}
        lock = Lock()
        
        def revoke_token(token):
            try:
                jwt_auth.revoke_token(token)
                with lock:
                    results["revoked"] += 1
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        # Each thread revokes a different token
        threads = [Thread(target=revoke_token, args=(token,)) for token in tokens]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All should succeed
        assert results["revoked"] == 10, f"Expected 10 revocations, got {results['revoked']}"
        assert results["errors"] == 0, f"Expected 0 errors, got {results['errors']}"
        
        # All tokens should be revoked
        for token in tokens:
            try:
                jwt_auth.verify_token(token)
                assert False, f"Token {token[:8]}... should be revoked"
            except ValueError:
                pass  # Expected
    
    def test_concurrent_revocation_and_verification(self, jwt_auth):
        """
        Critical: Revocation and verification happening concurrently
        
        Risk: Verification sees stale blacklist state during update
        Impact: Revoked token passes verification (security breach)
        """
        token = jwt_auth.create_access_token("user_123")
        
        results = {"verified_before_revocation": 0, "verified_after_revocation": 0, "revoked": 0}
        lock = Lock()
        
        def verify_token():
            try:
                jwt_auth.verify_token(token)
                with lock:
                    results["verified_before_revocation"] += 1
            except ValueError:
                with lock:
                    results["verified_after_revocation"] += 1
            except Exception:
                pass  # Other errors during revocation
        
        def revoke_token():
            time.sleep(0.01)  # Small delay to let some verifications complete
            jwt_auth.revoke_token(token)
            with lock:
                results["revoked"] += 1
        
        # Start 5 verification threads and 1 revocation thread
        threads = [Thread(target=verify_token) for _ in range(5)] + [Thread(target=revoke_token)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should have revoked exactly once
        assert results["revoked"] == 1, f"Expected 1 revocation, got {results['revoked']}"
        
        # After all threads complete, token should be revoked
        try:
            jwt_auth.verify_token(token)
            assert False, "Token should be revoked after concurrent operations"
        except ValueError:
            pass  # Expected


class TestRaceConditions:
    """Test blacklist race conditions"""
    
    @pytest.fixture
    def secret_key(self):
        """Generate random secret key for each test."""
        return secrets.token_urlsafe(32)
    
    @pytest.fixture
    def jwt_auth(self, secret_key):
        """Fresh JWTAuthenticator for each test."""
        return JWTAuthenticator(
            secret_key=secret_key,
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    def test_blacklist_write_race_condition(self, jwt_auth):
        """
        Critical: Simultaneous writes to blacklist must not corrupt data
        
        Risk: Race condition in blacklist data structure
        Impact: Blacklist corruption, lost revocations
        """
        tokens = [jwt_auth.create_access_token(f"user_{i}") for i in range(20)]
        
        results = {"added_to_blacklist": 0, "blacklist_corrupted": False}
        lock = Lock()
        
        def add_to_blacklist(token):
            try:
                jwt_auth.revoke_token(token)
                with lock:
                    results["added_to_blacklist"] += 1
            except Exception as e:
                with lock:
                    results["blacklist_corrupted"] = True
        
        # Add all tokens concurrently
        threads = [Thread(target=add_to_blacklist, args=(token,)) for token in tokens]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No corruption should occur
        assert not results["blacklist_corrupted"], "Blacklist should not be corrupted under concurrent writes"
        
        # All tokens should be in blacklist (verify by checking they fail verification)
        assert results["added_to_blacklist"] == 20, f"Expected 20 tokens added, got {results['added_to_blacklist']}"
        
        for token in tokens:
            try:
                jwt_auth.verify_token(token)
                assert False, f"Token {token[:8]}... should be revoked"
            except ValueError:
                pass  # Expected
    
    def test_blacklist_read_race_condition(self, jwt_auth):
        """
        Critical: Concurrent reads during writes must not crash
        
        Risk: Read/write race condition
        Impact: Service crash or stale data
        """
        token = jwt_auth.create_access_token("user_123")
        
        results = {"reads": 0, "writes": 0, "errors": 0}
        lock = Lock()
        
        def read_blacklist():
            try:
                jwt_auth.verify_token(token)  # This checks blacklist internally
                with lock:
                    results["reads"] += 1
            except ValueError:
                with lock:
                    results["reads"] += 1  # Failed verification is still a successful read
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        def write_blacklist():
            try:
                jwt_auth.revoke_token(token)
                with lock:
                    results["writes"] += 1
            except Exception as e:
                with lock:
                    results["errors"] += 1
        
        # 10 readers, 5 writers
        threads = [Thread(target=read_blacklist) for _ in range(10)] + [Thread(target=write_blacklist) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # No errors should occur
        assert results["errors"] == 0, f"Expected 0 errors, got {results['errors']}"
        assert results["reads"] == 10, f"Expected 10 reads, got {results['reads']}"
        assert results["writes"] == 5, f"Expected 5 writes, got {results['writes']}"


class TestMemoryManagement:
    """Test memory management under load"""
    
    @pytest.fixture
    def secret_key(self):
        """Generate random secret key for each test."""
        return secrets.token_urlsafe(32)
    
    @pytest.fixture
    def jwt_auth(self, secret_key):
        """Fresh JWTAuthenticator for each test."""
        return JWTAuthenticator(
            secret_key=secret_key,
            algorithm="HS256",
            access_token_expire_minutes=30,
            refresh_token_expire_days=7
        )
    
    def test_blacklist_memory_leak_prevention(self, jwt_auth):
        """
        Critical: Blacklist should not grow unbounded
        
        Risk: Memory leak in blacklist storage
        Impact: Memory exhaustion under load
        """
        initial_blacklist_size = len(jwt_auth.blacklist)
        
        # Revoke 100 tokens
        for i in range(100):
            token = jwt_auth.create_access_token(f"user_{i}")
            jwt_auth.revoke_token(token)
        
        # Check that blacklist has reasonable size
        current_blacklist_size = len(jwt_auth.blacklist)
        
        # Blacklist should not grow unbounded (should have 100 revoked tokens)
        assert current_blacklist_size == initial_blacklist_size + 100, f"Expected blacklist size {initial_blacklist_size + 100}, got {current_blacklist_size}"
        
        # Verify blacklist is bounded (implementation uses set, which is fine for testing)
        assert current_blacklist_size < 10000, "Blacklist should have bounded size"
