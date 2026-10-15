"""Error response schema according to API_SPEC.md."""
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Structured error payload."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Client-facing error message")


class ErrorResponse(BaseModel):
    """Standard error response."""
    error: ErrorDetail
