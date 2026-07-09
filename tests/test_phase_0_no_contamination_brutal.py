"""
Phase 0 Architectural Contamination - BRUTAL VERIFICATION SUITE
================================================================

This test suite provides HARD MODE verification that Phase 0 architectural
cleanup is complete and contamination has been eliminated from mahoun/core/models/.

Test Categories (7 Total):
1. Filesystem Scan Test - Physical file verification
2. Import Chain Validation - Canonical location imports work
3. Module Path Verification - __module__ attributes are correct
4. Backward Compatibility Test - Old imports still work via shim
5. __all__ Exports Validation - Export list is correct
6. Type Safety Test - Instantiation and type checking
7. No Contamination Proof - Directory integrity verification

This is a CONSTITUTIONAL test - any failure indicates P0 architectural debt.
"""

import os
import sys
import time
from pathlib import Path
from typing import Set, List
import pytest

# Test configuration
REPO_ROOT = Path(__file__).parent.parent
CORE_MODELS_DIR = REPO_ROOT / "mahoun" / "core" / "models"

# Expected files in mahoun/core/models/ after Phase 0 cleanup
EXPECTED_FILES_ONLY = {
    "__init__.py",
    "entity.py",
    "reasoning.py",
    "project_model",  # directory
    "__pycache__"  # directory (may or may not exist)
}

# Files that MUST NOT exist (contamination indicators)
FORBIDDEN_FILES = {
    "ai_response.py",
    "prompt_template.py",
    "audit_event.py",
    "deployment_profile.py"
}

class TestFilesystemScan:
    """Test Category 1: Verify no contaminated files exist in core/models/"""

    def test_no_forbidden_files_exist(self):
        """HARD: Verify contaminated files do not exist on filesystem"""
        actual_files = set(os.listdir(CORE_MODELS_DIR))

        # Check for forbidden files
        found_forbidden = actual_files & FORBIDDEN_FILES

        assert len(found_forbidden) == 0, (
            f"🔥 CONTAMINATION DETECTED! Found forbidden files in mahoun/core/models/: "
            f"{found_forbidden}\n"
            f"These files should have been moved to canonical locations during Phase 0 cleanup."
        )

    def test_only_expected_files_present(self):
        """HARD: Verify only expected files are present"""
        actual_files = set(os.listdir(CORE_MODELS_DIR))

        # Filter out __pycache__ for comparison if it doesn't exist
        expected = EXPECTED_FILES_ONLY.copy()
        if "__pycache__" not in actual_files:
            expected.discard("__pycache__")

        unexpected = actual_files - expected
        missing = expected - actual_files

        assert len(unexpected) == 0, (
            f"🔥 UNEXPECTED FILES in mahoun/core/models/: {unexpected}\n"
            f"Only these files should exist: {expected}"
        )

        assert len(missing) == 0, (
            f"🔥 MISSING FILES in mahoun/core/models/: {missing}\n"
            f"Expected files: {expected}"
        )

class TestImportChainValidation:
    """Test Category 2: Validate all imports work from canonical locations"""

    def test_import_from_canonical_ai_models(self):
        """HARD: Test imports from mahoun.ai.models work"""
        from mahoun.ai.models import AIResponse, PromptTemplate

        assert AIResponse is not None
        assert PromptTemplate is not None

    def test_import_from_canonical_audit_models(self):
        """HARD: Test imports from mahoun.audit.models work"""
        from mahoun.audit.models import AuditEvent

        assert AuditEvent is not None

    def test_import_from_canonical_infrastructure_models(self):
        """HARD: Test imports from mahoun.infrastructure.models work"""
        from mahoun.infrastructure.models import DeploymentProfile

        assert DeploymentProfile is not None

    def test_import_from_core_models_shim(self):
        """HARD: Test backward compatibility shim works"""
        from mahoun.core.models import AIResponse, AuditEvent, DeploymentProfile

        assert AIResponse is not None
        assert AuditEvent is not None
        assert DeploymentProfile is not None

    def test_imports_are_same_objects(self):
        """BRUTAL: Verify shim imports are IDENTICAL to canonical imports"""
        from mahoun.core.models import AIResponse as AIResp_shim
        from mahoun.ai.models import AIResponse as AIResp_canonical

        from mahoun.core.models import AuditEvent as AuditEvt_shim
        from mahoun.audit.models import AuditEvent as AuditEvt_canonical

        from mahoun.core.models import DeploymentProfile as DP_shim
        from mahoun.infrastructure.models import DeploymentProfile as DP_canonical

        # Identity check - must be the SAME object
        assert AIResp_shim is AIResp_canonical, (
            "🔥 AIResponse from shim is NOT the same object as canonical! "
            "This indicates contamination or duplicate definitions."
        )

        assert AuditEvt_shim is AuditEvt_canonical, (
            "🔥 AuditEvent from shim is NOT the same object as canonical! "
            "This indicates contamination or duplicate definitions."
        )

        assert DP_shim is DP_canonical, (
            "🔥 DeploymentProfile from shim is NOT the same object as canonical! "
            "This indicates contamination or duplicate definitions."
        )

class TestModulePathVerification:
    """Test Category 3: Check __module__ attributes point to canonical locations"""

    def test_airesponse_module_path(self):
        """BRUTAL: Verify AIResponse.__module__ is mahoun.ai.models"""
        from mahoun.core.models import AIResponse

        expected_module = "mahoun.ai.models"
        actual_module = AIResponse.__module__

        assert actual_module == expected_module, (
            f"🔥 AIResponse.__module__ is '{actual_module}' but should be '{expected_module}'!\n"
            f"This means AIResponse is defined in the wrong location."
        )

    def test_auditevent_module_path(self):
        """BRUTAL: Verify AuditEvent.__module__ is mahoun.audit.models"""
        from mahoun.core.models import AuditEvent

        expected_module = "mahoun.audit.models"
        actual_module = AuditEvent.__module__

        assert actual_module == expected_module, (
            f"🔥 AuditEvent.__module__ is '{actual_module}' but should be '{expected_module}'!\n"
            f"This means AuditEvent is defined in the wrong location."
        )

    def test_deploymentprofile_module_path(self):
        """BRUTAL: Verify DeploymentProfile.__module__ is mahoun.infrastructure.models"""
        from mahoun.core.models import DeploymentProfile

        expected_module = "mahoun.infrastructure.models"
        actual_module = DeploymentProfile.__module__

        assert actual_module == expected_module, (
            f"🔥 DeploymentProfile.__module__ is '{actual_module}' but should be '{expected_module}'!\n"
            f"This means DeploymentProfile is defined in the wrong location."
        )

    def test_entity_module_path(self):
        """BRUTAL: Verify Entity.__module__ is mahoun.core.models.entity"""
        from mahoun.core.models import Entity

        expected_module = "mahoun.core.models.entity"
        actual_module = Entity.__module__

        assert actual_module == expected_module, (
            f"🔥 Entity.__module__ is '{actual_module}' but should be '{expected_module}'!\n"
            f"Entity should remain in mahoun.core.models as it's a core primitive."
        )

class TestBackwardCompatibility:
    """Test Category 4: Verify old import paths still work via shim"""

    def test_legacy_import_patterns_work(self):
        """HARD: Test that legacy code can still import from mahoun.core.models"""
        try:
            from mahoun.core.models import (
                AIResponse,
                AuditEvent,
                DeploymentProfile,
                Entity,
                ReasoningStep
            )

            # All imports should succeed
            assert AIResponse is not None
            assert AuditEvent is not None
            assert DeploymentProfile is not None
            assert Entity is not None
            assert ReasoningStep is not None

        except ImportError as e:
            pytest.fail(
                f"🔥 BACKWARD COMPATIBILITY BROKEN! Legacy import failed: {e}\n"
                f"The shim in mahoun/core/models/__init__.py must maintain backward compatibility."
            )

class TestExportsValidation:
    """Test Category 5: Validate __all__ exports"""

    def test_all_exports_defined(self):
        """HARD: Verify __all__ is defined and non-empty"""
        from mahoun.core.models import __all__

        assert __all__ is not None, "🔥 __all__ is not defined!"
        assert len(__all__) > 0, "🔥 __all__ is empty!"

    def test_critical_exports_present(self):
        """BRUTAL: Verify critical exports are in __all__"""
        from mahoun.core.models import __all__

        critical_exports = {
            "AIResponse",
            "AuditEvent",
            "DeploymentProfile",
            "Entity",
            "ReasoningStep",
            "ReasoningResult"
        }

        missing = critical_exports - set(__all__)

        assert len(missing) == 0, (
            f"🔥 CRITICAL EXPORTS MISSING from __all__: {missing}\n"
            f"These must be exported for backward compatibility."
        )

class TestTypeSafety:
    """Test Category 6: Verify types work correctly"""

    def test_airesponse_instantiation(self):
        """HARD: Test AIResponse can be instantiated"""
        from mahoun.core.models import AIResponse, TokenUsage, ResponseStatus, GenerationMetadata

        # Create required objects
        token_usage = TokenUsage(prompt_tokens=10, completion_tokens=20, total_tokens=30)
        generation_metadata = GenerationMetadata(
            model_id="test-model",
            model_format="GGUF",
            quantization="Q4_K_M",
            parameters_count=7000000000,
            generation_params={"temperature": 0.7},
            inference_time_ms=100.0,
            tokens_per_second=100.0,
            memory_usage_mb=512.0,
            deployment_profile="test"
        )

        # Instantiate AIResponse with correct signature
        response = AIResponse(
            request_id="test-request-123",
            correlation_id="test-corr-456",
            response_text="test response",
            status=ResponseStatus.SUCCESS,
            confidence_score=0.95,
            token_usage=token_usage,
            generation_metadata=generation_metadata
        )

        assert response.response_text == "test response"
        assert response.generation_metadata.model_id == "test-model"
        assert response.status == ResponseStatus.SUCCESS
        assert response.confidence_score == 0.95

    def test_entity_instantiation(self):
        """HARD: Test Entity can be instantiated"""
        from mahoun.core.models import Entity, EntityType

        # Entity requires: text, entity_type, start, end
        entity = Entity(
            text="John Doe",
            entity_type=EntityType.PERSON,
            start=0,
            end=8,
            confidence=0.95
        )

        assert entity.text == "John Doe"
        assert entity.entity_type == EntityType.PERSON
        assert entity.confidence == 0.95
        assert entity.start == 0
        assert entity.end == 8

    def test_type_checking_works(self):
        """BRUTAL: Verify isinstance checks work across import paths"""
        from mahoun.core.models import AIResponse as AIResp_shim
        from mahoun.ai.models import (
            AIResponse as AIResp_canonical,
            TokenUsage,
            ResponseStatus,
            GenerationMetadata
        )

        # Create required objects
        token_usage = TokenUsage(prompt_tokens=5, completion_tokens=10, total_tokens=15)
        generation_metadata = GenerationMetadata(
            model_id="test-model",
            model_format="GGUF",
            quantization=None,
            parameters_count=None,
            generation_params={},
            inference_time_ms=50.0,
            tokens_per_second=None,
            memory_usage_mb=256.0,
            deployment_profile="test"
        )

        # Create instance using canonical import with correct signature
        response = AIResp_canonical(
            request_id="test-req",
            correlation_id="test-corr",
            response_text="test",
            status=ResponseStatus.SUCCESS,
            confidence_score=0.9,
            token_usage=token_usage,
            generation_metadata=generation_metadata
        )

        # Type check should work with shim import
        assert isinstance(response, AIResp_shim), (
            "🔥 TYPE CHECKING BROKEN! "
            "isinstance() fails across canonical and shim imports."
        )

class TestNoContaminationProof:
    """Test Category 7: Comprehensive contamination proof"""

    def test_directory_file_count(self):
        """BRUTAL: Count and verify exact file structure"""
        actual_files = [
            f for f in os.listdir(CORE_MODELS_DIR)
            if not f.startswith('.') and f != "__pycache__"
        ]

        # Should be exactly: __init__.py, entity.py, reasoning.py, project_model/
        expected_count = 4
        actual_count = len(actual_files)

        assert actual_count == expected_count, (
            f"🔥 FILE COUNT MISMATCH in mahoun/core/models/!\n"
            f"Expected {expected_count} items, found {actual_count}\n"
            f"Actual items: {actual_files}\n"
            f"This suggests contamination or missing files."
        )

    def test_no_py_files_with_contaminated_names(self):
        """BRUTAL: Scan for any .py files with contamination patterns"""
        contamination_patterns = [
            "ai_response",
            "prompt_template",
            "audit_event",
            "deployment_profile"
        ]

        all_files = []
        for root, dirs, files in os.walk(CORE_MODELS_DIR):
            # Skip __pycache__
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for file in files:
                if file.endswith(".py"):
                    all_files.append(os.path.join(root, file))

        contaminated = []
        for file_path in all_files:
            basename = os.path.basename(file_path)
            for pattern in contamination_patterns:
                if pattern in basename.lower():
                    contaminated.append((file_path, pattern))

        assert len(contaminated) == 0, (
            f"🔥 CONTAMINATION PATTERNS DETECTED!\n"
            f"Found files matching contamination patterns:\n" +
            "\n".join(f"  - {path} (pattern: {pattern})" for path, pattern in contaminated)
        )

class TestPerformanceMetrics:
    """Bonus: Performance verification"""

    def test_import_time_acceptable(self):
        """HARD: Verify import time is reasonable"""
        import timeit

        # Measure import time
        import_code = """
from mahoun.core.models import (
    AIResponse, AuditEvent, DeploymentProfile,
    Entity, ReasoningStep
)
"""

        # Run 10 times and take average
        time_taken = timeit.timeit(import_code, number=10) / 10

        # Should be under 100ms per import
        max_time = 0.1

        assert time_taken < max_time, (
            f"🔥 IMPORT TOO SLOW!\n"
            f"Import took {time_taken*1000:.2f}ms, max allowed is {max_time*1000:.2f}ms\n"
            f"This may indicate circular imports or heavy initialization."
        )

        print(f"✅ Import time: {time_taken*1000:.2f}ms (acceptable)")

# Summary test - runs last
class TestPhase0Summary:
    """Final summary test"""

    def test_phase_0_cleanup_complete(self):
        """FINAL: Comprehensive Phase 0 verification"""
        from mahoun.core.models import AIResponse, AuditEvent, DeploymentProfile, Entity
        from mahoun.ai.models import AIResponse as AIResp_canonical
        from mahoun.audit.models import AuditEvent as AuditEvt_canonical
        from mahoun.infrastructure.models import DeploymentProfile as DP_canonical

        # Verify no contaminated files
        actual_files = set(os.listdir(CORE_MODELS_DIR))
        forbidden_found = actual_files & FORBIDDEN_FILES

        # Verify imports are identical
        imports_identical = (
            AIResponse is AIResp_canonical and
            AuditEvent is AuditEvt_canonical and
            DeploymentProfile is DP_canonical
        )

        # Verify module paths
        paths_correct = (
            AIResponse.__module__ == "mahoun.ai.models" and
            AuditEvent.__module__ == "mahoun.audit.models" and
            DeploymentProfile.__module__ == "mahoun.infrastructure.models"
        )

        success = (
            len(forbidden_found) == 0 and
            imports_identical and
            paths_correct
        )

        if success:
            print("\n" + "="*70)
            print("🎉 PHASE 0 CONTAMINATION CLEANUP: VERIFIED ✅")
            print("="*70)
            print("✅ No contaminated files found")
            print("✅ All imports work from canonical locations")
            print("✅ Backward compatibility shim working")
            print("✅ Module paths are correct")
            print("✅ Type safety preserved")
            print("="*70)

        assert success, (
            "🔥 PHASE 0 CLEANUP INCOMPLETE!\n"
            f"Forbidden files: {forbidden_found}\n"
            f"Imports identical: {imports_identical}\n"
            f"Paths correct: {paths_correct}"
        )

if __name__ == "__main__":
    # Run with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
