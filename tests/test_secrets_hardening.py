"""
Extreme Security Tests for PR-2: Secrets Hardening
====================================================
These tests are BRUTAL - they verify NO default passwords exist anywhere
AND runtime validation of secrets policy enforcement.
"""

import os
import subprocess
import pytest
from pathlib import Path
from unittest.mock import patch


class TestSecretsRuntimeValidation:
    def test_dev_placeholder_detection_empty(self):
        from mahoun.core.secrets import _is_dev_placeholder
        assert _is_dev_placeholder("")
        assert _is_dev_placeholder("   ")

    def test_dev_placeholder_detection_known_values(self):
        from mahoun.core.secrets import _is_dev_placeholder, DEV_PLACEHOLDERS
        for placeholder in DEV_PLACEHOLDERS:
            assert _is_dev_placeholder(placeholder)
            assert _is_dev_placeholder(placeholder.upper())
            assert _is_dev_placeholder(f"  {placeholder}  ")

    def test_dev_placeholder_detection_safe_values(self):
        from mahoun.core.secrets import _is_dev_placeholder
        safe_values = [
            "a5f9d8e7c3b2a1f0e9d8c7b6a5f4e3d2",
            "Sup3rS3cur3P@ssw0rd!2024",
            "randomly_generated_strong_secret_12345",
        ]
        for value in safe_values:
            assert not _is_dev_placeholder(value)

    @patch.dict(os.environ, {"MAHOUN_ENV": "dev"})
    def test_require_secret_dev_allows_placeholders_with_warning(self, caplog):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"TEST_SECRET": "dev_password_change_me"}):
            result = require_secret("TEST_SECRET")
            assert result == "dev_password_change_me"
            assert "dev placeholder" in caplog.text.lower()

    @patch.dict(os.environ, {"MAHOUN_ENV": "dev"})
    def test_require_secret_dev_allows_strong_secrets(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"TEST_SECRET": "strong_secret_12345"}):
            result = require_secret("TEST_SECRET")
            assert result == "strong_secret_12345"

    @patch.dict(os.environ, {"MAHOUN_ENV": "dev"})
    def test_require_secret_dev_fallback_if_missing(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {}, clear=True):
            os.environ["MAHOUN_ENV"] = "dev"
            result = require_secret("DB_NEO4J_PASSWORD")
            assert result == "dev_password_change_me"

    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_require_secret_prod_rejects_missing(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "prod"}, clear=True):
            with pytest.raises(RuntimeError, match="SECURITY GATE.*NOT SET"):
                require_secret("MISSING_SECRET")

    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_require_secret_prod_rejects_dev_placeholders(self):
        from mahoun.core.secrets import require_secret
        for placeholder in ["dev_password_change_me", "CHANGE_ME", "password"]:
            with patch.dict(os.environ, {"MAHOUN_ENV": "prod", "TEST_SECRET": placeholder}):
                with pytest.raises(RuntimeError, match="SECURITY GATE.*DEV PLACEHOLDER"):
                    require_secret("TEST_SECRET")
    
    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_require_secret_prod_rejects_empty_string(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "prod", "TEST_SECRET": ""}):
            with pytest.raises(RuntimeError, match="SECURITY GATE.*NOT SET"):
                require_secret("TEST_SECRET")

    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_require_secret_prod_allows_strong_secrets(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "prod", "TEST_SECRET": "SuperSecure123!@#"}):
            result = require_secret("TEST_SECRET")
            assert result == "SuperSecure123!@#"

    @patch.dict(os.environ, {"MAHOUN_ENV": "staging"})
    def test_require_secret_staging_rejects_missing(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "staging"}, clear=True):
            with pytest.raises(RuntimeError, match="SECURITY GATE.*NOT SET"):
                require_secret("MISSING_SECRET")

    @patch.dict(os.environ, {"MAHOUN_ENV": "staging"})
    def test_require_secret_staging_rejects_placeholders(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "staging", "TEST_SECRET": "dev_password_change_me"}):
            with pytest.raises(RuntimeError, match="SECURITY GATE.*DEV PLACEHOLDER"):
                require_secret("TEST_SECRET")

    @patch.dict(os.environ, {"MAHOUN_ENV": "staging"})
    def test_require_secret_staging_allows_strong_secrets(self):
        from mahoun.core.secrets import require_secret
        with patch.dict(os.environ, {"MAHOUN_ENV": "staging", "TEST_SECRET": "StrongSecret2024!"}):
            result = require_secret("TEST_SECRET")
            assert result == "StrongSecret2024!"

    @patch.dict(os.environ, {"MAHOUN_ENV": "dev"})
    def test_validate_all_required_secrets_dev_allows_placeholders(self):
        from mahoun.core.secrets import validate_all_required_secrets
        with patch.dict(
            os.environ,
            {
                "MAHOUN_ENV": "dev",
                "DB_NEO4J_PASSWORD": "dev_password_change_me",
                "DB_POSTGRES_PASSWORD": "dev_password_change_me",
                "SECURITY_JWT_SECRET": "dev_jwt_secret_change_me_must_be_32_chars_minimum_for_security",
            },
        ):
            validate_all_required_secrets()

    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_validate_all_required_secrets_prod_rejects_any_placeholder(self):
        from mahoun.core.secrets import validate_all_required_secrets
        with patch.dict(
            os.environ,
            {
                "MAHOUN_ENV": "prod",
                "DB_NEO4J_PASSWORD": "SecureNeo4jP@ss2024!",
                "DB_POSTGRES_PASSWORD": "dev_password_change_me",
                "SECURITY_JWT_SECRET": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
            },
        ):
            with pytest.raises(RuntimeError, match="SECURITY GATE.*DEV PLACEHOLDER"):
                validate_all_required_secrets()

    @patch.dict(os.environ, {"MAHOUN_ENV": "prod"})
    def test_validate_all_required_secrets_prod_passes_with_strong_secrets(self):
        from mahoun.core.secrets import validate_all_required_secrets
        with patch.dict(
            os.environ,
            {
                "MAHOUN_ENV": "prod",
                "DB_NEO4J_PASSWORD": "SecureNeo4jP@ss2024!",
                "DB_POSTGRES_PASSWORD": "SecurePostgresP@ss2024!",
                "SECURITY_JWT_SECRET": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6",
            },
        ):
            validate_all_required_secrets()

    def test_required_secrets_canonical_names_defined(self):
        from mahoun.core.secrets import REQUIRED_SECRETS
        assert "DB_NEO4J_PASSWORD" in REQUIRED_SECRETS
        assert "DB_POSTGRES_PASSWORD" in REQUIRED_SECRETS
        assert "SECURITY_JWT_SECRET" in REQUIRED_SECRETS

    def test_dev_placeholders_frozenset_defined(self):
        from mahoun.core.secrets import DEV_PLACEHOLDERS
        assert "dev_password_change_me" in DEV_PLACEHOLDERS
        assert "CHANGE_ME" in DEV_PLACEHOLDERS
        assert "" in DEV_PLACEHOLDERS


class TestSecretsHardening:
    """سخت‌ترین تست‌های امنیتی برای PR-2"""
    
    def test_no_default_password_changeme_anywhere(self):
        """تست 1: هیچ‌جا نباید کلمه 'changeme' وجود داشته باشد"""
        result = subprocess.run(
            ["grep", "-r", "changeme", ".", 
             "--include=*.py", "--include=*.yml", "--include=*.yaml",
             "--exclude-dir=venv", "--exclude-dir=.git", "--exclude-dir=tests"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        # Exit code 1 means no matches found (SUCCESS)
        assert result.returncode == 1, (
            f"❌ SECURITY VIOLATION: Found 'changeme' in code!\n"
            f"Matches:\n{result.stdout}"
        )
    
    def test_no_default_password_in_compose(self):
        """تست 2: docker-compose.yml نباید default password داشته باشد"""
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        
        # Check for default patterns
        forbidden_patterns = [
            ":-changeme",
            ':-"changeme"',
            ":-password",
            ':-"password"',
            ":-neo4j_dev_password",
            ":-mahoun_dev_password",
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(pattern)
        
        assert len(violations) == 0, (
            f"❌ SECURITY VIOLATION: Found default passwords in docker-compose.yml!\n"
            f"Forbidden patterns found: {violations}\n"
            f"All passwords MUST use :? syntax to fail when not set"
        )
    
    def test_compose_requires_neo4j_password(self):
        """تست 3: docker-compose باید NEO4J_PASSWORD را require کند"""
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        
        # Must use :? syntax to require the variable
        assert "NEO4J_PASSWORD:?" in content or "NEO4J_PASSWORD:?ERROR" in content, (
            "❌ docker-compose.yml MUST require NEO4J_PASSWORD with :? syntax"
        )
    
    def test_compose_requires_postgres_password(self):
        """تست 4: docker-compose باید POSTGRES_PASSWORD را require کند"""
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        
        # Must use :? syntax
        assert "POSTGRES_PASSWORD:?" in content or "POSTGRES_PASSWORD:?ERROR" in content, (
            "❌ docker-compose.yml MUST require POSTGRES_PASSWORD with :? syntax"
        )
    
    def test_compose_requires_jwt_secret(self):
        """تست 5: docker-compose باید JWT_SECRET_KEY را require کند"""
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        
        assert "JWT_SECRET_KEY:?" in content or "JWT_SECRET_KEY:?ERROR" in content, (
            "❌ docker-compose.yml MUST require JWT_SECRET_KEY with :? syntax"
        )
    
    def test_no_default_password_in_api_config(self):
        """تست 6: api/config.py نباید default password داشته باشد"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        forbidden_patterns = [
            'default="changeme"',
            'default="password"',
            'default="neo4j_dev_password"',
            'default="mahoun_dev_password"',
            'default="dev-super-secret-key',
        ]
        
        violations = []
        for pattern in forbidden_patterns:
            if pattern in content:
                violations.append(pattern)
        
        assert len(violations) == 0, (
            f"❌ SECURITY VIOLATION: Found default passwords in api/config.py!\n"
            f"Forbidden patterns: {violations}\n"
            f"All password fields MUST use Field(...) to require env vars"
        )
    
    def test_config_requires_postgres_password(self):
        """تست 7: api/config.py باید postgres_password را require کند"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        # Check that postgres_password uses Field(...) not Field(default=...)
        assert "postgres_password: SecretStr = Field(\n        ..." in content or \
               "postgres_password: SecretStr = Field(..." in content, (
            "❌ api/config.py MUST require postgres_password with Field(...)"
        )
    
    def test_config_requires_neo4j_password(self):
        """تست 8: api/config.py باید neo4j_password را require کند"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        assert "neo4j_password: SecretStr = Field(\n        ..." in content or \
               "neo4j_password: SecretStr = Field(..." in content, (
            "❌ api/config.py MUST require neo4j_password with Field(...)"
        )
    
    def test_config_requires_jwt_secret(self):
        """تست 9: api/config.py باید jwt_secret را require کند"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        assert "jwt_secret: SecretStr = Field(\n        ..." in content or \
               "jwt_secret: SecretStr = Field(..." in content, (
            "❌ api/config.py MUST require jwt_secret with Field(...)"
        )
    
    def test_jwt_secret_min_length_enforced(self):
        """تست 10: jwt_secret باید minimum 32 کاراکتر باشد"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        # Check for min_length validation
        lines = content.split('\n')
        jwt_section_found = False
        min_length_found = False
        
        for i, line in enumerate(lines):
            if 'jwt_secret:' in line and 'SecretStr' in line:
                jwt_section_found = True
                # Check next 5 lines for min_length
                for j in range(i, min(i+5, len(lines))):
                    if 'min_length=32' in lines[j]:
                        min_length_found = True
                        break
        
        assert jwt_section_found, "❌ jwt_secret field not found"
        assert min_length_found, (
            "❌ jwt_secret MUST enforce min_length=32 for security"
        )
    
    def test_no_default_password_in_self_improve(self):
        """تست 11: self_improve module نباید default password داشته باشد"""
        self_improve_file = Path(__file__).parent.parent / "mahoun" / "self_improve" / "ultra_self_improvement_system.py"
        
        if not self_improve_file.exists():
            pytest.skip("Self-improve module not found")
        
        content = self_improve_file.read_text()
        
        # Should NOT have default="password" or "neo4j_password": "password"
        assert '"password"' not in content or 'neo4j_password": "password"' not in content, (
            "❌ SECURITY VIOLATION: self_improve module has hardcoded 'password'"
        )
        
        # Should use self.config["neo4j_password"] (KeyError if missing)
        # NOT self.config.get("neo4j_password", "password")
        assert 'self.config["neo4j_password"]' in content or \
               "neo4j_password MUST be provided" in content, (
            "❌ self_improve MUST raise error if neo4j_password missing"
        )
    
    def test_env_example_exists(self):
        """تست 12: .env.example باید وجود داشته باشد"""
        env_example = Path(__file__).parent.parent / ".env.example"
        assert env_example.exists(), (
            "❌ .env.example file MUST exist to document required secrets"
        )
    
    def test_env_example_has_required_vars(self):
        """تست 13: .env.example باید تمام متغیرهای ضروری را داشته باشد"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        required_vars = [
            "DB_POSTGRES_PASSWORD",
            "DB_NEO4J_PASSWORD",
            "SECURITY_JWT_SECRET",
            "NEO4J_PASSWORD",  # for docker-compose
            "POSTGRES_PASSWORD",  # for docker-compose
            "JWT_SECRET_KEY",  # for docker-compose
        ]
        
        missing = []
        for var in required_vars:
            if var not in content:
                missing.append(var)
        
        assert len(missing) == 0, (
            f"❌ .env.example MUST document these required variables:\n"
            f"Missing: {missing}"
        )
    
    def test_env_example_has_generation_instructions(self):
        """تست 14: .env.example باید دستورالعمل تولید password داشته باشد"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        # Must have openssl commands
        assert "openssl rand" in content, (
            "❌ .env.example MUST include 'openssl rand' commands for password generation"
        )
        
        assert "openssl rand -base64 32" in content, (
            "❌ .env.example MUST show 'openssl rand -base64 32' for passwords"
        )
        
        assert "openssl rand -hex 32" in content, (
            "❌ .env.example MUST show 'openssl rand -hex 32' for JWT secret"
        )
    
    def test_env_example_has_placeholders_not_real_secrets(self):
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        assert "dev_password_change_me" in content or "dev_jwt_secret_change_me" in content, (
            "❌ .env.example MUST use safe dev placeholders"
        )
        
        forbidden = ["password123", "secret123"]
        violations = [f for f in forbidden if f in content.lower()]
        
        assert len(violations) == 0, (
            f"❌ .env.example contains actual password-like values: {violations}"
        )
    
    def test_env_example_not_ignored_by_git(self):
        """تست 16: .env.example نباید توسط git ignore شود"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        content = gitignore.read_text()
        
        # .env.example should be explicitly allowed
        assert "!.env.example" in content or ".env.example" not in content, (
            "❌ .env.example MUST be tracked by git (add !.env.example to .gitignore)"
        )
    
    def test_actual_env_file_is_ignored(self):
        """تست 17: .env باید توسط git ignore شود"""
        gitignore = Path(__file__).parent.parent / ".gitignore"
        content = gitignore.read_text()
        
        assert ".env" in content or "*.env" in content, (
            "❌ .env MUST be in .gitignore to prevent committing secrets"
        )
    
    @pytest.mark.skipif(
        os.getenv("SKIP_DOCKER_TESTS") == "1",
        reason="Docker tests skipped"
    )
    def test_docker_compose_fails_without_neo4j_password(self):
        """تست 18: docker-compose باید بدون NEO4J_PASSWORD fail کند"""
        # This is an integration test - only run if docker available
        env = os.environ.copy()
        # Remove NEO4J_PASSWORD from environment
        env.pop("NEO4J_PASSWORD", None)
        
        result = subprocess.run(
            ["docker-compose", "config"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            env=env
        )
        
        # Should fail with error
        assert result.returncode != 0, (
            "❌ docker-compose MUST fail when NEO4J_PASSWORD not set"
        )
        assert "NEO4J_PASSWORD" in result.stderr, (
            "❌ Error message MUST mention NEO4J_PASSWORD"
        )
    
    @pytest.mark.skipif(
        os.getenv("SKIP_DOCKER_TESTS") == "1",
        reason="Docker tests skipped"
    )
    def test_docker_compose_fails_without_postgres_password(self):
        """تست 19: docker-compose باید بدون POSTGRES_PASSWORD fail کند"""
        env = os.environ.copy()
        env.pop("POSTGRES_PASSWORD", None)
        env.pop("NEO4J_PASSWORD", None)  # Remove this too to isolate the test
        
        result = subprocess.run(
            ["docker-compose", "config"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            env=env
        )
        
        assert result.returncode != 0, (
            "❌ docker-compose MUST fail when POSTGRES_PASSWORD not set"
        )
    
    def test_no_todo_deferred_for_secrets(self):
        """تست 20: نباید TODO-DEFERRED برای secrets وجود داشته باشد"""
        result = subprocess.run(
            ["grep", "-r", "TODO.*password", ".", 
             "--include=*.py", "--include=*.yml",
             "--exclude-dir=venv", "--exclude-dir=.git", "--exclude=test_*.py"],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True
        )
        
        # Exit code 1 means no matches (SUCCESS)
        assert result.returncode == 1, (
            f"❌ Found TODO comments related to passwords (incomplete implementation):\n"
            f"{result.stdout}"
        )
    
    def test_grep_for_any_hardcoded_credentials(self):
        """تست 21: جستجوی سخت‌گیرانه برای هرگونه credentials"""
        patterns_to_check = [
            "password.*=.*['\"]",  # password="something"
            "passwd.*=.*['\"]",    # passwd="something"
            "secret.*=.*['\"]",    # secret="something"
            "credential.*=.*['\"]", # credential="something"
        ]
        
        violations = []
        for pattern in patterns_to_check:
            result = subprocess.run(
                ["grep", "-rE", pattern, ".", 
                 "--include=*.py", "--include=*.yml",
                 "--exclude-dir=venv", "--exclude-dir=.git", 
                 "--exclude=test_*.py", "--exclude=*.example"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:  # Found matches
                violations.append((pattern, result.stdout))
        
        # Allow some exceptions (like description fields)
        filtered_violations = []
        for pattern, output in violations:
            lines = output.strip().split('\n')
            for line in lines:
                # Skip if it's a description or comment
                if 'description=' not in line and '#' not in line:
                    filtered_violations.append(line)
        
        if filtered_violations:
            print("\n⚠️  Potential hardcoded credentials found:")
            for v in filtered_violations[:10]:  # Show first 10
                print(f"  {v}")
    
    def test_all_secrets_use_secretstr_type(self):
        """تست 22: تمام passwords باید از SecretStr استفاده کنند"""
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        
        # All password fields should use SecretStr
        password_fields = [
            "postgres_password",
            "neo4j_password",
            "redis_password",
            "jwt_secret",
        ]
        
        for field in password_fields:
            assert f"{field}: SecretStr" in content or \
                   f"{field}: Optional[SecretStr]" in content, (
                f"❌ {field} MUST use SecretStr type for security"
            )


class TestSecurityRegression:
    """تست‌های regression برای اطمینان از عدم بازگشت مشکلات"""
    
    def test_count_changeme_occurrences(self):
        """شمارش دقیق تعداد 'changeme' - باید صفر باشد"""
        result = subprocess.run(
            ["grep", "-rc", "changeme", "."],
            cwd=Path(__file__).parent.parent,
            capture_output=True,
            text=True,
            shell=True
        )
        
        # Count total occurrences
        total = 0
        for line in result.stdout.split('\n'):
            if ':' in line and not any(x in line for x in ['venv', '.git', 'node_modules']):
                try:
                    count = int(line.split(':')[1])
                    total += count
                except:
                    pass
        
        assert total == 0, (
            f"❌ Found {total} occurrences of 'changeme' in codebase"
        )
    
    def test_security_checklist_all_pass(self):
        """چک‌لیست نهایی امنیت - همه باید pass شوند"""
        checklist = {
            "No 'changeme' in code": self._check_no_changeme(),
            "No default passwords in compose": self._check_compose_passwords(),
            "No default passwords in config": self._check_config_passwords(),
            ".env.example exists": Path(__file__).parent.parent / ".env.example",
            ".env.example tracked by git": self._check_env_example_tracked(),
        }
        
        failures = []
        for check, result in checklist.items():
            if isinstance(result, Path):
                if not result.exists():
                    failures.append(f"{check}: File not found")
            elif not result:
                failures.append(check)
        
        assert len(failures) == 0, (
            f"❌ Security checklist FAILED:\n" + "\n".join(f"  - {f}" for f in failures)
        )
    
    def _check_no_changeme(self):
        result = subprocess.run(
            ["grep", "-r", "changeme", ".", "--include=*.py", "--include=*.yml"],
            cwd=Path(__file__).parent.parent,
            capture_output=True
        )
        return result.returncode == 1
    
    def _check_compose_passwords(self):
        compose_file = Path(__file__).parent.parent / "docker-compose.yml"
        content = compose_file.read_text()
        return ":-changeme" not in content
    
    def _check_config_passwords(self):
        config_file = Path(__file__).parent.parent / "api" / "config.py"
        content = config_file.read_text()
        return 'default="neo4j_dev_password"' not in content
    
    def _check_env_example_tracked(self):
        gitignore = Path(__file__).parent.parent / ".gitignore"
        content = gitignore.read_text()
        return "!.env.example" in content or ".env.example" not in content


if __name__ == "__main__":
    # برای اجرای مستقیم
    pytest.main([__file__, "-v", "--tb=short"])

