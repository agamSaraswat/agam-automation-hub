"""Service layer exports."""

from src.services.automation import (
    get_environment_status,
    get_jobs_queue,
    get_jobs_stats,
    get_linkedin_status,
    get_system_status,
    run_briefing_now,
    run_gmail_triage_now,
    run_jobs_pipeline,
)

from src.services.linkedin_review import (
    generate_draft,
    get_draft_snapshot,
    publish_approved_draft,
    save_draft_edits,
    set_draft_decision,
)

from src.services.settings_manager import (
    get_settings_payload,
    update_settings_payload,
)

from src.services.run_history import (
    get_recent_runs,
    run_with_history,
)

__all__ = [
    "get_system_status",
    "get_environment_status",
    "get_jobs_queue",
    "get_jobs_stats",
    "run_jobs_pipeline",
    "run_briefing_now",
    "run_gmail_triage_now",
    "get_linkedin_status",
    "get_draft_snapshot",
    "generate_draft",
    "save_draft_edits",
    "set_draft_decision",
    "publish_approved_draft",
    "get_settings_payload",
    "update_settings_payload",
    "get_recent_runs",
    "run_with_history",
]
