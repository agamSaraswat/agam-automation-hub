"""Gmail API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.services import run_gmail_triage_now
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, GmailRunRequest, GmailRunResponse

router = APIRouter(prefix="/api/gmail", tags=["gmail"])


@router.post(
    "/run",
    response_model=GmailRunResponse,
    responses={500: {"model": APIError}},
    summary="Run Gmail triage",
    description="Runs Gmail triage and optionally forwards summary to Telegram.",
)
def run_gmail(payload: GmailRunRequest) -> GmailRunResponse:
    try:
        return GmailRunResponse(**run_gmail_triage_now(send_to_telegram=payload.send_to_telegram))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to run Gmail triage.", exc)
