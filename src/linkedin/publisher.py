"""
LinkedIn UGC Posts API publisher.

Publishes approved posts via the LinkedIn API v2.
NEVER called directly — always goes through reviewer.py gate.
"""

import os
import json
import logging
import shutil
from datetime import date, datetime
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

POSTED_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "linkedin" / "posted"
QUEUE_DIR = Path(__file__).resolve().parent.parent.parent / "output" / "linkedin" / "queue"

API_URL = "https://api.linkedin.com/v2/ugcPosts"


def _check_token_expiry() -> str | None:
    """Warn if LinkedIn token is close to expiring (60-day lifecycle)."""
    set_date_str = os.getenv("LINKEDIN_TOKEN_SET_DATE", "")
    if not set_date_str:
        return "LINKEDIN_TOKEN_SET_DATE not set — cannot check token expiry."
    try:
        set_date = datetime.strptime(set_date_str, "%Y-%m-%d").date()
        age_days = (date.today() - set_date).days
        if age_days > 50:
            return (
                f"⚠️ LinkedIn token is {age_days} days old (expires at ~60 days). "
                f"Refresh at: https://www.linkedin.com/developers/tools/oauth/token-generator"
            )
        return None
    except ValueError:
        return "Invalid LINKEDIN_TOKEN_SET_DATE format. Use YYYY-MM-DD."


def publish_post(content: str) -> str:
    """
    Publish a text post to LinkedIn via UGC Posts API.

    Args:
        content: The post text to publish.

    Returns:
        Status message (success or error detail).
    """
    token = os.getenv("LINKEDIN_ACCESS_TOKEN")
    person_urn = os.getenv("LINKEDIN_PERSON_URN")

    if not token:
        raise EnvironmentError("LINKEDIN_ACCESS_TOKEN not set in .env")
    if not person_urn:
        raise EnvironmentError("LINKEDIN_PERSON_URN not set in .env")

    # Check token expiry
    warning = _check_token_expiry()
    if warning:
        logger.warning(warning)

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
        "LinkedIn-Version": "202401",
    }

    payload = {
        "author": person_urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {
                    "text": content,
                },
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {
            "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC",
        },
    }

    try:
        resp = requests.post(API_URL, headers=headers, json=payload, timeout=30)
        resp.raise_for_status()

        # Archive the posted content
        _archive_post(content)

        result = resp.json() if resp.text else {}
        post_id = result.get("id", "unknown")
        logger.info("LinkedIn post published: %s", post_id)
        return f"Published (ID: {post_id})"

    except requests.exceptions.HTTPError as exc:
        error_body = exc.response.text if exc.response else "No response body"
        logger.error("LinkedIn API error: %s — %s", exc, error_body)
        raise RuntimeError(f"LinkedIn API error: {exc.response.status_code} — {error_body}")
    except requests.exceptions.RequestException as exc:
        logger.error("LinkedIn request failed: %s", exc)
        raise


def _archive_post(content: str) -> None:
    """Move the posted content to the archive directory."""
    POSTED_DIR.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    archive_file = POSTED_DIR / f"{today}.md"

    archive_file.write_text(
        f"---\ndate: {today}\nposted_at: {datetime.now().isoformat()}\n---\n\n{content}",
        encoding="utf-8",
    )

    # Remove from queue if it exists
    queue_file = QUEUE_DIR / f"{today}.md"
    if queue_file.exists():
        queue_file.unlink()

    logger.info("Archived posted content to %s", archive_file)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    warning = _check_token_expiry()
    if warning:
        print(warning)
    else:
        print("LinkedIn token status: OK")
