"""Request and response schemas for the web API."""

from __future__ import annotations

from pydantic import BaseModel


class OptimizeRequest(BaseModel):
    timezone: str = "Europe/Berlin"
    week_start: str | None = None
    day_start: str = "07:00"
    day_end: str = "07:00"


class OptimizeStartResponse(BaseModel):
    session_id: str


class AuthStatusResponse(BaseModel):
    authenticated: bool
    email: str | None = None
