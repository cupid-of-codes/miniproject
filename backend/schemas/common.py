"""Common Pydantic schemas."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    app_name: str
    environment: str
    database_status: str
    data_mode: str
    content_count: Optional[int] = None
    timestamp: datetime


class ErrorResponse(BaseModel):
    """Standardized safe error response."""

    error: str
    detail: str
    extra: Optional[Dict[str, Any]] = None
