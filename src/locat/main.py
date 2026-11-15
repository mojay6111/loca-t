"""Loca-T application entry point."""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlalchemy.orm import Session

from locat.api.routes_ussd import router as ussd_router
from locat.api.routes_payments import router as payments_router
from locat.config import get_settings
from locat.db import models  # noqa: F401  (registers tables on Base)
from locat.db.session import Base, engine, get_db

import logging
from locat.api.routes_dashboard import router as dashboard_router

settings = get_settings()

class _RedactCallbackSecret(logging.Filter):
    """Keep the payment callback secret out of uvicorn's access log."""

    def filter(self, record: logging.LogRecord) -> bool:
        secret = get_settings().payment_callback_secret
        if secret and isinstance(record.args, tuple):
            record.args = tuple(
                a.replace(secret, "***") if isinstance(a, str) else a
                for a in record.args
            )
        return True


logging.getLogger("uvicorn.access").addFilter(_RedactCallbackSecret())

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(ussd_router)
app.include_router(payments_router)
app.include_router(dashboard_router)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {
        "status": "ok",
        "app": settings.app_name,
        "environment": settings.environment,
        "database": "connected",
    }