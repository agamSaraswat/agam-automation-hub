"""Jobs API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.services import get_jobs_queue, get_jobs_stats, run_jobs_pipeline
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, JobsQueueResponse, JobsRunResponse, JobsStats

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post(
    "/run",
    response_model=JobsRunResponse,
    responses={500: {"model": APIError}},
    summary="Run jobs pipeline",
    description="Runs scraper + tailoring pipeline and returns structured counts.",
)
def run_jobs() -> JobsRunResponse:
    try:
        return JobsRunResponse(**run_jobs_pipeline())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to run jobs pipeline.", exc)


@router.get(
    "/queue",
    response_model=JobsQueueResponse,
    responses={500: {"model": APIError}},
    summary="Get today's jobs queue",
    description="Returns queued/tailored jobs for today.",
)
def jobs_queue() -> JobsQueueResponse:
    try:
        items = get_jobs_queue()
        return JobsQueueResponse(items=items, count=len(items))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch jobs queue.", exc)


@router.get(
    "/stats",
    response_model=JobsStats,
    responses={500: {"model": APIError}},
    summary="Get jobs stats",
    description="Returns aggregate job stats from the tracking database.",
)
def jobs_stats() -> JobsStats:
    try:
        return JobsStats(**get_jobs_stats())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch jobs stats.", exc)
