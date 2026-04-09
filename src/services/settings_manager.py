"""Settings read/write service for non-secret automation configuration."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from src.services.automation import get_environment_status

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
JOB_SEARCH_PATH = REPO_ROOT / "config" / "job_search.yaml"
SETTINGS_PATH = REPO_ROOT / "config" / "settings.yaml"

EDITABLE_FIELDS = [
    "target_roles",
    "locations",
    "include_keywords",
    "exclude_keywords",
    "daily_job_limit",
    "posting_time_window",
    "job_sources",
]

FILE_BASED_NOTES = [
    "Secrets (API keys/tokens) remain file/env-based and are never exposed in this API.",
    "Advanced scraper filters (title lists, match threshold, company exclusions) remain in config/job_search.yaml.",
    "Non-editable scheduler tasks remain in config/settings.yaml.",
]


def _read_yaml(path: Path) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as file:
        payload = yaml.safe_load(file) or {}
    return payload if isinstance(payload, dict) else {}


def _atomic_write_yaml(path: Path, payload: dict[str, Any]) -> None:
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as file:
        yaml.safe_dump(payload, file, sort_keys=False)
    tmp_path.replace(path)


def get_settings_payload() -> dict[str, Any]:
    job_cfg = _read_yaml(JOB_SEARCH_PATH)
    app_cfg = _read_yaml(SETTINGS_PATH)

    source_cfg = job_cfg.get("sources", {})
    sources_enabled = {
        source_name: bool((source_data or {}).get("enabled", False))
        for source_name, source_data in source_cfg.items()
        if isinstance(source_data, dict)
    }

    environment = get_environment_status()
    secret_status = {
        key: {
            "configured": bool(value.get("set", False)),
            "description": value.get("description", ""),
        }
        for key, value in environment.items()
    }

    return {
        "target_roles": list(job_cfg.get("target_roles", [])),
        "locations": list(job_cfg.get("locations", [])),
        "include_keywords": list(job_cfg.get("filters", {}).get("include_keywords", [])),
        "exclude_keywords": list(job_cfg.get("filters", {}).get("exclude_keywords", [])),
        "daily_job_limit": int(app_cfg.get("jobs", {}).get("daily_limit", 10)),
        "posting_time_window": {
            "start_hour": int(app_cfg.get("schedule", {}).get("linkedin_post_window_start", 8)),
            "end_hour": int(app_cfg.get("schedule", {}).get("linkedin_post_window_end", 11)),
        },
        "job_sources": sources_enabled,
        "secret_status": secret_status,
        "editable_fields": EDITABLE_FIELDS,
        "file_based_notes": FILE_BASED_NOTES,
    }


def update_settings_payload(update_data: dict[str, Any]) -> dict[str, Any]:
    job_cfg = _read_yaml(JOB_SEARCH_PATH)
    app_cfg = _read_yaml(SETTINGS_PATH)

    next_job_cfg = deepcopy(job_cfg)
    next_app_cfg = deepcopy(app_cfg)

    next_job_cfg["target_roles"] = list(update_data["target_roles"])
    next_job_cfg["locations"] = list(update_data["locations"])

    filters = next_job_cfg.setdefault("filters", {})
    filters["include_keywords"] = list(update_data["include_keywords"])
    filters["exclude_keywords"] = list(update_data["exclude_keywords"])

    jobs = next_app_cfg.setdefault("jobs", {})
    jobs["daily_limit"] = int(update_data["daily_job_limit"])

    schedule = next_app_cfg.setdefault("schedule", {})
    schedule["linkedin_post_window_start"] = int(update_data["posting_time_window"]["start_hour"])
    schedule["linkedin_post_window_end"] = int(update_data["posting_time_window"]["end_hour"])

    sources = next_job_cfg.setdefault("sources", {})
    for source_name, enabled in update_data["job_sources"].items():
        source_entry = sources.get(source_name)
        if isinstance(source_entry, dict):
            source_entry["enabled"] = bool(enabled)

    _atomic_write_yaml(JOB_SEARCH_PATH, next_job_cfg)
    _atomic_write_yaml(SETTINGS_PATH, next_app_cfg)

    return get_settings_payload()
