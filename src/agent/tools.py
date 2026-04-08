"""
Tool definitions for the Claude agent (Telegram bot + CLI).

Each tool is an Anthropic tool-use schema dict, plus a handler function.
"""

import os
import json
import sqlite3
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
OUTPUT_DIR = REPO_ROOT / "output"
DATA_DIR = REPO_ROOT / "data"


# ════════════════════════════════════════
# Tool schemas (sent to Claude)
# ════════════════════════════════════════

TOOL_SCHEMAS: list[dict[str, Any]] = [
    {
        "name": "read_file",
        "description": "Read the contents of any file in the repository.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path from repo root, e.g. 'master_resume/agam_master_resume.md'",
                }
            },
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": "Write content to a file in the output/ directory only.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Relative path under output/, e.g. 'linkedin/queue/2025-06-01.md'",
                },
                "content": {
                    "type": "string",
                    "description": "File content to write.",
                },
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "run_job_search",
        "description": "Trigger the job scraper and tailoring engine for today's batch.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "post_linkedin_now",
        "description": "Trigger the LinkedIn post review flow.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "get_briefing",
        "description": "Return today's morning briefing text.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_jobs_queue",
        "description": "Show today's job queue from the database.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mark_job_applied",
        "description": "Mark a job as 'applied' in the database.",
        "input_schema": {
            "type": "object",
            "properties": {
                "company": {
                    "type": "string",
                    "description": "Company name.",
                },
                "role": {
                    "type": "string",
                    "description": "Job title / role.",
                },
            },
            "required": ["company", "role"],
        },
    },
]


# ════════════════════════════════════════
# Tool handler functions
# ════════════════════════════════════════

def handle_read_file(path: str) -> str:
    """Read a file relative to the repo root."""
    full = REPO_ROOT / path
    if not full.exists():
        return f"File not found: {path}"
    try:
        return full.read_text(encoding="utf-8")[:8000]  # cap for context
    except Exception as exc:
        return f"Error reading {path}: {exc}"


def handle_write_file(path: str, content: str) -> str:
    """Write a file under output/ only."""
    if not path.startswith("output/") and not path.startswith("output\\"):
        path = f"output/{path}"
    full = OUTPUT_DIR.parent / path
    full.parent.mkdir(parents=True, exist_ok=True)
    try:
        full.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} chars to {path}"
    except Exception as exc:
        return f"Error writing {path}: {exc}"


def handle_run_job_search() -> str:
    """Trigger job search pipeline."""
    try:
        from src.jobs.scraper import run_scraper
        from src.jobs.tailoring_engine import run_tailoring

        new_jobs = run_scraper()
        tailored = run_tailoring()
        return f"Found {new_jobs} new jobs. Tailored {tailored} applications."
    except Exception as exc:
        logger.error("Job search error: %s", exc)
        return f"Job search error: {exc}"


def handle_post_linkedin() -> str:
    """Trigger LinkedIn generation (review must happen in terminal)."""
    try:
        from src.linkedin.generator import generate_post

        post = generate_post()
        return f"LinkedIn post generated:\n\n{post}\n\n(Use terminal reviewer to approve and publish.)"
    except Exception as exc:
        logger.error("LinkedIn error: %s", exc)
        return f"LinkedIn error: {exc}"


def handle_get_briefing() -> str:
    """Return today's briefing."""
    try:
        from src.briefing.morning_briefing import generate_briefing

        return generate_briefing()
    except Exception as exc:
        logger.error("Briefing error: %s", exc)
        return f"Briefing error: {exc}"


def handle_list_jobs_queue() -> str:
    """List today's queued jobs."""
    db_path = DATA_DIR / "jobs.db"
    if not db_path.exists():
        return "No jobs database found. Run job search first."
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "SELECT company, title, url, status FROM seen_jobs "
            "WHERE status IN ('queued', 'tailored') "
            "ORDER BY date_seen DESC LIMIT 20"
        )
        rows = cursor.fetchall()
        conn.close()
        if not rows:
            return "No jobs in queue."
        lines = []
        for i, (company, title, url, status) in enumerate(rows, 1):
            lines.append(f"{i}. [{status.upper()}] {title} @ {company}\n   {url}")
        return "\n".join(lines)
    except Exception as exc:
        return f"DB error: {exc}"


def handle_mark_applied(company: str, role: str) -> str:
    """Mark a job as applied."""
    db_path = DATA_DIR / "jobs.db"
    if not db_path.exists():
        return "No jobs database found."
    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.execute(
            "UPDATE seen_jobs SET status = 'applied' "
            "WHERE LOWER(company) LIKE ? AND LOWER(title) LIKE ?",
            (f"%{company.lower()}%", f"%{role.lower()}%"),
        )
        updated = cursor.rowcount
        conn.commit()
        conn.close()
        if updated == 0:
            return f"No matching job found for '{role}' at '{company}'."
        return f"Marked {updated} job(s) as applied: {role} @ {company}"
    except Exception as exc:
        return f"DB error: {exc}"


# ════════════════════════════════════════
# Dispatcher
# ════════════════════════════════════════

def dispatch_tool(name: str, inputs: dict[str, Any]) -> str:
    """Route a tool call to the correct handler. Returns result string."""
    handlers = {
        "read_file": lambda: handle_read_file(inputs["path"]),
        "write_file": lambda: handle_write_file(inputs["path"], inputs["content"]),
        "run_job_search": lambda: handle_run_job_search(),
        "post_linkedin_now": lambda: handle_post_linkedin(),
        "get_briefing": lambda: handle_get_briefing(),
        "list_jobs_queue": lambda: handle_list_jobs_queue(),
        "mark_job_applied": lambda: handle_mark_applied(
            inputs["company"], inputs["role"]
        ),
    }
    handler = handlers.get(name)
    if not handler:
        return f"Unknown tool: {name}"
    return handler()


if __name__ == "__main__":
    # Print tool schemas for inspection
    print(json.dumps(TOOL_SCHEMAS, indent=2))
