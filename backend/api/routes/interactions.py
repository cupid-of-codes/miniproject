"""Feedback and Saved Content routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, content_to_dict
from backend.schemas.api_schemas import (
    FeedbackRequest,
    FeedbackResponse,
    SavedContentRequest,
)
from recommendation_engine.algorithms.hybrid_recommender import apply_feedback_to_weights

router = APIRouter(tags=["Feedback & Saved Content"])


@router.post("/api/feedback", response_model=FeedbackResponse)
def submit_feedback(req: FeedbackRequest, db: Session = Depends(get_db)) -> FeedbackResponse:
    """Persist user feedback and update session preference weights transparently."""
    repo = VibeVerseRepository(db)
    item = repo.get_content_by_id(req.content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content item not found.")

    repo.record_feedback(req.session_id, req.content_id, req.feedback_type)
    pref = repo.get_or_create_preferences(req.session_id)
    updated_weights = apply_feedback_to_weights(
        current_weights=pref.preference_weights,
        item=content_to_dict(item),
        feedback_type=req.feedback_type,
    )
    repo.update_preference_weights(req.session_id, updated_weights)

    if req.feedback_type == "save":
        repo.save_content(req.session_id, req.content_id)

    return FeedbackResponse(
        status="recorded",
        session_id=req.session_id,
        content_id=req.content_id,
        feedback_type=req.feedback_type,
        updated_weights=updated_weights,
    )


@router.get("/api/feedback/{session_id}")
def list_session_feedback(session_id: str, db: Session = Depends(get_db)):
    """List feedback history for a session."""
    repo = VibeVerseRepository(db)
    return {"session_id": session_id, "items": repo.list_feedback(session_id)}


@router.post("/api/saved")
def save_item(req: SavedContentRequest, db: Session = Depends(get_db)):
    """Save an item to the session's Saved Discoveries."""
    repo = VibeVerseRepository(db)
    item = repo.get_content_by_id(req.content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Content item not found.")
    repo.save_content(req.session_id, req.content_id)
    return {"status": "saved", "session_id": req.session_id, "content_id": req.content_id}


@router.get("/api/saved/{session_id}")
def get_saved_items(session_id: str, db: Session = Depends(get_db)):
    """List all saved songs, movies, and web series for a session."""
    repo = VibeVerseRepository(db)
    items = repo.list_saved_content(session_id)
    return {"session_id": session_id, "total": len(items), "items": items}


@router.delete("/api/saved/{session_id}/{content_id}")
def delete_saved_item(session_id: str, content_id: int, db: Session = Depends(get_db)):
    """Remove an item from Saved Discoveries."""
    repo = VibeVerseRepository(db)
    removed = repo.remove_saved_content(session_id, content_id)
    if not removed:
        raise HTTPException(status_code=404, detail="Saved item not found for this session.")
    return {"status": "removed", "session_id": session_id, "content_id": content_id}
