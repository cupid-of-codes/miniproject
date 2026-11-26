"""NLP Mood-to-Story Matching across songs, movies, and web series."""

import re
from typing import Any, Dict, List, Optional

import numpy as np

from recommendation_engine.explainability.explainer import build_recommendation_explanation
from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex
from recommendation_engine.preprocessing.text_cleaner import CANONICAL_MOODS, canonicalize_moods

MOOD_INTENSITY_KEYWORDS = {
    "quiet": ("Calm", "Melancholic", "Dreamy"),
    "soft": ("Calm", "Comfort", "Dreamy"),
    "loud": ("Energetic", "Angry"),
    "fast": ("Energetic", "Adventurous"),
    "slow": ("Calm", "Melancholic"),
    "rain": ("Melancholic", "Nostalgic", "Romantic"),
    "night": ("Dark", "Mysterious", "Dreamy", "Chill"),
    "midnight": ("Dark", "Mysterious", "Dreamy"),
    "cry": ("Sad", "Emotional", "Melancholic"),
    "heal": ("Hopeful", "Comfort", "Calm"),
    "mystery": ("Mysterious", "Focused", "Dark"),
    "thriller": ("Anxious", "Mysterious", "Dark"),
    "cozy": ("Comfort", "Chill", "Happy"),
    "study": ("Focused", "Calm", "Chill"),
    "travel": ("Adventurous", "Hopeful", "Happy"),
    "atmospheric": ("Dreamy", "Dark", "Mysterious"),
    "emotional": ("Emotional", "Melancholic", "Sad"),
}


def extract_mood_signals_from_text(prompt: str) -> Dict[str, Any]:
    """Extract canonical moods, intensity, and theme keywords from free-text user mood prompts."""
    if not prompt or not prompt.strip():
        return {"extracted_moods": [], "keywords": [], "intensity": "balanced"}

    lowered = prompt.lower()
    extracted = canonicalize_moods([], fallback_text=prompt)
    seen = {m.lower() for m in extracted}

    for token, mapped_moods in MOOD_INTENSITY_KEYWORDS.items():
        if re.search(rf"\b{re.escape(token)}\b", lowered):
            for m in mapped_moods:
                if m.lower() not in seen:
                    seen.add(m.lower())
                    extracted.append(m)

    intensity = "balanced"
    if any(w in lowered for w in ["quiet", "gentle", "soft", "slow", "calm", "peaceful"]):
        intensity = "calm"
    elif any(w in lowered for w in ["intense", "energetic", "fast", "adrenaline", "loud", "fierce"]):
        intensity = "high"

    keywords = [w for w in re.findall(r"[a-z]{3,}", lowered) if w not in {"want", "something", "that", "feels", "very", "with", "and", "like"}]
    return {
        "extracted_moods": extracted,
        "keywords": keywords[:10],
        "intensity": intensity,
    }


def match_mood_to_story(
    index: CatalogFeatureIndex,
    selected_moods: List[str],
    mood_text: str = "",
    preferences: Optional[Dict[str, Any]] = None,
    language_mode: str = "both",
    limit_per_domain: int = 5,
) -> Dict[str, Any]:
    """Match selected moods and/or free-text mood description to songs, movies, and web series."""
    prefs = dict(preferences or {})
    nlp_signals = extract_mood_signals_from_text(mood_text)
    target_moods = canonicalize_moods(selected_moods + nlp_signals["extracted_moods"])

    if not target_moods and mood_text:
        target_moods = ["Dreamy", "Emotional"]

    target_set = {m.lower() for m in target_moods}
    tfidf_sims = index.query_tfidf_similarity(
        f"{' '.join(target_moods)} {mood_text}".strip()
    )

    # Language eligibility helper
    def _lang_allowed(item_lang: str) -> bool:
        if language_mode == "hindi_only":
            return item_lang in {"Hindi", "Bilingual"}
        if language_mode == "english_only":
            return item_lang in {"English", "Bilingual"}
        return True

    domain_results: Dict[str, List[Dict[str, Any]]] = {"song": [], "movie": [], "series": []}
    scored_by_domain: Dict[str, List[tuple[float, int, Dict[str, float]]]] = {
        "song": [],
        "movie": [],
        "series": [],
    }

    for idx, item in enumerate(index.items):
        if not _lang_allowed(item.get("language", "English")):
            continue
        item_moods = {m.lower() for m in item.get("mood_tags", [])}
        overlap_count = len(target_set & item_moods)
        mood_sim = overlap_count / max(1, len(target_set))
        text_sim = float(tfidf_sims[idx]) if idx < len(tfidf_sims) else 0.0

        extra = item.get("extra_metadata") or {}
        item_energy = str(
            extra.get("energy")
            or (extra.get("music_analysis") or {}).get("inferred_energy")
            or extra.get("pacing")
            or "balanced"
        ).lower()
        intensity_bonus = 0.0
        if nlp_signals["intensity"] == "calm" and item_energy in {"calm", "slow_burn"}:
            intensity_bonus = 0.12
        elif nlp_signals["intensity"] == "high" and item_energy in {"high", "fast_paced"}:
            intensity_bonus = 0.12

        total_score = min(1.0, (0.62 * mood_sim) + (0.28 * text_sim) + intensity_bonus)
        if total_score <= 0.0:
            continue

        ctype = item.get("content_type", "song")
        if ctype in scored_by_domain:
            scored_by_domain[ctype].append(
                (
                    total_score,
                    idx,
                    {
                        "mood_sim": mood_sim,
                        "content_sim": text_sim,
                        "intensity_bonus": intensity_bonus,
                    },
                )
            )

    for ctype, candidates in scored_by_domain.items():
        candidates.sort(key=lambda x: x[0], reverse=True)
        # Apply light Hindi/English balance when language_mode == 'both'
        if language_mode == "both":
            hindi = [c for c in candidates if index.items[c[1]].get("language") == "Hindi"]
            english = [c for c in candidates if index.items[c[1]].get("language") == "English"]
            other = [c for c in candidates if index.items[c[1]].get("language") not in {"Hindi", "English"}]
            balanced: List[tuple[float, int, Dict[str, float]]] = []
            hi_i, en_i = 0, 0
            while len(balanced) < limit_per_domain and (hi_i < len(hindi) or en_i < len(english)):
                if hi_i < len(hindi):
                    balanced.append(hindi[hi_i])
                    hi_i += 1
                if len(balanced) < limit_per_domain and en_i < len(english):
                    balanced.append(english[en_i])
                    en_i += 1
            for rem in other:
                if len(balanced) >= limit_per_domain:
                    break
                balanced.append(rem)
            chosen = balanced
        else:
            chosen = candidates[:limit_per_domain]

        for score, idx, breakdown in chosen:
            item = dict(index.items[idx])
            matched_moods = [m for m in item.get("mood_tags", []) if m.lower() in target_set]
            explanation = build_recommendation_explanation(
                item=item,
                preferences={**prefs, "moods": target_moods, "language_mode": language_mode},
                score_breakdown=breakdown,
            )
            if matched_moods:
                explanation["summary"] = (
                    f"Matches your {', '.join(matched_moods[:3])} mood signal"
                    + (f" and '{mood_text[:45]}'" if mood_text else ".")
                )
            item["match_score"] = round(score * 100.0, 1)
            item["explanation"] = explanation
            domain_results[ctype].append(item)

    return {
        "target_moods": target_moods,
        "nlp_signals": nlp_signals,
        "songs": domain_results["song"],
        "movies": domain_results["movie"],
        "series": domain_results["series"],
        "note": "Mood-to-Story Matching maps entertainment preferences and aesthetic tones—it is not a psychological or mental-health diagnostic tool.",
    }
