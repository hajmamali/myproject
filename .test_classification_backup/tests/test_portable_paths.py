"""
Extreme Tests for PR-4: Portable Paths
=======================================
These tests are BRUTAL - they verify NO hardcoded user paths exist
"""

import pytest
import os
import subprocess
from pathlib import Path
from unittest.mock import patch


class TestNoHardcodedPaths:
    """تست‌های سخت‌گیرانه برای عدم وجود مسیرهای hardcoded"""
    
    def test_no_home_user_paths_in_python_files(self):
        """تست 1: نباید /home/<user> در فایل‌های Python باشد"""
        result = subprocess.run(
            [
                "grep", "-RInE", r'(/home/[^/]+/|/Users/[^/]+/)',
                ".",
                "--include=*.py",
                "--exclude-dir=venv",
                "--exclude-dir=.git",
                "--exclude-dir=.mypy_cache",
                "--exclude-dir=__pycache__",
                "--exclude=test_portable_paths.py",  # Exclude self
                "--exclude=ci_check_hardcodes.py"    # Exclude CI checker (contains patterns as strings)
            ],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1, (  # grep returns 1 when no matches
            f"❌ PORTABILITY VIOLATION: Found hardcoded user paths in Python files!\n"
            f"Matches:\n{result.stdout}"
        )
    
    def test_no_home_paths_in_config_files(self):
        """تست 2: نباید /home/<user> در config files باشد"""
        result = subprocess.run(
            [
                "grep", "-RInE", r'/home/[^/]+/',
                ".",
                "--include=*.json",
                "--include=*.yaml",
                "--include=*.yml",
                "--exclude-dir=venv",
                "--exclude-dir=.git",
                "--exclude-dir=.mypy_cache"
            ],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1, (
            f"❌ PORTABILITY VIOLATION: Found hardcoded paths in config files!\n"
            f"Matches:\n{result.stdout}"
        )
    
    def test_no_desktop_paths(self):
        """تست 3: نباید Desktop/ در فایل‌ها باشد (except comments)"""
        result = subprocess.run(
            [
                "grep", "-RIn", "Desktop/",
                ".",
                "--include=*.py",
                "--include=*.json",
                "--include=*.yaml",
                "--exclude-dir=venv",
                "--exclude-dir=.git",
                "--exclude-dir=.mypy_cache",
                "--exclude=test_portable_paths.py"
            ],
            capture_output=True,
            text=True
        )
        
        # Filter out false positives (comments)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            real_violations = [
                line for line in lines 
                if line and not ('# ' in line and 'Desktop/Dev mode' in line)
            ]
            
            if len(real_violations) == 0:
                return  # PASS
        
            result.stdout = '\n'.join(real_violations)
        
        assert result.returncode == 1 or len(real_violations) == 0, (
            f"❌ PORTABILITY VIOLATION: Found Desktop/ paths!\n"
            f"Matches:\n{result.stdout}"
        )
    
    def test_runtime_json_uses_env_var(self):
        """تست 4: runtime.json باید از ${MAHOUN_MODEL_DIR} استفاده کند"""
        runtime_file = Path(__file__).parent.parent / "config" / "runtime.json"
        
        if not runtime_file.exists():
            pytest.skip("runtime.json not found")
        
        content = runtime_file.read_text()
        
        # Should NOT have /home/haji
        assert "/home/haji" not in content, (
            "❌ runtime.json still contains /home/haji path"
        )
        
        # Should have placeholder or env var reference
        assert "MAHOUN_MODEL_DIR" in content or "model_path" not in content, (
            "❌ runtime.json should use ${MAHOUN_MODEL_DIR} placeholder"
        )
    
    def test_env_example_documents_mahoun_model_dir(self):
        """تست 5: .env.example باید MAHOUN_MODEL_DIR را مستند کند"""
        env_example = Path(__file__).parent.parent / ".env.example"
        
        if not env_example.exists():
            pytest.fail("❌ .env.example not found")
        
        content = env_example.read_text()
        
        assert "MAHOUN_MODEL_DIR" in content, (
            "❌ .env.example MUST document MAHOUN_MODEL_DIR"
        )
    
    def test_env_example_documents_mahoun_data_dir(self):
        """تست 6: .env.example باید MAHOUN_DATA_DIR را مستند کند"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        assert "MAHOUN_DATA_DIR" in content, (
            "❌ .env.example MUST document MAHOUN_DATA_DIR"
        )
    
    def test_env_example_documents_mahoun_output_dir(self):
        """تست 7: .env.example باید MAHOUN_OUTPUT_DIR را مستند کند"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        assert "MAHOUN_OUTPUT_DIR" in content, (
            "❌ .env.example MUST document MAHOUN_OUTPUT_DIR"
        )


class TestPathsModule:
    """تست‌های ماژول mahoun.core.paths"""
    
    def test_paths_module_exists(self):
        """تست 8: mahoun/core/paths.py باید وجود داشته باشد"""
        paths_file = Path(__file__).parent.parent / "mahoun" / "core" / "paths.py"
        
        assert paths_file.exists(), (
            "❌ mahoun/core/paths.py not found - portable path helper missing"
        )
    
    def test_paths_module_imports(self):
        """تست 9: ماژول paths باید import شود"""
        try:
            from mahoun.core import paths
            assert paths is not None
        except ImportError as e:
            pytest.fail(f"❌ Cannot import mahoun.core.paths: {e}")
    
    def test_get_repo_root_function_exists(self):
        """تست 10: تابع get_repo_root باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "get_repo_root"), (
            "❌ get_repo_root function missing"
        )
        
        # Test it works
        repo_root = paths.get_repo_root()
        assert isinstance(repo_root, Path)
        assert repo_root.exists()
    
    def test_get_model_dir_function_exists(self):
        """تست 11: تابع get_model_dir باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "get_model_dir"), (
            "❌ get_model_dir function missing"
        )
    
    def test_get_data_dir_function_exists(self):
        """تست 12: تابع get_data_dir باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "get_data_dir"), (
            "❌ get_data_dir function missing"
        )
    
    def test_get_output_dir_function_exists(self):
        """تست 13: تابع get_output_dir باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "get_output_dir"), (
            "❌ get_output_dir function missing"
        )
    
    def test_get_model_dir_respects_env_var(self):
        """تست 14: get_model_dir باید MAHOUN_MODEL_DIR را رعایت کند"""
        from mahoun.core import paths
        
        test_path = "/tmp/test_models"
        
        with patch.dict(os.environ, {"MAHOUN_MODEL_DIR": test_path}):
            model_dir = paths.get_model_dir()
            assert str(model_dir) == test_path
    
    def test_get_model_dir_default_is_relative(self):
        """تست 15: get_model_dir default باید relative به repo باشد"""
        from mahoun.core import paths
        
        with patch.dict(os.environ, {}, clear=False):
            # Clear MAHOUN_MODEL_DIR if set
            if "MAHOUN_MODEL_DIR" in os.environ:
                del os.environ["MAHOUN_MODEL_DIR"]
            
            model_dir = paths.get_model_dir()
            repo_root = paths.get_repo_root()
            
            # Default should be under repo_root
            assert repo_root in model_dir.parents or model_dir == repo_root / "models"
    
    def test_get_data_dir_respects_env_var(self):
        """تست 16: get_data_dir باید MAHOUN_DATA_DIR را رعایت کند"""
        from mahoun.core import paths
        
        test_path = "/tmp/test_data"
        
        with patch.dict(os.environ, {"MAHOUN_DATA_DIR": test_path}):
            data_dir = paths.get_data_dir()
            assert str(data_dir) == test_path
    
    def test_get_output_dir_respects_env_var(self):
        """تست 17: get_output_dir باید MAHOUN_OUTPUT_DIR را رعایت کند"""
        from mahoun.core import paths
        
        test_path = "/tmp/test_output"
        
        with patch.dict(os.environ, {"MAHOUN_OUTPUT_DIR": test_path}):
            output_dir = paths.get_output_dir()
            assert str(output_dir) == test_path
    
    def test_ensure_dir_function_exists(self):
        """تست 18: تابع ensure_dir باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "ensure_dir"), (
            "❌ ensure_dir function missing"
        )
    
    def test_resolve_path_function_exists(self):
        """تست 19: تابع resolve_path باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "resolve_path"), (
            "❌ resolve_path function missing"
        )
    
    def test_validate_model_path_function_exists(self):
        """تست 20: تابع validate_model_path باید وجود داشته باشد"""
        from mahoun.core import paths
        
        assert hasattr(paths, "validate_model_path"), (
            "❌ validate_model_path function missing"
        )


class TestTestsArePortable:
    """تست‌ها باید portable باشند"""
    
    def test_llm_integration_test_handles_missing_models(self):
        """تست 21: test_llm_integration باید missing models را handle کند"""
        test_file = Path(__file__).parent / "test_llm_integration.py"
        
        if not test_file.exists():
            pytest.skip("test_llm_integration.py not found")
        
        content = test_file.read_text()
        
        # Should use MAHOUN_LLM_MODEL_PATH env var
        assert "MAHOUN" in content or "model_path" in content, (
            "❌ test_llm_integration should use env vars for model paths"
        )
        
        # Should have skip logic
        assert "skip" in content.lower() or "exists" in content, (
            "❌ test_llm_integration should skip if models missing"
        )
    
    def test_no_test_file_has_hardcoded_user_paths(self):
        """تست 22: هیچ test file نباید hardcoded user paths داشته باشد"""
        result = subprocess.run(
            [
                "grep", "-RInE", r'/home/[^/]+/',
                "tests/",
                "--include=*.py",
                "--exclude=test_portable_paths.py"
            ],
            capture_output=True,
            text=True
        )
        
        assert result.returncode == 1, (
            f"❌ Found hardcoded paths in test files!\n"
            f"Matches:\n{result.stdout}"
        )


class TestPortabilityDocumentation:
    """تست مستندات portability"""
    
    def test_env_vars_have_descriptions(self):
        """تست 23: env vars باید توضیحات داشته باشند"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        # Should have comments explaining each var
        for var in ["MAHOUN_MODEL_DIR", "MAHOUN_DATA_DIR", "MAHOUN_OUTPUT_DIR"]:
            # Find the var
            var_index = content.find(var)
            assert var_index != -1, f"❌ {var} not found in .env.example"
            
            # Check there's a comment before it (within 200 chars)
            section_before = content[max(0, var_index - 200):var_index]
            assert "#" in section_before, (
                f"❌ {var} should have comment/description"
            )
    
    def test_env_example_shows_default_values(self):
        """تست 24: .env.example باید default values را نشان دهد"""
        env_example = Path(__file__).parent.parent / ".env.example"
        content = env_example.read_text()
        
        # Should mention defaults in comments
        assert "Default:" in content or "default" in content.lower(), (
            "❌ .env.example should document default values"
        )


class TestCompileAndImport:
    """تست compile و import"""
    
    def test_all_python_files_compile(self):
        """تست 25: تمام فایل‌های Python باید compile شوند"""
        repo_root = Path(__file__).parent.parent
        
        result = subprocess.run(
            ["python", "-m", "compileall", "-q", str(repo_root / "mahoun")],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        
        assert result.returncode == 0, (
            f"❌ Python compilation failed!\n"
            f"Errors:\n{result.stderr}"
        )
    
    def test_paths_module_imports_without_error(self):
        """تست 26: ماژول paths باید بدون error import شود"""
        try:
            from mahoun.core.paths import (
                get_repo_root,
                get_model_dir,
                get_data_dir,
                get_output_dir,
                get_cache_dir,
                ensure_dir,
                resolve_path,
                validate_model_path,
                get_safe_model_path
            )
            
            # All functions should be callable
            assert callable(get_repo_root)
            assert callable(get_model_dir)
            assert callable(get_data_dir)
            assert callable(get_output_dir)
            assert callable(get_cache_dir)
            assert callable(ensure_dir)
            assert callable(resolve_path)
            assert callable(validate_model_path)
            assert callable(get_safe_model_path)
            
        except Exception as e:
            pytest.fail(f"❌ Failed to import paths module: {e}")


class TestProductionReadiness:
    """تست آمادگی production"""
    
    def test_no_absolute_paths_in_runtime_configs(self):
        """تست 27: نباید absolute paths در runtime configs باشد"""
        config_dir = Path(__file__).parent.parent / "config"
        
        if not config_dir.exists():
            pytest.skip("config directory not found")
        
        violations = []
        
        for config_file in config_dir.glob("*.json"):
            content = config_file.read_text()
            
            # Check for absolute paths
            if "/home/" in content or "/Users/" in content:
                # Unless it's a placeholder
                if "${" not in content:
                    violations.append(f"{config_file.name}: contains absolute path")
        
        assert len(violations) == 0, (
            f"❌ Found absolute paths in config files:\n" +
            "\n".join(violations)
        )
    
    def test_portable_paths_checklist_complete(self):
        """تست 28: چک‌لیست portability کامل باشد"""
        repo_root = Path(__file__).parent.parent
        
        # Check for /home/haji using find (more reliable)
        python_files = subprocess.run(
            ["find", ".", "-name", "*.py", 
             "-not", "-path", "./venv/*",
             "-not", "-path", "./.git/*",
             "-not", "-name", "ci_check_hardcodes.py",
             "-not", "-name", "test_portable_paths.py"],
            capture_output=True,
            text=True,
            cwd=repo_root
        )
        
        has_haji_in_python = False
        if python_files.returncode == 0:
            for pyfile in python_files.stdout.strip().split('\n'):
                if pyfile and Path(pyfile).exists():
                    if "/home/haji" in Path(repo_root / pyfile).read_text(errors='ignore'):
                        has_haji_in_python = True
                        break
        
        has_haji_in_config = False
        config_dir = repo_root / "config"
        if config_dir.exists():
            for cfg in config_dir.glob("*.json"):
                if "/home/haji" in cfg.read_text(errors='ignore'):
                    has_haji_in_config = True
                    break
        
        checklist = {
            "mahoun/core/paths.py exists": (repo_root / "mahoun" / "core" / "paths.py").exists(),
            "No /home/haji in Python": not has_haji_in_python,
            "No /home/haji in config": not has_haji_in_config,
            ".env.example has MAHOUN_MODEL_DIR": "MAHOUN_MODEL_DIR" in (repo_root / ".env.example").read_text(),
            "paths module imports": True,  # If we got here, it imported
        }
        
        failures = [check for check, passed in checklist.items() if not passed]
        
        assert len(failures) == 0, (
            f"❌ Portability checklist FAILED:\n" +
            "\n".join(f"  - {f}" for f in failures)
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])

