"""Sightengine External AI and Deepfake Detection Adapter.

Integrates with Sightengine's check.json endpoint for:
1. AI-generated image detection (models=genai)
2. Deepfake face manipulation detection (models=deepfake)

Adheres strictly to security, timeout, error-handling, and scientific honesty boundaries.
Official documentation:
- GenAI: https://sightengine.com/docs/ai-generated-image-detection
- Deepfake: https://sightengine.com/docs/deepfake-detection
"""
import logging
from typing import Any, Dict, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SIGHTENGINE_API_URL = "https://api.sightengine.com/1.0/check.json"


class SightengineAdapter:
    """
    Adapter for Sightengine hosted AI-generated image and deepfake detection services.
    Handles multipart image submission, credentials management, response parsing,
    deduplicated upstream network requests, and safe failure states without leaking sensitive keys.
    """

    def __init__(
        self,
        api_user: Optional[str] = None,
        api_secret: Optional[str] = None,
        enabled: Optional[bool] = None,
        genai_enabled: Optional[bool] = None,
        deepfake_enabled: Optional[bool] = None,
        timeout_seconds: Optional[float] = None,
        api_url: str = SIGHTENGINE_API_URL,
    ):
        self._api_user = api_user.strip() if api_user is not None else (settings.SIGHTENGINE_API_USER or "").strip()
        self._api_secret = api_secret.strip() if api_secret is not None else (settings.SIGHTENGINE_API_SECRET or "").strip()
        self._enabled = enabled if enabled is not None else settings.SIGHTENGINE_ENABLED
        self._genai_enabled = genai_enabled if genai_enabled is not None else getattr(settings, "SIGHTENGINE_GENAI_ENABLED", True)
        self._deepfake_enabled = deepfake_enabled if deepfake_enabled is not None else getattr(settings, "SIGHTENGINE_DEEPFAKE_ENABLED", False)
        self._timeout_seconds = timeout_seconds if timeout_seconds is not None else settings.SIGHTENGINE_REQUEST_TIMEOUT_SECONDS
        self._api_url = api_url

    @property
    def is_configured(self) -> bool:
        """Check whether valid credentials and master feature toggle are active."""
        return bool(self._enabled and self._api_user and self._api_secret)

    @property
    def is_genai_enabled(self) -> bool:
        """Check whether GenAI detection is configured and enabled."""
        return bool(self.is_configured and self._genai_enabled)

    @property
    def is_deepfake_enabled(self) -> bool:
        """Check whether Deepfake detection is configured and enabled."""
        return bool(self.is_configured and self._deepfake_enabled)

    @property
    def provider_name(self) -> str:
        return "Sightengine"

    def _determine_content_type(self, filename: str) -> str:
        lower = filename.lower()
        if lower.endswith(".png"):
            return "image/png"
        elif lower.endswith(".webp"):
            return "image/webp"
        return "image/jpeg"

    def _unconfigured_genai_response(self) -> Dict[str, Any]:
        """Return safe, non-crashing response when GenAI credentials are not configured or disabled."""
        if not self.is_configured:
            status = "not_configured"
            interp = (
                "Sightengine external AI-generation detection is not configured. "
                "Configure SIGHTENGINE_API_USER and SIGHTENGINE_API_SECRET to enable external verification."
            )
        else:
            status = "disabled"
            interp = "Sightengine external AI-generation detection is disabled in configuration."

        return {
            "provider": self.provider_name,
            "task": "ai_generated_image_detection",
            "status": status,
            "label": None,
            "score": None,
            "score_semantics": "ai_generated_probability",
            "generator_scores": None,
            "interpretation": interp,
            "error": None,
        }

    def _unconfigured_deepfake_response(self) -> Dict[str, Any]:
        """Return safe, non-crashing response when deepfake credentials are not configured or disabled."""
        if not self.is_configured:
            status = "not_configured"
            interp = (
                "Sightengine deepfake detection is not configured. "
                "Configure SIGHTENGINE_API_USER and SIGHTENGINE_API_SECRET to enable external verification."
            )
        else:
            status = "disabled"
            interp = (
                "Sightengine deepfake detection is disabled. "
                "Enable SIGHTENGINE_DEEPFAKE_ENABLED in configuration to assess face manipulation."
            )

        return {
            "provider": self.provider_name,
            "task": "deepfake_face_manipulation_detection",
            "status": status,
            "label": None,
            "score": None,
            "score_semantics": "deepfake_face_manipulation_probability",
            "generator_scores": None,
            "interpretation": interp,
            "error": None,
        }

    def _sanitize_error_details(self, status_code: int, data: Dict[str, Any]) -> Tuple[str, str]:
        """
        Sanitize upstream error information so that sensitive API keys or internal tokens are never leaked.
        Returns (safe_error_message, user_interpretation).
        """
        err_obj = data.get("error", {})
        err_type = str(err_obj.get("type", "api_error")).lower()
        err_code = err_obj.get("code")

        logger.warning(
            "Sightengine reported error: type=%s, code=%s (status_code=%s)",
            err_type,
            err_code,
            status_code,
        )

        if "credential" in err_type or err_code == 1 or status_code in (401, 403):
            return (
                "Sightengine authentication failed. Check API user and secret configuration.",
                "Upstream provider authentication failed. External detection unavailable.",
            )
        elif "usage" in err_type or "plan" in err_type or status_code == 429:
            return (
                "Sightengine request quota or rate limit exceeded.",
                "Sightengine account quota reached or rate limited.",
            )
        elif status_code >= 500 or "api" in err_type:
            return (
                "Sightengine upstream service error.",
                "Sightengine internal service error encountered.",
            )
        else:
            return (
                f"Sightengine request rejected: {err_type}.",
                "External detection request was rejected by provider.",
            )

    def _parse_genai_from_payload(self, status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse AI-generated image detection result from provider payload."""
        upstream_status = data.get("status")

        if upstream_status == "failure" or status_code >= 400:
            safe_err, interp = self._sanitize_error_details(status_code, data)
            return {
                "provider": self.provider_name,
                "task": "ai_generated_image_detection",
                "status": "failed",
                "label": None,
                "score": None,
                "score_semantics": "ai_generated_probability",
                "generator_scores": None,
                "interpretation": interp,
                "error": safe_err,
            }

        type_obj = data.get("type", {})
        if not isinstance(type_obj, dict) or "ai_generated" not in type_obj:
            # Fallback check for alternative schema shapes
            genai_obj = data.get("genai", {})
            if isinstance(genai_obj, dict) and "is_ai" in genai_obj:
                raw_score = genai_obj["is_ai"]
            else:
                logger.warning("Sightengine response missing 'type.ai_generated': %s", list(data.keys()))
                return {
                    "provider": self.provider_name,
                    "task": "ai_generated_image_detection",
                    "status": "failed",
                    "label": None,
                    "score": None,
                    "score_semantics": "ai_generated_probability",
                    "generator_scores": None,
                    "interpretation": "Sightengine response was malformed (missing expected 'type.ai_generated' field).",
                    "error": "Unexpected upstream response structure.",
                }
        else:
            raw_score = type_obj["ai_generated"]

        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            return {
                "provider": self.provider_name,
                "task": "ai_generated_image_detection",
                "status": "failed",
                "label": None,
                "score": None,
                "score_semantics": "ai_generated_probability",
                "generator_scores": None,
                "interpretation": f"Invalid non-numeric score received: {raw_score}",
                "error": "Invalid score type in response.",
            }

        score = max(0.0, min(1.0, score))

        # Extract generator-specific scores if documented and present
        generator_scores: Optional[Dict[str, float]] = None
        raw_generators = type_obj.get("ai_generators") or data.get("genai", {}).get("details")
        if isinstance(raw_generators, dict) and raw_generators:
            parsed_gen: Dict[str, float] = {}
            for gen_name, gen_val in raw_generators.items():
                try:
                    gen_num = float(gen_val)
                    parsed_gen[str(gen_name)] = round(max(0.0, min(1.0, gen_num)), 4)
                except (ValueError, TypeError):
                    continue
            if parsed_gen:
                generator_scores = parsed_gen

        # Scientific classification and calibrated interpretation
        if score >= 0.85:
            label = "likely_ai_generated"
            interpretation = (
                f"Sightengine reported an AI-generation probability of {score:.2f} (85%+ threshold), "
                "indicating a high likelihood of generative model synthesis (e.g., Midjourney, Stable Diffusion, DALL-E, Flux). "
                "Note: Statistical synthesis detectors can occasionally flag complex digital illustrations or stylized renders."
            )
        elif score <= 0.15:
            label = "low_probability_ai_generated"
            interpretation = (
                f"Sightengine reported an AI-generation probability of {score:.2f} (below 15% threshold), "
                "indicating a low likelihood of full generative synthesis. "
                "Note: This evaluates generative model synthesis only; it does not confirm a real photograph has not been "
                "spliced, cloned, retouched, or digitally manipulated."
            )
        else:
            label = "inconclusive"
            interpretation = (
                f"Sightengine returned an intermediate AI-generation score of {score:.2f}. "
                "The detected features were ambiguous and do not support a decisive categorization between camera capture, "
                "heavy post-processing, and partial generative synthesis."
            )

        return {
            "provider": self.provider_name,
            "task": "ai_generated_image_detection",
            "status": "completed",
            "label": label,
            "score": round(score, 4),
            "score_semantics": "ai_generated_probability",
            "generator_scores": generator_scores,
            "interpretation": interpretation,
            "error": None,
        }

    def _parse_deepfake_from_payload(self, status_code: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse deepfake face manipulation detection result from provider payload."""
        upstream_status = data.get("status")

        if upstream_status == "failure" or status_code >= 400:
            safe_err, interp = self._sanitize_error_details(status_code, data)
            return {
                "provider": self.provider_name,
                "task": "deepfake_face_manipulation_detection",
                "status": "failed",
                "label": None,
                "score": None,
                "score_semantics": "deepfake_face_manipulation_probability",
                "generator_scores": None,
                "interpretation": interp,
                "error": safe_err,
            }

        type_obj = data.get("type", {})
        if not isinstance(type_obj, dict) or "deepfake" not in type_obj:
            logger.warning("Sightengine response missing 'type.deepfake': %s", list(data.keys()))
            return {
                "provider": self.provider_name,
                "task": "deepfake_face_manipulation_detection",
                "status": "failed",
                "label": None,
                "score": None,
                "score_semantics": "deepfake_face_manipulation_probability",
                "generator_scores": None,
                "interpretation": "Sightengine response did not include the expected 'type.deepfake' score.",
                "error": "Unexpected upstream response structure.",
            }

        raw_score = type_obj["deepfake"]
        try:
            score = float(raw_score)
        except (ValueError, TypeError):
            return {
                "provider": self.provider_name,
                "task": "deepfake_face_manipulation_detection",
                "status": "failed",
                "label": None,
                "score": None,
                "score_semantics": "deepfake_face_manipulation_probability",
                "generator_scores": None,
                "interpretation": f"Invalid non-numeric deepfake score received: {raw_score}",
                "error": "Invalid score type in response.",
            }

        score = max(0.0, min(1.0, score))

        # Scientific classification and calibrated interpretation based on official documentation
        if score >= 0.80:
            label = "likely_deepfake"
            interpretation = (
                f"Sightengine reported a deepfake face manipulation score of {score:.2f} (80%+ threshold), "
                "indicating a high likelihood that a prominent face has been swapped, regenerated, or artificially altered. "
                "Note: Evaluates facial manipulation in photographic media; does not confirm whether background scenes are real."
            )
        elif score <= 0.15:
            label = "low_probability_deepfake"
            interpretation = (
                f"Sightengine reported a deepfake face manipulation score of {score:.2f} (below 15% threshold), "
                "indicating low likelihood of face swapping or identity manipulation on prominent faces. "
                "Note: Does not confirm the image is an authentic capture, nor does it evaluate whole-image synthesis or non-facial edits."
            )
        else:
            label = "inconclusive"
            interpretation = (
                f"Sightengine returned an intermediate deepfake face manipulation score of {score:.2f}. "
                "Facial features were ambiguous and do not conclusively establish or rule out facial replacement."
            )

        return {
            "provider": self.provider_name,
            "task": "deepfake_face_manipulation_detection",
            "status": "completed",
            "label": label,
            "score": round(score, 4),
            "score_semantics": "deepfake_face_manipulation_probability",
            "generator_scores": None,
            "interpretation": interpretation,
            "error": None,
        }

    def detect_all(self, image_bytes: bytes, filename: str, tasks: Optional[set[str]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Synchronously submit image to Sightengine check.json endpoint.
        If both genai and deepfake are enabled, combines models="genai,deepfake" into a single
        network call to avoid duplicate network latency and requests.
        Returns a tuple: (genai_result, deepfake_result).
        """
        run_genai = self._genai_enabled and (tasks is None or "ai_generation" in tasks)
        run_deepfake = self._deepfake_enabled and (tasks is None or "deepfake" in tasks)
        if not self.is_configured:
            return self._unconfigured_genai_response(), self._unconfigured_deepfake_response()

        models_to_run = []
        if run_genai:
            models_to_run.append("genai")
        if run_deepfake:
            models_to_run.append("deepfake")

        if not models_to_run:
            return self._unconfigured_genai_response(), self._unconfigured_deepfake_response()

        content_type = self._determine_content_type(filename)
        files = {"media": (filename, image_bytes, content_type)}
        data = {
            "models": ",".join(models_to_run),
            "api_user": self._api_user,
            "api_secret": self._api_secret,
        }

        try:
            with httpx.Client(timeout=self._timeout_seconds) as client:
                response = client.post(self._api_url, data=data, files=files)
                try:
                    payload = response.json()
                except Exception as json_err:
                    logger.warning("Failed to decode JSON from Sightengine (status %d): %s", response.status_code, str(json_err))
                    err_res = {
                        "provider": self.provider_name,
                        "status": "failed",
                        "label": None,
                        "score": None,
                        "generator_scores": None,
                        "interpretation": "Sightengine returned a malformed or non-JSON response.",
                        "error": f"JSON decode error from upstream (HTTP {response.status_code}).",
                    }
                    genai_res = {**err_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
                    deepfake_res = {**err_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
                    return genai_res, deepfake_res

                genai_res = self._parse_genai_from_payload(response.status_code, payload) if run_genai else self._unconfigured_genai_response()
                deepfake_res = self._parse_deepfake_from_payload(response.status_code, payload) if run_deepfake else self._unconfigured_deepfake_response()
                return genai_res, deepfake_res

        except httpx.TimeoutException:
            logger.warning("Sightengine request timed out after %s seconds", self._timeout_seconds)
            timeout_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": f"Connection to Sightengine service timed out after {self._timeout_seconds}s. External verification unavailable.",
                "error": "Request timed out.",
            }
            genai_res = {**timeout_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**timeout_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

        except httpx.RequestError as req_err:
            logger.warning("Sightengine request error: %s", str(req_err))
            net_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": "Network error communicating with Sightengine service. External verification unavailable.",
                "error": "Network transport error.",
            }
            genai_res = {**net_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**net_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

        except Exception as unk_err:
            logger.error("Unexpected error in Sightengine adapter: %s", str(unk_err), exc_info=True)
            unk_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": "Unexpected internal error executing external detection.",
                "error": "Internal adapter error.",
            }
            genai_res = {**unk_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**unk_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

    async def detect_all_async(self, image_bytes: bytes, filename: str, tasks: Optional[set[str]] = None) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Asynchronously submit image to Sightengine check.json endpoint.
        If both genai and deepfake are enabled, combines models="genai,deepfake" into a single
        network call to avoid duplicate network latency and requests.
        Returns a tuple: (genai_result, deepfake_result).
        """
        run_genai = self._genai_enabled and (tasks is None or "ai_generation" in tasks)
        run_deepfake = self._deepfake_enabled and (tasks is None or "deepfake" in tasks)
        if not self.is_configured:
            return self._unconfigured_genai_response(), self._unconfigured_deepfake_response()

        models_to_run = []
        if run_genai:
            models_to_run.append("genai")
        if run_deepfake:
            models_to_run.append("deepfake")

        if not models_to_run:
            return self._unconfigured_genai_response(), self._unconfigured_deepfake_response()

        content_type = self._determine_content_type(filename)
        files = {"media": (filename, image_bytes, content_type)}
        data = {
            "models": ",".join(models_to_run),
            "api_user": self._api_user,
            "api_secret": self._api_secret,
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout_seconds) as client:
                response = await client.post(self._api_url, data=data, files=files)
                try:
                    payload = response.json()
                except Exception as json_err:
                    logger.warning("Failed to decode JSON from Sightengine async (status %d): %s", response.status_code, str(json_err))
                    err_res = {
                        "provider": self.provider_name,
                        "status": "failed",
                        "label": None,
                        "score": None,
                        "generator_scores": None,
                        "interpretation": "Sightengine returned a malformed or non-JSON response.",
                        "error": f"JSON decode error from upstream (HTTP {response.status_code}).",
                    }
                    genai_res = {**err_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
                    deepfake_res = {**err_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
                    return genai_res, deepfake_res

                genai_res = self._parse_genai_from_payload(response.status_code, payload) if run_genai else self._unconfigured_genai_response()
                deepfake_res = self._parse_deepfake_from_payload(response.status_code, payload) if run_deepfake else self._unconfigured_deepfake_response()
                return genai_res, deepfake_res

        except httpx.TimeoutException:
            logger.warning("Sightengine async request timed out after %s seconds", self._timeout_seconds)
            timeout_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": f"Connection to Sightengine service timed out after {self._timeout_seconds}s. External verification unavailable.",
                "error": "Request timed out.",
            }
            genai_res = {**timeout_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**timeout_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

        except httpx.RequestError as req_err:
            logger.warning("Sightengine async request error: %s", str(req_err))
            net_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": "Network error communicating with Sightengine service. External verification unavailable.",
                "error": "Network transport error.",
            }
            genai_res = {**net_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**net_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

        except Exception as unk_err:
            logger.error("Unexpected error in Sightengine async adapter: %s", str(unk_err), exc_info=True)
            unk_res = {
                "provider": self.provider_name,
                "status": "failed",
                "label": None,
                "score": None,
                "generator_scores": None,
                "interpretation": "Unexpected internal error executing external detection.",
                "error": "Internal adapter error.",
            }
            genai_res = {**unk_res, "task": "ai_generated_image_detection", "score_semantics": "ai_generated_probability"} if run_genai else self._unconfigured_genai_response()
            deepfake_res = {**unk_res, "task": "deepfake_face_manipulation_detection", "score_semantics": "deepfake_face_manipulation_probability"} if run_deepfake else self._unconfigured_deepfake_response()
            return genai_res, deepfake_res

    def detect_genai(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Synchronously submit image to Sightengine models=genai endpoint.
        Preserves existing method contract for callers expecting standalone genai response.
        """
        genai_res, _ = self.detect_all(image_bytes, filename)
        return genai_res

    async def detect_genai_async(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        """
        Asynchronously submit image to Sightengine models=genai endpoint.
        Preserves existing method contract for callers expecting standalone genai response.
        """
        genai_res, _ = await self.detect_all_async(image_bytes, filename)
        return genai_res

    def detect_deepfake(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Synchronously evaluate image for face-swap / deepfake manipulation."""
        _, deepfake_res = self.detect_all(image_bytes, filename)
        return deepfake_res

    async def detect_deepfake_async(self, image_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Asynchronously evaluate image for face-swap / deepfake manipulation."""
        _, deepfake_res = await self.detect_all_async(image_bytes, filename)
        return deepfake_res
