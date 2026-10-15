"""Health check test matching API_SPEC.md."""


def test_health_check(client):
    """GET /api/v1/health should return 200 with status ok and service trace-api."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data == {
        "status": "ok",
        "service": "trace-api"
    }
