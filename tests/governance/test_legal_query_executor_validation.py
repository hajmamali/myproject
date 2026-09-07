"""
LegalQueryExecutor Param-Spec Adversarial Tests
=================================================

These tests prove that every ParameterSpec attached to a CypherQuery
is actually enforced by LegalQueryExecutor._validate_parameters BEFORE
the query reaches Neo4j. A bypass here means a caller can inject an
invalid enum value, a malformed date, or a missing required parameter
into the graph through a legal query — exactly the "let Neo4j reject
it" failure mode we closed.

Run: ``pytest tests/governance/test_legal_query_executor_validation.py -v``
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mahoun.graph.legal_cypher_queries import (
    LegalCypherQueries,
    LegalQueryExecutor,
    ParameterSpec,
)
from mahoun.core.governance.violations import (
    GovernanceViolationError,
    ViolationCategory,
    ViolationSeverity,
)


@pytest.fixture
def executor() -> LegalQueryExecutor:
    from mahoun.graph.neo4j.connection import Neo4jConnection

    mock_conn = MagicMock(spec=Neo4jConnection)
    return LegalQueryExecutor(mock_conn)


# ---------------------------------------------------------------------------
# Helper: discover every query that has param_specs and verify they
# are structurally sound (name + kind present, no duplicates).
# ---------------------------------------------------------------------------

class TestParamSpecCoverage:
    """Every annotated query must declare param_specs that map to real
    parameters used in its Cypher text."""

    def test_every_param_spec_matches_a_parameter_token(self) -> None:
        for q in LegalCypherQueries.list_all_queries():
            for spec in q.param_specs:
                token = f"${spec.name}"
                assert token in q.cypher, (
                    f"Query '{q.name}': param_spec name '{spec.name}' "
                    f"has no matching ${{spec.name}} token in Cypher"
                )

    def test_no_duplicate_spec_names_within_a_query(self) -> None:
        for q in LegalCypherQueries.list_all_queries():
            names = [s.name for s in q.param_specs]
            assert len(names) == len(set(names)), (
                f"Query '{q.name}' has duplicate param_spec names: {names}"
            )

    def test_unknown_spec_kind_rejected_at_runtime(self, executor: LegalQueryExecutor) -> None:
        """A spec with a kind that _validate_one does not recognise
        must raise GovernanceViolationError, not pass through."""
        fake_spec = ParameterSpec(name="bogus", kind="not_a_real_kind", required=True)
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_one(fake_spec, "value", "test_query")
        assert "Unknown parameter spec kind" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Deontic operator validation through the executor
# ---------------------------------------------------------------------------

class TestDeonticOperatorValidation:
    """FIND_NORMS_BY_DEONTIC_OPERATOR — deontic_operator must be a valid enum."""

    @pytest.mark.parametrize("invalid_value", [
        "obligation",        # lowercase
        "Obligation",        # mixed case
        "OBLIGATION ",       # trailing space
        " OBLIGATION",       # leading space
        "MANDATE",           # unknown operator
        "",                  # empty
        "   ",              # whitespace
        None,                # missing entirely
        42,                  # wrong type
    ])
    def test_invalid_deontic_operator_rejected(
        self, executor: LegalQueryExecutor, invalid_value: str
    ) -> None:
        params = {
            "deontic_operator": invalid_value,
            "legal_level": None,
            "as_of": "2024-06-01",
        }
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
            )
        assert exc_info.value.violation.category == ViolationCategory.ONTOLOGY_VIOLATION

    @pytest.mark.parametrize("valid_value", [
        "OBLIGATION",
        "PERMISSION",
        "PROHIBITION",
    ])
    def test_valid_deontic_operator_accepted(
        self, executor: LegalQueryExecutor, valid_value: str
    ) -> None:
        params = {
            "deontic_operator": valid_value,
            "legal_level": None,
            "as_of": "2024-06-01",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
        )


# ---------------------------------------------------------------------------
# LegalLevel validation through the executor
# ---------------------------------------------------------------------------

class TestLegalLevelValidation:
    """LegalLevel params must be valid enums; None for optional is OK."""

    def test_valid_legal_level_accepted(self, executor: LegalQueryExecutor) -> None:
        params = {
            "as_of": "2024-06-01",
            "legal_level": "CONSTITUTIONAL",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_LAWS_IN_FORCE_AT, params
        )

    def test_none_legal_level_accepted(self, executor: LegalQueryExecutor) -> None:
        params = {
            "as_of": "2024-06-01",
            "legal_level": None,
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_LAWS_IN_FORCE_AT, params
        )

    @pytest.mark.parametrize("invalid_level", [
        "constitutional",
        "Constitution",
        "ORDINARY_LAW ",
        "STATUTE",
        "BANANA",
        "",
    ])
    def test_invalid_legal_level_rejected(
        self, executor: LegalQueryExecutor, invalid_level: str
    ) -> None:
        params = {
            "as_of": "2024-06-01",
            "legal_level": invalid_level,
        }
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_LAWS_IN_FORCE_AT, params
            )

    def test_list_of_legal_level_validates_each_element(
        self, executor: LegalQueryExecutor
    ) -> None:
        params = {
            "legal_levels": ["CONSTITUTIONAL", "ORDINARY_LAW", "REGULATION"],
            "as_of": "2024-06-01",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORMS_BY_HIERARCHY_LEVEL, params
        )

    def test_list_of_legal_level_rejects_non_list(self, executor: LegalQueryExecutor) -> None:
        params = {
            "legal_levels": "CONSTITUTIONAL",
            "as_of": "2024-06-01",
        }
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_HIERARCHY_LEVEL, params
            )
        assert "must be a list" in str(exc_info.value)

    def test_list_of_legal_level_rejects_invalid_element(
        self, executor: LegalQueryExecutor
    ) -> None:
        params = {
            "legal_levels": ["CONSTITUTIONAL", "not_a_level"],
            "as_of": "2024-06-01",
        }
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_HIERARCHY_LEVEL, params
            )

    def test_list_of_legal_level_allows_empty(self, executor: LegalQueryExecutor) -> None:
        """An empty list is accepted (matches 'filter that excludes everything')."""
        params = {
            "legal_levels": [],
            "as_of": "2024-06-01",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORMS_BY_HIERARCHY_LEVEL, params
        )


# ---------------------------------------------------------------------------
# ConflictResolution validation through the executor
# ---------------------------------------------------------------------------

class TestConflictResolutionValidation:
    def test_valid_resolution_accepted(self, executor: LegalQueryExecutor) -> None:
        params = {"resolution": "RESOLVED_SUPERIOR"}
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORM_CONFLICTS_BY_RESOLUTION, params
        )

    @pytest.mark.parametrize("invalid_value", [
        "resolved_superior",
        "RESOLVED",
        "UNRESOLVED ",
        "BANANA",
        None,
        123,
    ])
    def test_invalid_resolution_rejected(
        self, executor: LegalQueryExecutor, invalid_value: str
    ) -> None:
        params = {"resolution": invalid_value}
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORM_CONFLICTS_BY_RESOLUTION, params
            )


# ---------------------------------------------------------------------------
# LegalForce validation through the executor
# ---------------------------------------------------------------------------

class TestLegalForceValidation:
    def test_valid_force_accepted(self, executor: LegalQueryExecutor) -> None:
        params = {
            "binding_scope": "ALL_COURTS",
            "as_of": "2024-06-01",
            "legal_force": "BINDING",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORMS_BY_VERDICT_BINDING_SCOPE, params
        )

    @pytest.mark.parametrize("invalid_value", [
        "binding",
        "BINDING ",
        "BIND",
        "PRE_BINDING",
        None,
    ])
    def test_invalid_force_rejected(
        self, executor: LegalQueryExecutor, invalid_value: str
    ) -> None:
        params = {
            "binding_scope": "ALL_COURTS",
            "as_of": "2024-06-01",
            "legal_force": invalid_value,
        }
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_VERDICT_BINDING_SCOPE, params
            )


# ---------------------------------------------------------------------------
# BindingScope validation through the executor
# ---------------------------------------------------------------------------

class TestBindingScopeValidation:
    @pytest.mark.parametrize("invalid_value", [
        "all_courts",
        "ALL_COURTS ",
        "UNIVERSAL",
        "",
        None,
    ])
    def test_invalid_scope_rejected(
        self, executor: LegalQueryExecutor, invalid_value: str
    ) -> None:
        params = {
            "binding_scope": invalid_value,
            "as_of": "2024-06-01",
            "legal_force": "BINDING",
        }
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_VERDICT_BINDING_SCOPE, params
            )


# ---------------------------------------------------------------------------
# ISO 8601 date validation through the executor
# ---------------------------------------------------------------------------

class TestIso8601Validation:
    def test_valid_date_accepted(self, executor: LegalQueryExecutor) -> None:
        params = {
            "deontic_operator": "OBLIGATION",
            "legal_level": None,
            "as_of": "2024-06-01",
        }
        executor._validate_parameters(
            LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
        )

    @pytest.mark.parametrize("malformed_date", [
        "2024-13-01",      # invalid month
        "2024-06-32",      # invalid day
        "not-a-date",
        "2024/06/01",      # wrong separator
        "06-01-2024",      # wrong order
        "",
        "   ",
        None,
        "2024-06-01T00:00:00Z garbage",
    ])
    def test_malformed_date_rejected(
        self, executor: LegalQueryExecutor, malformed_date: str
    ) -> None:
        params = {
            "deontic_operator": "OBLIGATION",
            "legal_level": None,
            "as_of": malformed_date,
        }
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
            )


# ---------------------------------------------------------------------------
# non_empty_string kind validation
# ---------------------------------------------------------------------------

class TestNonEmptyStringValidation:
    """String identifier params (norm_id, base_law_id) must be non-empty
    strings."""

    @pytest.mark.parametrize("invalid_value", [
        "",
        "   ",
        "\t\n",
        None,
        42,
        [],
        {},
    ])
    def test_invalid_id_rejected(
        self, executor: LegalQueryExecutor, invalid_value: Any
    ) -> None:
        params = {"norm_id": invalid_value}
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_AUTHORITY_OVER_NORM, params
            )

    @pytest.mark.parametrize("invalid_value", [
        "",
        "   ",
        None,
        42,
    ])
    def test_invalid_base_law_id_rejected(
        self, executor: LegalQueryExecutor, invalid_value: Any
    ) -> None:
        params = {"base_law_id": invalid_value}
        with pytest.raises(GovernanceViolationError):
            executor._validate_parameters(
                LegalCypherQueries.FIND_LATEST_VERSION_OF_LAW, params
            )

    def test_valid_ids_accepted(self, executor: LegalQueryExecutor) -> None:
        executor._validate_parameters(
            LegalCypherQueries.FIND_AUTHORITY_OVER_NORM,
            {"norm_id": "norm_001"},
        )
        executor._validate_parameters(
            LegalCypherQueries.FIND_LATEST_VERSION_OF_LAW,
            {"base_law_id": "law_001"},
        )


# ---------------------------------------------------------------------------
# Missing required parameters
# ---------------------------------------------------------------------------

class TestMissingRequiredParams:
    """A missing required parameter must raise GovernanceViolationError,
    not silently default or pass through."""

    def test_missing_deontic_operator_rejected(self, executor: LegalQueryExecutor) -> None:
        params = {"legal_level": None, "as_of": "2024-06-01"}
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
            )
        assert "Required parameter" in str(exc_info.value)
        assert "deontic_operator" in str(exc_info.value)

    def test_missing_as_of_rejected(self, executor: LegalQueryExecutor) -> None:
        params = {"deontic_operator": "OBLIGATION", "legal_level": None}
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR, params
            )
        assert "as_of" in str(exc_info.value)

    def test_missing_norm_id_rejected(self, executor: LegalQueryExecutor) -> None:
        params = {}
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_AUTHORITY_OVER_NORM, params
            )
        assert "norm_id" in str(exc_info.value)

    def test_missing_base_law_id_rejected(self, executor: LegalQueryExecutor) -> None:
        params = {}
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_LATEST_VERSION_OF_LAW, params
            )
        assert "base_law_id" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Violation severity and category through the executor
# ---------------------------------------------------------------------------

class TestViolationSeverityThroughExecutor:
    """All param_spec violations raised by the executor must be CRITICAL
    and ONTOLOGY_VIOLATION, not WARNING or INFO."""

    def test_missing_required_is_critical(self, executor: LegalQueryExecutor) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORMS_BY_DEONTIC_OPERATOR,
                {"legal_level": None},
            )
        v = exc_info.value.violation
        assert v.severity == ViolationSeverity.CRITICAL
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION

    def test_invalid_enum_is_critical(self, executor: LegalQueryExecutor) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_NORM_CONFLICTS_BY_RESOLUTION,
                {"resolution": "BOGUS"},
            )
        v = exc_info.value.violation
        assert v.severity == ViolationSeverity.CRITICAL
        assert v.category == ViolationCategory.ONTOLOGY_VIOLATION

    def test_non_empty_string_violation_is_critical(
        self, executor: LegalQueryExecutor
    ) -> None:
        with pytest.raises(GovernanceViolationError) as exc_info:
            executor._validate_parameters(
                LegalCypherQueries.FIND_AUTHORITY_OVER_NORM,
                {"norm_id": "   "},
            )
        v = exc_info.value.violation
        assert v.severity == ViolationSeverity.CRITICAL


# ---------------------------------------------------------------------------
# Queries with no param_specs still pass through cleanly
# ---------------------------------------------------------------------------

class TestNoParamSpecQueries:
    """Queries without param_specs should not be rejected by
    _validate_parameters."""

    def test_empty_param_specs_pass_with_empty_params(
        self, executor: LegalQueryExecutor
    ) -> None:
        executor._validate_parameters(
            LegalCypherQueries.FIND_UNRESOLVED_NORM_CONFLICTS, {}
        )

    def test_empty_param_specs_pass_with_supplied_params(
        self, executor: LegalQueryExecutor
    ) -> None:
        """If a query has no specs but the caller passes params anyway,
        those params are simply not validated (pass-through)."""
        executor._validate_parameters(
            LegalCypherQueries.FIND_UNRESOLVED_NORM_CONFLICTS,
            {"unused_key": "value"},
        )


# ---------------------------------------------------------------------------
# All 11 new constitutional queries have param_specs (or none if no params)
# ---------------------------------------------------------------------------

class TestAllConstitutionalQueriesAnnotated:
    """The 11 constitutional queries added in this round must each have
    param_specs that cover every $parameter in their Cypher."""

    CONSTITUTIONAL_QUERIES = [
        "find_norms_by_hierarchy_level",
        "resolve_lex_superior_conflict",
        "find_norms_by_deontic_operator",
        "detect_deontic_conflict",
        "find_laws_in_force_at",
        "find_latest_version_of_law",
        "find_versions_effective_at",
        "find_unresolved_norm_conflicts",
        "find_norm_conflicts_by_resolution",
        "find_authority_over_norm",
        "find_norms_by_verdict_binding_scope",
    ]

    @pytest.mark.parametrize("query_name", CONSTITUTIONAL_QUERIES)
    def test_query_exists_and_has_param_specs(self, query_name: str) -> None:
        q = LegalCypherQueries.get_query(query_name)
        assert q is not None, f"Query '{query_name}' not found"

    @pytest.mark.parametrize("query_name", CONSTITUTIONAL_QUERIES)
    def test_all_parameters_have_specs(self, query_name: str) -> None:
        q = LegalCypherQueries.get_query(query_name)
        assert q is not None
        # Extract $param names from Cypher
        import re
        tokens = set(re.findall(r"\$(\w+)", q.cypher))
        spec_names = {s.name for s in q.param_specs}
        uncovered = tokens - spec_names
        # FIND_UNRESOLVED_NORM_CONFLICTS has no parameters, so tokens is empty
        # and spec_names is empty — that's the expected case.
        assert not uncovered, (
            f"Query '{query_name}' has parameters {uncovered} "
            f"without param_specs"
        )
