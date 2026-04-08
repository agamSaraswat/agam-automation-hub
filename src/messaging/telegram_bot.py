"""
Telegram bot powered by Claude with tool use.

Commands:
  /start     — welcome message
  /briefing  — today's morning briefing
  /jobs      — show today's job queue
  /linkedin  — trigger LinkedIn post generation
  /applied   — mark a job as applied
  /status    — system status dashboard
"""

import os
import logging
from datetime import date

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from src.agent.claude_client import ClaudeClient
from src.agent.tools import TOOL_SCHEMAS, dispatch_tool
from src.jobs.deduplicator import get_stats, init_db

load_dotenv()
logger = logging.getLogger(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

AGENT_SYSTEM_PROMPT = """You are Agam's personal AI assistant, running on his local automation hub.

About Agam:
- Data Scientist at Humana (Healthcare AI, NLP, predictive analytics)
- Based in Massachusetts, USA
- MS Data Analytics from Clark University
- 4+ years experience across healthcare, fintech, consulting

You have tools to:
- Read files from the repository
- Write files to the output directory
- Run the job search pipeline
- Generate LinkedIn posts
- Get the morning briefing
- List and manage the job queue

Be concise in Telegram messages. Use short paragraphs.
If a task requires the terminal (like LinkedIn review), say so.
"""


def _check_auth(chat_id: int) -> bool:
    """Verify the message is from the authorized user."""
    if not ALLOWED_CHAT_ID:
        return True  # No restriction if not set
    return str(chat_id) == str(ALLOWED_CHAT_ID)


# ── Command handlers ──────────────────────────────────────

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not _check_auth(update.effective_chat.id):
        await update.message.reply_text("Unauthorized.")
        return
    await update.message.reply_text(
        "👋 Hey Agam! I'm your automation hub bot.\n\n"
        "Commands:\n"
        "/briefing — Morning briefing\n"
        "/jobs — Today's job queue\n"
        "/linkedin — Generate LinkedIn post\n"
        "/applied — Mark a job as applied\n"
        "/status — System status\n\n"
        "Or just message me anything — I'm Claude-powered!"
    )


async def cmd_briefing(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /briefing command."""
    if not _check_auth(update.effective_chat.id):
        return
    await update.message.reply_text("⏳ Generating briefing...")
    try:
        from src.briefing.morning_briefing import generate_briefing
        briefing = generate_briefing()
        await update.message.reply_text(briefing[:4096])
    except Exception as exc:
        await update.message.reply_text(f"Briefing error: {exc}")


async def cmd_jobs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /jobs command."""
    if not _check_auth(update.effective_chat.id):
        return
    try:
        result = dispatch_tool("list_jobs_queue", {})
        await update.message.reply_text(f"📋 Job Queue:\n\n{result}"[:4096])
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def cmd_linkedin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /linkedin command."""
    if not _check_auth(update.effective_chat.id):
        return
    await update.message.reply_text("✍️ Generating LinkedIn post...")
    try:
        result = dispatch_tool("post_linkedin_now", {})
        await update.message.reply_text(result[:4096])
    except Exception as exc:
        await update.message.reply_text(f"Error: {exc}")


async def cmd_applied(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /applied command — expects: /applied Company, Role"""
    if not _check_auth(update.effective_chat.id):
        return
    text = update.message.text.replace("/applied", "").strip()
    if "," not in text:
        await update.message.reply_text(
            "Usage: /applied Company, Role\nExample: /applied Google, Senior Data Scientist"
        )
        return
    parts = text.split(",", 1)
    company = parts[0].strip()
    role = parts[1].strip()
    result = dispatch_tool("mark_job_applied", {"company": company, "role": role})
    await update.message.reply_text(result)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command."""
    if not _check_auth(update.effective_chat.id):
        return
    try:
        init_db()
        stats = get_stats()
        msg = (
            f"📊 System Status — {date.today().isoformat()}\n\n"
            f"Jobs tracked: {stats['total_jobs']}\n"
            f"Today's queue: {stats['today_queued']}\n"
        )
        for status, count in stats.get("by_status", {}).items():
            msg += f"  • {status}: {count}\n"
        await update.message.reply_text(msg)
    except Exception as exc:
        await update.message.reply_text(f"Status error: {exc}")


# ── Free-form message handler (Claude agent) ─────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle free-form messages with Claude agent + tool use."""
    if not _check_auth(update.effective_chat.id):
        return

    user_msg = update.message.text
    if not user_msg:
        return

    await update.message.reply_text("🤔 Thinking...")

    try:
        client = ClaudeClient()
        messages = [{"role": "user", "content": user_msg}]

        reply = client.run_agent_loop(
            messages=messages,
            tools=TOOL_SCHEMAS,
            tool_handler=dispatch_tool,
            system=AGENT_SYSTEM_PROMPT,
            max_iterations=5,
        )

        # Telegram message limit is 4096 chars
        for i in range(0, len(reply), 4096):
            await update.message.reply_text(reply[i : i + 4096])

    except Exception as exc:
        logger.error("Agent error: %s", exc)
        await update.message.reply_text(f"Sorry, something went wrong: {exc}")


# ── Send a message programmatically ──────────────────────

async def send_message(text: str) -> None:
    """Send a message to the configured Telegram chat (for scheduled tasks)."""
    import httpx

    if not BOT_TOKEN or not ALLOWED_CHAT_ID:
        logger.warning("Telegram not configured — skipping message send.")
        return

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": ALLOWED_CHAT_ID,
        "text": text[:4096],
        "parse_mode": "Markdown",
    }
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(url, json=payload, timeout=15)
            resp.raise_for_status()
        logger.info("Telegram message sent (%d chars)", len(text))
    except Exception as exc:
        logger.error("Failed to send Telegram message: %s", exc)


def send_message_sync(text: str) -> None:
    """Synchronous wrapper for sending Telegram messages."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            loop.create_task(send_message(text))
        else:
            asyncio.run(send_message(text))
    except RuntimeError:
        asyncio.run(send_message(text))


# ── Bot startup ──────────────────────────────────────────

def start_bot() -> None:
    """Start the Telegram bot (blocking)."""
    if not BOT_TOKEN:
        raise EnvironmentError(
            "TELEGRAM_BOT_TOKEN not set. "
            "Create a bot via @BotFather and add the token to .env"
        )

    logger.info("Starting Telegram bot...")
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("briefing", cmd_briefing))
    app.add_handler(CommandHandler("jobs", cmd_jobs))
    app.add_handler(CommandHandler("linkedin", cmd_linkedin))
    app.add_handler(CommandHandler("applied", cmd_applied))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("🤖 Telegram bot is running. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    start_bot()
