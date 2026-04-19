"""Recourse FastAPI — port 8000."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend import db
from backend.routes import audit, contest, evidence, handoff, operator, review


def create_app() -> FastAPI:
    app = FastAPI(
        title="Recourse",
        description="Model decision contestation API",
        version="1.0.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://localhost:5174",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        db.init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "recourse", "version": "1.0.0"}

    app.include_router(handoff.router)
    app.include_router(evidence.router)
    app.include_router(contest.router)
    app.include_router(contest.revoke_router)
    app.include_router(audit.router)
    app.include_router(operator.router)
    app.include_router(review.router)
    return app


app = create_app()
