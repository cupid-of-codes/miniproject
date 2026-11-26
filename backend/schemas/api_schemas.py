"""Pydantic v2 request and response schemas for all VibeVerse AI endpoints."""

from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

LanguageMode = Literal[
    "hindi_only",
    "english_only",
    "both",
    "hindi_pref_english_rec",
    "english_pref_hindi_rec",
]

FeedbackType = Literal[
    "like",
    "dislike",
    "save",
    "not_interested",
    "more_like_this",
    "less_like_this",
]

CrossDomainPathway = Literal[
    "music_to_movies",
    "music_to_series",
    "movies_to_music",
    "series_to_music",
]


class PreferencePayload(BaseModel):
    """Editable user preference fields."""

    language_mode: LanguageMode = "both"
    music_genres: List[str] = Field(default_factory=list)
    movie_genres: List[str] = Field(default_factory=list)
    series_genres: List[str] = Field(default_factory=list)
    favourite_artists: List[str] = Field(default_factory=list)
    favourite_content: List[str] = Field(default_factory=list)
    moods: List[str] = Field(default_factory=list)
    music_energy_pref: Literal["calm", "balanced", "high"] = "balanced"
    music_style_pref: Literal["acoustic", "electronic", "balanced"] = "balanced"
    popularity_pref: Literal["popular", "underrated", "balanced"] = "balanced"
    movie_themes: List[str] = Field(default_factory=list)
    series_pacing: Literal["slow_burn", "balanced", "fast_paced"] = "balanced"
    storytelling_style: List[str] = Field(default_factory=list)


class PreferenceResponse(PreferencePayload):
    """Persisted preference profile for a session."""

    session_id: str
    preference_weights: Dict[str, Any] = Field(default_factory=dict)
    updated_at: Optional[datetime] = None


class ContentItemOut(BaseModel):
    """Serialized song, movie, or web series item."""

    id: Optional[int] = None
    external_id: str
    title: str
    content_type: str
    language: str
    release_year: Optional[int] = None
    description: str = ""
    genres: List[str] = Field(default_factory=list)
    mood_tags: List[str] = Field(default_factory=list)
    themes: List[str] = Field(default_factory=list)
    extra_metadata: Dict[str, Any] = Field(default_factory=dict)
    popularity: Optional[float] = None
    rating: Optional[float] = None
    artwork_url: Optional[str] = None
    source: str
    retrieved_at: Optional[Any] = None
    match_score: Optional[float] = None
    explanation: Optional[Dict[str, Any]] = None


class RecommendationRequest(BaseModel):
    """Domain recommendation request."""

    session_id: str = Field(..., min_length=3, max_length=64)
    limit: int = Field(default=10, ge=1, le=30)
    category: Optional[str] = None
    language_mode_override: Optional[LanguageMode] = None


class RecommendationResponse(BaseModel):
    """Domain recommendation response with explainability and language metadata."""

    session_id: str
    content_type: str
    language_mode: str
    items: List[ContentItemOut]
    language_notice: Optional[str] = None
    collaborative_filtering_active: bool = False
    based_on_profile_updated_at: Optional[datetime] = None


class SearchResponse(BaseModel):
    """Search and filter response."""

    total: int
    items: List[ContentItemOut]
    filters_applied: Dict[str, Any] = Field(default_factory=dict)


class CrossDomainRequest(BaseModel):
    """Cross-domain recommendation request."""

    session_id: str = Field(..., min_length=3, max_length=64)
    pathway: CrossDomainPathway = "music_to_movies"
    seed_titles: Optional[List[str]] = None
    limit: int = Field(default=8, ge=1, le=20)


class CrossDomainResponse(BaseModel):
    """Cross-domain pathway response."""

    pathway: str
    seed_items: List[str]
    recommendations: List[ContentItemOut]
    language_notice: Optional[str] = None


class ChainStepOut(BaseModel):
    """Single step in a Music -> Movie -> Series -> Soundtrack chain."""

    stage: str
    item: Optional[ContentItemOut] = None


class DiscoveryChainResponse(BaseModel):
    """Cross-domain discovery chain response."""

    shared_mood_bridge: List[str]
    steps: List[ChainStepOut]


class UnexpectedVibeRequest(BaseModel):
    """Request for 'Your Unexpected Vibe' exploration."""

    session_id: str = Field(..., min_length=3, max_length=64)
    limit: int = Field(default=6, ge=1, le=15)


class MoodMatchRequest(BaseModel):
    """Mood-to-Story Matching request."""

    session_id: str = Field(..., min_length=3, max_length=64)
    moods: List[str] = Field(default_factory=list)
    mood_text: str = Field(default="", max_length=500)
    language_mode: Optional[LanguageMode] = None
    limit_per_domain: int = Field(default=5, ge=1, le=15)


class MoodMatchResponse(BaseModel):
    """Mood-to-Story Matching synchronized response."""

    target_moods: List[str]
    nlp_signals: Dict[str, Any]
    songs: List[ContentItemOut]
    movies: List[ContentItemOut]
    series: List[ContentItemOut]
    note: str


class PersonalityAnalyzeRequest(BaseModel):
    """Request to compute entertainment personality profile."""

    session_id: str = Field(..., min_length=3, max_length=64)


class FeedbackRequest(BaseModel):
    """User feedback interaction payload."""

    session_id: str = Field(..., min_length=3, max_length=64)
    content_id: int = Field(..., ge=1)
    feedback_type: FeedbackType


class FeedbackResponse(BaseModel):
    """Feedback confirmation and updated weights."""

    status: str
    session_id: str
    content_id: int
    feedback_type: str
    updated_weights: Dict[str, Any]


class SavedContentRequest(BaseModel):
    """Save content item request."""

    session_id: str = Field(..., min_length=3, max_length=64)
    content_id: int = Field(..., ge=1)
