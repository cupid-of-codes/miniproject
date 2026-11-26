"""NLP text preprocessing, taxonomy canonicalization, and honest metadata inference."""

import re
from typing import Any, Dict, List

CANONICAL_MOODS = [
    "Happy",
    "Sad",
    "Romantic",
    "Chill",
    "Energetic",
    "Nostalgic",
    "Focused",
    "Dreamy",
    "Dark",
    "Mysterious",
    "Adventurous",
    "Comfort",
    "Angry",
    "Melancholic",
    "Anxious",
    "Hopeful",
    "Emotional",
    "Calm",
]

_MOOD_SYNONYMS = {
    "calm": "Calm",
    "peaceful": "Calm",
    "serene": "Calm",
    "tranquil": "Calm",
    "chill": "Chill",
    "relaxed": "Chill",
    "lofi": "Chill",
    "lo-fi": "Chill",
    "warm": "Comfort",
    "cozy": "Comfort",
    "comfort": "Comfort",
    "comforting": "Comfort",
    "feel-good": "Happy",
    "happy": "Happy",
    "joyful": "Happy",
    "uplifting": "Hopeful",
    "hopeful": "Hopeful",
    "optimistic": "Hopeful",
    "sad": "Sad",
    "heartbreak": "Sad",
    "grief": "Sad",
    "melancholic": "Melancholic",
    "melancholy": "Melancholic",
    "bittersweet": "Melancholic",
    "wistful": "Melancholic",
    "romantic": "Romantic",
    "love": "Romantic",
    "intimate": "Romantic",
    "nostalgic": "Nostalgic",
    "retro": "Nostalgic",
    "vintage": "Nostalgic",
    "energetic": "Energetic",
    "hype": "Energetic",
    "intense": "Energetic",
    "focused": "Focused",
    "focus": "Focused",
    "study": "Focused",
    "dreamy": "Dreamy",
    "ethereal": "Dreamy",
    "atmospheric": "Dreamy",
    "dark": "Dark",
    "noir": "Dark",
    "bleak": "Dark",
    "brooding": "Dark",
    "mysterious": "Mysterious",
    "mystery": "Mysterious",
    "suspense": "Mysterious",
    "eerie": "Mysterious",
    "adventurous": "Adventurous",
    "adventure": "Adventurous",
    "travel": "Adventurous",
    "angry": "Angry",
    "fierce": "Angry",
    "rebellious": "Angry",
    "anxious": "Anxious",
    "tense": "Anxious",
    "restless": "Anxious",
    "emotional": "Emotional",
    "moving": "Emotional",
    "poignant": "Emotional",
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "in", "on", "at", "to", "for", "of", "with",
    "is", "are", "was", "were", "by", "from", "into", "through", "about", "that",
    "this", "his", "her", "their", "its", "as", "it", "who", "while", "when",
}

_NON_ALNUM_RE = re.compile(r"[^a-z0-9\s\-]+")
_MULTI_SPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """Lowercase, strip punctuation, and remove basic English stopwords."""
    if not text:
        return ""
    cleaned = _NON_ALNUM_RE.sub(" ", text.lower())
    cleaned = _MULTI_SPACE_RE.sub(" ", cleaned).strip()
    tokens = [tok for tok in cleaned.split(" ") if tok and tok not in _STOPWORDS]
    return " ".join(tokens)


def normalize_language(raw_language: str) -> str:
    """Normalize language codes/labels into Hindi, English, or Bilingual."""
    if not raw_language:
        return "English"
    val = raw_language.strip().lower()
    if val in {"hi", "hin", "hindi"}:
        return "Hindi"
    if val in {"en", "eng", "english"}:
        return "English"
    if "hindi" in val and "english" in val:
        return "Bilingual"
    if val in {"bilingual", "mixed", "hinglish"}:
        return "Bilingual"
    return raw_language.strip().title()


def normalize_list_field(values: Any) -> List[str]:
    """Normalize comma-separated strings or lists into clean deduplicated title-cased lists."""
    if not values:
        return []
    if isinstance(values, str):
        items = [part.strip() for part in values.split(",")]
    elif isinstance(values, (list, tuple, set)):
        items = [str(part).strip() for part in values]
    else:
        items = [str(values).strip()]

    seen = set()
    result: List[str] = []
    for item in items:
        if not item:
            continue
        key = item.lower()
        if key not in seen:
            seen.add(key)
            result.append(item)
    return result


def canonicalize_moods(moods: Any, fallback_text: str = "") -> List[str]:
    """Map raw mood tags and optional descriptive text into canonical VibeVerse moods."""
    raw_items = normalize_list_field(moods)
    found: List[str] = []
    seen = set()

    for raw in raw_items:
        mapped = _MOOD_SYNONYMS.get(raw.lower())
        label = mapped or raw.title()
        if label.lower() not in seen:
            seen.add(label.lower())
            found.append(label)

    if not found and fallback_text:
        lowered = fallback_text.lower()
        for keyword, canonical in _MOOD_SYNONYMS.items():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered) and canonical.lower() not in seen:
                seen.add(canonical.lower())
                found.append(canonical)

    return found


def infer_music_characteristics(item: Dict[str, Any]) -> Dict[str, Any]:
    """Estimate music mood/style characteristics from metadata without fabricating audio numbers.

    Explicitly marks estimates as `model_generated_estimate` when raw audio features are absent.
    """
    extra = dict(item.get("extra_metadata") or {})
    genres_lower = " ".join(g.lower() for g in item.get("genres", []))
    moods_lower = " ".join(m.lower() for m in item.get("mood_tags", []))
    desc_lower = (item.get("description") or "").lower()
    combined = f"{genres_lower} {moods_lower} {desc_lower}"

    style = extra.get("style")
    if not style:
        if any(k in combined for k in ["synth", "electronic", "edm", "lo-fi", "lofi", "trip-hop"]):
            style = "electronic"
        elif any(k in combined for k in ["acoustic", "folk", "sufi", "piano", "guitar"]):
            style = "acoustic"
        else:
            style = "balanced"

    energy = extra.get("energy")
    if not energy:
        if any(k in combined for k in ["energetic", "workout", "dance", "high-octane", "rock", "angry"]):
            energy = "high"
        elif any(k in combined for k in ["calm", "chill", "ambient", "lullaby", "quiet", "slow"]):
            energy = "calm"
        else:
            energy = "medium"

    return {
        "inferred_style": style,
        "inferred_energy": energy,
        "inferred_moods": canonicalize_moods(item.get("mood_tags", []), item.get("description", "")),
        "is_model_generated_estimate": True,
        "estimation_basis": "Derived from genre, mood tags, and textual metadata (no audio waveform DSP features claimed).",
    }
