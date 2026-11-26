"""SQLAlchemy repository for VibeVerse AI persistence."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from backend.models.db_models import (
    ContentItem,
    DatasetRecord,
    Feedback,
    RecommendationHistory,
    SavedContent,
    TrendRecord,
    UserPreference,
)
from recommendation_engine.algorithms.hybrid_recommender import FEEDBACK_DELTAS


def content_to_dict(item: ContentItem) -> Dict[str, Any]:
    """Serialize ContentItem ORM instance to clean dict."""
    return {
        "id": item.id,
        "external_id": item.external_id,
        "title": item.title,
        "content_type": item.content_type,
        "language": item.language,
        "release_year": item.release_year,
        "description": item.description or "",
        "genres": list(item.genres or []),
        "mood_tags": list(item.mood_tags or []),
        "themes": list(item.themes or []),
        "extra_metadata": dict(item.extra_metadata or {}),
        "popularity": item.popularity,
        "rating": item.rating,
        "artwork_url": item.artwork_url,
        "source": item.source,
        "retrieved_at": item.retrieved_at.isoformat() if item.retrieved_at else None,
    }


def preference_to_dict(pref: UserPreference) -> Dict[str, Any]:
    """Serialize UserPreference ORM instance to clean dict."""
    return {
        "session_id": pref.session_id,
        "language_mode": pref.language_mode,
        "music_genres": list(pref.music_genres or []),
        "movie_genres": list(pref.movie_genres or []),
        "series_genres": list(pref.series_genres or []),
        "favourite_artists": list(pref.favourite_artists or []),
        "favourite_content": list(pref.favourite_content or []),
        "moods": list(pref.moods or []),
        "music_energy_pref": pref.music_energy_pref,
        "music_style_pref": pref.music_style_pref,
        "popularity_pref": pref.popularity_pref,
        "movie_themes": list(pref.movie_themes or []),
        "series_pacing": pref.series_pacing,
        "storytelling_style": list(pref.storytelling_style or []),
        "preference_weights": dict(pref.preference_weights or {}),
        "updated_at": pref.updated_at,
    }


class VibeVerseRepository:
    """Data access layer wrapping SQLAlchemy ORM operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_all_content(self) -> List[Dict[str, Any]]:
        rows = self.db.scalars(select(ContentItem).order_by(ContentItem.id)).all()
        return [content_to_dict(r) for r in rows]

    def get_content_by_id(self, content_id: int) -> Optional[ContentItem]:
        return self.db.get(ContentItem, content_id)

    def get_or_create_preferences(self, session_id: str) -> UserPreference:
        pref = self.db.get(UserPreference, session_id)
        if pref is None:
            pref = UserPreference(
                session_id=session_id,
                language_mode="both",
                music_genres=["Hindi Indie", "Dream Pop", "Acoustic"],
                movie_genres=["Mystery", "Drama", "Sci-Fi"],
                series_genres=["Mystery", "Psychological Drama", "Comedy"],
                favourite_artists=[],
                favourite_content=[],
                moods=["Dreamy", "Calm", "Mysterious"],
                music_energy_pref="balanced",
                music_style_pref="balanced",
                popularity_pref="balanced",
                movie_themes=[],
                series_pacing="balanced",
                storytelling_style=[],
                preference_weights={},
            )
            self.db.add(pref)
            self.db.commit()
            self.db.refresh(pref)
        return pref

    def update_preferences(self, session_id: str, payload: Dict[str, Any]) -> UserPreference:
        pref = self.get_or_create_preferences(session_id)
        for field, value in payload.items():
            if hasattr(pref, field) and field not in {"session_id", "preference_weights"}:
                setattr(pref, field, value)
        pref.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def reset_preferences(self, session_id: str) -> UserPreference:
        pref = self.get_or_create_preferences(session_id)
        pref.language_mode = "both"
        pref.music_genres = []
        pref.movie_genres = []
        pref.series_genres = []
        pref.favourite_artists = []
        pref.favourite_content = []
        pref.moods = []
        pref.music_energy_pref = "balanced"
        pref.music_style_pref = "balanced"
        pref.popularity_pref = "balanced"
        pref.movie_themes = []
        pref.series_pacing = "balanced"
        pref.storytelling_style = []
        pref.preference_weights = {}
        pref.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def update_preference_weights(self, session_id: str, weights: Dict[str, Any]) -> UserPreference:
        pref = self.get_or_create_preferences(session_id)
        pref.preference_weights = weights
        pref.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        self.db.commit()
        self.db.refresh(pref)
        return pref

    def record_feedback(self, session_id: str, content_id: int, feedback_type: str) -> Feedback:
        fb = Feedback(
            session_id=session_id,
            content_id=content_id,
            feedback_type=feedback_type,
            feedback_value=FEEDBACK_DELTAS.get(feedback_type, 0.0),
        )
        self.db.add(fb)
        self.db.commit()
        self.db.refresh(fb)
        return fb

    def list_feedback(self, session_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(Feedback, ContentItem)
            .join(ContentItem, Feedback.content_id == ContentItem.id)
            .where(Feedback.session_id == session_id)
            .order_by(desc(Feedback.created_at))
        )
        rows = self.db.execute(stmt).all()
        return [
            {
                "id": fb.id,
                "content_id": fb.content_id,
                "title": item.title,
                "content_type": item.content_type,
                "language": item.language,
                "feedback_type": fb.feedback_type,
                "feedback_value": fb.feedback_value,
                "created_at": fb.created_at.isoformat() if fb.created_at else None,
            }
            for fb, item in rows
        ]

    def list_all_interactions(self) -> List[Dict[str, Any]]:
        rows = self.db.scalars(select(Feedback)).all()
        return [
            {
                "session_id": r.session_id,
                "content_id": r.content_id,
                "feedback_type": r.feedback_type,
                "feedback_value": r.feedback_value,
            }
            for r in rows
        ]

    def save_content(self, session_id: str, content_id: int) -> SavedContent:
        existing = self.db.scalar(
            select(SavedContent).where(
                SavedContent.session_id == session_id,
                SavedContent.content_id == content_id,
            )
        )
        if existing:
            return existing
        saved = SavedContent(session_id=session_id, content_id=content_id)
        self.db.add(saved)
        self.db.commit()
        self.db.refresh(saved)
        return saved

    def list_saved_content(self, session_id: str) -> List[Dict[str, Any]]:
        stmt = (
            select(SavedContent, ContentItem)
            .join(ContentItem, SavedContent.content_id == ContentItem.id)
            .where(SavedContent.session_id == session_id)
            .order_by(desc(SavedContent.saved_at))
        )
        rows = self.db.execute(stmt).all()
        results = []
        for saved, item in rows:
            d = content_to_dict(item)
            d["saved_at"] = saved.saved_at.isoformat() if saved.saved_at else None
            results.append(d)
        return results

    def remove_saved_content(self, session_id: str, content_id: int) -> bool:
        res = self.db.execute(
            delete(SavedContent).where(
                SavedContent.session_id == session_id,
                SavedContent.content_id == content_id,
            )
        )
        self.db.commit()
        return res.rowcount > 0

    def log_recommendations(
        self,
        session_id: str,
        rec_type: str,
        items: List[Dict[str, Any]],
    ) -> None:
        for item in items:
            if item.get("id") is None:
                continue
            self.db.add(
                RecommendationHistory(
                    session_id=session_id,
                    recommended_content_id=int(item["id"]),
                    recommendation_type=rec_type,
                    recommendation_score=float(item.get("match_score") or 0.0),
                    recommendation_explanation=item.get("explanation") or {},
                )
            )
        self.db.commit()

    def list_datasets(self) -> List[Dict[str, Any]]:
        rows = self.db.scalars(select(DatasetRecord).order_by(desc(DatasetRecord.loaded_at))).all()
        return [
            {
                "name": r.name,
                "content_type": r.content_type,
                "source": r.source,
                "license_info": r.license_info,
                "record_count": r.record_count,
                "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
            }
            for r in rows
        ]

    def list_trends(self) -> List[Dict[str, Any]]:
        rows = self.db.scalars(select(TrendRecord)).all()
        return [
            {
                "metric_name": r.metric_name,
                "category": r.category,
                "language": r.language,
                "value": r.value,
                "source": r.source,
                "period_label": r.period_label,
                "retrieved_at": r.retrieved_at.isoformat() if r.retrieved_at else None,
            }
            for r in rows
        ]
