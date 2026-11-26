"""SQLAlchemy engine and session management for MySQL."""

import logging
from contextlib import contextmanager
from typing import Generator, Tuple

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.core.config import get_settings

logger = logging.getLogger("vibeverse.database")


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def build_engine(database_url: str | None = None):
    """Create a configured SQLAlchemy engine with MySQL pool health checks."""
    settings = get_settings()
    url = database_url or settings.sqlalchemy_database_url
    connect_args = {}
    if url.startswith("mysql"):
        connect_args = {"connect_timeout": 5}
    elif url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=False,
        connect_args=connect_args,
    )


engine = build_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Generator[Session, None, None]:
    """Transactional context manager for scripts and background tasks."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def check_database_connection() -> Tuple[bool, str]:
    """Verify database connectivity safely without exposing credentials."""
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        dialect = engine.dialect.name
        if dialect == "mysql":
            return True, "connected (mysql)"
        return True, f"connected (local_{dialect}_fallback)"
    except SQLAlchemyError as exc:
        logger.warning("Database connection check failed: %s", exc.__class__.__name__)
        return False, f"unavailable ({exc.__class__.__name__})"
