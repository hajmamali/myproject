from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from mahoun.core.governance.ingestion_runtime import (
    GovernedIngestionRuntime,
    IngestionAbortedError,
)
from mahoun.core.governance.ingestion_contract import RelationshipFact
from mahoun.core.governance.ingestion_execution_gate import (
    IngestionExecutionGate,
    IngestionExecutionRequest,
)
from mahoun.ingestion_adapters.banking_law_adapter import BankingLawAdapter


def build_batch():
    adapter = BankingLawAdapter(
        law_id="banking:sample",
        law_name="قانون نمونه بانکی",
        source_uri="test://banking/sample",
        correlation_id="corr-banking-002",
    )
    with IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ):
        return adapter.build_batch("ماده ۱: بانک موظف است.")


def runtime_with_transaction():
    transaction = MagicMock()
    transaction.is_open = True
    transaction.commit.return_value = (
        SimpleNamespace(receipt_id="receipt-1"),
    )
    session = MagicMock()
    session.begin_transaction.return_value = transaction
    return GovernedIngestionRuntime(session), session, transaction


def test_batch_is_materialized_through_one_governed_transaction():
    runtime, session, transaction = runtime_with_transaction()
    batch = build_batch()
    attested = SimpleNamespace(
        to_dict=lambda: {
            "source": "test://banking/sample",
            "timestamp": "2026-09-09T00:00:00+00:00",
            "correlation_id": "corr-banking-002",
            "author": "test-author",
        }
    )

    with patch(
        "mahoun.core.governance.ingestion_runtime.GovernanceContextManager"
        ".require_provenance",
        return_value=attested,
    ), IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ):
        result = runtime.ingest_batch_atomic(batch, "test-author")

    session.begin_transaction.assert_called_once_with()
    assert transaction.queue_node.call_count == 2
    transaction.queue_relationship.assert_called_once()
    transaction.commit.assert_called_once_with()
    assert result["status"] == "success"
    assert result["relationship_count"] == 1


def test_batch_aborts_when_relationship_has_no_matching_fact():
    runtime, _, transaction = runtime_with_transaction()
    batch = build_batch()
    relationship = batch.relationships[0]
    invalid = batch.__class__(
        batch.documents,
        batch.facts,
        (
            relationship.__class__(
                relationship.relationship_id,
                relationship.source_id,
                "SUPERSEDES",
                relationship.target_id,
                relationship.properties,
                relationship.provenance,
            ),
        ),
    )
    attested = SimpleNamespace(
        to_dict=lambda: {
            "source": "test://banking/sample",
            "timestamp": "2026-09-09T00:00:00+00:00",
            "correlation_id": "corr-banking-002",
            "author": "test-author",
        }
    )

    with patch(
        "mahoun.core.governance.ingestion_runtime.GovernanceContextManager"
        ".require_provenance",
        return_value=attested,
    ), IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ), pytest.raises(IngestionAbortedError, match="matching semantic fact"):
        runtime.ingest_batch_atomic(invalid, "test-author")

    transaction.commit.assert_not_called()
    transaction.abort.assert_called_once_with()



def test_batch_aborts_when_relationship_source_is_outside_batch():
    runtime, _, transaction = runtime_with_transaction()
    batch = build_batch()
    relationship = batch.relationships[0]
    invalid = batch.__class__(
        batch.documents,
        batch.facts,
        (
            RelationshipFact(
                relationship_id=relationship.relationship_id,
                source_id="law:foreign",
                relationship_type=relationship.relationship_type,
                target_id=relationship.target_id,
                properties=relationship.properties,
                provenance=relationship.provenance,
            ),
        ),
    )
    attested = SimpleNamespace(
        to_dict=lambda: {
            "source": "test://banking/sample",
            "timestamp": "2026-09-09T00:00:00+00:00",
            "correlation_id": "corr-banking-002",
            "author": "test-author",
        }
    )

    with patch(
        "mahoun.core.governance.ingestion_runtime.GovernanceContextManager"
        ".require_provenance",
        return_value=attested,
    ), IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ), pytest.raises(IngestionAbortedError, match="source is not a document"):
        runtime.ingest_batch_atomic(invalid, "test-author")

    transaction.commit.assert_not_called()
    transaction.abort.assert_called_once_with()


def test_batch_replay_uses_only_idempotent_merge_operations():
    runtime, _, transaction = runtime_with_transaction()
    batch = build_batch()
    attested = SimpleNamespace(
        to_dict=lambda: {
            "source": "test://banking/sample",
            "timestamp": "2026-09-09T00:00:00+00:00",
            "correlation_id": "corr-banking-002",
            "author": "test-author",
        }
    )

    with patch(
        "mahoun.core.governance.ingestion_runtime.GovernanceContextManager"
        ".require_provenance",
        return_value=attested,
    ), IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ):
        runtime.ingest_batch_atomic(batch, "test-author")

    for call in transaction.queue_node.call_args_list:
        assert call.kwargs["merge"] is True
    for call in transaction.queue_relationship.call_args_list:
        assert call.kwargs["merge"] is True


def test_batch_aborts_when_commit_fails():
    runtime, _, transaction = runtime_with_transaction()
    batch = build_batch()
    transaction.commit.side_effect = RuntimeError("database unavailable")
    attested = SimpleNamespace(
        to_dict=lambda: {
            "source": "test://banking/sample",
            "timestamp": "2026-09-09T00:00:00+00:00",
            "correlation_id": "corr-banking-002",
            "author": "test-author",
        }
    )

    with patch(
        "mahoun.core.governance.ingestion_runtime.GovernanceContextManager"
        ".require_provenance",
        return_value=attested,
    ), IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-002",
            adapter_name="BankingLawAdapter",
        )
    ), pytest.raises(IngestionAbortedError, match="database unavailable"):
        runtime.ingest_batch_atomic(batch, "test-author")

    transaction.abort.assert_called_once_with()