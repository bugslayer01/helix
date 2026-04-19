"""LenderCo FastAPI entrypoint — port 8001."""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from customer_portal.backend import db
from customer_portal.backend.routes import applications, cases, hiring, operator, webhooks


def create_app() -> FastAPI:
    app = FastAPI(title="LenderCo", description="Dummy customer portal (B2B pilot stand-in)", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5174", "http://localhost:5173"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _startup() -> None:
        db.init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "lenderco", "version": "0.1.0"}

    app.include_router(applications.router)
    app.include_router(cases.router)
    app.include_router(webhooks.router)
    app.include_router(operator.router)
    app.include_router(hiring.router)
    return app


app = create_app()
