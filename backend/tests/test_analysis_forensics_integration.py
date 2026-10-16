"""Integration test suite for metadata inspection and ELA anomaly integration into the API response."""
import io
import base64
from unittest.mock import patch, AsyncMock
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.azure_vision_adapter import AzureVisionAdapter
from app.services.analysis_service import AnalysisService
from app.schemas.analysis import AnalysisResponse


@pytest.fixture
def client():
    return TestClient(app)


def _create_jpeg_with_exif() -> bytes:
    """Construct an in-memory JPEG containing camera make/model EXIF tags."""
    img = Image.new("RGB", (64, 64), color="blue")
    exif = img.getexif()
    exif[271] = "Sony"       # Make
    exif[272] = "ILCE-7RM4"  # Model
    exif[305] = "Camera OS"  # Software
    buf = io.BytesIO()
    img.save(buf, format="JPEG", exif=exif)
    return buf.getvalue()


class TestAnalysisForensicsIntegration:
    """Test suite verifying Step 3 backend analysis response integration."""

    def test_successful_analysis_includes_metadata_and_ela(self, client):
        """Verify that metadata and ELA records appear in a 200 response alongside model findings."""
        mock_output = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "authentic",
            "score": None,
            "score_semantics": "not_applicable_qualitative_heuristic",
            "interpretation": "Image demonstrates consistent textures without obvious synthetic artifacts.",
            "limitations": ["Visual inspection is qualitative."]
        }

        jpeg_bytes = _create_jpeg_with_exif()

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_output)):
            files = {"file": ("camera_shot.jpg", jpeg_bytes, "image/jpeg")}
            response = client.post("/api/v1/analyze/image", files=files)

            assert response.status_code == 200
            data = response.json()

            # Core fields
            assert data["status"] == "completed"
            assert data["ai_detection"]["label"] == "authentic"
            assert data["ai_detection"]["score"] is None
            assert data["ai_detection"]["model_id"] == "gpt-4.1-mini"

            # Metadata forensics record
            metadata = data["metadata_forensics"]
            assert metadata is not None
            assert metadata["status"] == "completed"
            assert metadata["has_exif"] is True
            assert metadata["camera_make"] == "Sony"
            assert metadata["camera_model"] == "ILCE-7RM4"
            assert "disclaimer" in metadata
            assert len(metadata["disclaimer"]) > 0

            # Spatial anomaly map record
            spatial = data["spatial_anomaly_map"]
            assert spatial is not None
            assert spatial["status"] == "completed"
            assert spatial["map_type"] == "error_level_analysis"
            assert spatial["input_width"] == 64
            assert spatial["input_height"] == 64
            assert spatial["visualization_width"] == 64
            assert spatial["visualization_height"] == 64
            assert spatial["is_downsampled"] is False
            assert spatial["heatmap_data_uri"].startswith("data:image/png;base64,")
            assert spatial["grayscale_data_uri"].startswith("data:image/png;base64,")
            assert "residual_statistics" in spatial
            stats = spatial["residual_statistics"]
            assert "min_residual" in stats
            assert "max_residual" in stats
            assert "mean_residual" in stats
            assert "disclaimer" in spatial
            assert len(spatial["limitations"]) > 0

            # Limitations list merges standard, model, and forensic limitations
            assert any("error level analysis" in lim.lower() for lim in data["limitations"])
            assert any("metadata" in lim.lower() for lim in data["limitations"])

    def test_existing_error_semantics_remain_compatible(self, client):
        """Verify that 400, 415, and 422 HTTP error contracts are not altered."""
        # 1. Missing file -> 400
        res_missing = client.post("/api/v1/analyze/image")
        assert res_missing.status_code == 400
        assert res_missing.json()["error"]["code"] == "MISSING_FILE"

        # 2. Unsupported format -> 415
        res_unsupported = client.post(
            "/api/v1/analyze/image",
            files={"file": ("doc.txt", b"plain text", "text/plain")}
        )
        assert res_unsupported.status_code == 415
        assert res_unsupported.json()["error"]["code"] == "UNSUPPORTED_MEDIA_TYPE"

        # 3. Corrupted image -> 422
        res_corrupt = client.post(
            "/api/v1/analyze/image",
            files={"file": ("bad.jpg", b"not-an-image", "image/jpeg")}
        )
        assert res_corrupt.status_code == 422
        assert res_corrupt.json()["error"]["code"] == "INVALID_IMAGE"

    def test_metadata_failure_does_not_crash_analysis(self, client):
        """Verify that if metadata extraction throws an exception, the analysis still returns 200."""
        mock_output = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "inconclusive",
            "score": None,
            "interpretation": "Analysis completed."
        }

        buf = io.BytesIO()
        Image.new("RGB", (32, 32), color="green").save(buf, format="PNG")

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_output)), \
             patch("app.services.analysis_service.extract_image_metadata", side_effect=RuntimeError("EXIF corrupted")):
            files = {"file": ("sample.png", buf.getvalue(), "image/png")}
            response = client.post("/api/v1/analyze/image", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["ai_detection"]["label"] == "inconclusive"

            # Metadata should record failure safely without crashing endpoint
            metadata = data["metadata_forensics"]
            assert metadata is not None
            assert metadata["status"] == "failed"
            assert "EXIF corrupted" in metadata["error"]

            # ELA should still have succeeded
            assert data["spatial_anomaly_map"]["status"] == "completed"

    def test_ela_failure_does_not_crash_analysis(self, client):
        """Verify that if ELA processing fails, the analysis endpoint still returns 200."""
        mock_output = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "potential_manipulation",
            "score": None,
            "interpretation": "Inconsistencies observed."
        }

        buf = io.BytesIO()
        Image.new("RGB", (32, 32), color="purple").save(buf, format="PNG")

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_output)), \
             patch("app.services.analysis_service.generate_ela_map", side_effect=RuntimeError("Memory limit error")):
            files = {"file": ("sample.png", buf.getvalue(), "image/png")}
            response = client.post("/api/v1/analyze/image", files=files)

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "completed"
            assert data["ai_detection"]["label"] == "potential_manipulation"

            # ELA map should report safe failure
            spatial = data["spatial_anomaly_map"]
            assert spatial is not None
            assert spatial["status"] == "failed"
            assert "Memory limit error" in spatial["error"]

            # Metadata should still succeed
            assert data["metadata_forensics"]["status"] == "completed"

    def test_azure_score_semantics_preserved_independently(self, client):
        """Verify that ELA residual numbers are never assigned as model confidence or score."""
        mock_output = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "authentic",
            "score": None,
            "score_semantics": "not_applicable_qualitative_heuristic",
            "interpretation": "Checked."
        }

        buf = io.BytesIO()
        Image.new("RGB", (32, 32), color="red").save(buf, format="PNG")

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_output)):
            files = {"file": ("red.png", buf.getvalue(), "image/png")}
            response = client.post("/api/v1/analyze/image", files=files)

            assert response.status_code == 200
            data = response.json()

            # Ensure ai_detection score is untouched
            assert data["ai_detection"]["score"] is None
            assert data["ai_detection"]["score_semantics"] == "not_applicable_qualitative_heuristic"

            # Ensure residual statistics remain in spatial_anomaly_map only
            assert "mean_residual" in data["spatial_anomaly_map"]["residual_statistics"]

    def test_downsampled_visualization_dimensions(self):
        """Verify that large images have input vs visualization dimensions accurately tracked."""
        service = AnalysisService()

        # Create 1600x800 image
        img = Image.new("RGB", (1600, 800), color="yellow")
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        img_bytes = buf.getvalue()

        # Mock adapter
        service.model_adapter.predict = lambda _: {
            "status": "completed",
            "label": "authentic",
            "score": None,
            "interpretation": "Clean."
        }

        response = service.analyze_image("large.jpg", img, image_bytes=img_bytes)

        spatial = response.spatial_anomaly_map
        assert spatial is not None
        assert spatial.input_width == 1600
        assert spatial.input_height == 800
        assert spatial.visualization_width == 1280
        assert spatial.visualization_height == 640
        assert spatial.is_downsampled is True
        assert any("downsampled" in m.lower() for m in spatial.noteworthy_markers)

    def test_null_forensics_backward_compatibility(self):
        """Verify that AnalysisResponse models without forensics fields validate cleanly."""
        service = AnalysisService()
        raw_detection = {
            "status": "completed",
            "label": "authentic",
            "score": None,
            "interpretation": "Ok"
        }
        raw_provenance = {"status": "not_requested", "checks": []}

        # Compose with forensics omitted
        response = service._compose_response(
            filename="test.png",
            detection_raw=raw_detection,
            provenance_raw=raw_provenance,
            metadata_raw=None,
            ela_raw=None
        )

        assert response.metadata_forensics is None
        assert response.spatial_anomaly_map is None
        assert response.status == "completed"
        # Verify JSON serialization works without error
        dumped = response.model_dump()
        assert dumped["metadata_forensics"] is None
        assert dumped["spatial_anomaly_map"] is None
