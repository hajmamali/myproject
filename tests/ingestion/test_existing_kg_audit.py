from typing import Any

from mahoun.graph.validation.existing_kg_audit import (
    AuditStatus,
    ExistingKGAudit,
)


class FakeAuditConnection:
    def __init__(self, records: dict[str, list[dict[str, Any]]]):
        self.records = records

    def execute_query(self, query: str, parameters=None):
        for marker, records in self.records.items():
            if marker in query:
                return records
        raise AssertionError(f"unexpected audit query: {query}")


def healthy_connection() -> FakeAuditConnection:
    return FakeAuditConnection({
        "MATCH (n)\nRETURN count(n)": [{
            "total_nodes": 2,
            "laws": 1,
            "articles": 1,
            "norms": 0,
            "legal_versions": 0,
            "norm_conflicts": 0,
            "judicial_authorities": 0,
            "total_relationships": 1,
        }],
        "WHERE n.id IS NOT NULL\nWITH n.id": [{"count": 0}],
        "n.provenance IS NULL": [{"count": 0}],
        "a.id IS NULL OR b.id IS NULL": [{"count": 0}],
        "labels(a)[0] AS source_type": [{
            "source_type": "Document",
            "relationship_type": "REFERENCES",
            "target_type": "LawArticle",
        }],
        "labels(n) AS labels": [{
            "labels": ["Law"], "id": "law:1", "content_hash": "hash-law"
        }],
        "a.id AS source_id": [{
            "source_id": "law:1",
            "relationship_type": "REFERENCES",
            "target_id": "article:1",
        }],
    })


def test_existing_graph_audit_passes_without_writing():
    report = ExistingKGAudit(healthy_connection()).run()

    assert report.status is AuditStatus.PASS
    assert report.metrics["total_nodes"] == 2
    assert report.graph_fingerprint


def test_existing_graph_audit_fails_on_duplicate_ids():
    connection = healthy_connection()
    connection.records["WHERE n.id IS NOT NULL\nWITH n.id"] = [{"count": 2}]

    report = ExistingKGAudit(connection).run()

    assert report.status is AuditStatus.FAIL
    duplicate = next(item for item in report.findings if item.name == "duplicate_ids")
    assert duplicate.count == 2


def test_existing_graph_audit_is_inconclusive_on_query_failure():
    report = ExistingKGAudit(
        FakeAuditConnection({"MATCH (n)\nRETURN count(n)": []})
    ).run()

    assert report.status is AuditStatus.INCONCLUSIVE
    assert report.graph_fingerprint is None