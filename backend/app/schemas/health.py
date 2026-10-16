"""Health check schemas."""
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health check response schema according to API_SPEC.md."""
    status: str = Field(default="ok", description="Status of the API service")
    service: str = Field(default="trace-api", description="Service identifier")


class CapabilitiesResponse(BaseModel):
    """Availability of supported checks; contains no configuration values."""
    capabilities: dict[str, str] = Field(default_factory=dict)
