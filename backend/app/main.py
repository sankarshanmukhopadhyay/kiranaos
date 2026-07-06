import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import Base, SessionLocal, engine
from app.services.auth import ensure_default_store
from app.services.security import assert_secure_runtime_config, cors_origins


def create_app() -> FastAPI:
    settings = get_settings()
    logging.basicConfig(level=settings.log_level.upper())
    assert_secure_runtime_config()

    # Create all tables on startup (SQLite dev convenience).
    # For production Postgres, use Alembic migrations instead.
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ensure_default_store(db)
    finally:
        db.close()

    app = FastAPI(
        title="KiranaOS API",
        version="2.2.0",
        description=(
            "WhatsApp-native order management for kirana stores. "
            "Converts inbound messages into structured orders. "
            "Tracks udhaari, dormant customers, and item-level analytics."
        ),
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins(),
        allow_credentials=(settings.frontend_origin != "*"),
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api")
    return app


app = create_app()
