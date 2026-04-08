"""
Application queue manager.

Provides a daily view of the job pipeline and lets Agam
manage which jobs to apply to, skip, or revisit.
"""

import logging
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.table import Table

from src.jobs.deduplicator import (
    get_todays_queue,
    get_all_jobs,
    get_stats,
    update_status,
)

logger = logging.getLogger(__name__)
console = Console()

OUTPUT_BASE = Path(__file__).resolve().parent.parent.parent / "output" / "jobs"


def show_queue() -> None:
    """Display today's job queue in a rich table."""
    queue = get_todays_queue()
    if not queue:
        console.print("\n[yellow]No jobs in today's queue.[/yellow]")
        console.print("Run [bold]python run.py --jobs[/bold] to scrape and tailor.\n")
        return

    table = Table(title=f"Job Queue — {date.today().isoformat()}", show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Status", style="bold", width=10)
    table.add_column("Title", width=30)
    table.add_column("Company", width=20)
    table.add_column("Location", width=15)
    table.add_column("Source", width=10)

    for i, job in enumerate(queue, 1):
        status = job["status"].upper()
        style = {
            "QUEUED": "cyan",
            "TAILORED": "green",
            "APPLIED": "blue",
            "REJECTED": "red",
        }.get(status, "white")

        table.add_row(
            str(i),
            f"[{style}]{status}[/{style}]",
            job["title"],
            job["company"],
            job.get("location", "—"),
            job.get("source", "—"),
        )

    console.print()
    console.print(table)
    console.print()


def show_stats() -> None:
    """Display aggregate job stats."""
    stats = get_stats()
    console.print("\n[bold]📊 Job Pipeline Stats[/bold]")
    console.print(f"  Total tracked:  {stats['total_jobs']}")
    console.print(f"  Today's queue:  {stats['today_queued']}")
    for status, count in stats.get("by_status", {}).items():
        emoji = {
            "seen": "👀",
            "queued": "📋",
            "tailored": "✅",
            "applied": "📨",
            "rejected": "❌",
        }.get(status, "•")
        console.print(f"  {emoji} {status}: {count}")
    console.print()


def interactive_review() -> None:
    """
    Interactive terminal review of tailored applications.
    Lets Agam review each tailored job and decide to apply or skip.
    """
    queue = get_todays_queue()
    tailored = [j for j in queue if j["status"] == "tailored"]

    if not tailored:
        console.print("\n[yellow]No tailored jobs to review.[/yellow]\n")
        return

    console.print(f"\n[bold]Reviewing {len(tailored)} tailored application(s)...[/bold]\n")

    for job in tailored:
        today = date.today().isoformat()
        slug = f"{job['company'].lower().replace(' ', '_')[:30]}_{job['title'].lower().replace(' ', '_')[:30]}"
        out_dir = OUTPUT_BASE / today

        # Try to find the output directory
        score_text = "N/A"
        if out_dir.exists():
            for subdir in out_dir.iterdir():
                if subdir.is_dir():
                    score_file = subdir / "match_score.txt"
                    if score_file.exists():
                        score_text = score_file.read_text(encoding="utf-8")[:200]
                        break

        console.print(f"[bold cyan]{'='*60}[/bold cyan]")
        console.print(f"[bold]{job['title']}[/bold] @ [green]{job['company']}[/green]")
        console.print(f"Location: {job.get('location', '—')}")
        console.print(f"URL: {job['url']}")
        console.print(f"Match: {score_text.split(chr(10))[0]}")
        console.print(f"[bold cyan]{'='*60}[/bold cyan]")

        choice = console.input(
            "\n[A]pply / [S]kip / [Q]uit review: "
        ).strip().lower()

        if choice == "a":
            update_status(job["url"], "applied")
            console.print("[green]✓ Marked as applied[/green]\n")
        elif choice == "s":
            update_status(job["url"], "rejected")
            console.print("[yellow]→ Skipped[/yellow]\n")
        elif choice == "q":
            console.print("Exiting review.\n")
            break
        else:
            console.print("[dim]Unknown choice, skipping.[/dim]\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    show_queue()
    show_stats()
