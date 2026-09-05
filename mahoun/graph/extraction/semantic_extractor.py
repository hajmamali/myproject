"""
MAHOUN Semantic Extractor (Phase 2B)
===================================
Classification: CANONICAL SEMANTIC EXTRACTION ENGINE
Purpose: Deterministic, proof-carrying decomposition of legal text into
         logical conditions, sanctions, exceptions, and ontological concepts.
"""

from __future__ import annotations

import hashlib
import re
from typing import Dict, List, Optional, Set, Tuple

from mahoun.core.models.semantic import (
    ArticleDecomposition,
    ConditionClause,
    ExceptionClause,
    SanctionClause,
    SemanticAssertion,
    SemanticFact,
    VerificationStatus,
)
from mahoun.graph.ontology.legal_concepts import (
    CANONICAL_LEGAL_CONCEPTS,
    SemanticIdentity,
)


class SemanticExtractor:
    """
    Extracts structured semantic components from legal articles.
    All extracted facts and assertions are bound to exact character spans
    and verified against cryptographic hashes.
    """

    # Condition Trigger Keywords
    CONDITION_TRIGGERS = [
        "در صورتی که",
        "در صورتیکه",
        "مشروط بر اینکه",
        "مشروط به اینکه",
        "مشروط بر آنکه",
        "به شرط آنکه",
        "به شرط اینکه",
        "چنانچه",
        "هرگاه",
        "هر گاه",
        "اگر",
    ]

    # Exception Trigger Keywords
    EXCEPTION_TRIGGERS = [
        "مگر اینکه",
        "مگر آنکه",
        "به استثنای",
        "به استثناء",
        "مستثنی است",
        "الا در مواردی که",
        "مگر در مواردی که",
        "مگر در صورتی که",
        "مگر با رضایت",
        "مگر به حکم قانون",
        "مگر اینکه در قانون",
    ]

    # Sanction / Consequence Patterns (Category, Trigger Phrases)
    SANCTION_PATTERNS: Dict[str, List[str]] = {
        "VALIDITY": [
            "نافذ است",
            "معتبر است",
            "صحیح است",
            "رعایت آن الزامی است",
            "الزامی است",
            "اعتبار دارد",
            "لازم‌الاتباع است",
            "لازم الاتباع است",
        ],
        "NULLITY": [
            "باطل است",
            "باطل خواهد بود",
            "بی‌اثر است",
            "بی اثر است",
            "کان‌لم‌یکن است",
            "کان لم یکن است",
            "فاقد اعتبار است",
            "باطل و بلااثر است",
            "بی‌اعتبار است",
            "بی اعتبار است",
        ],
        "OBLIGATION": [
            "مکلف است",
            "مکلفند",
            "موظف است",
            "موظفند",
            "باید",
            "ملزم است",
            "الزام دارد",
            "تعهد دارد",
            "مکلف خواهد بود",
            "موظف خواهد بود",
        ],
        "LIABILITY": [
            "مسئول است",
            "مسئول خواهد بود",
            "مسئول جبران خسارت",
            "ضامن است",
            "مسئولیت مدنی دارد",
            "مسئولیت دارد",
            "ضامن خواهد بود",
        ],
        "PENALTY": [
            "محکوم می‌شود",
            "محکوم خواهد شد",
            "مجازات خواهد شد",
            "مشمول مجازات",
            "جریمه می‌شود",
            "به مجازات محکوم",
        ],
        "RIGHT_POWER": [
            "حق دارد",
            "می‌تواند",
            "مجاز است",
            "اختیار دارد",
            "حق خواهد داشت",
            "مجاز خواهد بود",
        ],
        "PROHIBITION": [
            "ممنوع است",
            "حق ندارد",
            "نمی‌تواند",
            "مجاز نیست",
            "نباید",
            "ممنوع خواهد بود",
        ],
    }

    def __init__(self, ontology: Optional[Dict[str, SemanticIdentity]] = None) -> None:
        self.ontology = ontology or CANONICAL_LEGAL_CONCEPTS

    @staticmethod
    def _compute_sha256(text: str) -> str:
        """Compute 16-char hex prefix of text's UTF-8 SHA-256."""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

    def decompose_article(
        self,
        article_id: str,
        law_id: str,
        raw_text: str,
    ) -> ArticleDecomposition:
        """
        Decomposes an article into Conditions, Sanctions, and Exceptions.
        Computes exact span offsets on raw_text to preserve proof validity.
        """
        if not raw_text:
            return ArticleDecomposition(
                article_id=article_id,
                law_id=law_id,
                raw_text="",
                normalized_text="",
                text_hash="",
            )

        text_hash = self._compute_sha256(raw_text)
        conditions = self._extract_conditions(article_id, raw_text)
        sanctions = self._extract_sanctions(article_id, raw_text)
        exceptions = self._extract_exceptions(article_id, raw_text)

        return ArticleDecomposition(
            article_id=article_id,
            law_id=law_id,
            raw_text=raw_text,
            normalized_text=raw_text.strip(),
            text_hash=text_hash,
            conditions=conditions,
            sanctions=sanctions,
            exceptions=exceptions,
            is_conditional=len(conditions) > 0,
            has_exceptions=len(exceptions) > 0,
        )

    def _extract_conditions(
        self, article_id: str, text: str
    ) -> List[ConditionClause]:
        """Extract conditions with exact character offsets."""
        conditions: List[ConditionClause] = []
        c_idx = 1

        for trigger in self.CONDITION_TRIGGERS:
            pattern = re.escape(trigger)
            for match in re.finditer(pattern, text):
                start = match.start()
                # Find end of clause (comma, period, semicolon, newline, or next trigger)
                end = self._find_clause_end(text, start)
                clause_text = text[start:end].strip()

                if len(clause_text) > len(trigger):
                    cond = ConditionClause(
                        id=f"{article_id}:cond_{c_idx}",
                        article_id=article_id,
                        condition_text=clause_text,
                        span_start=start,
                        span_end=start + len(clause_text),
                        trigger_keyword=trigger,
                    )
                    conditions.append(cond)
                    c_idx += 1

        return conditions

    def _extract_exceptions(
        self, article_id: str, text: str
    ) -> List[ExceptionClause]:
        """Extract exception clauses with exact character offsets."""
        exceptions: List[ExceptionClause] = []
        e_idx = 1

        for trigger in self.EXCEPTION_TRIGGERS:
            pattern = re.escape(trigger)
            for match in re.finditer(pattern, text):
                start = match.start()
                end = self._find_clause_end(text, start)
                clause_text = text[start:end].strip()

                if len(clause_text) > len(trigger):
                    exc = ExceptionClause(
                        id=f"{article_id}:exc_{e_idx}",
                        article_id=article_id,
                        exception_text=clause_text,
                        span_start=start,
                        span_end=start + len(clause_text),
                        trigger_keyword=trigger,
                    )
                    exceptions.append(exc)
                    e_idx += 1

        return exceptions

    def _extract_sanctions(
        self, article_id: str, text: str
    ) -> List[SanctionClause]:
        """Extract sanction / legal consequence clauses with exact character offsets."""
        sanctions: List[SanctionClause] = []
        s_idx = 1

        for sanction_type, triggers in self.SANCTION_PATTERNS.items():
            for trigger in triggers:
                pattern = re.escape(trigger)
                for match in re.finditer(pattern, text):
                    # Sanction keyword usually appears at the end or middle of a consequence phrase
                    # Look backwards to find clause start
                    m_start = match.start()
                    m_end = match.end()
                    c_start = self._find_clause_start(text, m_start)
                    c_end = self._find_clause_end(text, m_end)
                    clause_text = text[c_start:c_end].strip()

                    if clause_text:
                        # Ensure span matches exactly the slice
                        actual_start = text.find(clause_text, c_start)
                        actual_end = actual_start + len(clause_text)

                        sanc = SanctionClause(
                            id=f"{article_id}:sanc_{s_idx}",
                            article_id=article_id,
                            sanction_text=clause_text,
                            span_start=actual_start,
                            span_end=actual_end,
                            sanction_type=sanction_type,
                        )
                        sanctions.append(sanc)
                        s_idx += 1

        return sanctions

    def _find_clause_end(self, text: str, start: int) -> int:
        """Find the ending offset of a clause starting at `start`."""
        # Stop at sentence boundary or major clause delimiters
        delimiters = ["؛", ".\n", "\n", " - ", " – "]
        min_pos = len(text)
        for d in delimiters:
            pos = text.find(d, start)
            if pos != -1 and pos < min_pos:
                min_pos = pos

        # Also stop at period if followed by space or end
        p_match = re.search(r"\.(?:\s|$)", text[start:])
        if p_match:
            p_pos = start + p_match.start()
            if p_pos < min_pos:
                min_pos = p_pos

        return min_pos

    def _find_clause_start(self, text: str, target_pos: int) -> int:
        """Find the start of the clause containing `target_pos`."""
        delimiters = ["،", "؛", ".\n", "\n", " - "]
        max_pos = 0
        for d in delimiters:
            pos = text.rfind(d, 0, target_pos)
            if pos != -1 and (pos + len(d)) > max_pos:
                max_pos = pos + len(d)
        return max_pos

    def extract_concept_assertions(
        self,
        article_id: str,
        raw_text: str,
    ) -> List[SemanticAssertion]:
        """
        Matches article text against Canonical Legal Concepts taxonomy.
        Generates proof-carrying SemanticAssertions linking Article -> Concept.
        """
        if not raw_text:
            return []

        text_hash = self._compute_sha256(raw_text)
        assertions: List[SemanticAssertion] = []
        seen_concepts: Set[str] = set()

        for concept_id, concept in self.ontology.items():
            if concept_id in seen_concepts:
                continue

            # Search canonical label and all aliases
            candidates = [concept.canonical_label_fa] + concept.aliases_fa

            for candidate in candidates:
                if not candidate:
                    continue

                pos = raw_text.find(candidate)
                if pos != -1:
                    span_start = pos
                    span_end = pos + len(candidate)
                    evidence_span = raw_text[span_start:span_end]

                    assertion = SemanticAssertion(
                        assertion_id=f"assert:{article_id}:{concept_id}",
                        assertion_type="REGULATES",
                        source_entity_id=article_id,
                        target_entity_id=concept_id,
                        evidence_text_span=evidence_span,
                        evidence_offset_start=span_start,
                        evidence_offset_end=span_end,
                        evidence_sha256=text_hash,
                        status=VerificationStatus.VERIFIED,
                        verification_method="taxonomic_string_match",
                    )
                    assertions.append(assertion)
                    seen_concepts.add(concept_id)
                    break

        return assertions

    def extract_proof_carrying_facts(
        self,
        article_id: str,
        raw_text: str,
    ) -> List[SemanticFact]:
        """
        Converts all structural extractions (conditions, sanctions, exceptions, concepts)
        into verifiable SemanticFact objects with SHA-256 and byte span assertions.
        """
        if not raw_text:
            return []

        text_hash = self._compute_sha256(raw_text)
        facts: List[SemanticFact] = []

        decomposition = self.decompose_article(article_id, "", raw_text)

        # 1. Condition Facts
        for cond in decomposition.conditions:
            fact = SemanticFact(
                fact_id=f"fact:{cond.id}",
                fact_type="sub_clause",
                node_label="Condition",
                edge_type="HAS_CONDITION",
                source_article_id=article_id,
                source_text_span=cond.condition_text,
                source_offset_start=cond.span_start,
                source_offset_end=cond.span_end,
                source_sha256=text_hash,
                status=VerificationStatus.VERIFIED,
                verification_method="condition_extractor",
            )
            if fact.verify(raw_text):
                facts.append(fact)

        # 2. Sanction Facts
        for sanc in decomposition.sanctions:
            fact = SemanticFact(
                fact_id=f"fact:{sanc.id}",
                fact_type="sub_clause",
                node_label="Sanction",
                edge_type="HAS_SANCTION",
                source_article_id=article_id,
                source_text_span=sanc.sanction_text,
                source_offset_start=sanc.span_start,
                source_offset_end=sanc.span_end,
                source_sha256=text_hash,
                status=VerificationStatus.VERIFIED,
                verification_method="sanction_extractor",
            )
            if fact.verify(raw_text):
                facts.append(fact)

        # 3. Exception Facts
        for exc in decomposition.exceptions:
            fact = SemanticFact(
                fact_id=f"fact:{exc.id}",
                fact_type="sub_clause",
                node_label="Exception",
                edge_type="HAS_EXCEPTION",
                source_article_id=article_id,
                source_text_span=exc.exception_text,
                source_offset_start=exc.span_start,
                source_offset_end=exc.span_end,
                source_sha256=text_hash,
                status=VerificationStatus.VERIFIED,
                verification_method="exception_extractor",
            )
            if fact.verify(raw_text):
                facts.append(fact)

        # 4. Concept Assertion Facts
        assertions = self.extract_concept_assertions(article_id, raw_text)
        for a_idx, assert_obj in enumerate(assertions, start=1):
            fact = SemanticFact(
                fact_id=f"fact:{article_id}:concept_{a_idx}",
                fact_type="property",
                node_label="Concept",
                edge_type=assert_obj.assertion_type,
                source_article_id=article_id,
                source_text_span=assert_obj.evidence_text_span,
                source_offset_start=assert_obj.evidence_offset_start,
                source_offset_end=assert_obj.evidence_offset_end,
                source_sha256=text_hash,
                status=VerificationStatus.VERIFIED,
                verification_method="taxonomic_concept_match",
            )
            if fact.verify(raw_text):
                facts.append(fact)

        return facts
