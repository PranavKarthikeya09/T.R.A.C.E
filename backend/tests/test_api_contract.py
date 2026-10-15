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


def test_model_uninitialized_returns_503(client):
    """
    POST /api/v1/analyze/image with valid image in Phase 1 setup
    returns 503 MODEL_UNAVAILABLE rather than a fake or hard-coded result.
    """
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color="red")
    img.save(buf, format="PNG")
    buf.seek(0)

    files = {"file": ("test_sample.png", buf.getvalue(), "image/png")}
    response = client.post("/api/v1/analyze/image", files=files)
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "MODEL_UNAVAILABLE"
