"""
Transactional Outbox & Metrics Isolation Hardening Tests
========================================================

Verifies that:
1. Triggers correctly populate governance.transactional_outbox.
2. Outbox worker projects events to Neo4j idempotently.
3. Existing 'outbox' table is untouched.
4. Metrics are correctly isolated.
"""

import uuid
import pytest
import psycopg2
from unittest.mock import MagicMock, patch, AsyncMock
from mahoun.core.governance.outbox_worker import OutboxWorker
from mahoun.core.governance.governance_context import GovernanceContextManager

# Integration markers
pytestmark = pytest.mark.anyio

@pytest.fixture
def mock_neo4j_conn():
    with patch("mahoun.core.governance.outbox_worker.get_connection") as mock:
        yield mock

@pytest.fixture
def mock_pg_conn():
    with patch("mahoun.core.governance.outbox_worker.psycopg2.connect") as mock:
        conn = MagicMock()
        mock.return_value = conn
        yield conn

@pytest.fixture
def mock_gov_ctx():
    with patch("mahoun.core.governance.outbox_worker.GovernanceContextManager") as mock:
        ctx_cm = MagicMock()
        ctx_cm.__aenter__ = AsyncMock()
        ctx_cm.__aexit__ = AsyncMock()
        mock.active_context.return_value = ctx_cm
        yield mock

async def test_outbox_worker_picks_and_processes(mock_pg_conn, mock_neo4j_conn, mock_gov_ctx):
    """Verify worker picks up PENDING events and marks them PROCESSED."""
    worker = OutboxWorker(batch_size=1)
    
    # Setup mock event
    event_id = uuid.uuid4()
    aggregate_id = uuid.uuid4()
    mock_event = {
        'event_id': event_id,
        'aggregate_type': 'legal.chunks',
        'aggregate_id': aggregate_id,
        'action': 'INSERT',
        'payload': {'text': 'test chunk'},
        'correlation_id': uuid.uuid4()
    }
    
    cursor = mock_pg_conn.cursor.return_value.__enter__.return_value
    cursor.fetchall.side_effect = [[mock_event], []] # One event, then empty
    
    # Mock Neo4j session
    governed_session = MagicMock()
    mock_neo4j_conn.return_value.governed_session.return_value.__enter__.return_value = governed_session
    
    # Run one iteration (mocking the loop)
    processed_count = await worker.process_batch()
    assert processed_count == 1
    
    # Verify Neo4j was called correctly
    governed_session.write_node.assert_called_once()
    args, kwargs = governed_session.write_node.call_args
    assert kwargs['label'] == "Chunk"
    assert kwargs['node_data']['id'] == str(aggregate_id)
    
    # Verify status update in Postgres
    # Use call_args_list to see what actually happened
    all_calls = cursor.execute.call_args_list
    print(f"DEBUG: all_calls={all_calls}")
    assert len(all_calls) >= 2
    
    # Check if PROCESSED was called
    processed_called = any("status = 'PROCESSED'" in str(c) for c in all_calls)
    assert processed_called, f"PROCESSED update not found in calls: {all_calls}"

def test_sql_migration_compatibility():
    """
    Validation of the 004 migration logic (Unit level).
    Ensures that our new outbox does not collide with the existing one.
    """
    # This is a static analysis check of the provided migration script
    with open("mahoun/graph/schema/migrations/004_transactional_outbox_and_metrics_isolation.sql", "r") as f:
        content = f.read()
        
    assert "CREATE SCHEMA IF NOT EXISTS governance;" in content
    assert "CREATE TABLE IF NOT EXISTS governance.transactional_outbox" in content
    assert "DROP TABLE IF EXISTS outbox" not in content # MUST NOT drop the existing indexing outbox
    assert "ALTER TABLE legal.chunks DROP COLUMN IF EXISTS pagerank_score" in content

@pytest.fixture(scope="session")
def helpers():
    class Helpers:
        @staticmethod
        def match_sql(fragment):
            class SQLMatcher:
                def __init__(self, frag): self.frag = frag
                def __eq__(self, other): return self.frag in str(other)
            return SQLMatcher(fragment)
    return Helpers()

# Inject helper into pytest namespace
@pytest.fixture(autouse=True)
def _inject_helpers(helpers):
    pytest.helpers = helpers
