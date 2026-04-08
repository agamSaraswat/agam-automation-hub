"""
Morning briefing generator.

Aggregates:
  - Job queue summary
  - Gmail unread summary
  - LinkedIn post schedule
  - Tech news headlines
  - Claude formats into a clean Telegram message
"""

import logging
import os
from datetime import date, datetime
from pathlib import Path

import feedparser
import yaml

from src.agent.claude_client import ClaudeClient
from src.jobs.deduplicator import init_db, get_stats, get_todays_queue

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"
TOPICS_PATH = REPO_ROOT / "config" / "linkedin_topics.yaml"
BRIEFING_DIR = REPO_ROOT / "output" / "briefings"

SYSTEM_PROMPT = """You are Agam's personal briefing assistant.
Format a clean, scannable morning briefing for Telegram.
Use short lines, bullet points with emojis, and clear sections.
Max 300 words. No markdown headers — use emoji section dividers instead.
Keep it actionable and energizing to start the day."""


def _load_settings() -> dict:
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_news_headlines(feeds: list[str], count: int = 3) -> list[str]:
    """Fetch top headlines from RSS feeds."""
    headlines = []
    for feed_url in feeds:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:count]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "")
                if title:
                    headlines.append(f"{title}\n  {link}")
        except Exception as exc:
            logger.warning("Failed to fetch feed %s: %s", feed_url, exc)
    return headlines[:count]


def _get_linkedin_schedule() -> str:
    """Get today's LinkedIn post pillar and scheduled time."""
    try:
        with open(TOPICS_PATH, "r", encoding="utf-8") as f:
            topics = yaml.safe_load(f)
        weekday = date.today().weekday()
        pillar = topics.get("pillars", {}).get(weekday, {})
        name = pillar.get("name", "No post scheduled")

        queue_file = REPO_ROOT / "output" / "linkedin" / "queue" / f"{date.today().isoformat()}.md"
        if queue_file.exists():
            content = queue_file.read_text(encoding="utf-8")
            if "scheduled_time:" in content:
                for line in content.split("\n"):
                    if "scheduled_time:" in line:
                        time_str = line.split(":", 1)[1].strip()
                        return f"{name} — scheduled at {time_str}"
        return f"{name} — not yet generated"
    except Exception as exc:
        logger.warning("LinkedIn schedule error: %s", exc)
        return "Unable to check"


def _get_gmail_summary() -> str:
    """Get a quick Gmail unread summary (if configured)."""
    try:
        from src.messaging.gmail_triage import get_unread_count
        count = get_unread_count()
        return f"{count} unread emails"
    except Exception:
        return "Gmail not configured"


def generate_briefing() -> str:
    """
    Generate the morning briefing.
    Returns formatted text suitable for Telegram.
    """
    init_db()
    settings = _load_settings()
    today = date.today().isoformat()
    now = datetime.now().strftime("%A, %B %d, %Y")

    # Gather data
    job_stats = get_stats()
    job_queue = get_todays_queue()
    news_feeds = settings.get("briefing", {}).get("news_feeds", [])
    headlines = _get_news_headlines(news_feeds)
    linkedin_status = _get_linkedin_schedule()
    gmail_status = _get_gmail_summary()

    # Build context for Claude
    context = f"""Today is {now}.

JOB PIPELINE:
- Total jobs tracked: {job_stats['total_jobs']}
- Today's queue: {job_stats['today_queued']} jobs
- Status breakdown: {job_stats.get('by_status', {})}
- Queued jobs today: {len(job_queue)}
{chr(10).join(f'  • {j["title"]} @ {j["company"]}' for j in job_queue[:5])}

GMAIL:
- {gmail_status}

LINKEDIN:
- Today's pillar: {linkedin_status}

TECH NEWS:
{chr(10).join(f'- {h}' for h in headlines) if headlines else '- No headlines available'}
"""

    prompt = f"""Create Agam's morning briefing using this data:

{context}

Format for Telegram:
- Start with a greeting and date
- Section: 📋 Jobs (queue count + top items)
- Section: 📧 Email (unread summary)
- Section: 💼 LinkedIn (today's post plan)
- Section: 📰 News (top 3 headlines if available)
- End with a motivational one-liner
- Max 300 words, keep it tight
"""

    try:
        client = ClaudeClient()
        briefing = client.complete(prompt, system=SYSTEM_PROMPT, temperature=0.6)
    except Exception as exc:
        logger.error("Claude briefing generation failed: %s", exc)
        # Fallback: plain text briefing
        briefing = (
            f"☀️ Good morning, Agam! — {now}\n\n"
            f"📋 Jobs: {job_stats['today_queued']} in queue\n"
            f"📧 Email: {gmail_status}\n"
            f"💼 LinkedIn: {linkedin_status}\n"
            f"📰 News: {len(headlines)} headlines fetched\n\n"
            f"Have a great day!"
        )

    # Save briefing
    BRIEFING_DIR.mkdir(parents=True, exist_ok=True)
    (BRIEFING_DIR / f"{today}.md").write_text(briefing, encoding="utf-8")
    logger.info("Morning briefing generated and saved.")

    return briefing


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(generate_briefing())
