"""Analytics and Trend Intelligence routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, preference_to_dict
from backend.services.catalog_service import compute_catalog_analytics, get_catalog_index
from recommendation_engine.evaluation.evaluator import (
    compute_catalog_coverage,
    compute_intra_list_diversity,
    compute_novelty,
)
from recommendation_engine.algorithms.hybrid_recommender import recommend_for_domain
from recommendation_engine.personality.personality_analyzer import analyze_entertainment_personality

router = APIRouter(tags=["Analytics & Trends"])


@router.get("/api/analytics/trends")
def get_trends_analytics(db: Session = Depends(get_db)):
    """Return catalog-derived genre, language, mood, and cross-domain analytics."""
    repo = VibeVerseRepository(db)
    items = repo.list_all_content()
    analytics = compute_catalog_analytics(repo, items)
    analytics["stored_trends"] = repo.list_trends()
    return analytics


@router.get("/api/analytics/preferences/{session_id}")
def get_preference_analytics(session_id: str, db: Session = Depends(get_db)):
    """Return preference breakdown, feedback stats, and live recommendation quality metrics."""
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    prefs = preference_to_dict(repo.get_or_create_preferences(session_id))
    feedback = repo.list_feedback(session_id)
    saved = repo.list_saved_content(session_id)

    profile = analyze_entertainment_personality(index, prefs, feedback, saved)

    quality_metrics = {}
    if index.items:
        batches = []
        for ctype in ("song", "movie", "series"):
            rec = recommend_for_domain(index, ctype, prefs, limit=6)["items"]
            batches.append(rec)
            quality_metrics[ctype] = {
                "diversity": compute_intra_list_diversity(index, rec),
                "novelty": compute_novelty(index, rec),
            }
        quality_metrics["catalog_coverage"] = compute_catalog_coverage(
            batches, len(index.items)
        )

    return {
        "session_id": session_id,
        "preferences": prefs,
        "feedback_count": len(feedback),
        "saved_count": len(saved),
        "breakdowns": profile["breakdowns"],
        "quality_metrics": quality_metrics,
    }
