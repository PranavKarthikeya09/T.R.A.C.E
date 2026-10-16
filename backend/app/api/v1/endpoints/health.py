"""Health check endpoint."""
from fastapi import APIRouter
from app.schemas.health import HealthResponse, CapabilitiesResponse
from app.config import settings
from app.adapters.sightengine_adapter import SightengineAdapter
from app.adapters.azure_vision_adapter import AzureVisionAdapter

router = APIRouter()


def _get_capabilities() -> dict[str, str]:
    sightengine = SightengineAdapter()
    return {
        "visual_assessment": "available" if AzureVisionAdapter().is_configured else "not_configured",
        "metadata": "available",
        "spatial_analysis": "available",
        "ai_generation": "available" if sightengine.is_configured and sightengine._genai_enabled else "not_configured" if sightengine._genai_enabled else "disabled",
        "deepfake": "available" if sightengine.is_configured and sightengine._deepfake_enabled else "not_configured" if sightengine._deepfake_enabled else "disabled",
        "provenance": "disabled" if not settings.ENABLE_PROVENANCE_CHECK else "unavailable",
    }


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    Check whether the API process is available.
    Adheres to API_SPEC.md Section 3.
    """
    return HealthResponse(status="ok", service="trace-api")


@router.get("/capabilities", response_model=CapabilitiesResponse)
async def get_capabilities() -> CapabilitiesResponse:
    """Expose check availability without disclosing credentials or values."""
    return CapabilitiesResponse(capabilities=_get_capabilities())
