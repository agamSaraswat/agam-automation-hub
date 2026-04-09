"""FastAPI entrypoint for the backend web API."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.web.routers.briefing import router as briefing_router
from src.web.routers.gmail import router as gmail_router
from src.web.routers.health import router as health_router
from src.web.routers.jobs import router as jobs_router
from src.web.routers.linkedin import router as linkedin_router
from src.web.routers.status import router as status_router
from src.web.config import get_cors_origins


app = FastAPI(
    title="Agam Automation Hub API",
    version="0.1.0",
    description="Initial web API skeleton for the automation hub.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(health_router)
app.include_router(status_router)
app.include_router(jobs_router)
app.include_router(briefing_router)
app.include_router(gmail_router)
app.include_router(linkedin_router)
