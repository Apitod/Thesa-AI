"""
Router: /api/v1/health

Health check endpoint untuk monitoring, load balancer, dan Docker healthcheck.
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    tags=["health"],
)
async def health_check() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="thesa-python-api",
        version="1.0.0",
    )
