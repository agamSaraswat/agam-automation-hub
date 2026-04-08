"""
Scheduler — APScheduler with AsyncIOScheduler.

Schedule:
  07:00         — morning_briefing()
  08:00-11:00   — linkedin_post() [randomized daily within window]
  08:30         — job_scraper() + tailoring_engine()
  Every 30min   — gmail_triage()
  21:00         — daily_summary()
"""

import asyncio
import logging
import os
import random
from datetime import date, datetime

import yaml
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

TIMEZONE = os.getenv("TIMEZONE", "America/New_York")


# ── Wrapper functions (sync tasks run in executor) ────────

def _run_morning_briefing() -> None:
    """Generate and send morning briefing to Telegram."""
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
    """Run job scraper + tailoring engine."""
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
    """Generate a LinkedIn post (review happens in terminal)."""
    logger.info("⏰ Generating LinkedIn post...")
    try:
        from src.linkedin.generator import generate_post
        from src.messaging.telegram_bot import send_message_sync

        post = generate_post()
        if post and "Weekend" not in post:
            send_message_sync(
                f"💼 LinkedIn post generated for today.\n"
                f"Run `python run.py --linkedin` in terminal to review and publish."
            )
        logger.info("LinkedIn post generated.")
    except Exception as exc:
        logger.error("LinkedIn generation failed: %s", exc)


def _run_gmail_triage() -> None:
    """Run Gmail triage and send results to Telegram."""
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
    """Send end-of-day summary to Telegram."""
    logger.info("⏰ Running daily summary...")
    try:
        from src.jobs.deduplicator import get_stats
        from src.messaging.telegram_bot import send_message_sync

        stats = get_stats()
        today = date.today().isoformat()

        # Check if LinkedIn post was made
        from pathlib import Path
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


# ── Scheduler setup ──────────────────────────────────────

def start_scheduler() -> None:
    """Configure and start the APScheduler."""
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)

    # 07:00 — Morning briefing
    scheduler.add_job(
        _run_morning_briefing,
        CronTrigger(hour=7, minute=0, timezone=TIMEZONE),
        id="morning_briefing",
        name="Morning Briefing",
    )

    # 08:00-11:00 — LinkedIn post (random time within window)
    li_hour = random.randint(8, 10)
    li_minute = random.randint(0, 59)
    scheduler.add_job(
        _run_linkedin_generation,
        CronTrigger(hour=li_hour, minute=li_minute, timezone=TIMEZONE),
        id="linkedin_post",
        name=f"LinkedIn Post ({li_hour:02d}:{li_minute:02d})",
    )

    # 08:30 — Job pipeline
    scheduler.add_job(
        _run_job_pipeline,
        CronTrigger(hour=8, minute=30, timezone=TIMEZONE),
        id="job_pipeline",
        name="Job Pipeline",
    )

    # Every 30 minutes — Gmail triage
    scheduler.add_job(
        _run_gmail_triage,
        IntervalTrigger(minutes=30),
        id="gmail_triage",
        name="Gmail Triage",
    )

    # 21:00 — Daily summary
    scheduler.add_job(
        _run_daily_summary,
        CronTrigger(hour=21, minute=0, timezone=TIMEZONE),
        id="daily_summary",
        name="Daily Summary",
    )

    scheduler.start()
    logger.info("Scheduler started with %d jobs:", len(scheduler.get_jobs()))
    for job in scheduler.get_jobs():
        logger.info("  • %s — next run: %s", job.name, job.next_run_time)

    print("\n📅 Scheduler is running. Press Ctrl+C to stop.\n")
    print("Scheduled jobs:")
    for job in scheduler.get_jobs():
        print(f"  • {job.name} — next: {job.next_run_time}")
    print()

    # Keep the event loop alive
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        scheduler.shutdown()
        print("\nScheduler stopped.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
    start_scheduler()
