"""Health endpoint router."""

from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from backend.core.config import get_settings
from backend.database.session import SessionLocal, check_database_connection
from backend.models.db_models import ContentItem
from backend.schemas.common import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, summary="Check API and MySQL health")
def health_check() -> HealthResponse:
    """Return service and database connectivity status."""
    settings = get_settings()
    db_ok, db_msg = check_database_connection()
    content_count = None

    if db_ok:
        try:
            with SessionLocal() as db:
                content_count = db.scalar(select(func.count()).select_from(ContentItem))
        except SQLAlchemyError:
            content_count = None

    overall_status = "healthy" if db_ok else "degraded"
    return HealthResponse(
        status=overall_status,
        app_name=settings.app_name,
        environment=settings.app_env,
        database_status=db_msg,
        data_mode=settings.data_mode,
        content_count=content_count,
        timestamp=datetime.now(timezone.utc),
    )
