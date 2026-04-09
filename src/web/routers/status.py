"""System status API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.services import get_system_status
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, SystemStatusResponse

router = APIRouter(prefix="/api", tags=["status"])


@router.get(
    "/status",
    response_model=SystemStatusResponse,
    responses={500: {"model": APIError}},
    summary="System status snapshot",
    description=(
        "Returns aggregated status used by both CLI and frontend, "
        "including environment configuration flags, jobs stats, and LinkedIn status."
    ),
)
def system_status() -> SystemStatusResponse:
    try:
        return SystemStatusResponse(**get_system_status())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch system status.", exc)
