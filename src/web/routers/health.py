"""Health API router."""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from src.web.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Returns basic service heartbeat information.",
)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="agam-automation-hub-api",
        date=date.today().isoformat(),
    )
