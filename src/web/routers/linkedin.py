"""LinkedIn API router."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from src.services import (
    generate_draft,
    get_draft_snapshot,
    get_linkedin_status,
    publish_approved_draft,
    save_draft_edits,
    set_draft_decision,
    run_with_history,
)
from src.web.routers.utils import raise_internal
from src.web.schemas import (
    APIError,
    LinkedInDecisionResponse,
    LinkedInDraftResponse,
    LinkedInDraftUpdateRequest,
    LinkedInPublishRequest,
    LinkedInPublishResponse,
    LinkedInStatusResponse,
)

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


@router.get(
    "/draft",
    response_model=LinkedInDraftResponse,
    responses={500: {"model": APIError}},
    summary="Get today's LinkedIn draft",
)
def linkedin_draft() -> LinkedInDraftResponse:
    try:
        return LinkedInDraftResponse(**get_draft_snapshot())
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to fetch LinkedIn draft.", exc)


@router.post(
    "/draft/generate",
    response_model=LinkedInDraftResponse,
    responses={500: {"model": APIError}},
    summary="Generate today's LinkedIn draft",
)
def linkedin_generate_draft() -> LinkedInDraftResponse:
    try:
        payload = run_with_history(
            "linkedin_generation",
            lambda result: (
                "LinkedIn draft generated" if result.get("exists") else "No LinkedIn draft generated for today"
            ),
            generate_draft,
        )
        return LinkedInDraftResponse(**payload)
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to generate LinkedIn draft.", exc)


@router.put(
    "/draft",
    response_model=LinkedInDraftResponse,
    responses={500: {"model": APIError}},
    summary="Save LinkedIn draft edits",
)
def linkedin_save_draft(payload: LinkedInDraftUpdateRequest) -> LinkedInDraftResponse:
    try:
        return LinkedInDraftResponse(**save_draft_edits(payload.content))
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to save LinkedIn draft edits.", exc)


@router.post(
    "/draft/approve",
    response_model=LinkedInDecisionResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Approve today's LinkedIn draft",
)
def linkedin_approve() -> LinkedInDecisionResponse:
    try:
        draft = LinkedInDraftResponse(**set_draft_decision(approved=True))
        return LinkedInDecisionResponse(draft=draft, message="Draft approved.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to approve LinkedIn draft.", exc)


@router.post(
    "/draft/reject",
    response_model=LinkedInDecisionResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Reject today's LinkedIn draft",
)
def linkedin_reject() -> LinkedInDecisionResponse:
    try:
        draft = LinkedInDraftResponse(**set_draft_decision(approved=False))
        return LinkedInDecisionResponse(draft=draft, message="Draft rejected.")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to reject LinkedIn draft.", exc)


@router.post(
    "/draft/publish",
    response_model=LinkedInPublishResponse,
    responses={400: {"model": APIError}, 500: {"model": APIError}},
    summary="Publish approved LinkedIn draft",
)
def linkedin_publish(payload: LinkedInPublishRequest) -> LinkedInPublishResponse:
    try:
        message = publish_approved_draft(payload.confirm_publish)
        return LinkedInPublishResponse(published=True, message=message)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive path
        raise_internal("Failed to publish LinkedIn draft.", exc)
