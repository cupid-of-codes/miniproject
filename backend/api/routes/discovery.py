"""Search, Trending, and Domain Recommendation routes (Music, Movies, Web Series)."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, preference_to_dict
from backend.schemas.api_schemas import (
    ContentItemOut,
    RecommendationRequest,
    RecommendationResponse,
    SearchResponse,
)
from backend.services.catalog_service import (
    build_trending_overview,
    get_catalog_index,
    search_catalog,
)
from recommendation_engine.algorithms.hybrid_recommender import recommend_for_domain

router = APIRouter(tags=["Discovery & Search"])


def _run_domain_search(
    db: Session,
    content_type: Optional[str],
    q: Optional[str],
    language: Optional[str],
    genre: Optional[str],
    mood: Optional[str],
    theme: Optional[str],
    category: Optional[str],
    year_min: Optional[int],
    year_max: Optional[int],
    min_rating: Optional[float],
    limit: int,
) -> SearchResponse:
    repo = VibeVerseRepository(db)
    items = repo.list_all_content()
    matched = search_catalog(
        items=items,
        content_type=content_type,
        query=q,
        language=language,
        genre=genre,
        mood=mood,
        theme=theme,
        category=category,
        year_min=year_min,
        year_max=year_max,
        min_rating=min_rating,
        limit=limit,
    )
    return SearchResponse(
        total=len(matched),
        items=[ContentItemOut(**item) for item in matched],
        filters_applied={
            "content_type": content_type,
            "q": q,
            "language": language,
            "genre": genre,
            "mood": mood,
            "theme": theme,
            "category": category,
            "year_min": year_min,
            "year_max": year_max,
            "min_rating": min_rating,
        },
    )


def _run_domain_recommendations(
    db: Session,
    content_type: str,
    req: RecommendationRequest,
) -> RecommendationResponse:
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    if not index.items:
        raise HTTPException(
            status_code=503,
            detail="Entertainment catalog is empty. Run scripts/load_datasets.py to populate MySQL.",
        )

    pref_row = repo.get_or_create_preferences(req.session_id)
    prefs = preference_to_dict(pref_row)
    if req.language_mode_override:
        prefs["language_mode"] = req.language_mode_override

    interactions = repo.list_all_interactions()
    result = recommend_for_domain(
        index=index,
        target_content_type=content_type,
        preferences=prefs,
        limit=req.limit,
        category_filter=req.category,
        session_interactions=interactions,
    )

    repo.log_recommendations(req.session_id, f"{content_type}_discovery", result["items"])
    return RecommendationResponse(
        session_id=req.session_id,
        content_type=content_type,
        language_mode=prefs["language_mode"],
        items=[ContentItemOut(**item) for item in result["items"]],
        language_notice=result["language_notice"],
        collaborative_filtering_active=result["collaborative_filtering_active"],
        based_on_profile_updated_at=pref_row.updated_at,
    )


@router.get("/api/music/search", response_model=SearchResponse)
def search_music(
    q: Optional[str] = Query(default=None, max_length=150),
    language: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    mood: Optional[str] = Query(default=None),
    theme: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    year_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return _run_domain_search(db, "song", q, language, genre, mood, theme, category, year_min, year_max, None, limit)


@router.post("/api/music/recommendations", response_model=RecommendationResponse)
def recommend_music(
    req: RecommendationRequest, db: Session = Depends(get_db)
) -> RecommendationResponse:
    return _run_domain_recommendations(db, "song", req)


@router.get("/api/movies/search", response_model=SearchResponse)
def search_movies(
    q: Optional[str] = Query(default=None, max_length=150),
    language: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    mood: Optional[str] = Query(default=None),
    theme: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    year_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    min_rating: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return _run_domain_search(db, "movie", q, language, genre, mood, theme, category, year_min, year_max, min_rating, limit)


@router.post("/api/movies/recommendations", response_model=RecommendationResponse)
def recommend_movies(
    req: RecommendationRequest, db: Session = Depends(get_db)
) -> RecommendationResponse:
    return _run_domain_recommendations(db, "movie", req)


@router.get("/api/series/search", response_model=SearchResponse)
def search_series(
    q: Optional[str] = Query(default=None, max_length=150),
    language: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    mood: Optional[str] = Query(default=None),
    theme: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    year_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    min_rating: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return _run_domain_search(db, "series", q, language, genre, mood, theme, category, year_min, year_max, min_rating, limit)


@router.post("/api/series/recommendations", response_model=RecommendationResponse)
def recommend_series(
    req: RecommendationRequest, db: Session = Depends(get_db)
) -> RecommendationResponse:
    return _run_domain_recommendations(db, "series", req)


@router.get("/api/search", response_model=SearchResponse)
def unified_search(
    content_type: Optional[str] = Query(default="all"),
    q: Optional[str] = Query(default=None, max_length=150),
    language: Optional[str] = Query(default=None),
    genre: Optional[str] = Query(default=None),
    mood: Optional[str] = Query(default=None),
    theme: Optional[str] = Query(default=None),
    category: Optional[str] = Query(default=None),
    year_min: Optional[int] = Query(default=None, ge=1900, le=2100),
    year_max: Optional[int] = Query(default=None, ge=1900, le=2100),
    min_rating: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    limit: int = Query(default=40, ge=1, le=120),
    db: Session = Depends(get_db),
) -> SearchResponse:
    return _run_domain_search(
        db, content_type, q, language, genre, mood, theme, category, year_min, year_max, min_rating, limit
    )


@router.get("/api/trending")
def get_trending(db: Session = Depends(get_db)):
    """Return data-sourced trending/spotlight highlights with source attribution."""
    repo = VibeVerseRepository(db)
    items = repo.list_all_content()
    return build_trending_overview(repo, items)
