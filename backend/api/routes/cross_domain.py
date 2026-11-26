"""Cross-domain and Mood-to-Story recommendation routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.repositories.vibeverse_repo import VibeVerseRepository, preference_to_dict
from backend.schemas.api_schemas import (
    ContentItemOut,
    CrossDomainRequest,
    CrossDomainResponse,
    DiscoveryChainResponse,
    MoodMatchRequest,
    MoodMatchResponse,
    UnexpectedVibeRequest,
)
from backend.services.catalog_service import get_catalog_index
from recommendation_engine.cross_domain.cross_domain_engine import (
    build_discovery_chain,
    discover_unexpected_vibe,
    run_cross_domain_pathway,
)
from recommendation_engine.mood_matching.mood_matcher import match_mood_to_story

router = APIRouter(tags=["Cross-Domain & Mood Matching"])


@router.post("/api/recommendations/cross-domain", response_model=CrossDomainResponse)
def cross_domain_recommendations(
    req: CrossDomainRequest, db: Session = Depends(get_db)
) -> CrossDomainResponse:
    """Execute Music->Movies, Music->Series, Movies->Music, or Series->Music."""
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    if not index.items:
        raise HTTPException(status_code=503, detail="Entertainment catalog is empty.")

    prefs = preference_to_dict(repo.get_or_create_preferences(req.session_id))
    result = run_cross_domain_pathway(
        index=index,
        pathway=req.pathway,
        preferences=prefs,
        seed_titles_override=req.seed_titles,
        limit=req.limit,
    )
    repo.log_recommendations(req.session_id, f"cross_{req.pathway}", result["recommendations"])
    return CrossDomainResponse(
        pathway=result["pathway"],
        seed_items=result["seed_items"],
        recommendations=[ContentItemOut(**item) for item in result["recommendations"]],
        language_notice=result["language_notice"],
    )


@router.post("/api/recommendations/chain", response_model=DiscoveryChainResponse)
def cross_domain_chain(
    req: CrossDomainRequest, db: Session = Depends(get_db)
) -> DiscoveryChainResponse:
    """Generate a Music -> Mood -> Movie -> Web Series -> Soundtrack chain."""
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    if not index.items:
        raise HTTPException(status_code=503, detail="Entertainment catalog is empty.")

    prefs = preference_to_dict(repo.get_or_create_preferences(req.session_id))
    chain = build_discovery_chain(index, prefs, seed_titles_override=req.seed_titles)
    return DiscoveryChainResponse(**chain)


@router.post("/api/recommendations/unexpected")
def unexpected_vibe_discoveries(
    req: UnexpectedVibeRequest, db: Session = Depends(get_db)
):
    """Return 'Your Unexpected Vibe' cross-genre discoveries."""
    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    if not index.items:
        raise HTTPException(status_code=503, detail="Entertainment catalog is empty.")

    prefs = preference_to_dict(repo.get_or_create_preferences(req.session_id))
    items = discover_unexpected_vibe(index, prefs, limit=req.limit)
    return {"items": [ContentItemOut(**item).model_dump() for item in items]}


@router.post("/api/recommendations/mood", response_model=MoodMatchResponse)
def mood_to_story(
    req: MoodMatchRequest, db: Session = Depends(get_db)
) -> MoodMatchResponse:
    """Match selected moods and/or free-text mood description across songs, movies, and series."""
    if not req.moods and not req.mood_text.strip():
        raise HTTPException(
            status_code=422,
            detail="Please select at least one mood or describe your mood in text.",
        )

    repo = VibeVerseRepository(db)
    index = get_catalog_index(db)
    if not index.items:
        raise HTTPException(status_code=503, detail="Entertainment catalog is empty.")

    prefs = preference_to_dict(repo.get_or_create_preferences(req.session_id))
    lang_mode = req.language_mode or prefs.get("language_mode", "both")

    result = match_mood_to_story(
        index=index,
        selected_moods=req.moods,
        mood_text=req.mood_text,
        preferences=prefs,
        language_mode=lang_mode,
        limit_per_domain=req.limit_per_domain,
    )
    return MoodMatchResponse(**result)
