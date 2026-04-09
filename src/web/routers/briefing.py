"""Briefing API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.services import run_briefing_now
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, BriefingRunRequest, BriefingRunResponse

router = APIRouter(prefix="/api/briefing", tags=["briefing"])


@router.post(
    "/run",
    response_model=BriefingRunResponse,
    responses={500: {"model": APIError}},
    summary="Generate morning briefing",
    description="Generates a briefing and optionally sends it to Telegram.",
)
def run_briefing(payload: BriefingRunRequest) -> BriefingRunResponse:
    try:
        return BriefingRunResponse(**run_briefing_now(send_to_telegram=payload.send_to_telegram))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to run briefing.", exc)
