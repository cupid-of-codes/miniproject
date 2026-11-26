"""End-to-end integration tests verifying preference persistence, dynamic recalculation, and feedback loops."""

from backend.api.routes.discovery import recommend_movies, recommend_music
from backend.api.routes.interactions import get_saved_items, submit_feedback
from backend.api.routes.personality import get_personality
from backend.api.routes.preferences import get_preferences, update_preferences
from backend.schemas.api_schemas import (
    FeedbackRequest,
    PreferencePayload,
    RecommendationRequest,
)


def test_end_to_end_preference_and_feedback_loop(seeded_db_session_factory):
    sid = "integration_user_001"
    with seeded_db_session_factory() as db:
        # 1. Start with calm acoustic Hindi/English preferences
        update_preferences(
            sid,
            PreferencePayload(
                language_mode="both",
                music_genres=["Hindi Indie", "Acoustic", "Lo-Fi"],
                movie_genres=["Romance", "Feel-Good"],
                moods=["Calm", "Comfort", "Dreamy"],
                music_energy_pref="calm",
                music_style_pref="acoustic",
            ),
            db,
        )
        initial_music = recommend_music(RecommendationRequest(session_id=sid, limit=8), db)
        initial_ids = [i.external_id for i in initial_music.items]
        p_calm = get_personality(sid, db)

        # 2. Switch preferences materially to Dark Mystery / Thrillers / High-energy Rock
        update_preferences(
            sid,
            PreferencePayload(
                language_mode="both",
                music_genres=["Rock", "Electronic", "Dark Indie"],
                movie_genres=["Psychological Thriller", "Mystery", "Dark Cinema"],
                moods=["Dark", "Mysterious", "Anxious"],
                music_energy_pref="high",
                music_style_pref="electronic",
            ),
            db,
        )
        updated_music = recommend_music(RecommendationRequest(session_id=sid, limit=8), db)
        updated_ids = [i.external_id for i in updated_music.items]
        p_dark = get_personality(sid, db)

        assert initial_ids != updated_ids
        assert p_calm["archetype"] != p_dark["archetype"] or p_calm["dimensions"] != p_dark["dimensions"]

        # 3. Submit 'not_interested' and 'save' feedback and verify persistence & exclusion
        top_movie_recs = recommend_movies(RecommendationRequest(session_id=sid, limit=6), db)
        disliked_id = top_movie_recs.items[0].id
        saved_id = top_movie_recs.items[1].id

        submit_feedback(FeedbackRequest(session_id=sid, content_id=disliked_id, feedback_type="not_interested"), db)
        submit_feedback(FeedbackRequest(session_id=sid, content_id=saved_id, feedback_type="save"), db)

        after_fb_recs = recommend_movies(RecommendationRequest(session_id=sid, limit=10), db)
        assert all(item.id != disliked_id for item in after_fb_recs.items)

        saved = get_saved_items(sid, db)
        assert any(item["id"] == saved_id for item in saved["items"])

        persisted_prefs = get_preferences(sid, db)
        assert disliked_id in persisted_prefs.preference_weights["suppressed_ids"]
        assert saved_id in persisted_prefs.preference_weights["liked_ids"]
