"""Router helper utilities."""

from __future__ import annotations

import logging

from fastapi import HTTPException

logger = logging.getLogger(__name__)


def raise_internal(message: str, exc: Exception) -> None:
    """Log exception and raise HTTP 500 with a safe message."""
    logger.exception("%s: %s", message, exc)
    raise HTTPException(status_code=500, detail=message) from exc
