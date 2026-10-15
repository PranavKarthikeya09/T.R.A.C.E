"""Azure AI Foundry Vision Model Adapter.

Implements visual manipulation inspection using configurable Azure-hosted
vision models (such as GPT-4o, GPT-4o-mini, or Azure AI Foundry Vision deployments).
"""
import base64
import io
import json
import logging
import re
from typing import Any, Dict, Optional, Tuple
from PIL import Image
import httpx

from app.adapters.base import BaseInferenceAdapter
from app.adapters.exceptions import (
    ModelUnavailableException,
    ModelAuthenticationException,
    ModelRateLimitException,
    ModelNetworkException,
    ModelInferenceException,
)
from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are a cautious visual media analysis specialist for the T.R.A.C.E. verification system.
Your role is to inspect images for potential visual inconsistencies or signs of generative media synthesis, while communicating uncertainty clearly.

You must examine:
1. Directly observable image characteristics (subject, composition, lighting context).
2. Potential visual inconsistencies (inconsistent shadow angles, specular reflections in eyes/mirrors, perspective distortions, anatomical irregularities, unnatural skin/hair textures, boundary or blending halos).
3. Possible alternative explanations (lens distortions, heavy JPEG/social media compression, motion blur, unusual practical lighting).
4. Qualitative categorization.

IMPORTANT RULES:
- Never declare that an image is definitively authentic or definitively manipulated.
- If visual evidence is ambiguous, contradictory, or subtle, classify as "inconclusive".
- Do not invent non-existent defects.
- You must output valid JSON strictly matching the requested format.

Output JSON format:
{
  "directly_observable_characteristics": "<brief description of visible scene and subjects>",
  "visual_inconsistencies": ["<inconsistency 1>", "<inconsistency 2>"],
  "alternative_explanations": "<benign factors such as compression or lighting that could explain anomalies>",
  "classification_label": "potential_manipulation | authentic | inconclusive",
  "reasoning_summary": "<cautious 1-2 sentence explanation communicating uncertainty>",
  "limitations": [
    "Visual assessment by an AI vision model is heuristic and cannot provide definitive proof of authenticity or manipulation.",
    "Absence of obvious visual artifacts does not guarantee authenticity."
  ],
  "recommendations": "<suggested verification step, e.g. check source provenance or reverse search>"
}"""


class AzureVisionAdapter(BaseInferenceAdapter):
    """
    Adapter for Azure AI Foundry vision-capable deployments.
    Supports both Azure OpenAI and Azure AI Foundry Model Inference endpoints.
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout_seconds: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self._endpoint = endpoint.strip() if endpoint is not None else (settings.AZURE_AI_ENDPOINT or "").strip()
        self._api_key = api_key.strip() if api_key is not None else (settings.AZURE_AI_API_KEY or "").strip()
        self._deployment_name = deployment_name.strip() if deployment_name is not None else (settings.AZURE_AI_DEPLOYMENT_NAME or "").strip()
        self._api_version = api_version.strip() if api_version is not None else (settings.AZURE_AI_API_VERSION or "2024-08-01-preview").strip()
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.AZURE_AI_REQUEST_TIMEOUT_SECONDS
        self._max_retries = max_retries if max_retries is not None else settings.AZURE_AI_MAX_RETRIES

    @property
    def model_id(self) -> str:
        """Returns the configured deployment name or fallback identifier."""
        return self._deployment_name or "azure-vision-unconfigured"

    @property
    def is_configured(self) -> bool:
        """Check if required Azure configuration is present."""
        return bool(self._endpoint and self._api_key and self._deployment_name)

    def load(self) -> None:
        """Validate configuration readiness without testing network."""
        if not self.is_configured:
            logger.info("AzureVisionAdapter initialized without complete configuration.")
        else:
            logger.info("AzureVisionAdapter configured for deployment '%s'.", self._deployment_name)

    def build_url(self) -> str:
        """Construct the appropriate chat completions URL based on endpoint style."""
        if not self._endpoint:
            raise ModelUnavailableException("AZURE_AI_ENDPOINT is not configured.")

        endpoint = self._endpoint.rstrip("/")

        # Case 1: Full completions URL already provided
        if "/chat/completions" in endpoint:
            if "api-version" not in endpoint and self._api_version:
                delimiter = "&" if "?" in endpoint else "?"
                return f"{endpoint}{delimiter}api-version={self._api_version}"
            return endpoint

        # Case 2: Pre-routed deployment path (e.g., .../openai/deployments/{deployment})
        if "/openai/deployments/" in endpoint:
            endpoint = f"{endpoint}/chat/completions"
            if "api-version" not in endpoint and self._api_version:
                return f"{endpoint}?api-version={self._api_version}"
            return endpoint

        # Case 3: Azure OpenAI / Cognitive Services style endpoint (e.g., https://<resource>.openai.azure.com/ or .cognitiveservices.azure.com/)
        if ".openai.azure.com" in endpoint or ".cognitiveservices.azure.com" in endpoint:
            return (
                f"{endpoint}/openai/deployments/{self._deployment_name}"
                f"/chat/completions?api-version={self._api_version}"
            )

        # Case 4: Azure AI Foundry Model Inference / MaaS / Serverless
        # (e.g., https://<resource>.services.ai.azure.com/models or direct models endpoint)
        if "services.ai.azure.com" in endpoint or "models.ai.azure.com" in endpoint:
            if endpoint.endswith("/models"):
                return f"{endpoint}/chat/completions"
            return f"{endpoint}/chat/completions"

        # Case 5: Generic base URL
        return f"{endpoint}/chat/completions"

    def build_headers(self) -> Dict[str, str]:
        """Construct authentication and request headers without exposing secrets in logs."""
        if not self._api_key:
            raise ModelUnavailableException("AZURE_AI_API_KEY is not configured.")

        return {
            "Content-Type": "application/json",
            "api-key": self._api_key,
        }

    def encode_image(self, image: Image.Image) -> str:
        """
        Encode PIL image to base64 data URI.
        Resizes images exceeding 2048px on longest edge to optimize payload size.
        """
        img = image
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")

        # Cap max dimension at 2048 to prevent oversized payloads
        max_dim = 2048
        if max(img.size) > max_dim:
            img = img.copy()
            img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)

        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        b64_data = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return f"data:image/jpeg;base64,{b64_data}"

    def build_payload(self, image_data_uri: str) -> Dict[str, Any]:
        """Construct the chat completions payload with image and strict instructions."""
        payload: Dict[str, Any] = {
            "messages": [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Please perform a structured visual analysis of this image. "
                                "Identify any visual inconsistencies or potential indicators of manipulation, "
                                "consider alternative explanations, and provide a cautious qualitative categorization."
                            ),
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_uri,
                            },
                        },
                    ],
                },
            ],
            "max_tokens": 1000,
            "temperature": 0.1,  # Low temperature for stable, deterministic structured output
        }

        # Include model name in payload for OpenAI/Serverless-compatible endpoints
        if self._deployment_name:
            payload["model"] = self._deployment_name

        # If Azure deployment supports JSON response_format
        payload["response_format"] = {"type": "json_object"}

        return payload

    def parse_model_response(self, response_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract, parse, and validate structured findings from the model response.
        Handles optional markdown formatting and normalizes output labels.
        """
        try:
            choices = response_json.get("choices", [])
            if not choices:
                raise ModelInferenceException("Azure model returned response with no choices.")

            message = choices[0].get("message", {})
            content = message.get("content", "")

            if not content:
                raise ModelInferenceException("Azure model returned empty content.")

            # Clean markdown code block fences if present
            cleaned_content = content.strip()
            if cleaned_content.startswith("```"):
                cleaned_content = re.sub(r"^```(?:json)?\n?", "", cleaned_content, flags=re.IGNORECASE)
                cleaned_content = re.sub(r"\n?```$", "", cleaned_content)

            parsed = json.loads(cleaned_content)
        except json.JSONDecodeError as jde:
            logger.error("Failed to parse JSON from Azure response: %s", str(jde))
            raise ModelInferenceException("Model output was not valid JSON.") from jde

        if not isinstance(parsed, dict):
            raise ModelInferenceException("Model output was not a JSON object.")

        raw_label = str(parsed.get("classification_label", "")).strip().lower()
        if "manipulat" in raw_label or "fake" in raw_label or "synthetic" in raw_label:
            normalized_label = "potential_manipulation"
        elif "authentic" in raw_label or "real" in raw_label:
            normalized_label = "authentic"
        else:
            normalized_label = "inconclusive"

        reasoning = (
            parsed.get("reasoning_summary")
            or "Visual analysis completed. Observations indicate uncertainty; verify source evidence."
        )

        inconsistencies = parsed.get("visual_inconsistencies") or []
        if not isinstance(inconsistencies, list):
            inconsistencies = [str(inconsistencies)]

        limitations = parsed.get("limitations") or [
            "Visual assessment by an AI vision model is heuristic and cannot provide definitive proof.",
            "Absence of obvious visual artifacts does not guarantee authenticity.",
        ]
        if not isinstance(limitations, list):
            limitations = [str(limitations)]

        return {
            "status": "completed",
            "model_id": self.model_id,
            "label": normalized_label,
            "score": None,  # Vision models do not provide calibrated manipulation probabilities
            "score_semantics": "not_applicable_qualitative_heuristic",
            "interpretation": reasoning,
            "observations": {
                "characteristics": parsed.get("directly_observable_characteristics", "Not specified"),
                "inconsistencies": inconsistencies,
                "alternative_explanations": parsed.get("alternative_explanations", "None noted"),
                "recommendations": parsed.get("recommendations", "Verify source provenance."),
            },
            "limitations": limitations,
        }

    def _handle_http_error(self, status_code: int, response_text: str) -> None:
        """Map HTTP error status codes into domain exceptions without leaking credentials."""
        # Sanitize message to ensure API key is never reflected
        sanitized_msg = re.sub(r"([?&]api-key=)[^&]+", r"\1[REDACTED]", response_text)

        if status_code in (401, 403):
            raise ModelAuthenticationException(
                f"Authentication to Azure AI failed (HTTP {status_code}). Verify AZURE_AI_API_KEY."
            )
        elif status_code == 404:
            raise ModelUnavailableException(
                f"Azure AI deployment '{self._deployment_name}' or endpoint not found (HTTP 404)."
            )
        elif status_code == 429:
            raise ModelRateLimitException(
                "Azure AI rate limit exceeded or quota exhausted (HTTP 429)."
            )
        elif status_code >= 500:
            raise ModelInferenceException(
                f"Azure AI service encountered an error (HTTP {status_code})."
            )
        else:
            raise ModelInferenceException(
                f"Azure AI request failed with HTTP {status_code}: {sanitized_msg[:200]}"
            )

    def predict(self, image: Image.Image) -> Dict[str, Any]:
        """
        Synchronous prediction interface.
        Executes HTTP request to configured Azure AI vision model.
        """
        if not self.is_configured:
            raise ModelUnavailableException(
                "Azure AI Vision model is not configured. Please configure AZURE_AI_ENDPOINT, "
                "AZURE_AI_API_KEY, and AZURE_AI_DEPLOYMENT_NAME in your environment."
            )

        url = self.build_url()
        headers = self.build_headers()
        image_data_uri = self.encode_image(image)
        payload = self.build_payload(image_data_uri)

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as te:
            raise ModelNetworkException(
                f"Timeout after {self._timeout_seconds}s connecting to Azure AI inference endpoint."
            ) from te
        except httpx.RequestError as re_err:
            raise ModelNetworkException(
                f"Network transport error connecting to Azure AI endpoint: {type(re_err).__name__}"
            ) from re_err

        if response.status_code != 200:
            self._handle_http_error(response.status_code, response.text)

        try:
            resp_data = response.json()
        except Exception as je:
            raise ModelInferenceException("Failed to decode Azure HTTP response as JSON.") from je

        return self.parse_model_response(resp_data)

    async def predict_async(self, image: Image.Image) -> Dict[str, Any]:
        """
        Asynchronous prediction interface using httpx.AsyncClient.
        Prevents blocking FastAPI's event loop during remote inference.
        """
        if not self.is_configured:
            raise ModelUnavailableException(
                "Azure AI Vision model is not configured. Please configure AZURE_AI_ENDPOINT, "
                "AZURE_AI_API_KEY, and AZURE_AI_DEPLOYMENT_NAME in your environment."
            )

        url = self.build_url()
        headers = self.build_headers()
        image_data_uri = self.encode_image(image)
        payload = self.build_payload(image_data_uri)

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(url, headers=headers, json=payload)
        except httpx.TimeoutException as te:
            raise ModelNetworkException(
                f"Timeout after {self._timeout_seconds}s connecting to Azure AI inference endpoint."
            ) from te
        except httpx.RequestError as re_err:
            raise ModelNetworkException(
                f"Network transport error connecting to Azure AI endpoint: {type(re_err).__name__}"
            ) from re_err

        if response.status_code != 200:
            self._handle_http_error(response.status_code, response.text)

        try:
            resp_data = response.json()
        except Exception as je:
            raise ModelInferenceException("Failed to decode Azure HTTP response as JSON.") from je

        return self.parse_model_response(resp_data)
