"""Lightweight persistent run history for backend task observability."""

from __future__ import annotations

import json
import re
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
RUN_HISTORY_PATH = REPO_ROOT / "output" / "runs" / "history.jsonl"
_LOCK = threading.Lock()
_MAX_SUMMARY_LENGTH = 400
_MAX_ERROR_LENGTH = 800


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _normalize_status(status: str) -> str:
    if status.lower() in {"success", "ok", "completed"}:
        return "success"
    if status.lower() in {"failed", "error"}:
        return "failed"
    return status.lower()


def _redact_sensitive(text: str | None) -> str | None:
    if not text:
        return text

    redacted = text
    patterns = [
        r"sk-ant-[A-Za-z0-9_-]{10,}",
        r"Bearer\s+[A-Za-z0-9._\-]{10,}",
        r"(token|api[_-]?key|password)\s*[=:]\s*[^\s,;]+",
    ]
    for pattern in patterns:
        redacted = re.sub(pattern, "[REDACTED]", redacted, flags=re.IGNORECASE)

    return redacted[:_MAX_ERROR_LENGTH]


def _safe_summary(summary: str) -> str:
    cleaned = (summary or "").strip() or "Task completed"
    return cleaned[:_MAX_SUMMARY_LENGTH]


def append_run_record(
    *,
    task_type: str,
    start_time: str,
    end_time: str,
    status: str,
    summary: str,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Append a run record to jsonl storage."""
    record = {
        "run_id": uuid.uuid4().hex,
        "task_type": task_type,
        "start_time": start_time,
        "end_time": end_time,
        "status": _normalize_status(status),
        "summary": _safe_summary(summary),
        "error_message": _redact_sensitive(error_message),
    }

    RUN_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _LOCK:
        with open(RUN_HISTORY_PATH, "a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")

    return record


def get_recent_runs(limit: int = 25) -> list[dict[str, Any]]:
    """Read recent runs ordered newest first."""
    if not RUN_HISTORY_PATH.exists():
        return []

    rows: list[dict[str, Any]] = []
    with _LOCK:
        with open(RUN_HISTORY_PATH, "r", encoding="utf-8") as file:
            for line in file:
                raw = line.strip()
                if not raw:
                    continue
                try:
                    payload = json.loads(raw)
                    if isinstance(payload, dict) and payload.get("run_id") and payload.get("task_type"):
                        rows.append(payload)
                except json.JSONDecodeError:
                    continue

    return list(reversed(rows[-limit:]))


def run_with_history(task_type: str, summary_builder: Callable[[Any], str], fn: Callable[[], Any]) -> Any:
    """Execute task function and persist run result with summary + failure details."""
    start_time = _now_iso()
    try:
        result = fn()
        try:
            summary = _safe_summary(summary_builder(result))
        except Exception:
            summary = f"{task_type} run completed"

        append_run_record(
            task_type=task_type,
            start_time=start_time,
            end_time=_now_iso(),
            status="success",
            summary=summary,
            error_message=None,
        )
        return result
    except Exception as exc:
        append_run_record(
            task_type=task_type,
            start_time=start_time,
            end_time=_now_iso(),
            status="failed",
            summary=f"{task_type} run failed",
            error_message=str(exc),
        )
        raise
