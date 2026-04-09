"""Scheduler controls built on APScheduler for local single-user automation."""

from __future__ import annotations

import asyncio
import logging
import os
import random
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"
TIMEZONE = os.getenv("TIMEZONE", "America/New_York")

_scheduler: AsyncIOScheduler | None = None
_scheduler_started_at: str | None = None


# ── Wrapper functions (sync tasks run in scheduler threads) ────────

def _run_morning_briefing() -> None:
    logger.info("⏰ Running morning briefing...")
    try:
        from src.briefing.morning_briefing import generate_briefing
        from src.messaging.telegram_bot import send_message_sync

        briefing = generate_briefing()
        send_message_sync(briefing)
        logger.info("Morning briefing sent.")
    except Exception as exc:
        logger.error("Morning briefing failed: %s", exc)


def _run_job_pipeline() -> None:
    logger.info("⏰ Running job pipeline...")
    try:
        from src.jobs.scraper import run_scraper
        from src.jobs.tailoring_engine import run_tailoring
        from src.messaging.telegram_bot import send_message_sync

        new_count = run_scraper()
        tailored_count = run_tailoring()
        msg = (
            f"📋 Job Pipeline Complete\n"
            f"• {new_count} new jobs scraped\n"
            f"• {tailored_count} applications tailored\n"
            f"Check output/jobs/{date.today().isoformat()}/"
        )
        send_message_sync(msg)
        logger.info("Job pipeline: %d scraped, %d tailored", new_count, tailored_count)
    except Exception as exc:
        logger.error("Job pipeline failed: %s", exc)


def _run_linkedin_generation() -> None:
    logger.info("⏰ Generating LinkedIn post...")
    try:
        from src.linkedin.generator import generate_post
        from src.messaging.telegram_bot import send_message_sync

        post = generate_post()
        if post and "Weekend" not in post:
            send_message_sync(
                "💼 LinkedIn post generated for today.\n"
                "Review from the web LinkedIn page or run `python run.py --linkedin`."
            )
        logger.info("LinkedIn post generated.")
    except Exception as exc:
        logger.error("LinkedIn generation failed: %s", exc)


def _run_gmail_triage() -> None:
    logger.info("📧 Running Gmail triage...")
    try:
        from src.messaging.gmail_triage import run_triage
        from src.messaging.telegram_bot import send_message_sync

        summary = run_triage()
        if "No new emails" not in summary:
            send_message_sync(summary)
        logger.info("Gmail triage complete.")
    except Exception as exc:
        logger.error("Gmail triage failed: %s", exc)


def _run_daily_summary() -> None:
    logger.info("⏰ Running daily summary...")
    try:
        from src.jobs.deduplicator import get_stats
        from src.messaging.telegram_bot import send_message_sync

        stats = get_stats()
        today = date.today().isoformat()

        posted_file = Path("output/linkedin/posted") / f"{today}.md"
        li_status = "✅ Posted" if posted_file.exists() else "❌ Not posted"

        msg = (
            f"🌙 Daily Summary — {today}\n\n"
            f"📋 Jobs: {stats['today_queued']} queued today\n"
            f"   Breakdown: {stats.get('by_status', {})}\n"
            f"💼 LinkedIn: {li_status}\n"
            f"📊 Total jobs tracked: {stats['total_jobs']}\n\n"
            f"Great work today! 💪"
        )
        send_message_sync(msg)
        logger.info("Daily summary sent.")
    except Exception as exc:
        logger.error("Daily summary failed: %s", exc)


def _load_schedule_config() -> dict[str, Any]:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return payload.get("schedule", {}) if isinstance(payload, dict) else {}


def _parse_hhmm(raw: str, fallback_hour: int, fallback_minute: int) -> tuple[int, int]:
    try:
        hour_str, minute_str = (raw or "").split(":", 1)
        return int(hour_str), int(minute_str)
    except Exception:
        return fallback_hour, fallback_minute


def _add_jobs(scheduler: AsyncIOScheduler) -> None:
    schedule = _load_schedule_config()

    morning_hour, morning_minute = _parse_hhmm(schedule.get("morning_briefing", "07:00"), 7, 0)
    job_hour, job_minute = _parse_hhmm(schedule.get("job_scraper", "08:30"), 8, 30)
    summary_hour, summary_minute = _parse_hhmm(schedule.get("daily_summary", "21:00"), 21, 0)

    li_start = int(schedule.get("linkedin_post_window_start", 8))
    li_end = int(schedule.get("linkedin_post_window_end", 11))
    li_end_exclusive = max(li_start + 1, li_end)
    li_hour = random.randint(li_start, li_end_exclusive - 1)
    li_minute = random.randint(0, 59)

    gmail_interval = int(schedule.get("gmail_triage_interval_minutes", 30))

    scheduler.add_job(
        _run_morning_briefing,
        CronTrigger(hour=morning_hour, minute=morning_minute, timezone=TIMEZONE),
        id="morning_briefing",
        name="Morning Briefing",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_linkedin_generation,
        CronTrigger(hour=li_hour, minute=li_minute, timezone=TIMEZONE),
        id="linkedin_generation",
        name=f"LinkedIn Generation ({li_hour:02d}:{li_minute:02d})",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_job_pipeline,
        CronTrigger(hour=job_hour, minute=job_minute, timezone=TIMEZONE),
        id="job_pipeline",
        name="Job Pipeline",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_gmail_triage,
        IntervalTrigger(minutes=max(1, gmail_interval)),
        id="gmail_triage",
        name=f"Gmail Triage (every {max(1, gmail_interval)}m)",
        replace_existing=True,
    )
    scheduler.add_job(
        _run_daily_summary,
        CronTrigger(hour=summary_hour, minute=summary_minute, timezone=TIMEZONE),
        id="daily_summary",
        name="Daily Summary",
        replace_existing=True,
    )


def _scheduler_jobs_payload() -> list[dict[str, Any]]:
    if _scheduler is None:
        return []
    jobs = []
    for job in _scheduler.get_jobs():
        jobs.append(
            {
                "job_id": job.id,
                "name": job.name,
                "trigger": str(job.trigger),
                "next_run_time": job.next_run_time.isoformat() if job.next_run_time else None,
            }
        )
    return jobs


def get_scheduler_status() -> dict[str, Any]:
    running = bool(_scheduler and _scheduler.running)
    jobs = _scheduler_jobs_payload()
    next_run_time = None
    if jobs:
        candidates = [j["next_run_time"] for j in jobs if j.get("next_run_time")]
        next_run_time = min(candidates) if candidates else None

    return {
        "running": running,
        "timezone": TIMEZONE,
        "started_at": _scheduler_started_at,
        "job_count": len(jobs),
        "next_run_time": next_run_time,
        "jobs": jobs,
    }


def start_scheduler(foreground: bool = True) -> dict[str, Any]:
    """Configure and start APScheduler. Foreground mode keeps loop alive for CLI."""
    global _scheduler, _scheduler_started_at

    if _scheduler and _scheduler.running:
        return get_scheduler_status()

    _scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    _add_jobs(_scheduler)
    _scheduler.start()
    _scheduler_started_at = datetime.now().isoformat()
    logger.info("Scheduler started with %d jobs.", len(_scheduler.get_jobs()))

    if foreground:
        print("\n📅 Scheduler is running. Press Ctrl+C to stop.\n")
        for job in _scheduler.get_jobs():
            print(f"  • {job.name} — next: {job.next_run_time}")
        print()
        try:
            asyncio.get_event_loop().run_forever()
        except (KeyboardInterrupt, SystemExit):
            stop_scheduler()
            print("\nScheduler stopped.")

    return get_scheduler_status()


def stop_scheduler() -> dict[str, Any]:
    """Stop scheduler if running."""
    global _scheduler, _scheduler_started_at

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)

    _scheduler = None
    _scheduler_started_at = None
    return get_scheduler_status()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    start_scheduler(foreground=True)
