"""v1 API router configuration."""
from fastapi import APIRouter
from app.api.v1.endpoints.health import router as health_router
from app.api.v1.endpoints.analyze import router as analyze_router

api_router = APIRouter()
api_router.include_router(health_router, tags=["Health"])
api_router.include_router(analyze_router, tags=["Analyze"])
