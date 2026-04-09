"""Shared service-layer orchestration for CLI and API usage."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

REQUIRED_VARS = {
    "ANTHROPIC_API_KEY": "Required for Claude AI. Get from: https://console.anthropic.com/",
}

OPTIONAL_VARS = {
    "LINKEDIN_ACCESS_TOKEN": "For LinkedIn posting. Get from: linkedin.com/developers/tools/oauth/token-generator",
    "LINKEDIN_PERSON_URN": "Your LinkedIn person URN (urn:li:person:XXXXX)",
    "TELEGRAM_BOT_TOKEN": "For Telegram bot. Create via @BotFather",
    "TELEGRAM_CHAT_ID": "Your Telegram chat ID. Get via @userinfobot",
    "GMAIL_CREDENTIALS_PATH": "Path to Gmail OAuth credentials.json",
}


def get_environment_status() -> dict[str, dict[str, Any]]:
    """Check configured environment variables."""
    results: dict[str, dict[str, Any]] = {}
    for var, desc in {**REQUIRED_VARS, **OPTIONAL_VARS}.items():
        val = os.getenv(var, "")
        results[var] = {
            "set": bool(val),
            "required": var in REQUIRED_VARS,
            "description": desc,
        }
    return results


def get_linkedin_status() -> dict[str, Any]:
    """Return LinkedIn queue/post/token status for today."""
    today = date.today().isoformat()
    queue_file = REPO_ROOT / "output" / "linkedin" / "queue" / f"{today}.md"
    posted_file = REPO_ROOT / "output" / "linkedin" / "posted" / f"{today}.md"

    status = "Posted ✅" if posted_file.exists() else (
        "In queue (review needed)" if queue_file.exists() else "Not generated"
    )

    token_date = os.getenv("LINKEDIN_TOKEN_SET_DATE", "")
    token_age_days: int | None = None
    token_warning: str | None = None

    if token_date:
        try:
            token_age_days = (date.today() - datetime.strptime(token_date, "%Y-%m-%d").date()).days
            if token_age_days > 50:
                token_warning = f"Token is {token_age_days} days old — refresh soon!"
        except ValueError:
            token_warning = "Invalid LINKEDIN_TOKEN_SET_DATE (use YYYY-MM-DD)."

    return {
        "status": status,
        "today": today,
        "queue_file_exists": queue_file.exists(),
        "posted_file_exists": posted_file.exists(),
        "token_set_date": token_date or None,
        "token_age_days": token_age_days,
        "token_warning": token_warning,
    }


def get_system_status() -> dict[str, Any]:
    """Get aggregate system status for CLI and API."""
    from src.jobs.deduplicator import get_stats, init_db

    init_db()
    return {
        "date": date.today().isoformat(),
        "environment": get_environment_status(),
        "jobs": get_stats(),
        "linkedin": get_linkedin_status(),
    }


def run_jobs_pipeline() -> dict[str, Any]:
    """Run the job search and tailoring workflow."""
    from src.jobs.deduplicator import get_stats, get_todays_queue
    from src.jobs.scraper import run_scraper
    from src.jobs.tailoring_engine import run_tailoring

    new_count = run_scraper()
    tailored = run_tailoring() if new_count > 0 else 0

    return {
        "scraped_new_jobs": new_count,
        "tailored_jobs": tailored,
        "queue_size_today": len(get_todays_queue()),
        "stats": get_stats(),
    }


def get_jobs_queue(limit: int = 20) -> list[dict[str, Any]]:
    """Get queued/tailored jobs for today."""
    from src.jobs.deduplicator import get_todays_queue, init_db

    init_db()
    return get_todays_queue(limit=limit)


def get_jobs_stats() -> dict[str, Any]:
    """Get aggregate job stats."""
    from src.jobs.deduplicator import get_stats, init_db

    init_db()
    return get_stats()


def run_briefing_now(send_to_telegram: bool = True) -> dict[str, Any]:
    """Generate briefing and optionally send to Telegram."""
    from src.briefing.morning_briefing import generate_briefing

    briefing = generate_briefing()
    sent = False

    if send_to_telegram and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        from src.messaging.telegram_bot import send_message_sync

        send_message_sync(briefing)
        sent = True

    return {
        "briefing": briefing,
        "sent_to_telegram": sent,
    }


def run_gmail_triage_now(send_to_telegram: bool = False) -> dict[str, Any]:
    """Run Gmail triage and optionally send summary to Telegram."""
    from src.messaging.gmail_triage import run_triage

    summary = run_triage()
    sent = False

    if send_to_telegram and os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        from src.messaging.telegram_bot import send_message_sync

        send_message_sync(summary)
        sent = True

    return {
        "summary": summary,
        "sent_to_telegram": sent,
    }
