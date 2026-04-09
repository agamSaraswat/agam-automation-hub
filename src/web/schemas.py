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


class LinkedInDraftResponse(BaseModel):
    today: str = Field(description="Current date in YYYY-MM-DD format.")
    exists: bool = Field(description="Whether today's draft exists in queue.")
    content: str = Field(default="", description="Draft content without frontmatter.")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Frontmatter metadata.")
    status: str = Field(description="Review status for current draft.")
    publish_supported: bool = Field(description="Whether backend publish credentials are configured.")


class LinkedInDraftUpdateRequest(BaseModel):
    content: str = Field(description="Updated LinkedIn draft body.")


class LinkedInDecisionResponse(BaseModel):
    draft: LinkedInDraftResponse = Field(description="Updated draft snapshot.")
    message: str = Field(description="Decision result message.")




class ActionConfirmationRequest(BaseModel):
    confirm_action: bool = Field(
        default=False,
        description="Must be true to confirm a dangerous or state-changing action.",
    )

class LinkedInPublishRequest(BaseModel):
    confirm_publish: bool = Field(
        default=False,
        description="Must be true to explicitly confirm publication.",
    )


class LinkedInPublishResponse(BaseModel):
    published: bool = Field(description="Whether the draft was published.")
    message: str = Field(description="Publish result message.")




class PostingTimeWindow(BaseModel):
    start_hour: int = Field(ge=0, le=23, description="LinkedIn posting window start hour (24h).")
    end_hour: int = Field(ge=0, le=23, description="LinkedIn posting window end hour (24h).")


class SecretConfigStatus(BaseModel):
    configured: bool = Field(description="Whether the secret is configured.")
    description: str = Field(description="Human-readable description.")


class SettingsResponse(BaseModel):
    target_roles: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    include_keywords: list[str] = Field(default_factory=list)
    exclude_keywords: list[str] = Field(default_factory=list)
    daily_job_limit: int = Field(ge=1, le=200)
    posting_time_window: PostingTimeWindow
    job_sources: dict[str, bool] = Field(default_factory=dict)
    secret_status: dict[str, SecretConfigStatus] = Field(default_factory=dict)
    editable_fields: list[str] = Field(default_factory=list)
    file_based_notes: list[str] = Field(default_factory=list)


class SettingsUpdateRequest(BaseModel):
    target_roles: list[str] = Field(min_length=1)
    locations: list[str] = Field(min_length=1)
    include_keywords: list[str] = Field(min_length=1)
    exclude_keywords: list[str] = Field(default_factory=list)
    daily_job_limit: int = Field(ge=1, le=200)
    posting_time_window: PostingTimeWindow
    job_sources: dict[str, bool] = Field(default_factory=dict)

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






class SchedulerJobItem(BaseModel):
    job_id: str = Field(description="Scheduler job ID.")
    name: str = Field(description="Scheduler job display name.")
    trigger: str = Field(description="Cadence/trigger description.")
    next_run_time: str | None = Field(default=None, description="Next planned run time, if available.")


class SchedulerStatusResponse(BaseModel):
    running: bool = Field(description="Whether scheduler is currently running.")
    timezone: str = Field(description="Scheduler timezone.")
    started_at: str | None = Field(default=None, description="When scheduler was started.")
    job_count: int = Field(description="Number of configured jobs in scheduler.")
    next_run_time: str | None = Field(default=None, description="Earliest next run time, if available.")
    jobs: list[SchedulerJobItem] = Field(default_factory=list, description="Configured jobs and cadence.")

class RunHistoryItem(BaseModel):
    run_id: str = Field(description="Unique run identifier.")
    task_type: str = Field(description="Task category, e.g. jobs/briefing/gmail/linkedin_generation.")
    start_time: str = Field(description="Run start timestamp (ISO-8601).")
    end_time: str = Field(description="Run end timestamp (ISO-8601).")
    status: str = Field(description="Run status, e.g. success/failed.")
    summary: str = Field(description="Short run summary.")
    error_message: str | None = Field(default=None, description="Failure details, when status is failed.")


class RunsHistoryResponse(BaseModel):
    items: list[RunHistoryItem] = Field(default_factory=list, description="Recent run records.")
    count: int = Field(description="Number of returned run records.")

class APIError(BaseModel):
    detail: str = Field(description="Error message.")


def model_from_dict(model_cls: type[BaseModel], payload: dict[str, Any]) -> BaseModel:
    """Instantiate model from dictionary payload."""
    return model_cls(**payload)
