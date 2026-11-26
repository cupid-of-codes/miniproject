"""Preferences and catalog metadata routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, preference_to_dict
from backend.schemas.api_schemas import PreferencePayload, PreferenceResponse
from backend.services.catalog_service import get_catalog_metadata

router = APIRouter(tags=["Preferences & Metadata"])


@router.get("/api/preferences/{session_id}", response_model=PreferenceResponse)
def get_preferences(session_id: str, db: Session = Depends(get_db)) -> PreferenceResponse:
    """Fetch or initialize anonymous session preferences."""
    if not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id cannot be empty.")
    repo = VibeVerseRepository(db)
    pref = repo.get_or_create_preferences(session_id.strip())
    return PreferenceResponse(**preference_to_dict(pref))


@router.put("/api/preferences/{session_id}", response_model=PreferenceResponse)
def update_preferences(
    session_id: str,
    payload: PreferencePayload,
    db: Session = Depends(get_db),
) -> PreferenceResponse:
    """Update session entertainment preferences dynamically."""
    if not session_id.strip():
        raise HTTPException(status_code=400, detail="session_id cannot be empty.")
    repo = VibeVerseRepository(db)
    pref = repo.update_preferences(session_id.strip(), payload.model_dump())
    return PreferenceResponse(**preference_to_dict(pref))


@router.post("/api/preferences/{session_id}/reset", response_model=PreferenceResponse)
def reset_preferences(session_id: str, db: Session = Depends(get_db)) -> PreferenceResponse:
    """Reset session preferences and feedback weights."""
    repo = VibeVerseRepository(db)
    pref = repo.reset_preferences(session_id.strip())
    return PreferenceResponse(**preference_to_dict(pref))


@router.get("/api/catalog/metadata")
def catalog_metadata(db: Session = Depends(get_db)):
    """Return available genres, moods, artists, themes, and titles for UI selectors."""
    repo = VibeVerseRepository(db)
    items = repo.list_all_content()
    return get_catalog_metadata(items)
