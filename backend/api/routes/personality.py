"""Entertainment Personality Analyzer routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, preference_to_dict
from backend.schemas.api_schemas import PersonalityAnalyzeRequest
from backend.services.catalog_service import get_catalog_index
from recommendation_engine.personality.personality_analyzer import analyze_entertainment_personality

router = APIRouter(tags=["Entertainment Personality"])


@router.post("/api/personality/analyze")
def analyze_personality(req: PersonalityAnalyzeRequest, db: Session = Depends(get_db)):
    """Analyze entertainment personality dimensions and archetype for a session."""
    return _compute_personality(req.session_id, db)


@router.get("/api/personality/{session_id}")
def get_personality(session_id: str, db: Session = Depends(get_db)):
    """Retrieve entertainment personality profile for a session."""
    return _compute_personality(session_id, db)


def _compute_personality(session_id: str, db: Session):
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    prefs = preference_to_dict(repo.get_or_create_preferences(session_id))
    feedback = repo.list_feedback(session_id)
    saved = repo.list_saved_content(session_id)
    profile = analyze_entertainment_personality(index, prefs, feedback, saved)
    profile["session_id"] = session_id
    return profile
