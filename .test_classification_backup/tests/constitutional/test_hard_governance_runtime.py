import pytest


@pytest.mark.p2
def test_mutation_bypass_fails_before_connection_touch(monkeypatch):
    from mahoun.graph.graph_query_service import (
        GovernanceError,
        GraphQueryConfig,
        Neo4jConnectionManager,
    )

    manager = Neo4jConnectionManager(GraphQueryConfig())

    def _unexpected_connection():
        raise AssertionError("Connection layer must not be reached for unauthorized mutation")

    monkeypatch.setattr(manager, "_get_connection", _unexpected_connection)

    with pytest.raises(GovernanceError):
        manager.execute_query("CREATE (n:Case {id: 'c1'})")


@pytest.mark.asyncio
@pytest.mark.p2
async def test_async_mutation_bypass_fails_before_connection_touch(monkeypatch):
    from mahoun.graph.graph_query_service import (
        GovernanceError,
        GraphQueryConfig,
        Neo4jConnectionManager,
    )

    manager = Neo4jConnectionManager(GraphQueryConfig())

    def _unexpected_connection():
        raise AssertionError("Async connection layer must not be reached for unauthorized mutation")

    monkeypatch.setattr(manager, "_get_connection", _unexpected_connection)

    with pytest.raises(GovernanceError):
        await manager.execute_query_async("CREATE (n:Case {id: 'c2'})")


@pytest.mark.asyncio
@pytest.mark.p2
async def test_search_service_propagates_graph_contract_failures(monkeypatch):
    from mahoun.core.exceptions import GraphResolutionFailure
    from services.search.legal_search_service import LegalSearchFilters, LegalSearchService

    service = LegalSearchService()
    service._initialized = True
    service._legal_service = None
    service._init_error = None

    class FailingLegalService:
        async def legal_retrieve(self, **kwargs):
            raise GraphResolutionFailure("graph branch failed")

    service._legal_service = FailingLegalService()

    with pytest.raises(GraphResolutionFailure):
        await service.search_verdicts(
            query="must not silently return []",
            filters=LegalSearchFilters(court_level="supreme"),
            limit=5,
        )
