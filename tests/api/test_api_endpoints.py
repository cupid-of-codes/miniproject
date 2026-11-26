"""API endpoint, schema validation, and error handling tests."""

import httpx
import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.api.routes.analytics import get_preference_analytics, get_trends_analytics
from backend.api.routes.cross_domain import (
    cross_domain_chain,
    cross_domain_recommendations,
    mood_to_story,
    unexpected_vibe_discoveries,
)
from backend.api.routes.discovery import (
    get_trending,
    recommend_movies,
    recommend_music,
    recommend_series,
    search_movies,
    search_music,
    search_series,
    unified_search,
)
from backend.api.routes.interactions import (
    delete_saved_item,
    get_saved_items,
    list_session_feedback,
    save_item,
    submit_feedback,
)
from backend.api.routes.personality import analyze_personality, get_personality
from backend.api.routes.preferences import (
    catalog_metadata,
    get_preferences,
    reset_preferences,
    update_preferences,
)
from backend.schemas.api_schemas import (
    CrossDomainRequest,
    FeedbackRequest,
    MoodMatchRequest,
    PersonalityAnalyzeRequest,
    PreferencePayload,
    RecommendationRequest,
    SavedContentRequest,
    UnexpectedVibeRequest,
)
from frontend.services.api_client import APIClientError, VibeVerseAPIClient


def test_preferences_crud_and_validation(seeded_db_session_factory):
    sid = "test_api_sess_1"
    with seeded_db_session_factory() as db:
        pref = get_preferences(sid, db)
        assert pref.session_id == sid
        assert pref.language_mode == "both"

        updated = update_preferences(
            sid,
            PreferencePayload(
                language_mode="hindi_only",
                music_genres=["Hindi Indie", "Sufi"],
                moods=["Calm", "Nostalgic"],
            ),
            db,
        )
        assert updated.language_mode == "hindi_only"
        assert "Hindi Indie" in updated.music_genres

        reset = reset_preferences(sid, db)
        assert reset.language_mode == "both"
        assert reset.music_genres == []

        meta = catalog_metadata(db)
        assert len(meta["music_genres"]) > 0
        assert len(meta["movie_genres"]) > 0
        assert len(meta["series_genres"]) > 0

    with pytest.raises(ValidationError):
        PreferencePayload(language_mode="invalid_lang")


def test_search_and_recommendation_endpoints(seeded_db_session_factory):
    sid = "test_api_sess_2"
    with seeded_db_session_factory() as db:
        s_music = search_music(q="Anuv", language=None, genre=None, mood=None, theme=None, category=None, year_min=None, year_max=None, limit=10, db=db)
        assert s_music.total >= 2

        s_movies = search_movies(q=None, language="Hindi", genre="Mystery", mood=None, theme=None, category=None, year_min=None, year_max=None, min_rating=None, limit=10, db=db)
        assert s_movies.total >= 2

        s_series = search_series(q="Panchayat", language=None, genre=None, mood=None, theme=None, category=None, year_min=None, year_max=None, min_rating=None, limit=10, db=db)
        assert s_series.total == 1

        uni = unified_search(content_type="all", q=None, language="English", genre=None, mood="Dark", theme=None, category=None, year_min=None, year_max=None, min_rating=None, limit=20, db=db)
        assert uni.total > 0

        trending = get_trending(db)
        assert len(trending["trending_songs"]) == 4
        assert trending["has_live_popularity"] is False

        rec_m = recommend_music(RecommendationRequest(session_id=sid, limit=8), db)
        assert len(rec_m.items) == 8

        rec_mv = recommend_movies(RecommendationRequest(session_id=sid, limit=6), db)
        assert len(rec_mv.items) == 6

        rec_sr = recommend_series(RecommendationRequest(session_id=sid, limit=6), db)
        assert len(rec_sr.items) == 6


def test_cross_domain_mood_personality_and_analytics_endpoints(seeded_db_session_factory):
    sid = "test_api_sess_3"
    with seeded_db_session_factory() as db:
        cd = cross_domain_recommendations(
            CrossDomainRequest(session_id=sid, pathway="music_to_movies", limit=5), db
        )
        assert len(cd.recommendations) == 5

        chain = cross_domain_chain(CrossDomainRequest(session_id=sid, pathway="music_to_movies"), db)
        assert len(chain.steps) == 4

        unexp = unexpected_vibe_discoveries(UnexpectedVibeRequest(session_id=sid, limit=4), db)
        assert len(unexp["items"]) > 0

        mm = mood_to_story(
            MoodMatchRequest(session_id=sid, moods=["Dark"], mood_text="rainy mystery", limit_per_domain=3),
            db,
        )
        assert len(mm.songs) == 3 and len(mm.movies) == 3 and len(mm.series) == 3

        with pytest.raises(HTTPException) as exc_info:
            mood_to_story(MoodMatchRequest(session_id=sid, moods=[], mood_text="   "), db)
        assert exc_info.value.status_code == 422

        p1 = analyze_personality(PersonalityAnalyzeRequest(session_id=sid), db)
        p2 = get_personality(sid, db)
        assert p1["archetype"] == p2["archetype"]
        assert len(p1["dimensions"]) == 7

        trends = get_trends_analytics(db)
        assert trends["total_items"] >= 150

        pref_stats = get_preference_analytics(sid, db)
        assert "quality_metrics" in pref_stats


def test_feedback_saved_and_error_handling(seeded_db_session_factory):
    sid = "test_api_sess_4"
    with seeded_db_session_factory() as db:
        with pytest.raises(HTTPException) as not_found_fb:
            submit_feedback(FeedbackRequest(session_id=sid, content_id=999999, feedback_type="like"), db)
        assert not_found_fb.value.status_code == 404

        fb_res = submit_feedback(FeedbackRequest(session_id=sid, content_id=1, feedback_type="like"), db)
        assert fb_res.status == "recorded"

        fb_list = list_session_feedback(sid, db)
        assert len(fb_list["items"]) == 1

        sav_res = save_item(SavedContentRequest(session_id=sid, content_id=2), db)
        assert sav_res["status"] == "saved"

        saved_list = get_saved_items(sid, db)
        assert saved_list["total"] == 1

        del_res = delete_saved_item(sid, 2, db)
        assert del_res["status"] == "removed"

        with pytest.raises(HTTPException) as not_found_del:
            delete_saved_item(sid, 2, db)
        assert not_found_del.value.status_code == 404


def test_frontend_api_client_error_handling(monkeypatch):
    client = VibeVerseAPIClient(base_url="http://127.0.0.1:59999")

    def _raise_connect(*args, **kwargs):
        raise httpx.ConnectError("Connection refused")

    monkeypatch.setattr(httpx.Client, "request", _raise_connect)
    with pytest.raises(APIClientError) as exc_info:
        client.health()
    assert "Cannot reach the VibeVerse FastAPI backend" in str(exc_info.value)
