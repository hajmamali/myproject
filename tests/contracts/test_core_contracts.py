"""
Contract Tests for Core Module

These tests validate that core module contracts are correctly defined and enforceable.
Tests are independent of behavior - they only validate schema compliance.

Test Categories:
1. Input Contract Tests: Validate input schemas accept/reject correctly
2. Output Contract Tests: Validate output schemas are complete
3. Error Contract Tests: Validate error schemas cover all failure modes
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from mahoun.schemas.contracts.core_contracts import (
    # Runtime Configuration
    RuntimeMode,
    RuntimeSettingsOutput,
    BooleanOutput,
    GraphConfigOutput,
    
    # Core Models
    LegalDocTypeContract,
    LegalDocumentInput,
    LegalDocumentOutput,
    LegalEntityInput,
    LegalEntityOutput,
    ReasoningStepContract,
    CausalRelationContract,
    ReasoningResultContract,
    UncertaintyEstimateContract,
    
    # Errors
    CoreModuleError,
)


# ============================================================================
# Runtime Configuration Contract Tests
# ============================================================================

class TestRuntimeSettingsOutput:
    """Test RuntimeSettingsOutput contract."""
    
    def test_valid_runtime_settings(self):
        """Test valid runtime settings accepted."""
        settings = RuntimeSettingsOutput(
            mode=RuntimeMode.DESKTOP_MINIMAL,
            skip_graph=True,
            skip_lora_training=True,
            graph_config={"enable_analytics": False}
        )
        assert settings.mode == RuntimeMode.DESKTOP_MINIMAL
        assert settings.skip_graph is True
    
    def test_missing_required_fields(self):
        """Test missing required fields rejected."""
        with pytest.raises(ValidationError):
            RuntimeSettingsOutput(
                mode=RuntimeMode.PRODUCTION
                # Missing skip_graph, skip_lora_training
            )
    
    def test_invalid_mode(self):
        """Test invalid mode rejected."""
        with pytest.raises(ValidationError):
            RuntimeSettingsOutput(
                mode="invalid-mode",
                skip_graph=False,
                skip_lora_training=False
            )
    
    def test_immutability(self):
        """Test settings are immutable."""
        settings = RuntimeSettingsOutput(
            mode=RuntimeMode.PRODUCTION,
            skip_graph=False,
            skip_lora_training=False
        )
        with pytest.raises(ValidationError):
            settings.mode = RuntimeMode.DESKTOP_MINIMAL


class TestBooleanOutput:
    """Test BooleanOutput contract."""
    
    def test_valid_boolean_output(self):
        """Test valid boolean output accepted."""
        output = BooleanOutput(result=True)
        assert output.result is True
        
        output = BooleanOutput(result=False)
        assert output.result is False
    
    def test_missing_result(self):
        """Test missing result rejected."""
        with pytest.raises(ValidationError):
            BooleanOutput()


class TestGraphConfigOutput:
    """Test GraphConfigOutput contract."""
    
    def test_valid_graph_config(self):
        """Test valid graph config accepted."""
        config = GraphConfigOutput(
            enable_quality_assessment=True,
            enable_analytics=False,
            enable_real_time_updates=True,
            batch_size=500
        )
        assert config.batch_size == 500
    
    def test_default_values(self):
        """Test default values applied."""
        config = GraphConfigOutput()
        assert config.enable_quality_assessment is True
        assert config.batch_size == 100
    
    def test_batch_size_constraints(self):
        """Test batch size constraints enforced."""
        # Too small
        with pytest.raises(ValidationError):
            GraphConfigOutput(batch_size=0)
        
        # Too large
        with pytest.raises(ValidationError):
            GraphConfigOutput(batch_size=20000)
        
        # Valid boundaries
        GraphConfigOutput(batch_size=1)
        GraphConfigOutput(batch_size=10000)


# ============================================================================
# Core Models Contract Tests
# ============================================================================

class TestLegalDocumentInput:
    """Test LegalDocumentInput contract."""
    
    def test_valid_document_input(self):
        """Test valid document input accepted."""
        doc = LegalDocumentInput(
            doc_id="DOC-001",
            doc_type=LegalDocTypeContract.VERDICT,
            title="Test Verdict",
            content="This is a test verdict content."
        )
        assert doc.doc_id == "DOC-001"
        assert doc.doc_type == LegalDocTypeContract.VERDICT
    
    def test_empty_doc_id_rejected(self):
        """Test empty doc_id rejected."""
        with pytest.raises(ValidationError):
            LegalDocumentInput(
                doc_id="",
                doc_type=LegalDocTypeContract.VERDICT,
                title="Test",
                content="Content"
            )
    
    def test_whitespace_doc_id_rejected(self):
        """Test whitespace-only doc_id rejected."""
        with pytest.raises(ValidationError):
            LegalDocumentInput(
                doc_id="   ",
                doc_type=LegalDocTypeContract.VERDICT,
                title="Test",
                content="Content"
            )
    
    def test_empty_title_rejected(self):
        """Test empty title rejected."""
        with pytest.raises(ValidationError):
            LegalDocumentInput(
                doc_id="DOC-001",
                doc_type=LegalDocTypeContract.VERDICT,
                title="",
                content="Content"
            )
    
    def test_empty_content_rejected(self):
        """Test empty content rejected."""
        with pytest.raises(ValidationError):
            LegalDocumentInput(
                doc_id="DOC-001",
                doc_type=LegalDocTypeContract.VERDICT,
                title="Test",
                content=""
            )
    
    def test_metadata_optional(self):
        """Test metadata is optional."""
        doc = LegalDocumentInput(
            doc_id="DOC-001",
            doc_type=LegalDocTypeContract.STATUTE,
            title="Test Statute",
            content="Statute content"
        )
        assert doc.metadata == {}
    
    def test_doc_id_trimmed(self):
        """Test doc_id is trimmed."""
        doc = LegalDocumentInput(
            doc_id="  DOC-001  ",
            doc_type=LegalDocTypeContract.CONTRACT,
            title="Test",
            content="Content"
        )
        assert doc.doc_id == "DOC-001"


class TestLegalDocumentOutput:
    """Test LegalDocumentOutput contract."""
    
    def test_valid_document_output(self):
        """Test valid document output accepted."""
        doc = LegalDocumentOutput(
            doc_id="DOC-001",
            doc_type=LegalDocTypeContract.VERDICT,
            title="Test Verdict",
            content="Content",
            metadata={"key": "value"},
            created_at=datetime.now()
        )
        assert doc.doc_id == "DOC-001"
    
    def test_missing_created_at_rejected(self):
        """Test missing created_at rejected."""
        with pytest.raises(ValidationError):
            LegalDocumentOutput(
                doc_id="DOC-001",
                doc_type=LegalDocTypeContract.VERDICT,
                title="Test",
                content="Content",
                metadata={}
            )
    
    def test_immutability(self):
        """Test output is immutable."""
        doc = LegalDocumentOutput(
            doc_id="DOC-001",
            doc_type=LegalDocTypeContract.VERDICT,
            title="Test",
            content="Content",
            metadata={},
            created_at=datetime.now()
        )
        with pytest.raises(ValidationError):
            doc.title = "Modified"


class TestLegalEntityInput:
    """Test LegalEntityInput contract."""
    
    def test_valid_entity_input(self):
        """Test valid entity input accepted."""
        entity = LegalEntityInput(
            entity_id="ENT-001",
            entity_type="PERSON",
            name="John Doe",
            properties={"role": "plaintiff"},
            confidence=0.95
        )
        assert entity.entity_id == "ENT-001"
        assert entity.confidence == 0.95
    
    def test_confidence_defaults_to_one(self):
        """Test confidence defaults to 1.0."""
        entity = LegalEntityInput(
            entity_id="ENT-001",
            entity_type="ORGANIZATION",
            name="ACME Corp"
        )
        assert entity.confidence == 1.0
    
    def test_confidence_range_enforced(self):
        """Test confidence range [0.0, 1.0] enforced."""
        # Too low
        with pytest.raises(ValidationError):
            LegalEntityInput(
                entity_id="ENT-001",
                entity_type="PERSON",
                name="Test",
                confidence=-0.1
            )
        
        # Too high
        with pytest.raises(ValidationError):
            LegalEntityInput(
                entity_id="ENT-001",
                entity_type="PERSON",
                name="Test",
                confidence=1.5
            )
        
        # Valid boundaries
        LegalEntityInput(entity_id="E1", entity_type="T", name="N", confidence=0.0)
        LegalEntityInput(entity_id="E1", entity_type="T", name="N", confidence=1.0)
    
    def test_empty_entity_id_rejected(self):
        """Test empty entity_id rejected."""
        with pytest.raises(ValidationError):
            LegalEntityInput(
                entity_id="",
                entity_type="PERSON",
                name="Test"
            )
    
    def test_empty_name_rejected(self):
        """Test empty name rejected."""
        with pytest.raises(ValidationError):
            LegalEntityInput(
                entity_id="ENT-001",
                entity_type="PERSON",
                name=""
            )


class TestReasoningStepContract:
    """Test ReasoningStepContract."""
    
    def test_valid_reasoning_step(self):
        """Test valid reasoning step accepted."""
        step = ReasoningStepContract(
            step="Analyze question",
            reasoning="The question asks about...",
            confidence=0.9,
            evidence=["fact1", "fact2"]
        )
        assert step.confidence == 0.9
        assert len(step.evidence) == 2
    
    def test_empty_step_rejected(self):
        """Test empty step rejected."""
        with pytest.raises(ValidationError):
            ReasoningStepContract(
                step="",
                reasoning="Test",
                confidence=0.8
            )
    
    def test_empty_reasoning_rejected(self):
        """Test empty reasoning rejected."""
        with pytest.raises(ValidationError):
            ReasoningStepContract(
                step="Test step",
                reasoning="",
                confidence=0.8
            )
    
    def test_confidence_range_enforced(self):
        """Test confidence range enforced."""
        with pytest.raises(ValidationError):
            ReasoningStepContract(
                step="Test",
                reasoning="Test",
                confidence=1.5
            )
    
    def test_evidence_optional(self):
        """Test evidence is optional."""
        step = ReasoningStepContract(
            step="Test",
            reasoning="Test",
            confidence=0.8
        )
        assert step.evidence == []


class TestCausalRelationContract:
    """Test CausalRelationContract."""
    
    def test_valid_causal_relation(self):
        """Test valid causal relation accepted."""
        relation = CausalRelationContract(
            cause="Event A",
            effect="Event B",
            strength=0.75,
            explanation="A causes B because..."
        )
        assert relation.strength == 0.75
    
    def test_empty_cause_rejected(self):
        """Test empty cause rejected."""
        with pytest.raises(ValidationError):
            CausalRelationContract(
                cause="",
                effect="Event B",
                strength=0.5
            )
    
    def test_empty_effect_rejected(self):
        """Test empty effect rejected."""
        with pytest.raises(ValidationError):
            CausalRelationContract(
                cause="Event A",
                effect="",
                strength=0.5
            )
    
    def test_strength_range_enforced(self):
        """Test strength range [0.0, 1.0] enforced."""
        with pytest.raises(ValidationError):
            CausalRelationContract(
                cause="A",
                effect="B",
                strength=-0.1
            )
        
        with pytest.raises(ValidationError):
            CausalRelationContract(
                cause="A",
                effect="B",
                strength=1.1
            )
    
    def test_explanation_optional(self):
        """Test explanation is optional."""
        relation = CausalRelationContract(
            cause="A",
            effect="B",
            strength=0.5
        )
        assert relation.explanation == ""


class TestReasoningResultContract:
    """Test ReasoningResultContract."""
    
    def test_valid_reasoning_result(self):
        """Test valid reasoning result accepted."""
        result = ReasoningResultContract(
            question="What is the verdict?",
            context="Case context",
            facts=["fact1", "fact2"],
            reasoning_chain=[
                ReasoningStepContract(
                    step="Step 1",
                    reasoning="Reasoning 1",
                    confidence=0.9
                )
            ],
            final_answer="The verdict is...",
            confidence=0.85
        )
        assert result.confidence == 0.85
        assert len(result.reasoning_chain) == 1
    
    def test_empty_question_rejected(self):
        """Test empty question rejected."""
        with pytest.raises(ValidationError):
            ReasoningResultContract(
                question="",
                reasoning_chain=[
                    ReasoningStepContract(step="S", reasoning="R", confidence=0.8)
                ],
                final_answer="Answer",
                confidence=0.8
            )
    
    def test_empty_final_answer_rejected(self):
        """Test empty final answer rejected."""
        with pytest.raises(ValidationError):
            ReasoningResultContract(
                question="Question",
                reasoning_chain=[
                    ReasoningStepContract(step="S", reasoning="R", confidence=0.8)
                ],
                final_answer="",
                confidence=0.8
            )
    
    def test_empty_reasoning_chain_rejected(self):
        """Test empty reasoning chain rejected."""
        with pytest.raises(ValidationError):
            ReasoningResultContract(
                question="Question",
                reasoning_chain=[],
                final_answer="Answer",
                confidence=0.8
            )
    
    def test_confidence_range_enforced(self):
        """Test confidence range enforced."""
        with pytest.raises(ValidationError):
            ReasoningResultContract(
                question="Q",
                reasoning_chain=[
                    ReasoningStepContract(step="S", reasoning="R", confidence=0.8)
                ],
                final_answer="A",
                confidence=1.5
            )
    
    def test_reasoning_depth_non_negative(self):
        """Test reasoning depth must be non-negative."""
        with pytest.raises(ValidationError):
            ReasoningResultContract(
                question="Q",
                reasoning_chain=[
                    ReasoningStepContract(step="S", reasoning="R", confidence=0.8)
                ],
                final_answer="A",
                confidence=0.8,
                reasoning_depth=-1
            )


class TestUncertaintyEstimateContract:
    """Test UncertaintyEstimateContract."""
    
    def test_valid_uncertainty_estimate(self):
        """Test valid uncertainty estimate accepted."""
        estimate = UncertaintyEstimateContract(
            mean=0.75,
            variance=0.05,
            confidence_interval=(0.65, 0.85),
            method="bootstrap"
        )
        assert estimate.mean == 0.75
        assert estimate.variance == 0.05
    
    def test_negative_variance_rejected(self):
        """Test negative variance rejected."""
        with pytest.raises(ValidationError):
            UncertaintyEstimateContract(
                mean=0.5,
                variance=-0.1,
                confidence_interval=(0.4, 0.6),
                method="test"
            )
    
    def test_invalid_confidence_interval_rejected(self):
        """Test invalid confidence interval rejected."""
        # Lower > upper
        with pytest.raises(ValidationError):
            UncertaintyEstimateContract(
                mean=0.5,
                variance=0.1,
                confidence_interval=(0.7, 0.3),
                method="test"
            )
    
    def test_empty_method_rejected(self):
        """Test empty method rejected."""
        with pytest.raises(ValidationError):
            UncertaintyEstimateContract(
                mean=0.5,
                variance=0.1,
                confidence_interval=(0.4, 0.6),
                method=""
            )


# ============================================================================
# Error Contract Tests
# ============================================================================

class TestCoreModuleError:
    """Test CoreModuleError contract."""
    
    def test_valid_validation_error(self):
        """Test valid ValidationError accepted."""
        error = CoreModuleError(
            error_type="ValidationError",
            message="Invalid input",
            details={"field": "doc_id"},
            recoverable=True
        )
        assert error.error_type == "ValidationError"
    
    def test_valid_configuration_error(self):
        """Test valid ConfigurationError accepted."""
        error = CoreModuleError(
            error_type="ConfigurationError",
            message="Invalid config"
        )
        assert error.error_type == "ConfigurationError"
    
    def test_valid_state_error(self):
        """Test valid StateError accepted."""
        error = CoreModuleError(
            error_type="StateError",
            message="Invalid state"
        )
        assert error.error_type == "StateError"
    
    def test_invalid_error_type_rejected(self):
        """Test invalid error type rejected."""
        with pytest.raises(ValidationError):
            CoreModuleError(
                error_type="UnknownError",
                message="Test"
            )
    
    def test_empty_message_rejected(self):
        """Test empty message rejected."""
        with pytest.raises(ValidationError):
            CoreModuleError(
                error_type="ValidationError",
                message=""
            )
    
    def test_recoverable_defaults_to_true(self):
        """Test recoverable defaults to True."""
        error = CoreModuleError(
            error_type="ValidationError",
            message="Test"
        )
        assert error.recoverable is True
    
    def test_details_optional(self):
        """Test details is optional."""
        error = CoreModuleError(
            error_type="ValidationError",
            message="Test"
        )
        assert error.details is None


# ============================================================================
# Contract Completeness Tests
# ============================================================================

class TestContractCompleteness:
    """Test that all contracts are complete and consistent."""
    
    def test_all_runtime_contracts_defined(self):
        """Test all runtime configuration contracts defined."""
        assert RuntimeMode is not None
        assert RuntimeSettingsOutput is not None
        assert BooleanOutput is not None
        assert GraphConfigOutput is not None
    
    def test_all_core_model_contracts_defined(self):
        """Test all core model contracts defined."""
        assert LegalDocTypeContract is not None
        assert LegalDocumentInput is not None
        assert LegalDocumentOutput is not None
        assert LegalEntityInput is not None
        assert LegalEntityOutput is not None
        assert ReasoningStepContract is not None
        assert CausalRelationContract is not None
        assert ReasoningResultContract is not None
        assert UncertaintyEstimateContract is not None
    
    def test_error_contract_defined(self):
        """Test error contract defined."""
        assert CoreModuleError is not None
    
    def test_all_error_types_covered(self):
        """Test all error types are covered."""
        error_types = ["ValidationError", "ConfigurationError", "StateError"]
        for error_type in error_types:
            error = CoreModuleError(
                error_type=error_type,
                message="Test"
            )
            assert error.error_type == error_type
