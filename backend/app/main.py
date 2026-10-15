"""FastAPI application entry point for T.R.A.C.E."""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.api.v1.router import api_router
from app.schemas.error import ErrorResponse, ErrorDetail

app = FastAPI(
    title=settings.APP_NAME,
    description="T.R.A.C.E. — Tampering Recognition, Authentication & Content Evidence API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API v1 router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch unhandled errors and return standard JSON error response
    without leaking internal stack traces or filesystem paths to the client.
    """
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error=ErrorDetail(
                code="INTERNAL_ERROR",
                message="An unexpected server error occurred."
            )
        ).model_dump()
    )


@app.get("/")
async def root():
    """Root redirect / information endpoint."""
    return {
        "service": settings.APP_NAME,
        "api_v1": f"{settings.API_V1_PREFIX}/health",
        "docs": "/docs"
    }
