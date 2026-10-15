"""Automated tests for Azure Vision Model Adapter and Integration.

Covers:
1. Correct construction of the Azure request.
2. Correct image encoding and transmission.
3. Successful parsing of a valid model response.
4. Mapping into the existing response schema.
5. Missing configuration.
6. Authentication failure.
7. Rate limiting and service errors.
8. Network timeouts.
9. Malformed model output.
10. Preservation of the existing API contract.
11. Confirmation that secrets are not included in error responses.

All tests use mocked HTTP interactions and do not require live credentials.
"""
import io
import json
from unittest.mock import patch, MagicMock, AsyncMock
import pytest
from PIL import Image
import httpx

from app.adapters.azure_vision_adapter import AzureVisionAdapter
from app.adapters.exceptions import (
    ModelUnavailableException,
    ModelAuthenticationException,
    ModelRateLimitException,
    ModelNetworkException,
    ModelInferenceException,
)
from app.services.analysis_service import AnalysisService
from app.schemas.analysis import AnalysisResponse


@pytest.fixture
def sample_image():
    """Generates a small in-memory test image."""
    img = Image.new("RGB", (100, 100), color="blue")
    return img


@pytest.fixture
def sample_azure_adapter():
    """Provides an AzureVisionAdapter configured with mock test credentials."""
    return AzureVisionAdapter(
        endpoint="https://test-resource.openai.azure.com/",
        api_key="mock-secret-key-12345",
        deployment_name="gpt-4o-test",
        api_version="2024-08-01-preview",
        timeout_seconds=5.0,
    )


def test_azure_request_construction_openai_endpoint(sample_azure_adapter):
    """Test 1: Correct construction of Azure OpenAI request URL, headers, and payload."""
    url = sample_azure_adapter.build_url()
    assert url == (
        "https://test-resource.openai.azure.com/openai/deployments/gpt-4o-test"
        "/chat/completions?api-version=2024-08-01-preview"
    )

    headers = sample_azure_adapter.build_headers()
    assert headers["Content-Type"] == "application/json"
    assert headers["api-key"] == "mock-secret-key-12345"

    payload = sample_azure_adapter.build_payload("data:image/jpeg;base64,mockdata")
    assert payload["model"] == "gpt-4o-test"
    assert payload["response_format"] == {"type": "json_object"}
    assert len(payload["messages"]) == 2
    assert payload["messages"][0]["role"] == "system"
    assert payload["messages"][1]["role"] == "user"


def test_azure_request_construction_serverless_endpoint():
    """Test 1b: Correct construction of Azure AI Foundry Serverless/MaaS request URL."""
    adapter = AzureVisionAdapter(
        endpoint="https://test-resource.services.ai.azure.com/models",
        api_key="mock-key",
        deployment_name="Phi-3.5-vision-instruct",
    )
    url = adapter.build_url()
    assert url == "https://test-resource.services.ai.azure.com/models/chat/completions"


def test_azure_request_construction_cognitiveservices_endpoint():
    """Test 1c: Correct construction of Cognitive Services multi-service endpoint."""
    adapter = AzureVisionAdapter(
        endpoint="https://test-cs.cognitiveservices.azure.com/",
        api_key="mock-key",
        deployment_name="custom-vision-deploy",
        api_version="2024-10-21",
    )
    url = adapter.build_url()
    assert url == (
        "https://test-cs.cognitiveservices.azure.com/openai/deployments/custom-vision-deploy"
        "/chat/completions?api-version=2024-10-21"
    )


def test_azure_request_construction_prerouted_endpoint():
    """Test 1d: Correct construction when endpoint already includes deployment path."""
    adapter = AzureVisionAdapter(
        endpoint="https://test.openai.azure.com/openai/deployments/my-gpt4o",
        api_key="mock-key",
        deployment_name="my-gpt4o",
        api_version="2024-08-01-preview",
    )
    url = adapter.build_url()
    assert url == "https://test.openai.azure.com/openai/deployments/my-gpt4o/chat/completions?api-version=2024-08-01-preview"


def test_image_encoding_and_transmission(sample_azure_adapter, sample_image):
    """Test 2: Correct image encoding as base64 data URI and dimension handling."""
    data_uri = sample_azure_adapter.encode_image(sample_image)
    assert data_uri.startswith("data:image/jpeg;base64,")

    # Test resizing for oversized image
    large_img = Image.new("RGB", (3000, 1500), color="green")
    large_uri = sample_azure_adapter.encode_image(large_img)
    assert large_uri.startswith("data:image/jpeg;base64,")


def test_successful_parsing_and_schema_mapping(sample_azure_adapter):
    """Test 3 & 4: Successful parsing of valid response and mapping to response structure."""
    mock_model_json = {
        "directly_observable_characteristics": "Studio portrait with high-contrast lighting.",
        "visual_inconsistencies": [
            "Inconsistent specular reflection in the left pupil compared to right.",
            "Unnatural blending around hair strands on upper right boundary."
        ],
        "alternative_explanations": "Could be caused by multiple practical studio lights.",
        "classification_label": "potential_manipulation",
        "reasoning_summary": "Visual analysis identified reflection anomalies and boundary blending.",
        "limitations": [
            "Visual assessment is heuristic and cannot provide definitive proof."
        ],
        "recommendations": "Verify camera metadata and original source."
    }

    mock_azure_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(mock_model_json)
                }
            }
        ]
    }

    result = sample_azure_adapter.parse_model_response(mock_azure_resp)

    assert result["status"] == "completed"
    assert result["model_id"] == "gpt-4o-test"
    assert result["label"] == "potential_manipulation"
    assert result["score"] is None
    assert result["score_semantics"] == "not_applicable_qualitative_heuristic"
    assert "reflection anomalies" in result["interpretation"]
    assert len(result["observations"]["inconsistencies"]) == 2


def test_missing_configuration():
    """Test 5: Unconfigured adapter raises ModelUnavailableException."""
    unconfigured_adapter = AzureVisionAdapter(endpoint="", api_key="", deployment_name="")
    assert not unconfigured_adapter.is_configured

    sample_img = Image.new("RGB", (10, 10))
    with pytest.raises(ModelUnavailableException):
        unconfigured_adapter.predict(sample_img)


@patch("httpx.Client.post")
def test_authentication_failure(mock_post, sample_azure_adapter, sample_image):
    """Test 6 & 11: 401/403 raises ModelAuthenticationException without leaking secrets."""
    mock_post.return_value = httpx.Response(
        status_code=401,
        text="Access denied due to invalid subscription key or unauthorized endpoint."
    )

    with pytest.raises(ModelAuthenticationException) as exc_info:
        sample_azure_adapter.predict(sample_image)

    # Ensure secret API key is NOT leaked in exception text
    assert "mock-secret-key-12345" not in str(exc_info.value)
    assert "401" in str(exc_info.value)


@patch("httpx.Client.post")
def test_rate_limiting_and_service_errors(mock_post, sample_azure_adapter, sample_image):
    """Test 7: HTTP 429 raises ModelRateLimitException and 500 raises ModelInferenceException."""
    # Test 429 Rate Limit
    mock_post.return_value = httpx.Response(status_code=429, text="Rate limit exceeded.")
    with pytest.raises(ModelRateLimitException):
        sample_azure_adapter.predict(sample_image)

    # Test 503 Service Unavailable
    mock_post.return_value = httpx.Response(status_code=503, text="Azure service unavailable.")
    with pytest.raises(ModelInferenceException):
        sample_azure_adapter.predict(sample_image)


@patch("httpx.Client.post")
def test_network_timeout(mock_post, sample_azure_adapter, sample_image):
    """Test 8: Network timeout raises ModelNetworkException."""
    mock_post.side_effect = httpx.TimeoutException("Connection timed out after 5.0s")

    with pytest.raises(ModelNetworkException) as exc_info:
        sample_azure_adapter.predict(sample_image)

    assert "Timeout" in str(exc_info.value)


def test_malformed_model_output(sample_azure_adapter):
    """Test 9: Malformed JSON output raises ModelInferenceException without fallback mock."""
    malformed_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is plain text and not valid JSON at all."
                }
            }
        ]
    }

    with pytest.raises(ModelInferenceException):
        sample_azure_adapter.parse_model_response(malformed_resp)


def test_api_endpoint_integration_with_mocked_azure(client):
    """Test 10 & 11: End-to-end API execution through POST /api/v1/analyze/image with mocked Azure."""
    mock_model_json = {
        "directly_observable_characteristics": "Photograph of a city square.",
        "visual_inconsistencies": [],
        "alternative_explanations": "Standard daytime lighting.",
        "classification_label": "authentic",
        "reasoning_summary": "No strong signs of visual manipulation detected.",
        "limitations": [
            "Visual inspection is heuristic and cannot establish absolute authenticity."
        ],
        "recommendations": "Verify camera EXIF if necessary."
    }

    mock_azure_resp = {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": json.dumps(mock_model_json)
                }
            }
        ]
    }

    mock_adapter = AzureVisionAdapter(
        endpoint="https://test.openai.azure.com/",
        api_key="test-key-safe",
        deployment_name="gpt-4o",
    )

    # Mock predict_async to return structured parsed output
    with patch.object(
        AzureVisionAdapter,
        "predict_async",
        new=AsyncMock(return_value=mock_adapter.parse_model_response(mock_azure_resp))
    ):
        # Create a small valid test image in memory
        buf = io.BytesIO()
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(buf, format="PNG")
        buf.seek(0)

        files = {"file": ("test_city.png", buf.getvalue(), "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)

        assert response.status_code == 200
        data = response.json()

        # Validate against API_SPEC.md requirements
        assert "analysis_id" in data
        assert data["status"] == "completed"
        assert data["media"]["filename"] == "test_city.png"
        assert data["ai_detection"]["status"] == "completed"
        assert data["ai_detection"]["label"] == "authentic"
        assert data["ai_detection"]["score"] is None
        assert data["ai_detection"]["score_semantics"] == "not_applicable_qualitative_heuristic"
        assert data["trace_alert"]["level"] == "info"
        assert "authenticity cannot be definitively established" in data["trace_alert"]["message"].lower()
        assert len(data["limitations"]) >= 3


def test_api_endpoint_auth_failure_does_not_leak_secrets(client):
    """Test 11: When Azure returns 401, API returns 503 and never leaks secret key to client."""
    with patch.object(
        AzureVisionAdapter,
        "predict_async",
        side_effect=ModelAuthenticationException("Authentication failed (HTTP 401)")
    ):
        buf = io.BytesIO()
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(buf, format="PNG")
        buf.seek(0)

        files = {"file": ("test_city.png", buf.getvalue(), "image/png")}
        response = client.post("/api/v1/analyze/image", files=files)

        assert response.status_code == 503
        data = response.json()
        assert data["error"]["code"] == "MODEL_UNAVAILABLE"
        # Confirm no internal keys or sensitive trace text
        assert "key" not in data["error"]["message"].lower()
