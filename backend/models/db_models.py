"""SQLAlchemy ORM models for VibeVerse AI (MySQL compatible)."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.session import Base


class ContentItem(Base):
    """Unified entertainment item (song, movie, or web series)."""

    __tablename__ = "content_items"
    __table_args__ = (
        Index("ix_content_type_lang", "content_type", "language"),
        Index("ix_content_title", "title"),
        UniqueConstraint("external_id", "content_type", name="uq_external_id_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)  # song | movie | series
    language: Mapped[str] = mapped_column(String(64), nullable=False)  # Hindi | English | Bilingual
    release_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    genres: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    mood_tags: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    themes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    extra_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    popularity: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rating: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    artwork_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="local_dataset")
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    artist_links: Mapped[List["ContentArtist"]] = relationship(
        back_populates="content_item", cascade="all, delete-orphan"
    )


class Artist(Base):
    """Musicians, directors, creators, or key talent."""

    __tablename__ = "artists"
    __table_args__ = (UniqueConstraint("name", name="uq_artist_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    genres: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source: Mapped[str] = mapped_column(String(128), nullable=False, default="local_dataset")


class ContentArtist(Base):
    """Many-to-many link between content items and artists/creators."""

    __tablename__ = "content_artists"
    __table_args__ = (
        UniqueConstraint("content_id", "artist_id", "role", name="uq_content_artist_role"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    artist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(64), nullable=False, default="artist")

    content_item: Mapped["ContentItem"] = relationship(back_populates="artist_links")
    artist: Mapped["Artist"] = relationship()


class UserPreference(Base):
    """Anonymous session-based preference profile (no authentication)."""

    __tablename__ = "user_preferences"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    language_mode: Mapped[str] = mapped_column(String(64), nullable=False, default="both")
    music_genres: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    movie_genres: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    series_genres: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    favourite_artists: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    favourite_content: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    moods: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    music_energy_pref: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    music_style_pref: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    popularity_pref: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    movie_themes: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    series_pacing: Mapped[str] = mapped_column(String(32), nullable=False, default="balanced")
    storytelling_style: Mapped[List[str]] = mapped_column(JSON, nullable=False, default=list)
    preference_weights: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class RecommendationHistory(Base):
    """Audit trail of recommendations shown in a session."""

    __tablename__ = "recommendation_history"
    __table_args__ = (Index("ix_rec_hist_session", "session_id", "created_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    recommended_content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    recommendation_type: Mapped[str] = mapped_column(String(64), nullable=False)
    recommendation_score: Mapped[float] = mapped_column(Float, nullable=False)
    recommendation_explanation: Mapped[Dict[str, Any]] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class Feedback(Base):
    """User feedback interactions driving transparent weight updates."""

    __tablename__ = "feedback"
    __table_args__ = (Index("ix_feedback_session_content", "session_id", "content_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    feedback_type: Mapped[str] = mapped_column(String(32), nullable=False)
    feedback_value: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class SavedContent(Base):
    """Session-saved discoveries across songs, movies, and series."""

    __tablename__ = "saved_content"
    __table_args__ = (
        UniqueConstraint("session_id", "content_id", name="uq_saved_session_content"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)
    content_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("content_items.id", ondelete="CASCADE"), nullable=False
    )
    saved_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class DatasetRecord(Base):
    """Metadata registry of loaded datasets and API sync snapshots."""

    __tablename__ = "datasets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    license_info: Mapped[str] = mapped_column(String(255), nullable=False, default="Open/Curated")
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    retrieved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    loaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )


class TrendRecord(Base):
    """Real dataset/API-derived trend records (never fabricated)."""

    __tablename__ = "trends"
    __table_args__ = (Index("ix_trends_metric_cat", "metric_name", "category"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    metric_name: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(128), nullable=False)
    language: Mapped[str] = mapped_column(String(64), nullable=False, default="All")
    value: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    period_label: Mapped[str] = mapped_column(String(64), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
