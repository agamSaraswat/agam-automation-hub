"""LinkedIn draft review workflow helpers shared by API and CLI-like flows."""

from __future__ import annotations

import os
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml

from src.linkedin.generator import generate_post
from src.linkedin.publisher import publish_post

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
QUEUE_DIR = REPO_ROOT / "output" / "linkedin" / "queue"


def _today_queue_file() -> Path:
    return QUEUE_DIR / f"{date.today().isoformat()}.md"


def _publish_supported() -> bool:
    return bool(os.getenv("LINKEDIN_ACCESS_TOKEN")) and bool(os.getenv("LINKEDIN_PERSON_URN"))


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    if not text.startswith("---"):
        return {}, text.strip()

    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text.strip()

    metadata = yaml.safe_load(parts[1]) or {}
    if not isinstance(metadata, dict):
        metadata = {}
    return metadata, parts[2].strip()


def _serialize(metadata: dict[str, Any], content: str) -> str:
    frontmatter = yaml.safe_dump(metadata, sort_keys=False).strip()
    return f"---\n{frontmatter}\n---\n\n{content.strip()}\n"


def _read_current() -> tuple[dict[str, Any], str, bool]:
    queue_file = _today_queue_file()
    if not queue_file.exists():
        return {}, "", False
    metadata, content = _split_frontmatter(queue_file.read_text(encoding="utf-8"))
    return metadata, content, True


def _write_current(metadata: dict[str, Any], content: str) -> None:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    queue_file = _today_queue_file()
    queue_file.write_text(_serialize(metadata, content), encoding="utf-8")


def get_draft_snapshot() -> dict[str, Any]:
    metadata, content, exists = _read_current()
    status = metadata.get("status", "missing") if exists else "missing"
    return {
        "today": date.today().isoformat(),
        "exists": exists,
        "content": content,
        "metadata": metadata,
        "status": status,
        "publish_supported": _publish_supported(),
    }


def generate_draft() -> dict[str, Any]:
    generated = generate_post()
    if not generated:
        return get_draft_snapshot()
    return get_draft_snapshot()


def save_draft_edits(content: str) -> dict[str, Any]:
    metadata, _, exists = _read_current()
    if not exists:
        metadata = {
            "date": date.today().isoformat(),
            "status": "edited",
            "edited_at": datetime.now().isoformat(),
        }
    else:
        metadata["status"] = "edited"
        metadata["edited_at"] = datetime.now().isoformat()

    _write_current(metadata, content)
    return get_draft_snapshot()


def set_draft_decision(approved: bool) -> dict[str, Any]:
    metadata, content, exists = _read_current()
    if not exists:
        raise ValueError("No LinkedIn draft found for today.")

    metadata["status"] = "approved" if approved else "rejected"
    metadata["reviewed_at"] = datetime.now().isoformat()
    _write_current(metadata, content)
    return get_draft_snapshot()


def publish_approved_draft(confirm_publish: bool) -> str:
    if not confirm_publish:
        raise ValueError("Publish cancelled: explicit confirmation is required.")

    metadata, content, exists = _read_current()
    if not exists:
        raise ValueError("No LinkedIn draft found for today.")

    if metadata.get("status") != "approved":
        raise ValueError("Draft must be approved before publishing.")

    if not _publish_supported():
        raise ValueError("Publishing is disabled: missing LinkedIn credentials.")

    return publish_post(content)
