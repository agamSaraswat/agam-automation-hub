"""Settings API router for safe non-secret configuration updates."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services import get_settings_payload, update_settings_payload
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, SettingsResponse, SettingsUpdateRequest

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get(
    "",
    response_model=SettingsResponse,
    responses={500: {"model": APIError}},
    summary="Get editable UI settings",
)
def get_settings() -> SettingsResponse:
    try:
        return SettingsResponse(**get_settings_payload())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch editable settings.", exc)


@router.put(
    "",
    response_model=SettingsResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Update editable UI settings",
)
def update_settings(payload: SettingsUpdateRequest) -> SettingsResponse:
    if payload.posting_time_window.start_hour >= payload.posting_time_window.end_hour:
        raise HTTPException(status_code=400, detail="Posting time window start must be earlier than end.")

    try:
        return SettingsResponse(**update_settings_payload(payload.model_dump()))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to update editable settings.", exc)
