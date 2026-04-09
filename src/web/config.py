"""Configuration helpers for the FastAPI web layer."""

from __future__ import annotations

import os


DEFAULT_DEV_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def get_cors_origins() -> list[str]:
    """Return allowed CORS origins for the web API."""
    raw = os.getenv("WEB_CORS_ORIGINS", "")
    if not raw.strip():
        return DEFAULT_DEV_ORIGINS
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
