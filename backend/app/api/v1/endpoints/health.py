"""Health check endpoint."""
from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def get_health() -> HealthResponse:
    """
    Check whether the API process is available.
    Adheres to API_SPEC.md Section 3.
    """
    return HealthResponse(status="ok", service="trace-api")
