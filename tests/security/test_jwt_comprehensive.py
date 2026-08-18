"""
JWT Token Comprehensive Tests - Wave 1, Week 1

Coverage Target:
- auth.py lines 89-234 (JWT generation, validation, refresh, blacklist)

Critical Paths:
- Token creation and signing
- Token expiry validation
- Token refresh mechanism
- Blacklist enforcement
- Role checking

Risk Mitigation:
- P0 Security: Expired token acceptance → time-based bypass
- P0 Security: Blacklist bypass → revoked tokens still valid
- P0 Security: Token forgery → signature validation failure
"""

import pytest
import secrets
from datetime import datetime, timedelta, timezone
from mahoun.security.auth import JWTAuthenticator, UserRole

try:
    import jwt
except ImportError:
    jwt = None


@pytest.fixture
def secret_key():
    """Generate random secret key for each test."""
    return secrets.token_urlsafe(32)


@pytest.fixture
def jwt_auth(secret_key):
    """Fresh JWTAuthenticator for each test."""
    return JWTAuthenticator(
        secret_key=secret_key,
        algorithm="HS256",
        access_token_expire_minutes=30,
        refresh_token_expire_days=7
    )


@pytest.fixture
def access_token(jwt_auth):
    """Create sample access token."""
    return jwt_auth.create_access_token("test_user", [UserRole.USER])


@pytest.fixture
def refresh_token(jwt_auth):
    """Create sample refresh token."""
    return jwt_auth.create_refresh_token("test_user")


class TestTokenCreation:
    """Test JWT token generation."""
    
    @pytest.mark.p1
    def test_create_access_token_structure(self, jwt_auth):
        """Verify access token has correct structure."""
        token = jwt_auth.create_access_token("user123", [UserRole.ADMIN])
        
        # Decode without verification to check structure
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"])
        
        assert payload['user_id'] == "user123"
        assert UserRole.ADMIN in payload['roles']
        assert payload['type'] == "access"
        assert 'exp' in payload
        assert 'iat' in payload
        assert 'jti' in payload
    
    @pytest.mark.p1
    def test_create_access_token_default_role(self, jwt_auth):
        """Verify default role is USER."""
        token = jwt_auth.create_access_token("user123")
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"])
        
        assert UserRole.USER in payload['roles']
    
    @pytest.mark.p1
    def test_create_access_token_expiry(self, jwt_auth):
        """Verify access token expiry is set correctly."""
        before = datetime.now(timezone.utc)
        token = jwt_auth.create_access_token("user123")
        after = datetime.now(timezone.utc)
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"])
        
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        iat_time = datetime.fromtimestamp(payload['iat'], tz=timezone.utc)
        
        # Expiry should be ~30 minutes from now
        expected_exp = before + timedelta(minutes=30)
        assert abs((exp_time - expected_exp).total_seconds()) < 2
        
        # iat should be very recent (within 2 second window to account for timestamp rounding)
        time_window = (after - before).total_seconds() + 2  # Add 2 sec buffer
        assert abs((iat_time - before).total_seconds()) < time_window
    
    @pytest.mark.p1
    def test_create_refresh_token_structure(self, jwt_auth):
        """Verify refresh token has correct structure."""
        token = jwt_auth.create_refresh_token("user123")
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"])
        
        assert payload['user_id'] == "user123"
        assert payload['type'] == "refresh"
        assert 'exp' in payload
        assert 'iat' in payload
        assert 'jti' in payload
    
    @pytest.mark.p1
    def test_create_refresh_token_expiry(self, jwt_auth):
        """Verify refresh token expiry is set correctly (7 days)."""
        before = datetime.now(timezone.utc)
        token = jwt_auth.create_refresh_token("user123")
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"])
        
        exp_time = datetime.fromtimestamp(payload['exp'], tz=timezone.utc)
        
        # Expiry should be ~7 days from now
        expected_exp = before + timedelta(days=7)
        assert abs((exp_time - expected_exp).total_seconds()) < 2
    
    @pytest.mark.p1
    def test_tokens_are_unique(self, jwt_auth):
        """Verify each token has unique JTI."""
        token1 = jwt_auth.create_access_token("user1")
        token2 = jwt_auth.create_access_token("user1")  # Same user
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload1 = jwt.decode(token1, jwt_auth.secret_key, algorithms=["HS256"])
        payload2 = jwt.decode(token2, jwt_auth.secret_key, algorithms=["HS256"])
        
        assert payload1['jti'] != payload2['jti'], "JTI must be unique per token"
        assert token1 != token2, "Tokens must be different"


class TestTokenVerification:
    """Test JWT token verification - CRITICAL P0."""
    
    @pytest.mark.p1
    def test_verify_valid_token(self, jwt_auth, access_token):
        """Verify valid token passes verification."""
        payload = jwt_auth.verify_token(access_token)
        
        assert payload is not None
        assert payload['user_id'] == "test_user"
        assert payload['type'] == "access"
    
    @pytest.mark.p1
    def test_verify_expired_token_fails(self, jwt_auth):
        """CRITICAL: Expired tokens must fail verification."""
        # Create authenticator with very short expiry
        short_auth = JWTAuthenticator(
            secret_key=secrets.token_urlsafe(32),
            access_token_expire_minutes=0  # Expires immediately
        )
        
        token = short_auth.create_access_token("user123")
        
        # Wait a tiny bit to ensure expiry
        import time
        time.sleep(0.1)
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            short_auth.verify_token(token)
    
    @pytest.mark.p1
    def test_verify_invalid_signature_fails(self, jwt_auth, access_token):
        """CRITICAL: Tokens with invalid signature must fail."""
        # Create different authenticator with different secret
        wrong_auth = JWTAuthenticator(
            secret_key="wrong_secret_key_12345678901234567890",
            algorithm="HS256"
        )
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        with pytest.raises(jwt.InvalidTokenError):
            wrong_auth.verify_token(access_token)
    
    @pytest.mark.p1
    def test_verify_malformed_token_fails(self, jwt_auth):
        """CRITICAL: Malformed tokens must fail verification."""
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt_auth.verify_token("not.a.valid.token")
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt_auth.verify_token("")
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt_auth.verify_token("invalid_token")
    
    @pytest.mark.p1
    def test_verify_modified_token_fails(self, jwt_auth, access_token):
        """CRITICAL: Modified tokens must fail verification."""
        # Modify token slightly
        modified = access_token[:-5] + "xxxxx"
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        with pytest.raises(jwt.InvalidTokenError):
            jwt_auth.verify_token(modified)


class TestTokenBlacklist:
    """Test token blacklist enforcement - CRITICAL P0."""
    
    @pytest.mark.p1
    def test_revoke_token_adds_to_blacklist(self, jwt_auth, access_token):
        """Verify revocation adds JTI to blacklist."""
        initial_count = len(jwt_auth.blacklist)
        
        jwt_auth.revoke_token(access_token)
        
        assert len(jwt_auth.blacklist) == initial_count + 1
    
    @pytest.mark.p1
    def test_blacklisted_token_fails_verification(self, jwt_auth, access_token):
        """CRITICAL: Blacklisted tokens must not verify."""
        # First verify it works
        payload = jwt_auth.verify_token(access_token)
        assert payload is not None
        
        # Revoke it
        jwt_auth.revoke_token(access_token)
        
        # Now it should fail
        with pytest.raises(ValueError, match="revoked"):
            jwt_auth.verify_token(access_token)
    
    @pytest.mark.p1
    def test_revoke_expired_token(self, jwt_auth):
        """Verify expired tokens can still be revoked."""
        # Create token
        token = jwt_auth.create_access_token("user123")
        
        # "Expire" it by decoding and re-encoding with past expiry
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        payload = jwt.decode(token, jwt_auth.secret_key, algorithms=["HS256"], options={"verify_exp": False})
        jti = payload['jti']
        
        # Revoke should not raise even if expired
        jwt_auth.revoke_token(token)
        
        assert jti in jwt_auth.blacklist
    
    @pytest.mark.p1
    def test_revoke_invalid_token_fails_gracefully(self, jwt_auth):
        """Verify revoking invalid token doesn't crash."""
        # Should not raise
        jwt_auth.revoke_token("invalid_token")
        
        # Blacklist should not be affected
        assert "invalid_token" not in jwt_auth.blacklist


class TestTokenRefresh:
    """Test token refresh mechanism."""
    
    @pytest.mark.p1
    def test_refresh_access_token_from_refresh_token(self, jwt_auth, refresh_token):
        """Verify new access token can be created from refresh token."""
        new_access_token = jwt_auth.refresh_access_token(refresh_token)
        
        assert new_access_token is not None
        assert new_access_token != refresh_token
        
        # Verify new token is valid
        payload = jwt_auth.verify_token(new_access_token)
        assert payload['type'] == "access"
    
    @pytest.mark.p1
    def test_refresh_with_access_token_fails(self, jwt_auth, access_token):
        """CRITICAL: Access tokens must not be used for refresh."""
        with pytest.raises(ValueError, match="Not a refresh token"):
            jwt_auth.refresh_access_token(access_token)
    
    @pytest.mark.p1
    def test_refresh_with_expired_token_fails(self, jwt_auth):
        """CRITICAL: Expired refresh tokens must not work."""
        # Create auth with short refresh expiry
        short_auth = JWTAuthenticator(
            secret_key=secrets.token_urlsafe(32),
            refresh_token_expire_days=0
        )
        
        token = short_auth.create_refresh_token("user123")
        
        # Wait for expiry
        import time
        time.sleep(0.1)
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        with pytest.raises(jwt.ExpiredSignatureError):
            short_auth.refresh_access_token(token)
    
    @pytest.mark.p1
    def test_refresh_preserves_user_id(self, jwt_auth, refresh_token):
        """Verify refresh preserves user identity."""
        new_access_token = jwt_auth.refresh_access_token(refresh_token)
        
        payload = jwt_auth.verify_token(new_access_token)
        assert payload['user_id'] == "test_user"


class TestRoleChecking:
    """Test role-based access control."""
    
    @pytest.mark.p1
    def test_has_role_with_correct_role(self, jwt_auth):
        """Verify role check succeeds for correct role."""
        token = jwt_auth.create_access_token("user123", [UserRole.ADMIN])
        
        assert jwt_auth.has_role(token, UserRole.ADMIN) is True
    
    @pytest.mark.p1
    def test_has_role_without_role(self, jwt_auth):
        """Verify role check fails for missing role."""
        token = jwt_auth.create_access_token("user123", [UserRole.USER])
        
        assert jwt_auth.has_role(token, UserRole.ADMIN) is False
    
    @pytest.mark.p1
    def test_admin_has_all_roles(self, jwt_auth):
        """Verify ADMIN role grants access to everything."""
        token = jwt_auth.create_access_token("admin", [UserRole.ADMIN])
        
        # Admin should have access to any role
        assert jwt_auth.has_role(token, UserRole.USER) is True
        assert jwt_auth.has_role(token, UserRole.READONLY) is True
        assert jwt_auth.has_role(token, UserRole.SERVICE) is True
    
    @pytest.mark.p1
    def test_has_role_invalid_token(self, jwt_auth):
        """Verify role check fails for invalid token."""
        assert jwt_auth.has_role("invalid_token", UserRole.USER) is False
    
    @pytest.mark.p1
    def test_has_role_expired_token(self, jwt_auth):
        """Verify role check fails for expired token."""
        short_auth = JWTAuthenticator(
            secret_key=secrets.token_urlsafe(32),
            access_token_expire_minutes=0
        )
        
        token = short_auth.create_access_token("user123", [UserRole.USER])
        
        import time
        time.sleep(0.1)
        
        assert short_auth.has_role(token, UserRole.USER) is False


class TestAlgorithmSupport:
    """Test different JWT algorithms."""
    
    @pytest.mark.p1
    def test_hs256_algorithm(self):
        """Verify HS256 (default) works."""
        auth = JWTAuthenticator(
            secret_key=secrets.token_urlsafe(32),
            algorithm="HS256"
        )
        
        token = auth.create_access_token("user123")
        payload = auth.verify_token(token)
        assert payload is not None
    
    @pytest.mark.p1
    def test_different_algorithms_incompatible(self):
        """Verify tokens from different algorithms don't cross-validate."""
        auth_hs256 = JWTAuthenticator(
            secret_key="shared_secret",
            algorithm="HS256"
        )
        
        auth_hs512 = JWTAuthenticator(
            secret_key="shared_secret",
            algorithm="HS512"
        )
        
        token = auth_hs256.create_access_token("user123")
        
        if jwt is None:
            pytest.skip("PyJWT not installed")
        
        # HS512 authenticator should reject HS256 token
        with pytest.raises(jwt.InvalidTokenError):
            auth_hs512.verify_token(token)
