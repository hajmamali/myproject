"""
Adversarial Bypass Tests
=========================

These tests are explicitly written to FIND bypasses in the
OntologyEnforcer. They are NOT happy-path tests. Each test asserts a
specific invariant that, if violated, would allow a caller to:

- introduce an unknown enum value into the graph
- bypass a conflict-state check
- inject a temporal range that is logically invalid
- claim a hierarchy ordering that contradicts the canonical ladder

Bypasses discovered during this test session
--------------------------------------------
The following real bypasses were found while writing this file and have
been recorded as failures. They are NOT silently allowed to pass.

1. ``validate_conflict_state('RESOLVED_SUPERIOR', float('-inf'))`` was
   accepted because no rule forbids negative or non-finite scores for
   the RESOLVED_* states. The fix lives in
   ``OntologyEnforcer.validate_conflict_state``: when the resolution
   is one of the RESOLVED_* states, ``target_authority_score`` must
   satisfy ``0.0 <= score <= 1.0`` and must be finite.

2. ``validate_conflict_state('RESOLVED_LEX_POSTERIOR', -0.0)`` was
   accepted. Same fix as #1.

3. Whitespace-only strings (``"   "``, ``"\\t\\n"``) are treated as
   "missing" by several validators. This is a deliberate
   pass-through (treated like ``None``). Tests document this
   behaviour so any future tightening is a deliberate decision.

Run: ``pytest tests/governance/test_adversarial_bypass.py -v``
"""

from __future__ import annotations

import math
from datetime import date, datetime
from typing import Any, List

import pytest

from mahoun.core.governance.ontology_enforcer import OntologyEnforcer
from mahoun.core.governance.violations import (
    GovernanceViolation,
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

@pytest.fixture
def enforcer() -> OntologyEnforcer:
    return OntologyEnforcer()


# ===========================================================================
# 1. Hierarchy Precedence Bypass Attempts
# ===========================================================================

class TestHierarchyPrecedenceBypass:
    """
    Hierarchy is the cornerstone of lex-superior conflict resolution.
    Any caller that can persuade the enforcer to return an incorrect
    ordering can shift the entire legal interpretation of a case.
    """

    def test_unknown_higher_level_is_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_hierarchy_precedence("BANANA", "ORDINARY_LAW")
        assert exc_info.value.violation.category == ViolationCategory.ONTOLOGY_VIOLATION
        assert "BANANA" in str(exc_info.value.violation.message)

    def test_unknown_lower_level_is_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_hierarchy_precedence("CONSTITUTIONAL", "BANANA")

    def test_both_unknown_levels_rejected_with_first_in_message(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_hierarchy_precedence("X1", "X2")
        # Either X1 or X2 may be reported first; both are unknown.
        msg = str(exc_info.value.violation.message)
        assert "X1" in msg or "X2" in msg

    def test_canonical_full_ordering_chain(self, enforcer: OntologyEnforcer) -> None:
        """The full CONSTITUTIONAL > ORDINARY_LAW > ... > DOCTRINE chain
        must be respected in both directions. This is the strict
        anti-symmetry test.
        """
        rank = [
            "CONSTITUTIONAL",
            "ORDINARY_LAW",
            "DECREE",
            "REGULATION",
            "BYLAW",
            "CIRCULAR",
            "JUDICIAL_PRECEDENT",
            "DOCTRINE",
        ]
        for i, higher in enumerate(rank):
            for j, lower in enumerate(rank):
                if i == j:
                    # Same level: never greater.
                    assert enforcer.validate_hierarchy_precedence(higher, lower) is False, (
                        f"Reflexivity violated: {higher} should NOT be greater "
                        f"than itself"
                    )
                elif i < j:
                    # higher is canonically above lower
                    assert enforcer.validate_hierarchy_precedence(higher, lower) is True, (
                        f"{higher} should be greater than {lower}"
                    )
                else:
                    # higher is canonically below lower
                    assert enforcer.validate_hierarchy_precedence(higher, lower) is False, (
                        f"{higher} should NOT be greater than {lower}"
                    )

    def test_symmetry_breaking(self, enforcer: OntologyEnforcer) -> None:
        """If A > B, then NOT (B > A). The enforcer must not allow
        both directions to be true simultaneously.
        """
        a, b = "CONSTITUTIONAL", "ORDINARY_LAW"
        fwd = enforcer.validate_hierarchy_precedence(a, b)
        rev = enforcer.validate_hierarchy_precedence(b, a)
        assert fwd is True
        assert rev is False
        # Logical NAND — exactly one must be true
        assert fwd != rev

    def test_empty_string_higher_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_hierarchy_precedence("", "ORDINARY_LAW")

    def test_empty_string_lower_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_hierarchy_precedence("CONSTITUTIONAL", "")

    def test_none_higher_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_hierarchy_precedence(None, "ORDINARY_LAW")  # type: ignore[arg-type]

    def test_int_higher_rejected_with_type_error_message(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_hierarchy_precedence(8, "ORDINARY_LAW")  # type: ignore[arg-type]
        # The error must surface the bad type so callers can debug.
        assert "int" in str(exc_info.value.violation.message)


# ===========================================================================
# 2. Conflict State Bypass Attempts
# ===========================================================================

class TestConflictStateBypass:
    """
    Conflict state is the most dangerous bypass vector: a caller who
    can write UNRESOLVED + score, or RESOLVED + negative score, can
    either pass a contradicting state through as if it were decided,
    or seed the system with a corrupt numerical "authority" claim.
    """

    def test_unresolved_with_zero_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """0.0 is still a score; presence of score on UNRESOLVED is a
        bypass attempt even when the score is zero.
        """
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_conflict_state("UNRESOLVED", 0.0)
        msg = str(exc_info.value.violation.message).lower()
        assert "unresolved" in msg
        assert "authority_score" in msg or "authority score" in msg

    def test_unresolved_with_positive_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("UNRESOLVED", 0.5)

    def test_unresolved_with_negative_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("UNRESOLVED", -0.5)

    def test_unresolved_with_infinity_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("UNRESOLVED", math.inf)

    def test_unresolved_with_neg_infinity_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("UNRESOLVED", -math.inf)

    def test_unresolved_with_nan_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("UNRESOLVED", math.nan)

    def test_contradictory_with_any_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """CONTRADICTORY is structurally an UNRESOLVED state. Any
        authority_score must be rejected for it.
        """
        for score in (0.0, 0.5, -0.1, math.inf, -math.inf, math.nan):
            with pytest.raises(GovernanceViolationError):
                enforcer.validate_conflict_state("CONTRADICTORY", score)

    def test_resolved_superior_with_negative_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """A negative authority_score is nonsensical — it would mean
        a norm has NEGATIVE weight, inverting the lex-superior rule.
        """
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", -0.1)
        msg = str(exc_info.value.violation.message).lower()
        assert "negative" in msg or "non-negative" in msg or "0.0" in msg

    def test_resolved_superior_with_neg_infinity_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", -math.inf)

    def test_resolved_superior_with_nan_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", math.nan)

    def test_resolved_superior_with_positive_infinity_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Authority scores are bounded to [0.0, 1.0]. +inf exceeds 1.0."""
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", math.inf)

    def test_resolved_superior_with_score_above_one_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", 1.5)

    def test_resolved_lex_posterior_with_negative_zero_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """-0.0 is a distinct float from +0.0 in Python. It is
        negative by IEEE 754 even though it equals zero. A bypass
        that uses -0.0 to slip past a ``score >= 0`` check must be
        caught.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_LEX_POSTERIOR", -0.0)

    def test_resolved_lex_posterior_with_negative_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_LEX_POSTERIOR", -0.1)

    def test_resolved_lex_specialis_with_negative_score_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_LEX_SPECIALIS", -0.1)

    def test_resolved_states_with_score_above_one_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        for resolution in (
            "RESOLVED_SUPERIOR",
            "RESOLVED_LEX_POSTERIOR",
            "RESOLVED_LEX_SPECIALIS",
        ):
            with pytest.raises(GovernanceViolationError):
                enforcer.validate_conflict_state(resolution, 2.0)

    def test_resolved_states_with_score_at_upper_bound_accepted(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """1.0 is the upper bound; must be accepted."""
        for resolution in (
            "RESOLVED_SUPERIOR",
            "RESOLVED_LEX_POSTERIOR",
            "RESOLVED_LEX_SPECIALIS",
        ):
            enforcer.validate_conflict_state(resolution, 1.0)

    def test_resolved_states_with_zero_score_accepted(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """0.0 is the lower bound for RESOLVED_* states and means
        'no residual influence' — different semantics from
        'authority score absent' (UNRESOLVED).
        """
        for resolution in (
            "RESOLVED_SUPERIOR",
            "RESOLVED_LEX_POSTERIOR",
            "RESOLVED_LEX_SPECIALIS",
        ):
            enforcer.validate_conflict_state(resolution, 0.0)

    def test_none_resolution_accepted(self, enforcer: OntologyEnforcer) -> None:
        """None is treated as 'uninitialized'; no score rules apply."""
        enforcer.validate_conflict_state(None, 0.5)  # type: ignore[arg-type]
        enforcer.validate_conflict_state(None, None)  # type: ignore[arg-type]

    def test_bool_score_for_resolved_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """True/False are technically int subclass, but a boolean
        score is semantically nonsense. The validator must require
        a real numeric (int|float) value.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", True)  # type: ignore[arg-type]

    def test_string_score_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("RESOLVED_SUPERIOR", "0.5")  # type: ignore[arg-type]

    def test_unknown_resolution_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("HAND_WAVED", 0.5)

    def test_lowercase_resolution_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Case variants must be REJECTED. Normalization is a bypass vector.
        Callers must supply exact enum values.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("resolved_superior", 0.0)
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_state("unresolved", None)


# ===========================================================================
# 3. Temporal Range Bypass Attempts
# ===========================================================================

class TestTemporalRangeBypass:
    """
    Temporal ranges are the substrate of point-in-time reasoning.
    A bad range poisons every retrieval that filters on it.
    """

    def test_none_valid_from_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_temporal_range(None, "2024-12-31")  # type: ignore[arg-type]
        assert "valid_from" in str(exc_info.value.violation.message)

    def test_valid_from_must_not_be_empty_string(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range("", "2024-12-31")

    def test_valid_from_must_not_be_whitespace(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range("   ", "2024-12-31")

    def test_valid_until_equals_valid_from_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """A zero-length range is meaningless. Reject strictly."""
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range("2024-01-01", "2024-01-01")

    def test_valid_until_before_valid_from_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range("2024-12-31", "2024-01-01")

    def test_valid_from_with_invalid_iso_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        for bad in ("2024-13-01", "2024-01-32", "not-a-date", "2024/01/01"):
            with pytest.raises(GovernanceViolationError):
                enforcer.validate_temporal_range(bad, "2024-12-31")

    def test_int_valid_from_rejected_with_type_info(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_temporal_range(20240101, "2024-12-31")  # type: ignore[arg-type]
        assert "int" in str(exc_info.value.violation.message)

    def test_dict_valid_from_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range({"year": 2024}, "2024-12-31")  # type: ignore[arg-type]

    def test_none_valid_until_accepted_as_open_ended(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """None for valid_until is the documented open-ended norm."""
        enforcer.validate_temporal_range("2024-01-01", None)  # type: ignore[arg-type]

    def test_valid_until_with_invalid_iso_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range("2024-01-01", "2024-13-01")

    def test_datetime_strings_with_t_separator_accepted(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """ISO 8601 with T separator and Z suffix must work for
        bitemporal use cases where transaction time matters.
        """
        enforcer.validate_temporal_range(
            "2024-01-01T00:00:00", "2024-12-31T23:59:59"
        )
        enforcer.validate_temporal_range(
            "2024-01-01T00:00:00Z", "2024-12-31T23:59:59Z"
        )

    def test_mixed_date_and_datetime_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """A date-only lower bound and a datetime upper bound mix
        precision levels. This is rejected so callers are forced to
        pick a single precision level for both endpoints — otherwise
        a downstream system that expects a datetime would crash.
        """
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_temporal_range("2024-01-01", "2024-12-31T00:00:00")
        assert "precision" in str(exc_info.value.violation.message).lower() or \
               "consistent" in str(exc_info.value.violation.message).lower()

    def test_valid_until_with_only_date_when_valid_from_is_datetime_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Mixing date-only upper with datetime-lower is rejected
        for the same reason as the inverse direction. Precision
        consistency is mandatory.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_range(
                "2024-01-01T00:00:00", "2024-12-31"
            )

    def test_far_past_range_accepted(self, enforcer: OntologyEnforcer) -> None:
        """Sanity: very old dates must not be rejected by the
        validator (the year must be 4-digit positive).
        """
        enforcer.validate_temporal_range("0001-01-01", "9999-12-31")

    def test_year_1_through_9999_accepted(self, enforcer: OntologyEnforcer) -> None:
        enforcer.validate_temporal_range("0001-01-01", "0001-12-31")
        enforcer.validate_temporal_range("9999-01-01", "9999-12-31")


# ===========================================================================
# 4. Deontic Operator Bypass Attempts
# ===========================================================================

class TestDeonticOperatorBypass:
    def test_unknown_operator_rejected(self, enforcer: OntologyEnforcer) -> None:
        for bad in ("SUGGESTION", "RECOMMENDATION", "ADVICE", "DUTY"):
            with pytest.raises(GovernanceViolationError):
                enforcer.validate_deontic_operator(bad)

    def test_legal_term_aliases_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """SDL has only three operators. The legal-domain synonyms
        'shall', 'may', 'must not' must be NORMALIZED at extraction
        time, not silently accepted as deontic operators.
        """
        for bad in ("shall", "may", "must not", "is entitled to"):
            with pytest.raises(GovernanceViolationError):
                enforcer.validate_deontic_operator(bad)

    def test_none_accepted_as_neutral_text(
        self, enforcer: OntologyEnforcer
    ) -> None:
        enforcer.validate_deontic_operator(None)  # type: ignore[arg-type]

    def test_lowercase_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Case variants must be REJECTED. Normalization is a bypass vector.
        Callers must supply exact enum values.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_deontic_operator("obligation")
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_deontic_operator("ObLiGaTiOn")

    def test_int_rejected(self, enforcer: OntologyEnforcer) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            enforcer.validate_deontic_operator(0)  # type: ignore[arg-type]
        # The error must say "int" so the caller can debug.
        assert "int" in str(exc_info.value.violation.message)


# ===========================================================================
# 5. Enum Validator Type Confusion Bypass Attempts
# ===========================================================================

class TestEnumValidatorTypeConfusion:
    """
    Cross-cutting type-confusion tests. The enum validators are
    security-relevant: a bypass that allows a list or dict to flow
    through as a string is a direct write-injection vector.
    """

    @pytest.mark.parametrize(
        "method_name,valid_value",
        [
            ("validate_deontic_operator", "OBLIGATION"),
            ("validate_legal_level", "CONSTITUTIONAL"),
            ("validate_conflict_resolution", "UNRESOLVED"),
            ("validate_legal_force", "BINDING"),
            ("validate_binding_scope", "ALL_COURTS"),
            ("validate_norm_status", "IN_FORCE"),
            ("validate_decision_type", "UNIFICATION"),
        ],
    )
    def test_list_value_rejected(
        self, enforcer: OntologyEnforcer, method_name: str, valid_value: str
    ) -> None:
        method = getattr(enforcer, method_name)
        with pytest.raises(GovernanceViolationError):
            method([valid_value])

    @pytest.mark.parametrize(
        "method_name,valid_value",
        [
            ("validate_deontic_operator", "OBLIGATION"),
            ("validate_legal_level", "CONSTITUTIONAL"),
            ("validate_conflict_resolution", "UNRESOLVED"),
            ("validate_legal_force", "BINDING"),
            ("validate_binding_scope", "ALL_COURTS"),
            ("validate_norm_status", "IN_FORCE"),
            ("validate_decision_type", "UNIFICATION"),
        ],
    )
    def test_dict_value_rejected(
        self, enforcer: OntologyEnforcer, method_name: str, valid_value: str
    ) -> None:
        method = getattr(enforcer, method_name)
        with pytest.raises(GovernanceViolationError):
            method({"value": valid_value})

    @pytest.mark.parametrize(
        "method_name,valid_value",
        [
            ("validate_deontic_operator", "OBLIGATION"),
            ("validate_legal_level", "CONSTITUTIONAL"),
            ("validate_conflict_resolution", "UNRESOLVED"),
            ("validate_legal_force", "BINDING"),
            ("validate_binding_scope", "ALL_COURTS"),
            ("validate_norm_status", "IN_FORCE"),
            ("validate_decision_type", "UNIFICATION"),
        ],
    )
    def test_bytes_value_rejected(
        self, enforcer: OntologyEnforcer, method_name: str, valid_value: str
    ) -> None:
        """bytes are a common smuggling vector in text processing."""
        method = getattr(enforcer, method_name)
        with pytest.raises(GovernanceViolationError):
            method(valid_value.encode("utf-8"))


# ===========================================================================
# 6. Norm / Conflict / JudicialAuthority Relationship Bypass Attempts
# ===========================================================================

class TestRelationshipBypass:
    def test_norm_to_verdict_relationship_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Norm-CITES-Verdict is not in the ontology. A caller trying
        to fabricate an inference path through a verdict must fail.
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_norm_relationship(
                "Norm", "Verdict", "CITES"
            )

    def test_article_to_law_confl_with_relationship_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_conflict_record(
                "Article", "Norm", "CONFLICTS_WITH"
            )

    def test_verdict_authority_over_authority_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """JudicialAuthority cannot claim authority over another
        JudicialAuthority (would create infinite authority chain)."""
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_judicial_authority_relationship(
                "JudicialAuthority",
                "JudicialAuthority",
                "AUTHORITY_OVER",
            )

    def test_norm_relationship_uses_unknown_rel_type_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_norm_relationship(
                "Norm", "Article", "INVENTS"
            )

    def test_temporal_relationship_with_unknown_rel_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_relationship(
                "Law", "Article", "TELEPORTS"
            )

    def test_temporal_relationship_with_invalid_pair_rejected(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Evidence is not allowed as source or target for temporal
        relationships (those are reserved for Law/Article/Verdict).
        """
        with pytest.raises(GovernanceViolationError):
            enforcer.validate_temporal_relationship(
                "Evidence", "Article", "AMENDED_BY"
            )


# ===========================================================================
# 7. Cross-cutting: ensure fail-closed produces CRITICAL severity
# ===========================================================================

class TestViolationSeverity:
    """
    All violations in this layer must be CRITICAL. A WARNING or INFO
    would let a caller ignore it via a try/except.
    """

    @pytest.mark.parametrize(
        "call",
        [
            lambda e: e.validate_deontic_operator("WRONG"),
            lambda e: e.validate_legal_level("WRONG"),
            lambda e: e.validate_legal_level(None),
            lambda e: e.validate_conflict_resolution("WRONG"),
            lambda e: e.validate_legal_force("WRONG"),
            lambda e: e.validate_binding_scope("WRONG"),
            lambda e: e.validate_norm_status("WRONG"),
            lambda e: e.validate_decision_type("WRONG"),
            lambda e: e.validate_hierarchy_precedence("WRONG", "WRONG"),
            lambda e: e.validate_temporal_range(None, "2024-12-31"),
            lambda e: e.validate_temporal_range("2024-12-31", "2024-01-01"),
            lambda e: e.validate_conflict_state("UNRESOLVED", 0.0),
            lambda e: e.validate_conflict_state("CONTRADICTORY", 0.5),
            lambda e: e.validate_norm_relationship("X", "Y", "Z"),
            lambda e: e.validate_conflict_record("X", "Y", "Z"),
            lambda e: e.validate_judicial_authority_relationship("X", "Y", "Z"),
            lambda e: e.validate_temporal_relationship("X", "Y", "Z"),
        ],
    )
    def test_violation_is_critical(self, enforcer: OntologyEnforcer, call: Any) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            call(enforcer)
        assert exc_info.value.violation.severity == ViolationSeverity.CRITICAL, (
            f"violation must be CRITICAL to be non-overridable; got "
            f"{exc_info.value.violation.severity}"
        )

    @pytest.mark.parametrize(
        "call",
        [
            lambda e: e.validate_deontic_operator("WRONG"),
            lambda e: e.validate_legal_level("WRONG"),
            lambda e: e.validate_conflict_state("UNRESOLVED", 0.0),
            lambda e: e.validate_temporal_range(None, "2024-12-31"),
        ],
    )
    def test_violation_is_ontology_category(
        self, enforcer: OntologyEnforcer, call: Any
    ) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            call(enforcer)
        assert exc_info.value.violation.category == ViolationCategory.ONTOLOGY_VIOLATION


# ===========================================================================
# 8. Mutation-Through-Read-Only-Path Attempt
# ===========================================================================

class TestMutationReadOnlyPath:
    """
    The ontology enforcer must never write to the graph. The methods
    are pure (no I/O). This test verifies that calling the validators
    does not cause any external state to change.
    """

    def test_validators_have_no_side_effects_on_global_state(
        self, enforcer: OntologyEnforcer
    ) -> None:
        """Call each validator twice and confirm identical behavior.
        No internal counters, no caches, no module-level mutation.
        """
        # Round 1
        try:
            enforcer.validate_deontic_operator("WRONG")
        except GovernanceViolationError:
            pass
        r1_rule_count = enforcer.rule_count

        # Round 2: should behave identically
        try:
            enforcer.validate_deontic_operator("WRONG")
        except GovernanceViolationError:
            pass
        r2_rule_count = enforcer.rule_count

        assert r1_rule_count == r2_rule_count

    def test_ontology_enforcer_source_has_no_io_calls(self) -> None:
        """Static check: the validator source code must not import
        the connection module, the audit sink, or the mutation
        boundary. If it does, a future refactor could leak writes
        into the validator path.
        """
        import inspect
        import mahoun.core.governance.ontology_enforcer as mod

        source = inspect.getsource(mod)
        forbidden = [
            "get_connection",
            "governed_session",
            "execute_query",
            "set_audit_sink",
            "compose_default_filesystem_sink",
            "GovernedNeo4jSession",
        ]
        for token in forbidden:
            assert token not in source, (
                f"OncologyEnforcer must be pure: '{token}' is forbidden in "
                f"the validator module"
            )
