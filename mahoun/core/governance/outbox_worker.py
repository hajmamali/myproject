"""Compatibility shim for the legacy governance outbox worker import path."""

import logging
import psycopg2

from mahoun.core.governance.governance_context import GovernanceContextManager
from mahoun.graph.neo4j.connection import get_connection
from mahoun.graph.sync.outbox_worker import OutboxWorker as _SyncOutboxWorker

logger = logging.getLogger(__name__)


class OutboxWorker(_SyncOutboxWorker):
    """Compatibility wrapper that uses the shim module's injected dependencies."""

    async def _project_event(self, event):
        correlation_id = str(event['correlation_id']) if event['correlation_id'] else f"outbox-{__import__('uuid').uuid4()}"

        try:
            async with GovernanceContextManager.active_context(
                correlation_id=correlation_id,
                execution_mode="STRICT"
            ):
                conn = get_connection()
                with conn.governed_session(
                    correlation_id=correlation_id,
                    actor_id="outbox_worker"
                ) as session:
                    if event['aggregate_type'] == 'legal.chunks':
                        return self._process_chunk_event(session, event)

                    logger.warning(f"Unknown aggregate type: {event['aggregate_type']}")
                    return True

        except Exception as exc:
            logger.error(f"Failed to project event {event['event_id']}: {exc}")
            return False


__all__ = ["OutboxWorker", "GovernanceContextManager", "get_connection", "psycopg2"]
