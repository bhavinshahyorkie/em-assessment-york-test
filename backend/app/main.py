"""
FastAPI application factory: middleware + route registration only.

Business logic: `app/services/`. HTTP handlers: `app/api/routes/`. Settings: `app/core/`.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, match

app = FastAPI(title="Talent Intelligence & Ranking Engine", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(match.router)
