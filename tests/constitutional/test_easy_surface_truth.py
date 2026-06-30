from api.main import app


def _route_methods():
    mapping = {}
    for route in app.routes:
        path = getattr(route, "path", None)
        methods = frozenset(getattr(route, "methods", []) or [])
        if path:
            mapping.setdefault(path, set()).update(methods)
    return mapping


def test_critical_live_routes_are_registered():
    routes = _route_methods()

    assert "/v1/search/verdicts" in routes
    assert "/api/v1/reasoning/generate-verdict" in routes
    assert "/api/v1/reasoning/verify-verdict" in routes
    assert "/api/v1/reasoning/query-ledger" in routes
    assert "/api/v1/policy/current" in routes
    assert "/api/v1/policy/list" in routes
    assert "/health" in routes


def test_fake_control_plane_routes_are_absent():
    routes = _route_methods()

    assert "/api/v1/finetuning/jobs" not in routes
    assert "/api/v1/experiments" not in routes
    assert "/api/v1/policy/deploy" not in routes
    assert "/api/v1/policy/rollback" not in routes


def test_runtime_config_surface_is_read_only():
    routes = _route_methods()

    assert "/api/v1/config" in routes
    assert "GET" in routes["/api/v1/config"]
    assert "PUT" not in routes["/api/v1/config"]
