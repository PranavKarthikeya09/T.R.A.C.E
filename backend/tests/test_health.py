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


def test_capabilities_catalog_contains_statuses_without_credentials(client):
    response = client.get("/api/v1/capabilities")
    assert response.status_code == 200
    capabilities = response.json()["capabilities"]
    assert set(capabilities) == {
        "visual_assessment", "ai_generation", "deepfake", "metadata", "spatial_analysis", "provenance"
    }
    assert all(value in {"available", "not_configured", "disabled", "unavailable"} for value in capabilities.values())
