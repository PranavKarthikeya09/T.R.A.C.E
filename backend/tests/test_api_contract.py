"""API contract and validation tests matching API_SPEC.md."""
import io
from PIL import Image


def test_missing_file_rejected(client):
    """POST /api/v1/analyze/image with no file returns 400 Bad Request."""
    response = client.post("/api/v1/analyze/image")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MISSING_FILE"


def test_unsupported_file_type_rejected(client):
    """POST /api/v1/analyze/image with unsupported extension returns 415."""
    files = {"file": ("test.pdf", b"%PDF-1.4 dummy content", "application/pdf")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 415
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_corrupt_image_rejected(client):
    """POST /api/v1/analyze/image with non-image bytes returns 422."""
    files = {"file": ("corrupt.jpg", b"not-a-valid-jpeg-stream", "image/jpeg")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 422
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "INVALID_IMAGE"


from unittest.mock import patch
from app.adapters.exceptions import ModelUnavailableException
from app.adapters.azure_vision_adapter import AzureVisionAdapter


def test_model_uninitialized_returns_503(client):
    """
    POST /api/v1/analyze/image with valid image when model is uninitialized
    returns 503 MODEL_UNAVAILABLE rather than a fake or hard-coded result.
    """
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color="red")
    img.save(buf, format="PNG")
    buf.seek(0)

    with patch.object(
        AzureVisionAdapter,
        "predict_async",
        side_effect=ModelUnavailableException("Model uninitialized")
    ):
        files = {"file": ("test_sample.png", buf.getvalue(), "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 503
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == "MODEL_UNAVAILABLE"


from unittest.mock import AsyncMock
from app.composer.result_composer import ResultComposer


def test_result_composer_alert_mapping():
    """Verify that label 'potential_manipulation' produces 'caution' and does not fall back to 'inconclusive'."""
    # 1. Potential manipulation -> caution
    alert = ResultComposer.compose_alert(
        ai_result={"status": "completed", "label": "potential_manipulation"},
        provenance_result={"status": "not_requested"}
    )
    assert alert.level == "caution"
    assert "potential media manipulation" in alert.message.lower()

    # 2. Authentic -> info
    alert_auth = ResultComposer.compose_alert(
        ai_result={"status": "completed", "label": "authentic"},
        provenance_result={"status": "not_requested"}
    )
    assert alert_auth.level == "info"
    assert "authenticity cannot be definitively established" in alert_auth.message.lower()

    # 3. Inconclusive -> inconclusive
    alert_inc = ResultComposer.compose_alert(
        ai_result={"status": "completed", "label": "inconclusive"},
        provenance_result={"status": "not_requested"}
    )
    assert alert_inc.level == "inconclusive"
    assert "ambiguous indicators" in alert_inc.message.lower()

    # 4. Uncompleted detection -> inconclusive
    alert_failed = ResultComposer.compose_alert(
        ai_result={"status": "failed", "label": "potential_manipulation"},
        provenance_result={"status": "not_requested"}
    )
    assert alert_failed.level == "inconclusive"

    # 5. Tampered provenance -> caution
    alert_tampered = ResultComposer.compose_alert(
        ai_result={"status": "completed", "label": "authentic"},
        provenance_result={"status": "tampered"}
    )
    assert alert_tampered.level == "caution"
    assert "provenance credentials" in alert_tampered.message.lower()


def test_api_potential_manipulation_produces_caution_alert(client):
    """End-to-end API test: when vision model finds potential_manipulation, trace_alert is caution."""
    mock_parsed_output = {
        "status": "completed",
        "model_id": "gpt-4.1-mini",
        "label": "potential_manipulation",
        "score": None,
        "score_semantics": "not_applicable_qualitative_heuristic",
        "interpretation": "Observed inconsistencies along object boundary.",
        "observations": {
            "characteristics": "Object on table.",
            "inconsistencies": ["Inconsistent shadows."],
            "alternative_explanations": "None.",
            "recommendations": "Verify origin."
        },
        "limitations": ["Visual inspection is heuristic."]
    }

    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color="blue")
    img.save(buf, format="PNG")
    buf.seek(0)

    with patch.object(
        AzureVisionAdapter,
        "predict_async",
        new=AsyncMock(return_value=mock_parsed_output)
    ):
        files = {"file": ("sample.png", buf.getvalue(), "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)
        assert response.status_code == 200
        data = response.json()
        assert data["ai_detection"]["label"] == "potential_manipulation"
        assert data["trace_alert"]["level"] == "caution"
        assert "potential media manipulation" in data["trace_alert"]["message"].lower()

