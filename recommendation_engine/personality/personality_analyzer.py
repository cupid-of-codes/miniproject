"""Entertainment Personality Analyzer (non-clinical preference pattern analysis)."""

from collections import Counter
from typing import Any, Dict, List, Optional

from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex


def _clamp(val: float) -> float:
    return round(max(5.0, min(95.0, val)), 1)


def analyze_entertainment_personality(
    index: CatalogFeatureIndex,
    preferences: Dict[str, Any],
    feedback_history: Optional[List[Dict[str, Any]]] = None,
    saved_items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Compute 7 entertainment preference dimensions, archetype, breakdowns, and narrative."""
    feedback_list = list(feedback_history or [])
    saved_list = list(saved_items or [])

    moods = [m.lower() for m in preferences.get("moods", [])]
    music_genres = [g.lower() for g in preferences.get("music_genres", [])]
    movie_genres = [g.lower() for g in preferences.get("movie_genres", [])]
    series_genres = [g.lower() for g in preferences.get("series_genres", [])]
    themes = [t.lower() for t in preferences.get("movie_themes", [])]
    storytelling = [s.lower() for s in preferences.get("storytelling_style", [])]

    all_tokens = set(moods + music_genres + movie_genres + series_genres + themes + storytelling)

    # Also incorporate positive feedback / saved item signals
    liked_item_ids = {
        int(f["content_id"])
        for f in feedback_list
        if f.get("feedback_type") in {"like", "save", "more_like_this"} and f.get("content_id") is not None
    } | {int(s["id"]) for s in saved_list if s.get("id") is not None}

    liked_items = [item for item in index.items if item.get("id") in liked_item_ids]
    for item in liked_items:
        all_tokens.update(g.lower() for g in item.get("genres", []))
        all_tokens.update(m.lower() for m in item.get("mood_tags", []))
        all_tokens.update(t.lower() for t in item.get("themes", []))

    # 1. Emotional vs Analytical (0 = Analytical, 100 = Emotional)
    emotional_hits = len(all_tokens & {"emotional", "melancholic", "sad", "romantic", "soul", "sufi", "heartbreak", "drama"})
    analytical_hits = len(all_tokens & {"mystery", "focused", "sci-fi", "crime and investigation", "puzzle-box", "investigative", "procedural"})
    emotional_vs_analytical = _clamp(50.0 + (emotional_hits - analytical_hits) * 11.0)

    # 2. Mainstream vs Niche (0 = Mainstream, 100 = Niche)
    pop_pref = preferences.get("popularity_pref", "balanced")
    niche_base = {"popular": 28.0, "balanced": 50.0, "underrated": 78.0}.get(pop_pref, 50.0)
    niche_hits = len(all_tokens & {"indie", "hindi indie", "ambient", "art rock", "trip-hop", "neoclassical", "experimental", "slow-burn"})
    mainstream_vs_niche = _clamp(niche_base + niche_hits * 5.0)

    # 3. Calm vs Energetic (0 = Calm, 100 = Energetic)
    energy_pref = preferences.get("music_energy_pref", "balanced")
    energy_base = {"calm": 24.0, "balanced": 50.0, "high": 78.0}.get(energy_pref, 50.0)
    calm_hits = len(all_tokens & {"calm", "chill", "lo-fi", "ambient", "acoustic", "sleep", "slow_burn"})
    high_hits = len(all_tokens & {"energetic", "workout", "rock", "dance", "edm", "fast_paced", "action"})
    calm_vs_energetic = _clamp(energy_base + (high_hits - calm_hits) * 7.5)

    # 4. Lighthearted vs Dark (0 = Lighthearted, 100 = Dark)
    dark_hits = len(all_tokens & {"dark", "dark cinema", "dark stories", "neo-noir", "mysterious", "anxious", "psychological thriller", "crime"})
    light_hits = len(all_tokens & {"happy", "comfort", "feel-good", "comedy", "slice-of-life", "hopeful"})
    lighthearted_vs_dark = _clamp(50.0 + (dark_hits - light_hits) * 10.0)

    # 5. Romantic vs Adventure-Oriented (0 = Romantic, 100 = Adventure-Oriented)
    rom_hits = len(all_tokens & {"romantic", "romance", "intimacy", "love", "dream pop"})
    adv_hits = len(all_tokens & {"adventure", "adventurous", "sci-fi", "travel", "fantasy", "action"})
    romantic_vs_adventure = _clamp(50.0 + (adv_hits - rom_hits) * 12.0)

    # 6. Familiar vs Exploratory (0 = Familiar, 100 = Exploratory)
    unique_genre_count = len(set(music_genres + movie_genres + series_genres))
    lang_bonus = 12.0 if preferences.get("language_mode") in {"both", "hindi_pref_english_rec", "english_pref_hindi_rec"} else 0.0
    familiar_vs_exploratory = _clamp(32.0 + unique_genre_count * 4.5 + lang_bonus)

    # 7. Story-Driven vs Aesthetic-Driven (0 = Story-Driven, 100 = Aesthetic-Driven)
    story_hits = len(all_tokens & {"storytelling", "mystery", "psychological drama", "crime and investigation", "character-driven", "plot-twist"})
    aesthetic_hits = len(all_tokens & {"dreamy", "atmospheric", "synthwave", "ambient", "lo-fi", "visual", "neon", "cinematic"})
    story_vs_aesthetic = _clamp(50.0 + (aesthetic_hits - story_hits) * 10.0)

    dimensions = [
        {"axis": "Emotional vs Analytical", "left_label": "Analytical", "right_label": "Emotional", "score": emotional_vs_analytical},
        {"axis": "Mainstream vs Niche", "left_label": "Mainstream", "right_label": "Niche", "score": mainstream_vs_niche},
        {"axis": "Calm vs Energetic", "left_label": "Calm", "right_label": "Energetic", "score": calm_vs_energetic},
        {"axis": "Lighthearted vs Dark", "left_label": "Lighthearted", "right_label": "Dark", "score": lighthearted_vs_dark},
        {"axis": "Romantic vs Adventure", "left_label": "Romantic", "right_label": "Adventure", "score": romantic_vs_adventure},
        {"axis": "Familiar vs Exploratory", "left_label": "Familiar", "right_label": "Exploratory", "score": familiar_vs_exploratory},
        {"axis": "Story vs Aesthetic", "left_label": "Story-Driven", "right_label": "Aesthetic-Driven", "score": story_vs_aesthetic},
    ]

    # Deterministic Archetype Mapping based on dominant dimension patterns
    if lighthearted_vs_dark >= 62 and emotional_vs_analytical <= 48:
        archetype = "The Plot Detective"
        archetype_tagline = "Drawn to intricate mysteries, layered suspense, and razor-sharp storytelling."
    elif story_vs_aesthetic >= 58 and calm_vs_energetic <= 48 and lighthearted_vs_dark >= 52:
        archetype = "The Midnight Dreamer"
        archetype_tagline = "Lives for atmospheric late-night soundtracks, moody visuals, and quiet emotional depth."
    elif mainstream_vs_niche >= 62 and familiar_vs_exploratory >= 60:
        archetype = "The Indie Explorer"
        archetype_tagline = "Finds hidden gems across borders, acoustic textures, and unconventional narratives."
    elif "nostalgic" in all_tokens or "comfort" in all_tokens and calm_vs_energetic <= 50:
        archetype = "The Nostalgia Collector"
        archetype_tagline = "Treasures timeless melodies, warm comfort cinema, and memories woven into story."
    elif calm_vs_energetic >= 64 and lighthearted_vs_dark <= 52:
        archetype = "The Main Character Energy"
        archetype_tagline = "Fuels every moment with kinetic soundtracks, bold momentum, and vibrant stories."
    elif emotional_vs_analytical >= 64 and story_vs_aesthetic <= 55:
        archetype = "The Cinematic Soul"
        archetype_tagline = "Connects deeply with character-driven arcs, expressive music, and unforgettable emotion."
    elif familiar_vs_exploratory >= 68:
        archetype = "The Genre Jumper"
        archetype_tagline = "Effortlessly bridges Hindi and English worlds from lo-fi beats to psychological sci-fi."
    else:
        archetype = "The Soft Chaos Curator"
        archetype_tagline = "Balances comfort warmth with sudden plunges into moody, captivating worlds."

    # Real breakdown counts from preferences + liked items
    genre_counter = Counter(preferences.get("music_genres", []) + preferences.get("movie_genres", []) + preferences.get("series_genres", []))
    mood_counter = Counter(preferences.get("moods", []))
    for item in liked_items:
        genre_counter.update(item.get("genres", []))
        mood_counter.update(item.get("mood_tags", []))

    lang_mode = preferences.get("language_mode", "both")
    lang_dist = {
        "hindi_only": {"Hindi": 100, "English": 0},
        "english_only": {"Hindi": 0, "English": 100},
        "both": {"Hindi": 50, "English": 50},
        "hindi_pref_english_rec": {"Hindi": 60, "English": 40},
        "english_pref_hindi_rec": {"Hindi": 40, "English": 60},
    }.get(lang_mode, {"Hindi": 50, "English": 50})

    domain_interest = {
        "Music": max(1, len(preferences.get("music_genres", [])) + len(preferences.get("favourite_artists", []))),
        "Movies": max(1, len(preferences.get("movie_genres", [])) + len(preferences.get("movie_themes", []))),
        "Web Series": max(1, len(preferences.get("series_genres", [])) + len(preferences.get("storytelling_style", []))),
    }

    top_genres_str = ", ".join(g for g, _ in genre_counter.most_common(3)) or "diverse genres"
    top_moods_str = ", ".join(m for m, _ in mood_counter.most_common(3)) or "balanced moods"

    explanation = (
        f"Based on your current selections ({top_genres_str}) and mood affinity ({top_moods_str}), "
        f"your profile aligns with '{archetype}'. {archetype_tagline}"
    )

    return {
        "archetype": archetype,
        "archetype_tagline": archetype_tagline,
        "explanation": explanation,
        "dimensions": dimensions,
        "breakdowns": {
            "top_genres": dict(genre_counter.most_common(8)),
            "mood_distribution": dict(mood_counter.most_common(8)),
            "language_distribution": lang_dist,
            "domain_balance": domain_interest,
        },
        "disclaimer": "Entertainment preference dimensions reflect your selected tastes and interactions only—they are not psychological traits or diagnoses.",
    }
