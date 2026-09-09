import pytest

from mahoun.core.governance.ingestion_contract import IngestionContractError
from mahoun.core.governance.ingestion_execution_gate import (
    IngestionExecutionGate,
    IngestionExecutionRequest,
    IngestionExecutionDenied,
)
from mahoun.ingestion_adapters.banking_law_adapter import BankingLawAdapter


TEXT = "قانون نمونه\nماده ۱: بانک موظف است.\nماده ۲: بانک مجاز است."


def adapter() -> BankingLawAdapter:
    return BankingLawAdapter(
        law_id="banking:sample",
        law_name="قانون نمونه بانکی",
        source_uri="test://banking/sample",
        correlation_id="corr-banking-001",
    )


def execution():
    return IngestionExecutionGate.enter(
        IngestionExecutionRequest(
            source="test://banking/sample",
            author_id="test-author",
            correlation_id="corr-banking-001",
            adapter_name="BankingLawAdapter",
        )
    )


def test_adapter_emits_deterministic_canonical_batch():
    with execution():
        first = adapter().build_batch(TEXT)
        second = adapter().build_batch(TEXT)

    assert first == second
    assert [fact.object_id for fact in first.facts] == [
        "banking:sample:article:1",
        "banking:sample:article:2",
    ]
    assert {fact.predicate for fact in first.facts} == {"REFERENCES"}
    assert {
        item.relationship_type for item in first.relationships
    } == {"REFERENCES"}
    assert len(first.relationships) == 2
    assert first.documents[0].provenance["source_hash"]


def test_adapter_normalizes_persian_and_arabic_article_numbers():
    with execution():
        batch = adapter().build_batch("ماده ۰۱: الف\nماده ٢: ب")

    assert [fact.object_id for fact in batch.facts] == [
        "banking:sample:article:1",
        "banking:sample:article:2",
    ]


@pytest.mark.parametrize(
    "text, message",
    [
        ("فقط متن بدون ماده", "no article"),
        ("ماده ۱: الف\nماده ۱: تکرار", "duplicate article"),
        ("ماده الف: متن", "unsupported article"),
    ],
)
def test_adapter_fails_closed_for_unsafe_article_structure(
    text: str,
    message: str,
):
    with execution(), pytest.raises(IngestionContractError, match=message):
        adapter().build_batch(text)


def test_adapter_refuses_extraction_without_execution_gate():
    with pytest.raises(IngestionExecutionDenied, match="No Gate"):
        adapter().build_batch(TEXT)
