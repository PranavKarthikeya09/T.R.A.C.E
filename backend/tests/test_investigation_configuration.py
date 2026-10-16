"""Regression tests for check selection and honest provenance states."""
import io
import json
from unittest.mock import AsyncMock, patch

from PIL import Image
from fastapi.testclient import TestClient

from app.api.v1.endpoints import analyze as analyze_endpoint
from app.main import app
from app.provenance.provenance_adapter import ProvenanceAdapter
from app.adapters.exceptions import ModelUnavailableException


def _image_bytes() -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (16, 16), color="white").save(buffer, format="JPEG")
    return buffer.getvalue()


def test_requested_provenance_disabled_is_not_reported_as_not_requested():
    result = ProvenanceAdapter(enabled=False).verify("")
    assert result["status"] == "disabled"
    assert result["checks"][0]["status"] == "disabled"


def test_requested_provenance_is_unavailable_when_verifier_is_not_implemented():
    result = ProvenanceAdapter(enabled=True).verify("")
    assert result["status"] == "unavailable"
    assert "not implemented" in result["checks"][0]["details"]


def test_legacy_request_keeps_default_checks_and_provenance_not_requested():
    client = TestClient(app)
    prediction = {"label": "inconclusive", "interpretation": "Mocked assessment."}
    with patch.object(analyze_endpoint.analysis_service.model_adapter, "predict_async", new=AsyncMock(return_value=prediction)), \
         patch.object(analyze_endpoint.analysis_service.sightengine_adapter, "detect_all_async", new=AsyncMock(return_value=(
             {"status": "not_configured", "interpretation": "Unconfigured."},
             {"status": "disabled", "interpretation": "Disabled."},
         ))):
        response = client.post("/api/v1/analyze/image", files={"file": ("image.jpg", _image_bytes(), "image/jpeg")})

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["metadata_forensics"]["status"] == "completed"
    assert data["spatial_anomaly_map"]["status"] == "completed"
    assert data["provenance"]["status"] == "not_requested"
    assert set(data["investigation_scope"]["selected_checks"]) == {
        "visual_assessment", "ai_generation", "deepfake", "metadata", "spatial_analysis"
    }


def test_custom_selection_only_runs_requested_checks_and_records_scope():
    client = TestClient(app)
    with patch.object(analyze_endpoint.analysis_service.model_adapter, "predict_async", new=AsyncMock()) as predict, \
         patch.object(analyze_endpoint.analysis_service.sightengine_adapter, "detect_all_async", new=AsyncMock()) as sightengine, \
         patch("app.services.analysis_service.extract_image_metadata", return_value={
             "has_exif": False, "disclaimer": "Metadata caveat.", "noteworthy_markers": [], "identifiable_fields": [], "raw_tags": {}
         }) as metadata, \
         patch("app.services.analysis_service.generate_ela_map") as ela, \
         patch.object(analyze_endpoint.analysis_service.provenance_adapter, "verify", return_value={"status": "unavailable", "checks": [{"name": "c2pa_manifest", "status": "unavailable", "details": "Unavailable."}]}) as provenance:
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("image.jpg", _image_bytes(), "image/jpeg")},
            data={"selected_checks": json.dumps(["metadata", "provenance"])},
        )

    assert response.status_code == 200
    data = response.json()
    assert not predict.await_count
    assert not sightengine.await_count
    metadata.assert_called_once()
    ela.assert_not_called()
    provenance.assert_called_once()
    assert data["provenance"]["status"] == "unavailable"
    assert data["status"] == "partial"
    scope = data["investigation_scope"]
    assert set(scope["selected_checks"]) == {"metadata", "provenance"}
    assert scope["check_statuses"]["metadata"] == "completed"
    assert scope["check_statuses"]["provenance"] == "unavailable"
    assert scope["check_statuses"]["deepfake"] == "not_requested"


def test_unsupported_selected_check_is_rejected():
    client = TestClient(app)
    response = client.post(
        "/api/v1/analyze/image",
        files={"file": ("image.jpg", _image_bytes(), "image/jpeg")},
        data={"selected_checks": json.dumps(["video_analysis"])},
    )
    assert response.status_code == 422


def test_selected_provider_failure_preserves_other_check_results():
    client = TestClient(app)
    with patch.object(analyze_endpoint.analysis_service.model_adapter, "predict_async", new=AsyncMock(side_effect=ModelUnavailableException("unconfigured"))), \
         patch("app.services.analysis_service.extract_image_metadata", return_value={
             "has_exif": False, "disclaimer": "Metadata caveat.", "noteworthy_markers": [], "identifiable_fields": [], "raw_tags": {}
         }):
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("image.jpg", _image_bytes(), "image/jpeg")},
            data={"selected_checks": json.dumps(["visual_assessment", "metadata"])},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["ai_detection"]["status"] == "unavailable"
    assert data["status"] == "partial"
    assert data["metadata_forensics"]["status"] == "completed"
    assert data["investigation_scope"]["check_statuses"]["visual_assessment"] == "unavailable"
    assert data["investigation_scope"]["check_statuses"]["metadata"] == "completed"


def test_sightengine_selection_invokes_only_the_selected_detector():
    client = TestClient(app)
    with patch.object(analyze_endpoint.analysis_service.model_adapter, "predict_async", new=AsyncMock()) as predict, \
         patch.object(analyze_endpoint.analysis_service.sightengine_adapter, "detect_all_async", new=AsyncMock(return_value=(
             {"status": "completed", "label": "inconclusive", "score": 0.4, "interpretation": "Mocked provider result."},
             {"status": "disabled", "interpretation": "Not run."},
         ))) as sightengine:
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("image.jpg", _image_bytes(), "image/jpeg")},
            data={"selected_checks": json.dumps(["ai_generation"])},
        )

    assert response.status_code == 200
    assert not predict.await_count
    assert sightengine.await_args.args[2] == {"ai_generation"}
    data = response.json()
    assert data["external_ai_detection"]["status"] == "completed"
    assert data["deepfake_detection"] is None
    assert data["investigation_scope"]["check_statuses"]["deepfake"] == "not_requested"


def test_provenance_runtime_error_is_reported_as_failed_and_keeps_partial_record():
    client = TestClient(app)
    with patch.object(analyze_endpoint.analysis_service.provenance_adapter, "verify", side_effect=RuntimeError("private diagnostic")):
        response = client.post(
            "/api/v1/analyze/image",
            files={"file": ("image.jpg", _image_bytes(), "image/jpeg")},
            data={"selected_checks": json.dumps(["provenance"])},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "partial"
    assert data["provenance"]["status"] == "failed"
    assert "private diagnostic" not in response.text
