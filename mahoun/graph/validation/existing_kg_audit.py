"""Read-only audit of an existing Neo4j legal knowledge graph."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, Iterable, Mapping, Protocol

from mahoun.core.governance.ontology_enforcer import OntologyEnforcer


class AuditConnection(Protocol):
    def execute_query(
        self,
        query: str,
        parameters: Mapping[str, Any] | None = None,
    ) -> Iterable[Any]: ...


class AuditStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    INCONCLUSIVE = "INCONCLUSIVE"


@dataclass(frozen=True, slots=True)
class AuditFinding:
    name: str
    status: AuditStatus
    count: int | None
    detail: str


@dataclass(frozen=True, slots=True)
class ExistingKGAuditReport:
    status: AuditStatus
    findings: tuple[AuditFinding, ...]
    metrics: Mapping[str, int]
    graph_fingerprint: str | None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        data["findings"] = [
            {
                **asdict(finding),
                "status": finding.status.value,
            }
            for finding in self.findings
        ]
        return data


METRICS_QUERY = """
MATCH (n)
RETURN count(n) AS total_nodes,
       count { (n:Law) } AS laws,
       count { (n:Article) } AS articles,
       count { (n:Norm) } AS norms,
       count { (n:LegalVersion) } AS legal_versions,
       count { (n:NormConflict) } AS norm_conflicts,
       count { (n:JudicialAuthority) } AS judicial_authorities,
       count { ()-[r]->() } AS total_relationships
"""
DUPLICATE_ID_QUERY = """
MATCH (n)
WHERE n.id IS NOT NULL
WITH n.id AS id, count(n) AS copies
WHERE copies > 1
RETURN count(id) AS count
"""
MISSING_PROVENANCE_QUERY = """
MATCH (n)
WHERE n.id IS NOT NULL
  AND (n.provenance IS NULL AND n.source_hash IS NULL AND n.text_hash IS NULL)
RETURN count(n) AS count
"""
DANGLING_ENDPOINT_QUERY = """
MATCH (a)-[r]->(b)
WHERE a.id IS NULL OR b.id IS NULL
RETURN count(r) AS count
"""
RELATIONSHIP_PATTERNS_QUERY = """
MATCH (a)-[r]->(b)
RETURN labels(a)[0] AS source_type,
       type(r) AS relationship_type,
       labels(b)[0] AS target_type
ORDER BY source_type, relationship_type, target_type
"""
FINGERPRINT_QUERY = """
MATCH (n)
RETURN labels(n) AS labels, n.id AS id,
       coalesce(n.source_hash, n.text_hash, '') AS content_hash
ORDER BY labels, id, content_hash
"""
FINGERPRINT_RELATIONSHIPS_QUERY = """
MATCH (a)-[r]->(b)
RETURN a.id AS source_id, type(r) AS relationship_type, b.id AS target_id
ORDER BY source_id, relationship_type, target_id
"""


def _record_value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, Mapping):
        return record.get(key, default)
    try:
        return record[key]
    except (KeyError, IndexError, TypeError):
        return default


def _single_count(connection: AuditConnection, query: str) -> int:
    records = list(connection.execute_query(query))
    if len(records) != 1:
        raise ValueError("audit count query did not return exactly one record")
    value = _record_value(records[0], "count")
    if not isinstance(value, int) or value < 0:
        raise ValueError("audit count query returned an invalid count")
    return value


class ExistingKGAudit:
    """Execute a deterministic, read-only audit against an existing graph."""

    def __init__(
        self,
        connection: AuditConnection,
        enforcer: OntologyEnforcer | None = None,
    ) -> None:
        self._connection = connection
        self._enforcer = enforcer or OntologyEnforcer()

    def run(self) -> ExistingKGAuditReport:
        try:
            metrics = self._metrics()
            findings = [
                self._count_finding(
                    "duplicate_ids", DUPLICATE_ID_QUERY,
                    "canonical ids must be unique",
                ),
                self._count_finding(
                    "missing_provenance", MISSING_PROVENANCE_QUERY,
                    "nodes must carry provenance or a source hash",
                ),
                self._count_finding(
                    "dangling_endpoints", DANGLING_ENDPOINT_QUERY,
                    "relationship endpoints must carry canonical ids",
                ),
                self._ontology_finding(),
            ]
            fingerprint = self._fingerprint()
        except Exception as exc:
            return ExistingKGAuditReport(
                status=AuditStatus.INCONCLUSIVE,
                findings=(AuditFinding(
                    "audit_execution", AuditStatus.INCONCLUSIVE, None, str(exc)
                ),),
                metrics={},
                graph_fingerprint=None,
            )

        status = (
            AuditStatus.PASS
            if all(finding.status is AuditStatus.PASS for finding in findings)
            else AuditStatus.FAIL
        )
        return ExistingKGAuditReport(
            status=status,
            findings=tuple(findings),
            metrics=metrics,
            graph_fingerprint=fingerprint,
        )

    def _metrics(self) -> dict[str, int]:
        records = list(self._connection.execute_query(METRICS_QUERY))
        if len(records) != 1:
            raise ValueError("metrics query did not return exactly one record")
        metrics: dict[str, int] = {}
        for key in (
            "total_nodes", "laws", "articles", "norms", "legal_versions",
            "norm_conflicts", "judicial_authorities", "total_relationships",
        ):
            value = _record_value(records[0], key)
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"metrics query returned invalid {key}")
            metrics[key] = value
        return metrics

    def _count_finding(
        self,
        name: str,
        query: str,
        detail: str,
    ) -> AuditFinding:
        count = _single_count(self._connection, query)
        return AuditFinding(
            name=name,
            status=AuditStatus.PASS if count == 0 else AuditStatus.FAIL,
            count=count,
            detail=detail,
        )

    def _ontology_finding(self) -> AuditFinding:
        violations = []
        for record in self._connection.execute_query(RELATIONSHIP_PATTERNS_QUERY):
            pattern = (
                _record_value(record, "source_type"),
                _record_value(record, "relationship_type"),
                _record_value(record, "target_type"),
            )
            if None in pattern or pattern not in self._enforcer._rules:
                violations.append(pattern)
        return AuditFinding(
            name="ontology_relationships",
            status=AuditStatus.PASS if not violations else AuditStatus.FAIL,
            count=len(violations),
            detail="all live relationship patterns must exist in canonical ontology",
        )

    def _fingerprint(self) -> str:
        nodes = [
            {
                "labels": _record_value(record, "labels", []),
                "id": _record_value(record, "id"),
                "content_hash": _record_value(record, "content_hash", ""),
            }
            for record in self._connection.execute_query(FINGERPRINT_QUERY)
        ]
        relationships = [
            {
                "source_id": _record_value(record, "source_id"),
                "relationship_type": _record_value(record, "relationship_type"),
                "target_id": _record_value(record, "target_id"),
            }
            for record in self._connection.execute_query(
                FINGERPRINT_RELATIONSHIPS_QUERY
            )
        ]
        payload = json.dumps(
            {"nodes": nodes, "relationships": relationships},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()