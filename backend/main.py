from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes import audit, contest, evaluate, review
from services import audit_log, evidence_store


def create_app() -> FastAPI:
    app = FastAPI(
        title="Recourse",
        description="Model decision contestation API",
        version="0.1.0",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.on_event("startup")
    def _init() -> None:
        audit_log.init_db()
        evidence_store.init_db()

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    app.include_router(evaluate.router)
    app.include_router(contest.router)
    app.include_router(review.router)
    app.include_router(audit.router)

    return app


app = create_app()
