#!/usr/bin/env python3
"""
Agam Automation Hub — Unified CLI Entry Point.

Usage:
  python run.py --briefing       # Run morning briefing now
  python run.py --jobs           # Run job search + tailoring now
  python run.py --linkedin       # Generate + review + post LinkedIn
  python run.py --telegram       # Start Telegram bot
  python run.py --gmail          # Run Gmail triage now
  python run.py --schedule       # Start full scheduler (all jobs)
  python run.py --status         # Print system status dashboard
  python run.py --setup          # First-time setup wizard
"""

import argparse
import logging
import os
import sys
import webbrowser
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from src.services.automation import (
    get_environment_status,
    get_system_status,
    run_briefing_now,
    run_gmail_triage_now,
    run_jobs_pipeline,
)

# Ensure repo root is on the path
REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT))

load_dotenv()
console = Console()

# ── Logging setup ─────────────────────────────────────────

LOG_DIR = REPO_ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)


def setup_logging() -> None:
    """Configure rotating file + console logging."""
    from logging.handlers import RotatingFileHandler

    log_file = LOG_DIR / f"{date.today().isoformat()}.log"
    handlers = [
        RotatingFileHandler(log_file, maxBytes=5_242_880, backupCount=7),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=handlers,
    )


# ── Environment validation ────────────────────────────────

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


def check_env() -> dict:
    """Check environment variables. Returns dict of {var: status}."""
    return get_environment_status()


def validate_required_env() -> bool:
    """Assert all required env vars are set. Fail fast if not."""
    missing = []
    for var in REQUIRED_VARS:
        if not os.getenv(var):
            missing.append(var)
    if missing:
        console.print(f"\n[bold red]Missing required environment variables:[/bold red]")
        for var in missing:
            console.print(f"  • {var}: {REQUIRED_VARS[var]}")
        console.print(f"\nRun [bold]python run.py --setup[/bold] for guided setup.\n")
        return False
    return True


# ── Command implementations ───────────────────────────────

def cmd_briefing() -> None:
    """Run morning briefing now."""
    console.print("\n[bold]☀️ Generating morning briefing...[/bold]\n")
    result = run_briefing_now(send_to_telegram=True)
    briefing = result["briefing"]
    console.print(Panel(briefing, title="Morning Briefing", border_style="cyan"))

    if result["sent_to_telegram"]:
        console.print("[green]Sent to Telegram.[/green]\n")


def cmd_jobs() -> None:
    """Run job search + tailoring pipeline."""
    console.print("\n[bold]🔍 Running job search pipeline...[/bold]\n")
    from src.jobs.application_queue import show_queue, show_stats

    result = run_jobs_pipeline()
    new_count = result["scraped_new_jobs"]
    console.print(f"[green]Scraped {new_count} new jobs.[/green]")

    if new_count > 0:
        console.print("\n[bold]✍️ Tailoring resumes...[/bold]\n")
        tailored = result["tailored_jobs"]
        console.print(f"[green]Tailored {tailored} applications.[/green]")

    show_queue()
    show_stats()


def cmd_linkedin() -> None:
    """Generate, review, and optionally publish LinkedIn post."""
    console.print("\n[bold]💼 LinkedIn Post Workflow[/bold]\n")
    from src.linkedin.reviewer import review_post
    review_post()


def cmd_telegram() -> None:
    """Start the Telegram bot."""
    console.print("\n[bold]🤖 Starting Telegram bot...[/bold]\n")
    from src.messaging.telegram_bot import start_bot
    start_bot()


def cmd_gmail() -> None:
    """Run Gmail triage now."""
    console.print("\n[bold]📧 Running Gmail triage...[/bold]\n")
    result = run_gmail_triage_now(send_to_telegram=False)
    console.print(result["summary"])


def cmd_schedule() -> None:
    """Start the full scheduler."""
    console.print("\n[bold]📅 Starting scheduler...[/bold]\n")
    from src.scheduler.cron import start_scheduler
    start_scheduler()


def cmd_status() -> None:
    """Print system status dashboard."""
    snapshot = get_system_status()
    stats = snapshot["jobs"]
    env = snapshot["environment"]
    linkedin = snapshot["linkedin"]

    console.print()
    console.print(Panel(
        f"[bold]Agam Automation Hub[/bold] — {snapshot['date']}",
        border_style="cyan",
    ))

    # Environment status
    env_table = Table(title="Environment", show_lines=False)
    env_table.add_column("Variable", style="bold")
    env_table.add_column("Status")
    env_table.add_column("Description", style="dim")
    for var, info in env.items():
        status = "[green]✓ Set[/green]" if info["set"] else (
            "[red]✗ Missing (required)[/red]" if info["required"] else "[yellow]○ Not set[/yellow]"
        )
        env_table.add_row(var, status, info["description"][:50])
    console.print(env_table)

    # Job stats
    console.print(f"\n[bold]📋 Job Pipeline[/bold]")
    console.print(f"  Total tracked: {stats['total_jobs']}")
    console.print(f"  Today's queue: {stats['today_queued']}")
    for status, count in stats.get("by_status", {}).items():
        console.print(f"    {status}: {count}")

    # LinkedIn status
    console.print(f"\n[bold]💼 LinkedIn[/bold]: {linkedin['status']}")

    # Token expiry check
    if linkedin["token_warning"]:
        console.print(f"  [red]⚠ {linkedin['token_warning']}[/red]")
    elif linkedin["token_age_days"] is not None:
        console.print(f"  Token age: {linkedin['token_age_days']} days")

    console.print()


# ── Setup wizard ──────────────────────────────────────────

def cmd_setup() -> None:
    """Interactive first-time setup wizard."""
    console.print(Panel(
        "[bold]Agam Automation Hub — Setup Wizard[/bold]\n\n"
        "This will guide you through configuring all services.",
        border_style="cyan",
    ))

    env_lines = []

    # 1. Check existing .env
    env_path = REPO_ROOT / ".env"
    if env_path.exists():
        console.print("[yellow]Existing .env found. We'll update it.[/yellow]\n")
        with open(env_path, "r") as f:
            for line in f:
                env_lines.append(line.rstrip())

    def _set_var(name: str, prompt_text: str, default: str = "") -> str:
        current = os.getenv(name, default)
        display = f" [dim](current: {current[:20]}...)[/dim]" if current else ""
        val = console.input(f"  {prompt_text}{display}: ").strip()
        return val or current

    # 2. Anthropic API key
    console.print("\n[bold]1/4 — Anthropic (Claude AI)[/bold]")
    console.print("  Get your API key from: https://console.anthropic.com/")
    key = _set_var("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY")
    if key:
        env_lines.append(f"ANTHROPIC_API_KEY={key}")

    # 3. LinkedIn
    console.print("\n[bold]2/4 — LinkedIn[/bold]")
    console.print("  Create an app at: https://www.linkedin.com/developers/apps")
    open_link = console.input("  Open LinkedIn developer tools? [y/N]: ").strip().lower()
    if open_link == "y":
        webbrowser.open("https://www.linkedin.com/developers/tools/oauth/token-generator")

    li_token = _set_var("LINKEDIN_ACCESS_TOKEN", "LINKEDIN_ACCESS_TOKEN")
    li_urn = _set_var("LINKEDIN_PERSON_URN", "LINKEDIN_PERSON_URN", "urn:li:person:XXXXXXX")
    if li_token:
        env_lines.append(f"LINKEDIN_ACCESS_TOKEN={li_token}")
        env_lines.append(f"LINKEDIN_PERSON_URN={li_urn}")
        env_lines.append(f"LINKEDIN_TOKEN_SET_DATE={date.today().isoformat()}")

    # 4. Telegram
    console.print("\n[bold]3/4 — Telegram[/bold]")
    console.print("  1. Open Telegram and message @BotFather")
    console.print("  2. Send /newbot and follow the prompts")
    console.print("  3. Copy the bot token")
    console.print("  4. Message @userinfobot to get your chat ID")

    tg_token = _set_var("TELEGRAM_BOT_TOKEN", "TELEGRAM_BOT_TOKEN")
    tg_chat = _set_var("TELEGRAM_CHAT_ID", "TELEGRAM_CHAT_ID")
    if tg_token:
        env_lines.append(f"TELEGRAM_BOT_TOKEN={tg_token}")
    if tg_chat:
        env_lines.append(f"TELEGRAM_CHAT_ID={tg_chat}")

    # 5. Gmail
    console.print("\n[bold]4/4 — Gmail (optional)[/bold]")
    console.print("  1. Go to Google Cloud Console → APIs & Services → Credentials")
    console.print("  2. Create an OAuth 2.0 client (Desktop app)")
    console.print("  3. Download credentials.json to the repo root")
    creds_path = _set_var("GMAIL_CREDENTIALS_PATH", "Path to credentials.json", "credentials.json")
    env_lines.append(f"GMAIL_CREDENTIALS_PATH={creds_path}")
    env_lines.append(f"GMAIL_TOKEN_PATH=token.json")

    # Add defaults
    env_lines.append(f"TIMEZONE=America/New_York")
    env_lines.append(f"DAILY_JOB_LIMIT=10")
    env_lines.append(f"POST_TIME_WINDOW_START=8")
    env_lines.append(f"POST_TIME_WINDOW_END=11")

    # Write .env
    # De-duplicate by keeping last value for each key
    seen_keys = {}
    for line in env_lines:
        if "=" in line and not line.startswith("#"):
            key = line.split("=", 1)[0]
            seen_keys[key] = line
        elif line.startswith("#") or not line.strip():
            pass  # skip comments for dedup

    with open(env_path, "w") as f:
        f.write("# Agam Automation Hub — Configuration\n")
        f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
        for line in seen_keys.values():
            f.write(line + "\n")

    console.print(f"\n[green]✅ .env written to {env_path}[/green]")

    # Create output directories
    for d in ["output/linkedin/queue", "output/linkedin/posted", "output/jobs", "output/briefings", "data", "logs"]:
        (REPO_ROOT / d).mkdir(parents=True, exist_ok=True)
    console.print("[green]✅ Output directories created.[/green]")

    # Init database
    from src.jobs.deduplicator import init_db
    init_db()
    console.print("[green]✅ SQLite database initialised.[/green]")

    # Test connections
    console.print("\n[bold]Testing connections...[/bold]")

    # Test Claude
    if os.getenv("ANTHROPIC_API_KEY") or key:
        try:
            os.environ["ANTHROPIC_API_KEY"] = key or os.getenv("ANTHROPIC_API_KEY", "")
            from src.agent.claude_client import ClaudeClient
            c = ClaudeClient()
            c.complete("Say OK")
            console.print("  [green]✓ Claude API: connected[/green]")
        except Exception as exc:
            console.print(f"  [red]✗ Claude API: {exc}[/red]")

    console.print(f"\n[bold green]Setup complete![/bold green]")
    console.print("Next steps:")
    console.print("  1. python run.py --status    — verify everything")
    console.print("  2. python run.py --jobs      — run your first job search")
    console.print("  3. python run.py --linkedin   — generate your first post")
    console.print("  4. python run.py --schedule   — start the scheduler\n")


# ── Main ──────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Agam Automation Hub — Personal productivity automation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run.py --setup          First-time setup
  python run.py --status         Check system status
  python run.py --jobs           Run job search + tailoring
  python run.py --linkedin       Generate + review LinkedIn post
  python run.py --briefing       Generate morning briefing
  python run.py --telegram       Start Telegram bot
  python run.py --gmail          Run Gmail triage
  python run.py --schedule       Start full scheduler
        """,
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--briefing", action="store_true", help="Run morning briefing")
    group.add_argument("--jobs", action="store_true", help="Run job search + tailoring")
    group.add_argument("--linkedin", action="store_true", help="LinkedIn post workflow")
    group.add_argument("--telegram", action="store_true", help="Start Telegram bot")
    group.add_argument("--gmail", action="store_true", help="Run Gmail triage")
    group.add_argument("--schedule", action="store_true", help="Start full scheduler")
    group.add_argument("--status", action="store_true", help="System status dashboard")
    group.add_argument("--setup", action="store_true", help="First-time setup wizard")

    args = parser.parse_args()
    setup_logging()

    if args.setup:
        cmd_setup()
        return

    if args.status:
        cmd_status()
        return

    # All other commands need at least ANTHROPIC_API_KEY
    if not args.status and not validate_required_env():
        sys.exit(1)

    if args.briefing:
        cmd_briefing()
    elif args.jobs:
        cmd_jobs()
    elif args.linkedin:
        cmd_linkedin()
    elif args.telegram:
        cmd_telegram()
    elif args.gmail:
        cmd_gmail()
    elif args.schedule:
        cmd_schedule()


if __name__ == "__main__":
    main()
