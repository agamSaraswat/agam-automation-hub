"""Pydantic models for FastAPI responses and request bodies."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(description="Health status.")
    service: str = Field(description="Service name.")
    date: str = Field(description="Server date in YYYY-MM-DD format.")


class EnvironmentVarStatus(BaseModel):
    set: bool = Field(description="Whether the environment variable is configured.")
    required: bool = Field(description="Whether this variable is required.")
    description: str = Field(description="Human-readable description.")


class JobsStats(BaseModel):
    total_jobs: int = Field(description="Total jobs tracked in the database.")
    today_queued: int = Field(description="Jobs seen/queued today.")
    by_status: dict[str, int] = Field(default_factory=dict, description="Counts grouped by status.")


class LinkedInStatusResponse(BaseModel):
    status: str = Field(description="Today's LinkedIn status summary.")
    today: str = Field(description="Current date in YYYY-MM-DD format.")
    queue_file_exists: bool = Field(description="Whether today's queue draft exists.")
    posted_file_exists: bool = Field(description="Whether today's post archive exists.")
    token_set_date: str | None = Field(default=None, description="Configured token set date.")
    token_age_days: int | None = Field(default=None, description="Token age in days.")
    token_warning: str | None = Field(default=None, description="Warning if token is near expiry or invalid.")


class SystemStatusResponse(BaseModel):
    date: str = Field(description="Current date in YYYY-MM-DD format.")
    environment: dict[str, EnvironmentVarStatus] = Field(description="Environment configuration status.")
    jobs: JobsStats = Field(description="Job pipeline aggregate stats.")
    linkedin: LinkedInStatusResponse = Field(description="LinkedIn status snapshot.")


class JobsRunResponse(BaseModel):
    scraped_new_jobs: int = Field(description="Number of newly scraped jobs.")
    tailored_jobs: int = Field(description="Number of tailored jobs.")
    queue_size_today: int = Field(description="Queued/tailored jobs today after run.")
    stats: JobsStats = Field(description="Updated aggregate job stats.")


class JobQueueItem(BaseModel):
    id: int | None = Field(default=None, description="Database ID.")
    url: str = Field(description="Job URL.")
    company: str = Field(description="Company name.")
    title: str = Field(description="Role title.")
    location: str = Field(default="", description="Job location.")
    date_seen: str | None = Field(default=None, description="Date first seen.")
    status: str = Field(description="Current job status.")
    source: str = Field(default="", description="Ingestion source.")


class JobsQueueResponse(BaseModel):
    items: list[JobQueueItem] = Field(default_factory=list, description="Queued jobs.")
    count: int = Field(description="Number of returned queue items.")


class BriefingRunRequest(BaseModel):
    send_to_telegram: bool = Field(
        default=False,
        description="If true, sends the briefing to Telegram when bot credentials are configured.",
    )


class BriefingRunResponse(BaseModel):
    briefing: str = Field(description="Generated briefing text.")
    sent_to_telegram: bool = Field(description="Whether the briefing was sent to Telegram.")


class GmailRunRequest(BaseModel):
    send_to_telegram: bool = Field(
        default=False,
        description="If true, sends triage summary to Telegram when bot credentials are configured.",
    )


class GmailRunResponse(BaseModel):
    summary: str = Field(description="Gmail triage summary.")
    sent_to_telegram: bool = Field(description="Whether the summary was sent to Telegram.")


class APIError(BaseModel):
    detail: str = Field(description="Error message.")


def model_from_dict(model_cls: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    """Instantiate model from dictionary payload."""
    return model_cls(**payload)
