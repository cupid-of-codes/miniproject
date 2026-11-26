"""Unit tests for Phase 3 data pipeline and Phase 4 recommendation engine."""

import pytest

from recommendation_engine.algorithms.hybrid_recommender import (
    apply_feedback_to_weights,
    recommend_for_domain,
)
from recommendation_engine.cross_domain.cross_domain_engine import (
    build_discovery_chain,
    discover_unexpected_vibe,
    run_cross_domain_pathway,
)
from recommendation_engine.evaluation.evaluator import (
    compute_catalog_coverage,
    compute_intra_list_diversity,
    compute_novelty,
    evaluate_ranking_against_ground_truth,
)
from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex
from recommendation_engine.mood_matching.mood_matcher import (
    extract_mood_signals_from_text,
    match_mood_to_story,
)
from recommendation_engine.personality.personality_analyzer import analyze_entertainment_personality
from recommendation_engine.preprocessing.dataset_loader import load_all_datasets
from recommendation_engine.preprocessing.text_cleaner import (
    canonicalize_moods,
    clean_text,
    infer_music_characteristics,
    normalize_language,
)


@pytest.fixture(scope="module")
def catalog_index():
    items, _ = load_all_datasets(include_external=False)
    for idx, item in enumerate(items, start=1):
        item["id"] = idx
    return CatalogFeatureIndex(items)


def test_preprocessing_and_music_inference():
    assert clean_text("The Midnight City & Neon Lights!") == "midnight city neon lights"
    assert normalize_language("hi") == "Hindi"
    assert normalize_language("en") == "English"
    moods = canonicalize_moods(["lofi", "melancholy"], fallback_text="")
    assert "Chill" in moods and "Melancholic" in moods

    est = infer_music_characteristics(
        {"genres": ["Synthwave"], "mood_tags": ["Calm"], "description": "Quiet analog dream"}
    )
    assert est["is_model_generated_estimate"] is True
    assert est["inferred_style"] == "electronic"
    assert est["inferred_energy"] == "calm"


def test_dataset_loader_balances_hindi_and_english(catalog_index):
    items = catalog_index.items
    assert len(items) >= 150
    hi_count = sum(1 for i in items if i["language"] == "Hindi")
    en_count = sum(1 for i in items if i["language"] == "English")
    assert hi_count >= 70
    assert en_count >= 70
    assert len(catalog_index.cluster_labels) == len(items)


def test_hybrid_recommendations_and_language_modes(catalog_index):
    prefs = {
        "language_mode": "both",
        "music_genres": ["Hindi Indie", "Dream Pop", "Acoustic"],
        "movie_genres": ["Mystery", "Sci-Fi"],
        "series_genres": ["Psychological Drama", "Mystery"],
        "favourite_artists": ["Anuv Jain", "Cigarettes After Sex"],
        "favourite_content": ["Alag Aasmaan", "Interstellar"],
        "moods": ["Melancholic", "Dreamy", "Calm"],
        "music_energy_pref": "calm",
        "music_style_pref": "acoustic",
        "popularity_pref": "balanced",
        "movie_themes": ["Memory"],
        "series_pacing": "slow_burn",
        "storytelling_style": ["atmospheric"],
        "preference_weights": {},
    }
    res_both = recommend_for_domain(catalog_index, "song", prefs, limit=10)
    langs = [item["language"] for item in res_both["items"]]
    assert len(res_both["items"]) == 10
    assert langs.count("Hindi") >= 4 and langs.count("English") >= 4
    assert all(item["explanation"]["reasons"] for item in res_both["items"])

    res_hi = recommend_for_domain(catalog_index, "movie", {**prefs, "language_mode": "hindi_only"}, limit=6)
    assert all(item["language"] in {"Hindi", "Bilingual"} for item in res_hi["items"])

    res_en = recommend_for_domain(catalog_index, "series", {**prefs, "language_mode": "english_only"}, limit=6)
    assert all(item["language"] in {"English", "Bilingual"} for item in res_en["items"])


def test_preference_changes_update_recommendations(catalog_index):
    calm_prefs = {
        "language_mode": "both",
        "music_genres": ["Acoustic", "Lo-Fi"],
        "moods": ["Calm", "Sad", "Melancholic"],
        "music_energy_pref": "calm",
        "music_style_pref": "acoustic",
    }
    energetic_prefs = {
        "language_mode": "both",
        "music_genres": ["Rock", "Electronic", "Dance"],
        "moods": ["Energetic", "Happy", "Adventurous"],
        "music_energy_pref": "high",
        "music_style_pref": "electronic",
    }
    r1 = [i["external_id"] for i in recommend_for_domain(catalog_index, "song", calm_prefs, limit=8)["items"]]
    r2 = [i["external_id"] for i in recommend_for_domain(catalog_index, "song", energetic_prefs, limit=8)["items"]]
    assert r1 != r2


def test_feedback_updates_and_suppresses(catalog_index):
    song = next(i for i in catalog_index.items if i["content_type"] == "song")
    weights = apply_feedback_to_weights({}, song, "like")
    assert song["id"] in weights["liked_ids"]
    assert any(v > 0 for v in weights["genres"].values())

    weights = apply_feedback_to_weights(weights, song, "not_interested")
    assert song["id"] in weights["suppressed_ids"]

    res = recommend_for_domain(
        catalog_index,
        "song",
        {"language_mode": "both", "preference_weights": weights},
        limit=20,
    )
    assert all(item["id"] != song["id"] for item in res["items"])


def test_cross_domain_pathways_and_chain(catalog_index):
    prefs = {
        "language_mode": "both",
        "music_genres": ["Atmospheric", "Dream Pop", "Hindi Indie"],
        "movie_genres": ["Drama"],
        "series_genres": ["Comedy"],
        "favourite_content": ["Nightcall", "Bayaan — Nahin Milta"],
        "moods": ["Dark", "Mysterious", "Melancholic"],
    }
    m_res = run_cross_domain_pathway(catalog_index, "music_to_movies", prefs, limit=6)
    assert len(m_res["recommendations"]) == 6
    assert all(r["content_type"] == "movie" for r in m_res["recommendations"])

    s_res = run_cross_domain_pathway(catalog_index, "series_to_music", prefs, limit=6)
    assert len(s_res["recommendations"]) == 6
    assert all(r["content_type"] == "song" for r in s_res["recommendations"])

    chain = build_discovery_chain(catalog_index, prefs)
    assert len(chain["steps"]) == 4
    assert all(step["item"] is not None for step in chain["steps"])

    unexpected = discover_unexpected_vibe(catalog_index, prefs, limit=6)
    assert len(unexpected) > 0
    assert all(u["explanation"]["reasons"] for u in unexpected)


def test_mood_to_story_nlp_matching(catalog_index):
    signals = extract_mood_signals_from_text(
        "I want something quiet, emotional, slightly mysterious, and atmospheric."
    )
    assert "Mysterious" in signals["extracted_moods"]
    assert signals["intensity"] == "calm"

    res = match_mood_to_story(
        catalog_index,
        selected_moods=["Mysterious"],
        mood_text="quiet emotional atmospheric rain",
        limit_per_domain=4,
    )
    assert len(res["songs"]) == 4
    assert len(res["movies"]) == 4
    assert len(res["series"]) == 4
    assert "not a psychological" in res["note"].lower()


def test_personality_analyzer_and_evaluation(catalog_index):
    prefs = {
        "language_mode": "both",
        "music_genres": ["Ambient", "Dream Pop"],
        "movie_genres": ["Mystery", "Psychological Thriller"],
        "series_genres": ["Sci-Fi", "Mystery"],
        "moods": ["Dark", "Mysterious", "Focused"],
        "music_energy_pref": "calm",
        "popularity_pref": "underrated",
    }
    profile = analyze_entertainment_personality(catalog_index, prefs)
    assert profile["archetype"]
    assert len(profile["dimensions"]) == 7
    assert "not psychological" in profile["disclaimer"].lower()

    recs = recommend_for_domain(catalog_index, "movie", prefs, limit=8)["items"]
    div = compute_intra_list_diversity(catalog_index, recs)
    nov = compute_novelty(catalog_index, recs)
    cov = compute_catalog_coverage([recs], len(catalog_index.items))
    assert 0.0 <= div <= 1.0
    assert nov >= 0.0
    assert cov > 0.0

    no_gt = evaluate_ranking_against_ground_truth([r["external_id"] for r in recs], None)
    assert no_gt["ground_truth_available"] is False
    assert no_gt["precision_at_k"] is None

    with_gt = evaluate_ranking_against_ground_truth(
        [r["external_id"] for r in recs], {recs[0]["external_id"]}, k=5
    )
    assert with_gt["hit_rate_at_k"] == 1.0
    assert with_gt["recall_at_k"] == 1.0
