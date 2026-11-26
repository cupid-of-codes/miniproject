"""Deterministic 'Why This Is Your Vibe' recommendation explanation generator."""

from typing import Any, Dict, List, Optional


def build_recommendation_explanation(
    item: Dict[str, Any],
    preferences: Dict[str, Any],
    score_breakdown: Dict[str, float],
    seed_titles: Optional[List[str]] = None,
    pathway_label: Optional[str] = None,
    is_unexpected_discovery: bool = False,
) -> Dict[str, Any]:
    """Generate structured, algorithmic explanations derived strictly from real score signals."""
    reasons: List[str] = []

    item_genres = {g.lower(): g for g in item.get("genres", [])}
    item_moods = {m.lower(): m for m in item.get("mood_tags", [])}
    item_themes = {t.lower(): t for t in item.get("themes", [])}

    # 1. Genre overlap
    ctype = item.get("content_type", "song")
    pref_genre_key = {
        "song": "music_genres",
        "movie": "movie_genres",
        "series": "series_genres",
    }.get(ctype, "music_genres")
    pref_genres = [g for g in preferences.get(pref_genre_key, []) if g.lower() in item_genres]
    if pref_genres:
        reasons.append(f"Matches your selected genres: {', '.join(pref_genres[:3])}.")

    # 2. Mood overlap
    pref_moods = [m for m in preferences.get("moods", []) if m.lower() in item_moods]
    if pref_moods:
        reasons.append(f"Aligns with your current mood profile ({', '.join(pref_moods[:3])}).")

    # 3. Artist/talent match
    extra = item.get("extra_metadata") or {}
    talent_str = " ".join(
        str(extra.get(k, "")) for k in ("artist", "director", "creator")
    ).lower()
    fav_artists = [a for a in preferences.get("favourite_artists", []) if a.lower() in talent_str]
    if fav_artists:
        reasons.append(f"Features your favourite artist/creator: {', '.join(fav_artists[:2])}.")

    # 4. Theme overlap
    pref_themes = [t for t in preferences.get("movie_themes", []) if t.lower() in item_themes]
    if pref_themes:
        reasons.append(f"Matches your preferred storytelling themes ({', '.join(pref_themes[:2])}).")

    # 5. Cross-domain / seed similarity
    if pathway_label and score_breakdown.get("cross_domain_sim", 0.0) > 0.15:
        reasons.append(
            f"Bridges your {pathway_label} vibe through shared mood and thematic atmosphere."
        )
    elif seed_titles and score_breakdown.get("content_sim", 0.0) > 0.12:
        reasons.append(f"Shares strong narrative and aesthetic DNA with {', '.join(seed_titles[:2])}.")

    # 6. Feedback influence
    if score_breakdown.get("feedback_boost", 0.0) > 0.05:
        reasons.append("Boosted by your previous likes, saves, or 'More like this' feedback.")

    # 7. Language match
    lang_mode = preferences.get("language_mode", "both")
    item_lang = item.get("language", "English")
    if lang_mode == "hindi_only" and item_lang == "Hindi":
        reasons.append("Fits your Hindi-language preference.")
    elif lang_mode == "english_only" and item_lang == "English":
        reasons.append("Fits your English-language preference.")
    elif lang_mode == "hindi_pref_english_rec" and item_lang == "English":
        reasons.append("Translates your Hindi taste profile into an English discovery.")
    elif lang_mode == "english_pref_hindi_rec" and item_lang == "Hindi":
        reasons.append("Translates your English taste profile into a Hindi discovery.")

    # 8. Unexpected discovery
    if is_unexpected_discovery:
        reasons.append(
            "Introduces you to an unexplored genre while preserving your core mood and thematic vibe."
        )

    if not reasons:
        top_moods = ", ".join(item.get("mood_tags", [])[:2]) or "balanced tone"
        reasons.append(
            f"Selected for high overall vibe compatibility ({top_moods}) across your current profile."
        )

    return {
        "summary": reasons[0],
        "reasons": reasons[:4],
        "score_breakdown": {k: round(float(v), 4) for k, v in score_breakdown.items()},
    }
