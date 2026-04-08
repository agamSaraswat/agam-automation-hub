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

logger = logging.getLogger(__name__)

CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config" / "job_search.yaml"
DAILY_LIMIT = int(os.getenv("DAILY_JOB_LIMIT", "10"))
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

            # Filter: check if relevant to DS/ML
            title_lower = title.lower()
            keywords = config.get("keywords", {}).get("primary", [])
            tag_str = " ".join(tags).lower()
            relevant = any(
                kw.lower() in title_lower or kw.lower() in tag_str
                for kw in ["data", "machine learning", "ml", "ai", "nlp", "scientist", "analytics"]
            )
            if not relevant:
                continue

            jobs.append({
                "title": title,
                "company": company,
                "url": job_url,
                "location": location,
                "jd_text": description[:5000],
                "source": "remoteok",
            })
        logger.info("RemoteOK: found %d relevant jobs", len(jobs))
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
    remaining = DAILY_LIMIT - current_count
    if remaining <= 0:
        logger.info("Daily limit reached (%d). Skipping scrape.", DAILY_LIMIT)
        return 0

    # Collect from all sources
    all_jobs: list[dict] = []
    all_jobs.extend(scrape_remoteok(config))
    all_jobs.extend(scrape_himalayas(config))
    all_jobs.extend(scrape_indeed_rss(config))

    logger.info("Total raw jobs collected: %d", len(all_jobs))

    # Filter by excluded titles
    exclude_titles = [t.lower() for t in config.get("filters", {}).get("exclude_titles", [])]
    filtered = []
    for job in all_jobs:
        title_lower = job["title"].lower()
        if any(ex in title_lower for ex in exclude_titles):
            continue
        filtered.append(job)

    # Add to DB, respecting daily limit
    added = 0
    for job in filtered:
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


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    count = run_scraper()
    print(f"\nScraper complete. {count} new jobs added.")
