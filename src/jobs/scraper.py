"""
Job scraper using only free, no-auth sources.

Sources:
  - RemoteOK API (JSON, no auth)
  - Himalayas API (JSON, no auth)
  - Indeed RSS feeds
  - LinkedIn Jobs page scraping (fallback)

All jobs are deduplicated before being queued.
"""

import os
import json
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

import requests
import feedparser
import yaml
from bs4 import BeautifulSoup

from src.jobs.deduplicator import init_db, add_job, count_todays_jobs
from src.jobs.filtering import apply_relevance_filter

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "job_search.yaml"
REQUEST_TIMEOUT = 15
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def load_config() -> dict:
    """Load job search configuration."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def _get_daily_limit() -> int:
    """Get daily job limit from env override or settings.yaml fallback."""
    env_value = os.getenv("DAILY_JOB_LIMIT", "").strip()
    if env_value:
        try:
            return max(1, int(env_value))
        except ValueError:
            logger.warning("Invalid DAILY_JOB_LIMIT env value '%s'; falling back to settings.yaml", env_value)

    settings_path = Path(__file__).resolve().parent.parent.parent / "config" / "settings.yaml"
    try:
        with open(settings_path, "r", encoding="utf-8") as settings_file:
            settings_cfg = yaml.safe_load(settings_file) or {}
        return max(1, int(settings_cfg.get("jobs", {}).get("daily_limit", 10)))
    except Exception as exc:
        logger.warning("Unable to read daily_limit from settings.yaml: %s", exc)
        return 10


def _clean_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    if not html:
        return ""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(separator=" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


# ════════════════════════════════════════
# RemoteOK
# ════════════════════════════════════════

def scrape_remoteok(config: dict) -> list[dict]:
    """Fetch jobs from RemoteOK API."""
    jobs = []
    src_cfg = config.get("sources", {}).get("remoteok", {})
    if not src_cfg.get("enabled", False):
        return jobs

    url = src_cfg.get("url", "https://remoteok.com/api")
    try:
        resp = requests.get(
            url,
            headers={**HEADERS, "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()

        # First element is metadata, skip it
        for item in data[1:]:
            title = item.get("position", "")
            company = item.get("company", "")
            job_url = item.get("url", "")
            location = item.get("location", "Remote")
            description = _clean_html(item.get("description", ""))
            tags = item.get("tags", [])

            jobs.append({
                "title": title,
                "company": company,
                "url": job_url,
                "location": location,
                "jd_text": description[:5000],
                "source": "remoteok",
                "tags": tags,
            })
        logger.info("RemoteOK: found %d raw jobs", len(jobs))
    except Exception as exc:
        logger.error("RemoteOK scrape failed: %s", exc)

    return jobs


# ════════════════════════════════════════
# Himalayas
# ════════════════════════════════════════

def scrape_himalayas(config: dict) -> list[dict]:
    """Fetch jobs from Himalayas API."""
    jobs = []
    src_cfg = config.get("sources", {}).get("himalayas", {})
    if not src_cfg.get("enabled", False):
        return jobs

    base_url = src_cfg.get("url", "https://himalayas.app/jobs/api")
    categories = src_cfg.get("categories", ["data-science"])

    for category in categories:
        try:
            params = {"category": category, "limit": 25}
            resp = requests.get(
                base_url,
                params=params,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("jobs", []):
                title = item.get("title", "")
                company = item.get("companyName", "")
                job_url = item.get("applicationLink", "") or item.get("url", "")
                location = item.get("location", "Remote")
                description = _clean_html(item.get("description", ""))

                if not job_url:
                    continue

                jobs.append({
                    "title": title,
                    "company": company,
                    "url": job_url,
                    "location": location,
                    "jd_text": description[:5000],
                    "source": "himalayas",
                })
            logger.info("Himalayas [%s]: found %d jobs", category, len(data.get("jobs", [])))
        except Exception as exc:
            logger.error("Himalayas scrape [%s] failed: %s", category, exc)

    return jobs


# ════════════════════════════════════════
# Indeed RSS
# ════════════════════════════════════════

def scrape_indeed_rss(config: dict) -> list[dict]:
    """Fetch jobs from Indeed RSS feeds."""
    jobs = []
    src_cfg = config.get("sources", {}).get("indeed_rss", {})
    if not src_cfg.get("enabled", False):
        return jobs

    base_url = src_cfg.get("base_url", "https://www.indeed.com/rss")
    keywords = config.get("keywords", {}).get("primary", [])[:3]
    locations = config.get("locations", ["Remote"])[:2]

    for kw in keywords:
        for loc in locations:
            try:
                url = f"{base_url}?q={requests.utils.quote(kw)}&l={requests.utils.quote(loc)}"
                feed = feedparser.parse(url)
                for entry in feed.entries[:10]:
                    title = entry.get("title", "")
                    link = entry.get("link", "")
                    description = _clean_html(entry.get("summary", ""))

                    # Extract company from title if formatted as "Title - Company"
                    company = "Unknown"
                    if " - " in title:
                        parts = title.rsplit(" - ", 1)
                        title = parts[0].strip()
                        company = parts[1].strip()

                    jobs.append({
                        "title": title,
                        "company": company,
                        "url": link,
                        "location": loc,
                        "jd_text": description[:5000],
                        "source": "indeed",
                    })
                logger.info("Indeed RSS [%s, %s]: %d entries", kw, loc, len(feed.entries))
            except Exception as exc:
                logger.error("Indeed RSS failed [%s]: %s", kw, exc)

    return jobs


# ════════════════════════════════════════
# Main scraper orchestrator
# ════════════════════════════════════════

def run_scraper() -> int:
    """
    Run all scrapers and add new jobs to the database.
    Returns the count of newly added jobs.
    """
    init_db()
    config = load_config()

    current_count = count_todays_jobs()
    daily_limit = _get_daily_limit()
    remaining = daily_limit - current_count
    if remaining <= 0:
        logger.info("Daily limit reached (%d). Skipping scrape.", daily_limit)
        return 0

    # Collect from all sources
    all_jobs: list[dict] = []
    all_jobs.extend(scrape_remoteok(config))
    all_jobs.extend(scrape_himalayas(config))
    all_jobs.extend(scrape_indeed_rss(config))

    logger.info("Total raw jobs collected: %d", len(all_jobs))

    kept_jobs, rejected_jobs = apply_relevance_filter(all_jobs, config)
    logger.info(
        "Relevance filter kept %d jobs and rejected %d jobs",
        len(kept_jobs),
        len(rejected_jobs),
    )
    _write_filter_report(kept_jobs=kept_jobs, rejected_jobs=rejected_jobs)

    # Add to DB, respecting daily limit
    added = 0
    for job in kept_jobs:
        if added >= remaining:
            break
        was_added = add_job(
            url=job["url"],
            company=job["company"],
            title=job["title"],
            location=job.get("location", ""),
            jd_text=job.get("jd_text", ""),
            source=job.get("source", ""),
            status="queued",
        )
        if was_added:
            added += 1

    logger.info("Added %d new jobs to queue (daily total: %d)", added, current_count + added)
    return added


def _write_filter_report(kept_jobs: list[dict], rejected_jobs: list[dict]) -> None:
    """Write explainable keep/reject decisions for auditing relevance."""
    out_dir = Path(__file__).resolve().parent.parent.parent / "output" / "jobs" / date.today().isoformat()
    out_dir.mkdir(parents=True, exist_ok=True)
    report_path = out_dir / "filtering_report.jsonl"

    with open(report_path, "w", encoding="utf-8") as f:
        for job in kept_jobs:
            row = {
                "decision": "kept",
                "score": job.get("match_score", 0),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "source": job.get("source", ""),
                "location": job.get("location", ""),
                "reasons": job.get("reasons", []),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

        for job in rejected_jobs:
            row = {
                "decision": "rejected",
                "score": job.get("match_score", 0),
                "title": job.get("title", ""),
                "company": job.get("company", ""),
                "source": job.get("source", ""),
                "location": job.get("location", ""),
                "reject_reason": job.get("reject_reason", ""),
                "reasons": job.get("reasons", []),
            }
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = run_scraper()
    print(f"\nScraper complete. {count} new jobs added.")
