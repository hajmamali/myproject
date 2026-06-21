"""
Comprehensive Core Module Tests
================================
Tests for mahoun.core and mahoun.schemas modules.
Target: Increase coverage from 3% to higher!
"""

import pytest
from datetime import datetime
from typing import Dict, Any


# =============================================================================
# SCHEMA TESTS - mahoun.schemas.legal_struct_schema
# =============================================================================

class TestPartyInfo:
    """Tests for PartyInfo schema"""
    
    def test_party_info_empty(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo()
        assert party.title is None
        assert party.name is None
        assert party.father_name is None
    
    def test_party_info_full(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo(title="آقای", name="علی احمدی", father_name="محمد")
        assert party.title == "آقای"
        assert party.name == "علی احمدی"
        assert party.father_name == "محمد"
    
    def test_party_info_extra_fields(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo(name="Test", custom_field="extra")
        assert party.name == "Test"
        assert party.custom_field == "extra"  # extra="allow"


class TestParties:
    """Tests for Parties schema"""
    
    def test_parties_empty(self):
        from mahoun.schemas.legal_struct_schema import Parties, PartyInfo
        parties = Parties()
        assert parties.respondents == []
        assert parties.third_party_objector is None
    
    def test_parties_with_respondents(self):
        from mahoun.schemas.legal_struct_schema import Parties, PartyInfo
        p1 = PartyInfo(name="شخص اول")
        p2 = PartyInfo(name="شخص دوم")
        parties = Parties(respondents=[p1, p2])
        assert len(parties.respondents) == 2
        assert parties.respondents[0].name == "شخص اول"


class TestCaseMeta:
    """Tests for CaseMeta schema"""
    
    def test_case_meta_empty(self):
        from mahoun.schemas.legal_struct_schema import CaseMeta
        meta = CaseMeta()
        assert meta.court_level is None
        assert meta.is_final is None
    
    def test_case_meta_full(self):
        from mahoun.schemas.legal_struct_schema import CaseMeta
        meta = CaseMeta(
            court_level="دادگاه تجدیدنظر",
            procedure_stage="تجدیدنظر",
            case_type="اعتراض ثالث",
            is_final=True,
            finality_basis="عدم اعتراض",
            branch_number="15",
            city="تهران",
            province="تهران",
            decision_date="2024-01-15"
        )
        assert meta.court_level == "دادگاه تجدیدنظر"
        assert meta.is_final is True
        assert meta.city == "تهران"


class TestClaims:
    """Tests for Claims schema"""
    
    def test_claims_empty(self):
        from mahoun.schemas.legal_struct_schema import Claims
        claims = Claims()
        assert claims.main == []
        assert claims.execution_files == []
    
    def test_claims_with_data(self):
        from mahoun.schemas.legal_struct_schema import Claims
        claims = Claims(
            main=["مطالبه خسارت", "استرداد ثمن"],
            execution_files=["1402/123", "1402/456"]
        )
        assert len(claims.main) == 2
        assert "مطالبه خسارت" in claims.main


class TestLegalReferences:
    """Tests for LegalReferences schema"""
    
    def test_legal_references_empty(self):
        from mahoun.schemas.legal_struct_schema import LegalReferences
        refs = LegalReferences()
        assert refs.substantive_law == []
        assert refs.procedural_law == []
        assert refs.fiqh_principles == []
    
    def test_legal_references_with_data(self):
        from mahoun.schemas.legal_struct_schema import LegalReferences
        refs = LegalReferences(
            substantive_law=["ماده 183 قانون مدنی", "ماده 10 قانون مدنی"],
            procedural_law=["ماده 358 آیین دادرسی مدنی"],
            fiqh_principles=["اصل لزوم", "قاعده لاضرر"]
        )
        assert len(refs.substantive_law) == 2
        assert "ماده 183 قانون مدنی" in refs.substantive_law


class TestPersonEntityInfo:
    """Tests for PersonEntityInfo NER schema"""
    
    def test_person_entity_minimal(self):
        from mahoun.schemas.legal_struct_schema import PersonEntityInfo
        person = PersonEntityInfo(text="علی احمدی")
        assert person.text == "علی احمدی"
        assert person.confidence == 1.0
        assert person.start == 0
        assert person.end == 0
    
    def test_person_entity_full(self):
        from mahoun.schemas.legal_struct_schema import PersonEntityInfo
        person = PersonEntityInfo(
            text="آقای علی احمدی فرزند محمد",
            title="آقای",
            name="علی احمدی",
            father_name="محمد",
            role="خواهان",
            national_id="0012345678",
            confidence=0.95,
            start=10,
            end=35
        )
        assert person.title == "آقای"
        assert person.role == "خواهان"
        assert person.confidence == 0.95
    
    def test_person_entity_confidence_bounds(self):
        from mahoun.schemas.legal_struct_schema import PersonEntityInfo
        # Test valid confidence
        person = PersonEntityInfo(text="test", confidence=0.5)
        assert person.confidence == 0.5
        
        # Test boundary values
        person_min = PersonEntityInfo(text="test", confidence=0.0)
        assert person_min.confidence == 0.0
        
        person_max = PersonEntityInfo(text="test", confidence=1.0)
        assert person_max.confidence == 1.0


class TestExtractedEntities:
    """Tests for ExtractedEntities container"""
    
    def test_extracted_entities_empty(self):
        from mahoun.schemas.legal_struct_schema import ExtractedEntities
        entities = ExtractedEntities()
        assert entities.persons == []
        assert entities.organizations == []
        assert entities.courts == []
        assert entities.laws == []
        assert entities.topics == []
    
    def test_extracted_entities_with_data(self):
        from mahoun.schemas.legal_struct_schema import (
            ExtractedEntities, PersonEntityInfo, LawEntityInfo
        )
        entities = ExtractedEntities(
            persons=[PersonEntityInfo(text="علی")],
            laws=[LawEntityInfo(text="ماده 183", article_number="183")]
        )
        assert len(entities.persons) == 1
        assert len(entities.laws) == 1


class TestVerdictStruct:
    """Tests for the main VerdictStruct schema"""
    
    def test_verdict_struct_empty(self):
        from mahoun.schemas.legal_struct_schema import VerdictStruct
        verdict = VerdictStruct()
        assert verdict.case_meta is not None
        assert verdict.parties is not None
        assert verdict.claims is not None
        assert verdict.system_tags == []
    
    def test_verdict_struct_full(self):
        from mahoun.schemas.legal_struct_schema import (
            VerdictStruct, CaseMeta, Parties, PartyInfo, Claims,
            LegalReferences, ExtractedEntities, PersonEntityInfo
        )
        verdict = VerdictStruct(
            case_meta=CaseMeta(
                court_level="دادگاه بدوی",
                is_final=True
            ),
            parties=Parties(
                respondents=[PartyInfo(name="خوانده")]
            ),
            claims=Claims(main=["مطالبه خسارت"]),
            legal_references=LegalReferences(
                substantive_law=["ماده 183"]
            ),
            entities=ExtractedEntities(
                persons=[PersonEntityInfo(text="خواهان")]
            ),
            system_tags=["processed", "verified"]
        )
        assert verdict.case_meta.court_level == "دادگاه بدوی"
        assert len(verdict.parties.respondents) == 1
        assert len(verdict.system_tags) == 2


# =============================================================================
# CORE MODEL TESTS - mahoun.core.models
# =============================================================================

class TestLegalDocType:
    """Tests for LegalDocType enum"""
    
    def test_legal_doc_types(self):
        from mahoun.core.models import LegalDocType
        assert LegalDocType.LAW == "law"
        assert LegalDocType.VERDICT == "verdict"
        assert LegalDocType.CONTRACT == "contract"
        assert LegalDocType.REGULATION == "regulation"
        assert LegalDocType.ARTICLE == "article"
        assert LegalDocType.OPINION == "opinion"
        assert LegalDocType.OTHER == "other"
    
    def test_legal_doc_type_all_values(self):
        from mahoun.core.models import LegalDocType
        all_types = list(LegalDocType)
        assert len(all_types) == 7


class TestLegalDocument:
    """Tests for LegalDocument model"""
    
    def test_legal_document_minimal(self):
        from mahoun.core.models import LegalDocument
        doc = LegalDocument(id="doc-1", text="متن سند")
        assert doc.id == "doc-1"
        assert doc.text == "متن سند"
        assert doc.metadata == {}
        assert doc.doc_type is None
    
    def test_legal_document_full(self):
        from mahoun.core.models import LegalDocument, LegalDocType
        doc = LegalDocument(
            id="verdict-123",
            text="رای دادگاه",
            metadata={"source": "tara.ir"},
            doc_type=LegalDocType.VERDICT,
            title="رای شماره ۱۲۳",
            source_file="verdict.txt"
        )
        assert doc.id == "verdict-123"
        assert doc.doc_type == LegalDocType.VERDICT
        assert doc.metadata["source"] == "tara.ir"
        assert doc.created_at is not None


class TestLegalEntity:
    """Tests for LegalEntity model"""
    
    def test_legal_entity_minimal(self):
        from mahoun.core.models import LegalEntity
        entity = LegalEntity(name="علی احمدی", entity_type="person")
        assert entity.name == "علی احمدی"
        assert entity.entity_type == "person"
        assert entity.role is None
    
    def test_legal_entity_full(self):
        from mahoun.core.models import LegalEntity
        entity = LegalEntity(
            name="بانک ملی",
            entity_type="organization",
            role="خوانده",
            metadata={"registration_id": "12345"}
        )
        assert entity.entity_type == "organization"
        assert entity.role == "خوانده"


class TestReasoningStep:
    """Tests for ReasoningStep dataclass"""
    
    def test_reasoning_step_minimal(self):
        from mahoun.core.models import ReasoningStep
        step = ReasoningStep(step="تحلیل", reasoning="بررسی مدارک")
        assert step.step == "تحلیل"
        assert step.reasoning == "بررسی مدارک"
        assert step.confidence == 0.5
        assert step.evidence == []
    
    def test_reasoning_step_full(self):
        from mahoun.core.models import ReasoningStep
        step = ReasoningStep(
            step="نتیجه‌گیری",
            reasoning="با توجه به مدارک",
            confidence=0.9,
            evidence=["سند ۱", "سند ۲"]
        )
        assert step.confidence == 0.9
        assert len(step.evidence) == 2


class TestCausalRelation:
    """Tests for CausalRelation dataclass"""
    
    def test_causal_relation(self):
        from mahoun.core.models import CausalRelation
        rel = CausalRelation(
            cause="عدم پرداخت",
            effect="فسخ قرارداد",
            strength=0.85,
            explanation="طبق ماده ۲۱۹"
        )
        assert rel.cause == "عدم پرداخت"
        assert rel.effect == "فسخ قرارداد"
        assert rel.strength == 0.85


class TestReasoningResult:
    """Tests for ReasoningResult dataclass"""
    
    def test_reasoning_result_minimal(self):
        from mahoun.core.models import ReasoningResult, ReasoningStep, CausalRelation
        result = ReasoningResult(
            question="آیا قرارداد معتبر است؟",
            context="قرارداد فروش ملک",
            facts=["امضا شده", "ثبت شده"],
            reasoning_chain=[],
            causal_chain=[],
            primary_cause=None,
            final_answer="بله",
            confidence=0.8,
            supporting_evidence=["سند رسمی"],
            evidence_strength="strong"
        )
        assert result.question == "آیا قرارداد معتبر است؟"
        assert result.final_answer == "بله"
        assert result.confidence == 0.8
    
    def test_reasoning_result_to_trace_json(self):
        from mahoun.core.models import ReasoningResult, CausalRelation
        
        causal = CausalRelation(
            cause="دلیل",
            effect="نتیجه",
            strength=0.9,
            explanation="توضیح"
        )
        
        result = ReasoningResult(
            question="سوال",
            context="متن",
            facts=["واقعیت"],
            reasoning_chain=[],
            causal_chain=[causal],
            primary_cause=causal,
            final_answer="پاسخ",
            confidence=0.9,
            supporting_evidence=["مدرک"],
            evidence_strength="strong",
            visited_nodes=["node1", "node2"],
            graph_edges_used=[("a", "b")],
            used_rule_ids=["rule1"],
            limitations="محدودیت",
            graph_dependency_proof=True
        )
        
        trace = result.to_trace_json()
        assert trace["final_answer"] == "پاسخ"
        assert trace["confidence"] == 0.9
        assert trace["visited_nodes"] == ["node1", "node2"]
        assert trace["graph_dependency_proof"] is True
        assert len(trace["causal_chain"]) == 1


class TestUncertaintyEstimate:
    """Tests for UncertaintyEstimate dataclass"""
    
    def test_uncertainty_estimate_defaults(self):
        from mahoun.core.models import UncertaintyEstimate
        est = UncertaintyEstimate()
        assert est.epistemic == 0.0
        assert est.aleatoric == 0.0
        assert est.total == 0.0
        assert est.confidence == 1.0
        assert est.method == "ensemble"
    
    def test_uncertainty_estimate_auto_total(self):
        from mahoun.core.models import UncertaintyEstimate
        est = UncertaintyEstimate(epistemic=0.3, aleatoric=0.2)
        assert est.total == 0.5  # auto-calculated in __post_init__
    
    def test_uncertainty_estimate_manual_total(self):
        from mahoun.core.models import UncertaintyEstimate
        est = UncertaintyEstimate(epistemic=0.3, aleatoric=0.2, total=0.6)
        assert est.total == 0.6  # manual override


# =============================================================================
# ERROR HANDLING TESTS - mahoun.core.error_handling
# =============================================================================

class TestErrorContext:
    """Tests for ErrorContext dataclass"""
    
    def test_error_context_minimal(self):
        from mahoun.core.error_handling import ErrorContext
        ctx = ErrorContext(
            operation="test_op",
            module="test_module",
            error_type="ValueError",
            error_message="test error"
        )
        assert ctx.operation == "test_op"
        assert ctx.module == "test_module"
        assert ctx.timestamp is not None  # auto-set in __post_init__
    
    def test_error_context_full(self):
        from mahoun.core.error_handling import ErrorContext
        from datetime import datetime
        
        now = datetime.now()
        ctx = ErrorContext(
            operation="process",
            module="processor",
            error_type="IOError",
            error_message="file not found",
            traceback="Traceback...",
            metadata={"file": "test.txt"},
            timestamp=now
        )
        assert ctx.traceback == "Traceback..."
        assert ctx.metadata["file"] == "test.txt"
        assert ctx.timestamp == now


class TestErrorHandler:
    """Tests for ErrorHandler class"""
    
    def test_handle_error_basic(self):
        from mahoun.core.error_handling import ErrorHandler
        
        try:
            raise ValueError("test error")
        except ValueError as e:
            ctx = ErrorHandler.handle_error(
                error=e,
                operation="test_operation",
                module="test_module"
            )
        
        assert ctx.error_type == "ValueError"
        assert ctx.error_message == "test error"
        assert ctx.operation == "test_operation"
    
    def test_handle_error_with_metadata(self):
        from mahoun.core.error_handling import ErrorHandler
        
        try:
            raise RuntimeError("runtime error")
        except RuntimeError as e:
            ctx = ErrorHandler.handle_error(
                error=e,
                operation="process_file",
                module="file_processor",
                metadata={"filename": "test.txt", "line": 42}
            )
        
        assert ctx.metadata["filename"] == "test.txt"
        assert ctx.metadata["line"] == 42
    
    def test_handle_error_reraise(self):
        from mahoun.core.error_handling import ErrorHandler
        
        with pytest.raises(TypeError):
            try:
                raise TypeError("type mismatch")
            except TypeError as e:
                ErrorHandler.handle_error(
                    error=e,
                    operation="convert",
                    module="converter",
                    reraise=True
                )
    
    def test_handle_specific_error_expected(self):
        from mahoun.core.error_handling import ErrorHandler
        
        expected_errors = {
            FileNotFoundError: "فایل یافت نشد",
            PermissionError: "دسترسی مجاز نیست"
        }
        
        try:
            raise FileNotFoundError("missing.txt")
        except FileNotFoundError as e:
            ctx = ErrorHandler.handle_specific_error(
                error=e,
                operation="read_file",
                module="reader",
                expected_errors=expected_errors
            )
        
        assert ctx.error_message == "فایل یافت نشد"
    
    def test_handle_specific_error_unexpected(self):
        from mahoun.core.error_handling import ErrorHandler
        
        expected_errors = {
            FileNotFoundError: "فایل یافت نشد"
        }
        
        # RuntimeError is not in expected_errors, should reraise
        with pytest.raises(RuntimeError):
            try:
                raise RuntimeError("unexpected")
            except RuntimeError as e:
                ErrorHandler.handle_specific_error(
                    error=e,
                    operation="process",
                    module="processor",
                    expected_errors=expected_errors
                )


class TestHandleErrorFunction:
    """Tests for handle_error convenience function"""
    
    def test_handle_error_function(self):
        from mahoun.core.error_handling import handle_error
        
        try:
            raise ValueError("convenience test")
        except ValueError as e:
            ctx = handle_error(e, "test_op", "test_mod")
        
        assert ctx.error_type == "ValueError"
        assert ctx.operation == "test_op"


# =============================================================================
# ADDITIONAL SCHEMA TESTS
# =============================================================================

class TestOrganizationEntityInfo:
    """Tests for OrganizationEntityInfo"""
    
    def test_organization_entity(self):
        from mahoun.schemas.legal_struct_schema import OrganizationEntityInfo
        org = OrganizationEntityInfo(
            text="بانک ملی ایران",
            name="بانک ملی",
            org_type="بانک",
            registration_id="12345",
            confidence=0.92
        )
        assert org.name == "بانک ملی"
        assert org.org_type == "بانک"


class TestCourtEntityInfo:
    """Tests for CourtEntityInfo"""
    
    def test_court_entity(self):
        from mahoun.schemas.legal_struct_schema import CourtEntityInfo
        court = CourtEntityInfo(
            text="شعبه ۱۵ دادگاه تجدیدنظر استان تهران",
            name="دادگاه تجدیدنظر",
            level="تجدیدنظر",
            branch="15",
            city="تهران",
            province="تهران"
        )
        assert court.level == "تجدیدنظر"
        assert court.branch == "15"


class TestLawEntityInfo:
    """Tests for LawEntityInfo"""
    
    def test_law_entity(self):
        from mahoun.schemas.legal_struct_schema import LawEntityInfo
        law = LawEntityInfo(
            text="ماده ۱۸۳ قانون مدنی",
            article_number="183",
            law_name="قانون مدنی",
            normalized_ref="civil_law_183"
        )
        assert law.article_number == "183"
        assert law.law_name == "قانون مدنی"


class TestTopicEntityInfo:
    """Tests for TopicEntityInfo"""
    
    def test_topic_entity(self):
        from mahoun.schemas.legal_struct_schema import TopicEntityInfo
        topic = TopicEntityInfo(
            text="عقد بیع",
            category="عقود",
            parent_topic="ملکی"
        )
        assert topic.category == "عقود"


class TestFinalDecision:
    """Tests for FinalDecision"""
    
    def test_final_decision(self):
        from mahoun.schemas.legal_struct_schema import FinalDecision
        decision = FinalDecision(
            appeal_result="تایید",
            third_party_objection="رد",
            is_final=True
        )
        assert decision.appeal_result == "تایید"
        assert decision.is_final is True


class TestParsingQuality:
    """Tests for ParsingQuality"""
    
    def test_parsing_quality(self):
        from mahoun.schemas.legal_struct_schema import ParsingQuality
        quality = ParsingQuality(
            confidence_score=0.85,
            metrics={"completeness": 0.9, "accuracy": 0.8}
        )
        assert quality.confidence_score == 0.85
        assert quality.metrics["completeness"] == 0.9


class TestSourceInfo:
    """Tests for SourceInfo"""
    
    def test_source_info(self):
        from mahoun.schemas.legal_struct_schema import SourceInfo
        source = SourceInfo(
            filename="verdict_001.txt",
            filepath="/data/verdicts/verdict_001.txt",
            file_size_bytes=1024
        )
        assert source.filename == "verdict_001.txt"
        assert source.file_size_bytes == 1024


# =============================================================================
# EDGE CASE TESTS
# =============================================================================

class TestEdgeCases:
    """Edge case tests for robustness"""
    
    def test_empty_strings(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo(name="", title="")
        assert party.name == ""
        assert party.title == ""
    
    def test_unicode_persian_text(self):
        from mahoun.schemas.legal_struct_schema import PartyInfo
        party = PartyInfo(
            name="محمدرضا احمدی‌نژاد",  # Contains Persian special chars
            title="آقای"
        )
        assert "احمدی" in party.name
    
    def test_large_list(self):
        from mahoun.schemas.legal_struct_schema import Claims
        claims = Claims(main=["خواسته " + str(i) for i in range(100)])
        assert len(claims.main) == 100
    
    def test_nested_structure(self):
        from mahoun.schemas.legal_struct_schema import (
            VerdictStruct, ExtractedEntities, PersonEntityInfo
        )
        persons = [PersonEntityInfo(text=f"شخص {i}") for i in range(10)]
        verdict = VerdictStruct(
            entities=ExtractedEntities(persons=persons)
        )
        assert len(verdict.entities.persons) == 10





