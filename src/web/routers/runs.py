"""Runs history API router."""

from __future__ import annotations

from fastapi import APIRouter, Query

from src.services import get_recent_runs
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, RunHistoryItem, RunsHistoryResponse

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get(
    "",
    response_model=RunsHistoryResponse,
    responses={500: {"model": APIError}},
    summary="Get recent backend task runs",
)
def list_runs(limit: int = Query(default=25, ge=1, le=200)) -> RunsHistoryResponse:
    try:
        items = [RunHistoryItem(**row) for row in get_recent_runs(limit=limit)]
        return RunsHistoryResponse(items=items, count=len(items))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch run history.", exc)
