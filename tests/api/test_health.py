"""Health & root endpoint verification tests."""

from backend.api.routes.health import health_check
from backend.main import app, root


def test_root_endpoint():
    data = root()
    assert data["app"] == "VibeVerse AI"
    assert data["docs"] == "/docs"
    assert data["health"] == "/health"


def test_health_endpoint_handles_db_gracefully():
    res = health_check()
    assert res.app_name == "VibeVerse AI"
    assert res.status in {"healthy", "degraded"}
    assert isinstance(res.database_status, str)


def test_fastapi_routes_registered():
    paths = set(app.openapi()["paths"].keys())
    expected = {
        "/health",
        "/api/preferences/{session_id}",
        "/api/preferences/{session_id}/reset",
        "/api/catalog/metadata",
        "/api/music/search",
        "/api/music/recommendations",
        "/api/movies/search",
        "/api/movies/recommendations",
        "/api/series/search",
        "/api/series/recommendations",
        "/api/search",
        "/api/trending",
        "/api/recommendations/cross-domain",
        "/api/recommendations/chain",
        "/api/recommendations/unexpected",
        "/api/recommendations/mood",
        "/api/personality/analyze",
        "/api/personality/{session_id}",
        "/api/feedback",
        "/api/feedback/{session_id}",
        "/api/saved",
        "/api/saved/{session_id}",
        "/api/saved/{session_id}/{content_id}",
        "/api/analytics/trends",
        "/api/analytics/preferences/{session_id}",
    }
    assert expected.issubset(paths)
