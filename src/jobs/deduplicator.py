"""
SQLite-based job deduplication and status tracking.

Table: seen_jobs(id, url, company, title, location, date_seen, status, jd_text)
Status values: 'seen', 'queued', 'tailored', 'applied', 'rejected'
"""

import sqlite3
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "jobs.db"

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS seen_jobs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    url         TEXT UNIQUE NOT NULL,
    company     TEXT NOT NULL,
    title       TEXT NOT NULL,
    location    TEXT DEFAULT '',
    date_seen   TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'seen',
    jd_text     TEXT DEFAULT '',
    source      TEXT DEFAULT ''
);
"""


def init_db() -> None:
    """Create the database and table if they don't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(CREATE_TABLE_SQL)
    conn.commit()
    conn.close()
    logger.info("Jobs database initialised at %s", DB_PATH)


def is_seen(url: str) -> bool:
    """Check if a job URL has already been recorded."""
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT 1 FROM seen_jobs WHERE url = ?", (url,)
    ).fetchone()
    conn.close()
    return row is not None


def add_job(
    url: str,
    company: str,
    title: str,
    location: str = "",
    jd_text: str = "",
    source: str = "",
    status: str = "seen",
) -> bool:
    """
    Insert a new job if it hasn't been seen before.
    Returns True if inserted, False if duplicate.
    """
    if is_seen(url):
        return False
    conn = sqlite3.connect(str(DB_PATH))
    try:
        conn.execute(
            "INSERT INTO seen_jobs (url, company, title, location, date_seen, status, jd_text, source) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (url, company, title, location, date.today().isoformat(), status, jd_text, source),
        )
        conn.commit()
        logger.info("Added job: %s @ %s", title, company)
        return True
    except sqlite3.IntegrityError:
        logger.debug("Duplicate job URL skipped: %s", url)
        return False
    finally:
        conn.close()


def get_todays_queue(limit: int = 10) -> list[dict]:
    """Get today's queued jobs, respecting the daily limit."""
    today = date.today().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM seen_jobs "
        "WHERE date_seen = ? AND status IN ('queued', 'tailored') "
        "ORDER BY id ASC LIMIT ?",
        (today, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def count_todays_jobs() -> int:
    """Count how many jobs have been queued today."""
    today = date.today().isoformat()
    conn = sqlite3.connect(str(DB_PATH))
    row = conn.execute(
        "SELECT COUNT(*) FROM seen_jobs WHERE date_seen = ?", (today,)
    ).fetchone()
    conn.close()
    return row[0] if row else 0


def update_status(url: str, status: str) -> None:
    """Update the status of a job by URL."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE seen_jobs SET status = ? WHERE url = ?", (status, url)
    )
    conn.commit()
    conn.close()
    logger.info("Updated job %s → %s", url[:60], status)


def get_all_jobs(status: Optional[str] = None, limit: int = 50) -> list[dict]:
    """Retrieve jobs, optionally filtered by status."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    if status:
        rows = conn.execute(
            "SELECT * FROM seen_jobs WHERE status = ? ORDER BY date_seen DESC LIMIT ?",
            (status, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM seen_jobs ORDER BY date_seen DESC LIMIT ?",
            (limit,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_stats() -> dict:
    """Return aggregate stats for the status dashboard."""
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT COUNT(*) FROM seen_jobs").fetchone()[0]
    by_status = {}
    for row in conn.execute(
        "SELECT status, COUNT(*) FROM seen_jobs GROUP BY status"
    ).fetchall():
        by_status[row[0]] = row[1]
    today_count = count_todays_jobs()
    conn.close()
    return {
        "total_jobs": total,
        "by_status": by_status,
        "today_queued": today_count,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    init_db()
    # Quick test
    added = add_job(
        url="https://example.com/test-job",
        company="TestCorp",
        title="Senior Data Scientist",
        location="Remote",
        jd_text="Looking for an experienced DS...",
        source="test",
        status="queued",
    )
    print(f"Added: {added}")
    print(f"Stats: {get_stats()}")
