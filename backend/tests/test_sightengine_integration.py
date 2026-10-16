"""Test suite for Sightengine external AI-generation and deepfake detection integration.

Tests cover:
1. Valid GenAI response with overall score.
2. Generator-specific fields when documented and present.
3. Missing generator-specific fields (graceful fallback).
4. Valid deepfake response.
5. Deepfake not configured.
6. Deepfake disabled.
7. Provider timeout on single and combined requests.
8. Provider HTTP / API error sanitization (no secret leakage).
9. Malformed provider response / non-JSON / missing score fields.
10. Independent GenAI and Deepfake results (one failing does not fail the other).
11. Single network call when both models enabled (models="genai,deepfake").
12. Evidence generation from real analysis outputs distinguishing observation, interpretation, limitation, status.
13. No fabricated evidence when detector is unavailable.
14. No change to primary verdict logic.
15. End-to-end API response contract compatibility.
16. Mocked external calls (no billable requests or live credentials required).
"""
import io
from unittest.mock import patch, MagicMock, AsyncMock
import httpx
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from app.main import app
from app.adapters.sightengine_adapter import SightengineAdapter
from app.adapters.azure_vision_adapter import AzureVisionAdapter
from app.composer.result_composer import ResultComposer
from app.schemas.analysis import (
    AIDetectionResult,
    ProvenanceResult,
    MetadataForensicsResult,
    SpatialAnomalyMap,
    ExternalAIDetectionResult,
)


@pytest.fixture
def client():
    return TestClient(app)


def _create_test_image_bytes() -> bytes:
    img = Image.new("RGB", (32, 32), color="red")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


class TestSightengineAdapter:
    """Unit tests for SightengineAdapter logic, model selection, parsing, and error sanitization."""

    def test_missing_credentials_returns_not_configured_safely(self):
        """Missing credentials returns not_configured state without raising exception."""
        adapter = SightengineAdapter(api_user="", api_secret="", enabled=True)
        assert not adapter.is_configured

        res_genai, res_df = adapter.detect_all(_create_test_image_bytes(), "test.jpg")
        assert res_genai["status"] == "not_configured"
        assert res_df["status"] == "not_configured"
        assert res_genai["score"] is None
        assert res_df["score"] is None
        assert "not configured" in res_genai["interpretation"].lower()
        assert "not configured" in res_df["interpretation"].lower()

    @pytest.mark.asyncio
    async def test_missing_credentials_async(self):
        """Async missing credentials returns not_configured state safely without network call."""
        adapter = SightengineAdapter(api_user="", api_secret="", enabled=True)
        res_genai, res_df = await adapter.detect_all_async(_create_test_image_bytes(), "test.jpg")
        assert res_genai["status"] == "not_configured"
        assert res_df["status"] == "not_configured"

    def test_disabled_master_toggle(self):
        """When SIGHTENGINE_ENABLED is False, adapter reports not_configured."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=False)
        assert not adapter.is_configured
        res = adapter.detect_genai(_create_test_image_bytes(), "test.jpg")
        assert res["status"] == "not_configured"

    def test_deepfake_disabled_by_default(self):
        """When deepfake_enabled is False, deepfake result has status='disabled' without network call."""
        adapter = SightengineAdapter(
            api_user="usr",
            api_secret="sec",
            enabled=True,
            genai_enabled=True,
            deepfake_enabled=False,
        )
        assert adapter.is_genai_enabled
        assert not adapter.is_deepfake_enabled

        mock_payload = {
            "status": "success",
            "type": {"ai_generated": 0.95},
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "test.jpg")

            # Only genai requested
            assert mock_post.called
            data_sent = mock_post.call_args[1]["data"]
            assert data_sent["models"] == "genai"

            assert genai_res["status"] == "completed"
            assert genai_res["score"] == 0.95
            assert df_res["status"] == "disabled"
            assert df_res["score"] is None
            assert "disabled" in df_res["interpretation"].lower()

    def test_single_network_call_when_both_enabled(self):
        """When both genai and deepfake are enabled, exactly 1 request with models='genai,deepfake' is made."""
        adapter = SightengineAdapter(
            api_user="usr",
            api_secret="sec",
            enabled=True,
            genai_enabled=True,
            deepfake_enabled=True,
        )
        assert adapter.is_genai_enabled
        assert adapter.is_deepfake_enabled

        mock_payload = {
            "status": "success",
            "type": {
                "ai_generated": 0.88,
                "deepfake": 0.03,
                "ai_generators": {"midjourney": 0.85, "flux": 0.02}
            }
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp) as mock_post:
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "test.jpg")

            assert mock_post.call_count == 1
            data_sent = mock_post.call_args[1]["data"]
            assert data_sent["models"] == "genai,deepfake"

            # Both parsed correctly from single payload
            assert genai_res["status"] == "completed"
            assert genai_res["score"] == 0.88
            assert genai_res["generator_scores"]["midjourney"] == 0.85

            assert df_res["status"] == "completed"
            assert df_res["score"] == 0.03
            assert df_res["label"] == "low_probability_deepfake"

    def test_genai_generator_specific_fields_parsed_when_present(self):
        """Documented type.ai_generators dictionary is extracted into generator_scores."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, deepfake_enabled=False)
        mock_payload = {
            "status": "success",
            "type": {
                "ai_generated": 0.985,
                "ai_generators": {
                    "stable_diffusion": 0.92,
                    "midjourney": 0.04,
                    "flux": 0.01,
                    "other": 0.01,
                }
            }
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            res = adapter.detect_genai(_create_test_image_bytes(), "test.jpg")
            assert res["status"] == "completed"
            assert res["score"] == 0.985
            assert res["generator_scores"] is not None
            assert res["generator_scores"]["stable_diffusion"] == 0.92
            assert res["generator_scores"]["midjourney"] == 0.04

    def test_genai_missing_generator_specific_fields_graceful_fallback(self):
        """When type.ai_generators is omitted by upstream, generator_scores is None without error."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, deepfake_enabled=False)
        mock_payload = {
            "status": "success",
            "type": {"ai_generated": 0.12}
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            res = adapter.detect_genai(_create_test_image_bytes(), "photo.jpg")
            assert res["status"] == "completed"
            assert res["score"] == 0.12
            assert res["generator_scores"] is None
            assert res["label"] == "low_probability_ai_generated"

    def test_deepfake_valid_high_score_response(self):
        """Deepfake score >= 0.80 maps to likely_deepfake."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, genai_enabled=False, deepfake_enabled=True)
        mock_payload = {
            "status": "success",
            "type": {"deepfake": 0.875}
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            res = adapter.detect_deepfake(_create_test_image_bytes(), "face.jpg")
            assert res["status"] == "completed"
            assert res["label"] == "likely_deepfake"
            assert res["score"] == 0.875
            assert res["score_semantics"] == "deepfake_face_manipulation_probability"
            assert "0.88" in res["interpretation"] or "0.87" in res["interpretation"]

    def test_deepfake_valid_low_score_response(self):
        """Deepfake score <= 0.15 maps to low_probability_deepfake."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, genai_enabled=False, deepfake_enabled=True)
        mock_payload = {
            "status": "success",
            "type": {"deepfake": 0.02}
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            res = adapter.detect_deepfake(_create_test_image_bytes(), "face.jpg")
            assert res["status"] == "completed"
            assert res["label"] == "low_probability_deepfake"
            assert res["score"] == 0.02

    def test_deepfake_missing_score_field_fails_safely(self):
        """When response succeeds but type.deepfake is missing, returns status='failed' without crash."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, genai_enabled=False, deepfake_enabled=True)
        mock_payload = {
            "status": "success",
            "type": {"ai_generated": 0.99}  # Missing deepfake field
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            res = adapter.detect_deepfake(_create_test_image_bytes(), "face.jpg")
            assert res["status"] == "failed"
            assert res["score"] is None
            assert "expected 'type.deepfake'" in res["interpretation"]

    def test_independent_results_when_one_field_missing(self):
        """In a combined response, if deepfake is present but genai is malformed, genai fails while deepfake succeeds."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, genai_enabled=True, deepfake_enabled=True)
        mock_payload = {
            "status": "success",
            "type": {
                # ai_generated is missing!
                "deepfake": 0.91
            }
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 200
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "face.jpg")
            assert genai_res["status"] == "failed"
            assert df_res["status"] == "completed"
            assert df_res["score"] == 0.91

    def test_upstream_authentication_error_sanitizes_secret(self):
        """Upstream credentials rejection never echoes the API secret in error messages."""
        adapter = SightengineAdapter(api_user="bad", api_secret="MY_SUPER_SECRET_TOKEN", enabled=True, deepfake_enabled=True)
        mock_payload = {
            "status": "failure",
            "error": {"type": "credentials_error", "code": 1, "message": "Invalid secret: MY_SUPER_SECRET_TOKEN"}
        }
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 401
        mock_resp.json.return_value = mock_payload

        with patch("httpx.Client.post", return_value=mock_resp):
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "test.jpg")
            for r in (genai_res, df_res):
                assert r["status"] == "failed"
                assert "MY_SUPER_SECRET_TOKEN" not in r["error"]
                assert "MY_SUPER_SECRET_TOKEN" not in r["interpretation"]
                assert "authentication failed" in r["error"].lower()

    def test_network_timeout_handled_safely(self):
        """Network timeout returns failed status with safe explanation."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, deepfake_enabled=True, timeout_seconds=5.0)

        with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Timed out")):
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "test.jpg")
            assert genai_res["status"] == "failed"
            assert df_res["status"] == "failed"
            assert "timed out" in genai_res["error"].lower()
            assert "timed out" in df_res["error"].lower()

    def test_malformed_json_response_handled_safely(self):
        """HTML error page or malformed JSON from gateway returns failed status cleanly."""
        adapter = SightengineAdapter(api_user="usr", api_secret="sec", enabled=True, deepfake_enabled=True)
        mock_resp = MagicMock(spec=httpx.Response)
        mock_resp.status_code = 502
        mock_resp.json.side_effect = ValueError("Bad Gateway")

        with patch("httpx.Client.post", return_value=mock_resp):
            genai_res, df_res = adapter.detect_all(_create_test_image_bytes(), "test.jpg")
            assert genai_res["status"] == "failed"
            assert df_res["status"] == "failed"
            assert "malformed" in genai_res["interpretation"].lower()


class TestStructuredEvidencePresentation:
    """Unit tests for ResultComposer.build_evidence_items."""

    def test_build_evidence_items_distinguishes_facets(self):
        """Each EvidenceItem clearly distinguishes observation, interpretation, limitation, and status."""
        ai_det = AIDetectionResult(
            status="completed",
            model_id="gpt-4.1-mini",
            label="authentic",
            score=None,
            score_semantics="not_applicable_qualitative_heuristic",
            interpretation="Visual rendering coherence appears natural."
        )
        prov = ProvenanceResult(status="not_requested", checks=[])
        meta = MetadataForensicsResult(
            status="completed",
            has_exif=True,
            camera_make="Canon",
            camera_model="EOS R5",
            software="Lightroom",
            identifiable_fields=["Make", "Model", "Software"],
            disclaimer="Metadata disclaimer",
        )
        ela = SpatialAnomalyMap(
            status="completed",
            residual_statistics={"mean_residual": 3.42, "max_residual": 42.1, "rms_residual": 5.12},
            disclaimer="ELA disclaimer",
        )
        ext_ai = ExternalAIDetectionResult(
            provider="Sightengine",
            task="ai_generated_image_detection",
            status="completed",
            score=0.924,
            generator_scores={"midjourney": 0.88, "flux": 0.04},
            interpretation="Elevated AI-generation probability.",
        )
        ext_df = ExternalAIDetectionResult(
            provider="Sightengine",
            task="deepfake_face_manipulation_detection",
            status="completed",
            score=0.041,
            interpretation="Low deepfake face manipulation probability.",
        )

        items = ResultComposer.build_evidence_items(
            ai_detection=ai_det,
            provenance=prov,
            metadata_forensics=meta,
            spatial_anomaly_map=ela,
            external_ai_detection=ext_ai,
            deepfake_detection=ext_df,
        )

        categories = {item.category: item for item in items}
        assert "visual_assessment" in categories
        assert "ai_generation" in categories
        assert "deepfake" in categories
        assert "metadata" in categories
        assert "compression_analysis" in categories
        assert "provenance" in categories

        # Check GenAI exhibit
        gen_item = categories["ai_generation"]
        assert gen_item.status == "completed"
        assert "0.9240" in gen_item.observation or "92.4%" in gen_item.observation
        assert "midjourney" in gen_item.observation.lower()
        assert "not proof" in gen_item.limitation.lower()

        # Check Deepfake exhibit
        df_item = categories["deepfake"]
        assert df_item.status == "completed"
        assert "0.0410" in df_item.observation or "4.1%" in df_item.observation
        assert "prominent faces" in df_item.limitation.lower()

        # Check Metadata exhibit
        meta_item = categories["metadata"]
        assert "Canon EOS R5" in meta_item.observation
        assert "Lightroom" in meta_item.observation
        assert "stripped" in meta_item.limitation.lower()

        # Check Compression exhibit
        ela_item = categories["compression_analysis"]
        assert "mean=3.42" in ela_item.observation
        assert "not proof of manipulation" in ela_item.limitation.lower()

    def test_no_fabricated_evidence_when_detectors_unavailable(self):
        """When detectors are unavailable/disabled, observations state so explicitly without fictional scores."""
        ai_det = AIDetectionResult(
            status="completed",
            model_id="gpt-4.1-mini",
            label="authentic",
            score=None,
            score_semantics="not_applicable_qualitative_heuristic",
            interpretation="Visual rendering coherence appears natural."
        )
        prov = ProvenanceResult(status="not_requested", checks=[])
        ext_ai = ExternalAIDetectionResult(
            provider="Sightengine",
            task="ai_generated_image_detection",
            status="not_configured",
            score=None,
            interpretation="External AI-generation detection is not configured.",
        )
        ext_df = ExternalAIDetectionResult(
            provider="Sightengine",
            task="deepfake_face_manipulation_detection",
            status="disabled",
            score=None,
            interpretation="Deepfake detection is disabled.",
        )

        items = ResultComposer.build_evidence_items(
            ai_detection=ai_det,
            provenance=prov,
            external_ai_detection=ext_ai,
            deepfake_detection=ext_df,
        )

        categories = {item.category: item for item in items}
        assert categories["ai_generation"].status == "not_configured"
        assert categories["ai_generation"].details["score"] is None
        assert "not configured" in categories["ai_generation"].observation.lower()

        assert categories["deepfake"].status == "disabled"
        assert categories["deepfake"].details["score"] is None
        assert "disabled" in categories["deepfake"].observation.lower()

    def test_verdict_logic_remains_unchanged(self):
        """Primary alert logic depends only on ai_detection and provenance, unaltered by external detector presence."""
        ai_res_real = {"status": "completed", "label": "authentic"}
        ai_res_fake = {"status": "completed", "label": "potential_manipulation"}
        prov_valid = {"status": "verified"}
        prov_tampered = {"status": "invalid"}

        alert_real = ResultComposer.compose_alert(ai_res_real, prov_valid)
        assert alert_real.level == "info"

        alert_fake = ResultComposer.compose_alert(ai_res_fake, prov_valid)
        assert alert_fake.level == "caution"

        alert_tampered = ResultComposer.compose_alert(ai_res_real, prov_tampered)
        assert alert_tampered.level == "caution"


class TestSightengineAPIIntegration:
    """End-to-end integration tests verifying HTTP endpoint responses and schema compatibility."""

    def test_end_to_end_analysis_response_schema_compatibility(self, client):
        """POST /api/v1/analyze/image returns external_ai_detection, deepfake_detection, and evidence_items."""
        mock_azure = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "authentic",
            "score": None,
            "score_semantics": "not_applicable_qualitative_heuristic",
            "interpretation": "Visual features appear coherent.",
            "limitations": ["Visual assessment is heuristic."]
        }
        mock_genai = {
            "provider": "Sightengine",
            "task": "ai_generated_image_detection",
            "status": "completed",
            "label": "likely_ai_generated",
            "score": 0.9415,
            "score_semantics": "ai_generated_probability",
            "generator_scores": {"midjourney": 0.91, "flux": 0.03},
            "interpretation": "High probability of AI generation (0.94).",
            "error": None,
        }
        mock_deepfake = {
            "provider": "Sightengine",
            "task": "deepfake_face_manipulation_detection",
            "status": "completed",
            "label": "low_probability_deepfake",
            "score": 0.0512,
            "score_semantics": "deepfake_face_manipulation_probability",
            "generator_scores": None,
            "interpretation": "Low deepfake face manipulation probability (0.05).",
            "error": None,
        }

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_azure)):
            with patch.object(
                SightengineAdapter,
                "detect_all_async",
                new=AsyncMock(return_value=(mock_genai, mock_deepfake))
            ):
                files = {"file": ("test_art.jpg", _create_test_image_bytes(), "image/jpeg")}
                response = client.post("/api/v1/analyze/image", files=files)

                assert response.status_code == 200
                data = response.json()

                # Core response structure preserved
                assert data["status"] == "completed"
                assert "analysis_id" in data
                assert data["ai_detection"]["model_id"] == "gpt-4.1-mini"

                # External AI GenAI detection field populated with generator_scores
                ext_ai = data.get("external_ai_detection")
                assert ext_ai is not None
                assert ext_ai["provider"] == "Sightengine"
                assert ext_ai["status"] == "completed"
                assert ext_ai["score"] == 0.9415
                assert ext_ai["generator_scores"]["midjourney"] == 0.91

                # Deepfake detection field populated independently
                df = data.get("deepfake_detection")
                assert df is not None
                assert df["task"] == "deepfake_face_manipulation_detection"
                assert df["status"] == "completed"
                assert df["score"] == 0.0512
                assert df["label"] == "low_probability_deepfake"

                # Structured evidence items present
                ev_items = data.get("evidence_items")
                assert ev_items is not None
                assert len(ev_items) >= 4
                categories = [item["category"] for item in ev_items]
                assert "ai_generation" in categories
                assert "deepfake" in categories
                assert "metadata" in categories

                for item in ev_items:
                    assert "observation" in item and item["observation"]
                    assert "interpretation" in item and item["interpretation"]
                    assert "limitation" in item and item["limitation"]
                    assert "status" in item and item["status"]

                # Sightengine limitations merged safely
                assert any("Sightengine" in lim for lim in data["limitations"])

    def test_end_to_end_analysis_when_deepfake_disabled(self, client):
        """When deepfake is disabled, deepfake_detection returns disabled status without pipeline failure."""
        mock_azure = {
            "status": "completed",
            "model_id": "gpt-4.1-mini",
            "label": "authentic",
            "score": None,
            "score_semantics": "not_applicable_qualitative_heuristic",
            "interpretation": "Visual features appear coherent.",
            "limitations": ["Visual assessment is heuristic."]
        }
        mock_genai = {
            "provider": "Sightengine",
            "task": "ai_generated_image_detection",
            "status": "completed",
            "label": "low_probability_ai_generated",
            "score": 0.02,
            "score_semantics": "ai_generated_probability",
            "generator_scores": None,
            "interpretation": "Low AI probability.",
            "error": None,
        }
        mock_deepfake_disabled = {
            "provider": "Sightengine",
            "task": "deepfake_face_manipulation_detection",
            "status": "disabled",
            "label": None,
            "score": None,
            "score_semantics": "deepfake_face_manipulation_probability",
            "generator_scores": None,
            "interpretation": "Sightengine deepfake detection is disabled.",
            "error": None,
        }

        with patch.object(AzureVisionAdapter, "predict_async", new=AsyncMock(return_value=mock_azure)):
            with patch.object(
                SightengineAdapter,
                "detect_all_async",
                new=AsyncMock(return_value=(mock_genai, mock_deepfake_disabled))
            ):
                files = {"file": ("df_disabled.jpg", _create_test_image_bytes(), "image/jpeg")}
                response = client.post("/api/v1/analyze/image", files=files)

                assert response.status_code == 200
                data = response.json()
                assert data["status"] == "completed"
                assert data["deepfake_detection"]["status"] == "disabled"
                assert data["deepfake_detection"]["score"] is None
