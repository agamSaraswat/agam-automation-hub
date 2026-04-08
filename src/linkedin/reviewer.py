"""
LinkedIn post terminal reviewer — HUMAN GATE.

This is the critical approval step. Posts are NEVER published
without explicit confirmation here.

Flow: Print post → [P]ost / [E]dit / [R]egenerate / [S]kip
"""

import os
import subprocess
import tempfile
import logging
from datetime import date
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

from src.linkedin.generator import generate_post, get_todays_pillar
from src.linkedin.publisher import publish_post

logger = logging.getLogger(__name__)
console = Console()

QUEUE_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "linkedin" / "queue"


def _count_words(text: str) -> int:
    """Count words, excluding YAML frontmatter."""
    content = text
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            content = parts[2]
    return len(content.split())


def _strip_frontmatter(text: str) -> str:
    """Remove YAML frontmatter from post."""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return text.strip()


def _edit_in_editor(text: str) -> str:
    """Open text in $EDITOR for manual editing."""
    editor = os.environ.get("EDITOR", "nano")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write(text)
        f.flush()
        tmp_path = f.name

    try:
        subprocess.call([editor, tmp_path])
        with open(tmp_path, "r", encoding="utf-8") as f:
            return f.read().strip()
    finally:
        os.unlink(tmp_path)


def review_post(post_text: str | None = None) -> bool:
    """
    Interactive terminal review of a LinkedIn post.
    Returns True if the post was published.
    """
    # Load today's post if none provided
    if post_text is None:
        today = date.today().isoformat()
        queue_file = QUEUE_DIR / f"{today}.md"
        if queue_file.exists():
            post_text = queue_file.read_text(encoding="utf-8")
        else:
            console.print("\n[yellow]No post in queue for today. Generating...[/yellow]\n")
            post_text = generate_post()
            if not post_text:
                console.print("[red]Could not generate post (weekend or error).[/red]")
                return False

    pillar = get_todays_pillar()
    content = _strip_frontmatter(post_text)
    word_count = _count_words(post_text)
    read_time = max(1, word_count // 200)

    while True:
        # Display the post
        console.print()
        console.print(Panel(
            content,
            title=f"[bold]LinkedIn Post — {pillar.get('name', 'Unknown Pillar')}[/bold]",
            subtitle=f"{word_count} words · ~{read_time} min read",
            border_style="cyan",
            padding=(1, 2),
        ))
        console.print()

        # Prompt for action
        console.print("[bold]Actions:[/bold]")
        console.print("  [green][P][/green]ost now    — publish to LinkedIn")
        console.print("  [yellow][E][/yellow]dit      — open in $EDITOR")
        console.print("  [blue][R][/blue]egenerate — new post, same pillar")
        console.print("  [red][S][/red]kip       — don't post today")
        console.print()

        choice = console.input("[bold]Choose action: [/bold]").strip().lower()

        if choice == "p":
            console.print("\n[bold yellow]⚠ Confirm publish to LinkedIn?[/bold yellow]")
            confirm = console.input("Type 'yes' to confirm: ").strip().lower()
            if confirm == "yes":
                try:
                    result = publish_post(content)
                    console.print(f"\n[bold green]✅ Published successfully![/bold green]")
                    console.print(f"[dim]{result}[/dim]\n")
                    return True
                except Exception as exc:
                    console.print(f"\n[red]Publish failed: {exc}[/red]")
                    console.print("Post saved in queue. Try again later.\n")
                    return False
            else:
                console.print("[dim]Publish cancelled.[/dim]\n")

        elif choice == "e":
            content = _edit_in_editor(content)
            word_count = len(content.split())
            read_time = max(1, word_count // 200)
            # Save edited version
            today = date.today().isoformat()
            queue_file = QUEUE_DIR / f"{today}.md"
            queue_file.write_text(f"---\ndate: {today}\nstatus: edited\n---\n\n{content}", encoding="utf-8")
            console.print("[green]Saved edits.[/green]")

        elif choice == "r":
            console.print("\n[blue]Regenerating with a different angle...[/blue]\n")
            new_post = generate_post()
            if new_post:
                content = _strip_frontmatter(new_post) if "---" in new_post else new_post
                word_count = len(content.split())
                read_time = max(1, word_count // 200)
            else:
                console.print("[red]Regeneration failed.[/red]")

        elif choice == "s":
            console.print("\n[dim]Skipped today's post.[/dim]\n")
            return False

        else:
            console.print("[dim]Unknown option. Try P, E, R, or S.[/dim]")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    review_post()
