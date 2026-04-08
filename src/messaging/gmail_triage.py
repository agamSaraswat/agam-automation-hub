"""
Gmail triage — scan inbox, Claude classifies and summarizes.

Uses Gmail API (OAuth2) with readonly + compose scopes.
NEVER auto-sends emails. Draft only, human reviews via Telegram.
"""

import os
import base64
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def _get_gmail_service():
    """Build and return the Gmail API service object."""
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds_path = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
    token_path = os.getenv("GMAIL_TOKEN_PATH", "token.json")
    scopes = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.compose",
    ]

    creds = None
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(creds_path):
                raise FileNotFoundError(
                    f"Gmail credentials file not found: {creds_path}\n"
                    "Download it from Google Cloud Console → APIs → Credentials → OAuth 2.0"
                )
            flow = InstalledAppFlow.from_client_secrets_file(creds_path, scopes)
            creds = flow.run_local_server(port=0)

        with open(token_path, "w") as token_file:
            token_file.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


def get_unread_count() -> int:
    """Get the count of unread emails in the inbox."""
    try:
        service = _get_gmail_service()
        results = service.users().messages().list(
            userId="me", q="is:unread in:inbox", maxResults=1
        ).execute()
        return results.get("resultSizeEstimate", 0)
    except Exception as exc:
        logger.error("Gmail unread count error: %s", exc)
        return -1


def get_recent_emails(minutes: int = 30, max_results: int = 10) -> list[dict]:
    """
    Fetch recent unread emails from the last N minutes.
    Returns list of dicts with: id, subject, sender, snippet, date.
    """
    try:
        service = _get_gmail_service()
        after = datetime.now() - timedelta(minutes=minutes)
        after_epoch = int(after.timestamp())

        results = service.users().messages().list(
            userId="me",
            q=f"is:unread in:inbox after:{after_epoch}",
            maxResults=max_results,
        ).execute()

        messages = results.get("messages", [])
        emails = []

        for msg_ref in messages:
            msg = service.users().messages().get(
                userId="me", id=msg_ref["id"], format="metadata",
                metadataHeaders=["From", "Subject", "Date"],
            ).execute()

            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "id": msg_ref["id"],
                "subject": headers.get("Subject", "(no subject)"),
                "sender": headers.get("From", "unknown"),
                "snippet": msg.get("snippet", ""),
                "date": headers.get("Date", ""),
            })

        return emails

    except Exception as exc:
        logger.error("Gmail fetch error: %s", exc)
        return []


def classify_and_summarize(emails: list[dict]) -> list[dict]:
    """
    Use Claude to classify emails and generate reply drafts for urgent ones.
    Categories: urgent, normal, newsletter, spam
    """
    if not emails:
        return []

    from src.agent.claude_client import ClaudeClient

    client = ClaudeClient()

    email_summaries = "\n".join(
        f"- Subject: {e['subject']}\n  From: {e['sender']}\n  Preview: {e['snippet'][:150]}"
        for e in emails
    )

    prompt = f"""Classify these emails and provide brief summaries.

EMAILS:
{email_summaries}

For each email, respond with:
EMAIL: <subject>
CATEGORY: <urgent|normal|newsletter|spam>
SUMMARY: <1 sentence summary>
DRAFT_REPLY: <if urgent, suggest a brief reply; otherwise write "N/A">

Be concise. Focus on what Agam needs to act on."""

    system = (
        "You are Agam's email assistant. Classify emails by urgency. "
        "Urgent = needs response within hours (from boss, clients, time-sensitive). "
        "Normal = can wait. Newsletter = marketing/digest. Spam = obvious junk."
    )

    try:
        result = client.complete(prompt, system=system, temperature=0.2)
        # Parse results back into structured data
        classified = []
        for email in emails:
            entry = {**email, "category": "normal", "summary": email["snippet"][:100], "draft_reply": None}
            # Simple extraction from Claude's response
            for block in result.split("EMAIL:"):
                if email["subject"][:30] in block:
                    if "CATEGORY:" in block:
                        cat_line = block.split("CATEGORY:")[1].split("\n")[0].strip().lower()
                        if cat_line in ("urgent", "normal", "newsletter", "spam"):
                            entry["category"] = cat_line
                    if "SUMMARY:" in block:
                        entry["summary"] = block.split("SUMMARY:")[1].split("\n")[0].strip()
                    if "DRAFT_REPLY:" in block:
                        draft = block.split("DRAFT_REPLY:")[1].split("\nEMAIL:")[0].strip()
                        if draft.lower() != "n/a":
                            entry["draft_reply"] = draft
                    break
            classified.append(entry)
        return classified
    except Exception as exc:
        logger.error("Classification error: %s", exc)
        return [{**e, "category": "normal", "summary": e["snippet"][:100], "draft_reply": None} for e in emails]


def create_draft(to: str, subject: str, body: str) -> str:
    """
    Create a Gmail draft (NOT send). Human must review and send manually.
    Returns the draft ID.
    """
    try:
        service = _get_gmail_service()
        message = MIMEText(body)
        message["to"] = to
        message["subject"] = f"Re: {subject}"

        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        draft = service.users().drafts().create(
            userId="me", body={"message": {"raw": raw}}
        ).execute()

        draft_id = draft.get("id", "unknown")
        logger.info("Gmail draft created: %s", draft_id)
        return draft_id
    except Exception as exc:
        logger.error("Draft creation error: %s", exc)
        return f"Error: {exc}"


def run_triage() -> str:
    """
    Run the full Gmail triage pipeline.
    Returns a summary string suitable for Telegram.
    """
    emails = get_recent_emails(minutes=30)
    if not emails:
        return "📧 No new emails in the last 30 minutes."

    classified = classify_and_summarize(emails)

    urgent = [e for e in classified if e["category"] == "urgent"]
    normal = [e for e in classified if e["category"] == "normal"]
    newsletters = [e for e in classified if e["category"] == "newsletter"]

    lines = [f"📧 Gmail Triage — {len(emails)} new emails\n"]

    if urgent:
        lines.append("🔴 URGENT:")
        for e in urgent:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['sender']}")
            lines.append(f"    {e['summary']}")
            if e.get("draft_reply"):
                lines.append(f"    💬 Suggested reply: {e['draft_reply'][:200]}")
        lines.append("")

    if normal:
        lines.append(f"🟡 Normal: {len(normal)} emails")
        for e in normal[:3]:
            lines.append(f"  • {e['subject']} — {e['sender']}")
        lines.append("")

    if newsletters:
        lines.append(f"📰 Newsletters: {len(newsletters)}")

    return "\n".join(lines)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    print(run_triage())
