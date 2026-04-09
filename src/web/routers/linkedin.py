"""LinkedIn API router."""

from __future__ import annotations

from fastapi import APIRouter

from src.services import get_linkedin_status
from src.web.routers.utils import raise_internal
from src.web.schemas import APIError, LinkedInStatusResponse

router = APIRouter(prefix="/api/linkedin", tags=["linkedin"])


@router.get(
    "/status",
    response_model=LinkedInStatusResponse,
    responses={500: {"model": APIError}},
    summary="Get LinkedIn status",
    description="Returns today's LinkedIn generation/posting status and token age metadata.",
)
def linkedin_status() -> LinkedInStatusResponse:
    try:
        return LinkedInStatusResponse(**get_linkedin_status())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch LinkedIn status.", exc)
