"""Scheduler control API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.scheduler.cron import get_scheduler_status, start_scheduler, stop_scheduler
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, ActionConfirmationRequest, SchedulerStatusResponse

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


@router.get(
    "/status",
    response_model=SchedulerStatusResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Get scheduler status and planned jobs",
)
def scheduler_status() -> SchedulerStatusResponse:
    try:
        return SchedulerStatusResponse(**get_scheduler_status())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch scheduler status.", exc)


@router.post(
    "/start",
    response_model=SchedulerStatusResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Start scheduler",
)
def scheduler_start(payload: ActionConfirmationRequest) -> SchedulerStatusResponse:
    if not payload.confirm_action:
        raise HTTPException(status_code=400, detail="Scheduler start requires explicit confirmation.")
    try:
        return SchedulerStatusResponse(**start_scheduler(foreground=False))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to start scheduler.", exc)


@router.post(
    "/stop",
    response_model=SchedulerStatusResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Stop scheduler",
)
def scheduler_stop(payload: ActionConfirmationRequest) -> SchedulerStatusResponse:
    if not payload.confirm_action:
        raise HTTPException(status_code=400, detail="Scheduler stop requires explicit confirmation.")
    try:
        return SchedulerStatusResponse(**stop_scheduler())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to stop scheduler.", exc)
