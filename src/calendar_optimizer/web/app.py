"""FastAPI application factory."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from calendar_optimizer.web.routes_auth import router as auth_router
from calendar_optimizer.web.routes_calendar import router as calendar_router
from calendar_optimizer.web.routes_optimize import router as optimize_router
from calendar_optimizer.web.static import mount_static


def create_app() -> FastAPI:
    app = FastAPI(title="Calendar Optimizer", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(calendar_router, prefix="/api/calendar", tags=["calendar"])
    app.include_router(optimize_router, prefix="/api/optimize", tags=["optimize"])
    app.include_router(auth_router, prefix="/api/auth", tags=["auth"])

    mount_static(app)

    return app


app = create_app()
