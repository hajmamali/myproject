import pytest

from scripts.simple_neo4j_ingest import ingest_judgments


def test_legacy_simple_ingestion_refuses_writes():
    with pytest.raises(RuntimeError, match="quarantined"):
        ingest_judgments("missing.json", dry_run=False)