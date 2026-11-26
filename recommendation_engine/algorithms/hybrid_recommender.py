"""Hybrid recommendation scoring, language balancing, diversity, collaborative filtering, and feedback weights."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from recommendation_engine.explainability.explainer import build_recommendation_explanation
from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex

FEEDBACK_DELTAS: Dict[str, float] = {
    "like": 0.35,
    "save": 0.45,
    "more_like_this": 0.60,
    "dislike": -0.45,
    "not_interested": -0.35,
    "less_like_this": -0.55,
}


@dataclass(frozen=True)
class HybridWeights:
    """Configurable, documented hybrid scoring weights (sum to 1.0)."""

    preference_sim: float = 0.28
    content_sim: float = 0.24
    mood_sim: float = 0.20
    cross_domain_sim: float = 0.14
    feedback_boost: float = 0.10
    novelty: float = 0.04


def apply_feedback_to_weights(
    current_weights: Optional[Dict[str, Any]],
    item: Dict[str, Any],
    feedback_type: str,
) -> Dict[str, Any]:
    """Update preference_weights transparently based on user feedback on an item."""
    weights: Dict[str, Any] = {
        "genres": dict((current_weights or {}).get("genres", {})),
        "moods": dict((current_weights or {}).get("moods", {})),
        "themes": dict((current_weights or {}).get("themes", {})),
        "artists": dict((current_weights or {}).get("artists", {})),
        "liked_ids": list((current_weights or {}).get("liked_ids", [])),
        "suppressed_ids": list((current_weights or {}).get("suppressed_ids", [])),
        "boosted_seed_ids": list((current_weights or {}).get("boosted_seed_ids", [])),
    }

    delta = FEEDBACK_DELTAS.get(feedback_type, 0.0)
    if delta == 0.0:
        return weights

    def _bump(bucket: Dict[str, float], key: str, amount: float) -> None:
        k = key.strip().lower()
        if not k:
            return
        updated = max(-2.5, min(3.0, float(bucket.get(k, 0.0)) + amount))
        bucket[k] = round(updated, 4)

    for g in item.get("genres", []):
        _bump(weights["genres"], g, delta)
    for m in item.get("mood_tags", []):
        _bump(weights["moods"], m, delta)
    for t in item.get("themes", []):
        _bump(weights["themes"], t, delta * 0.75)

    extra = item.get("extra_metadata") or {}
    for role_key in ("artist", "director", "creator"):
        val = extra.get(role_key)
        if isinstance(val, str):
            for name in val.split(","):
                _bump(weights["artists"], name, delta)

    item_id = item.get("id")
    if item_id is not None:
        item_id_int = int(item_id)
        if feedback_type in {"like", "save", "more_like_this"}:
            if item_id_int not in weights["liked_ids"]:
                weights["liked_ids"].append(item_id_int)
            if item_id_int in weights["suppressed_ids"]:
                weights["suppressed_ids"].remove(item_id_int)
            if feedback_type == "more_like_this" and item_id_int not in weights["boosted_seed_ids"]:
                weights["boosted_seed_ids"].append(item_id_int)
        elif feedback_type in {"dislike", "not_interested", "less_like_this"}:
            if item_id_int not in weights["suppressed_ids"]:
                weights["suppressed_ids"].append(item_id_int)
            if item_id_int in weights["liked_ids"]:
                weights["liked_ids"].remove(item_id_int)

    return weights


def compute_item_item_cf_scores(
    index: CatalogFeatureIndex,
    session_interactions: List[Dict[str, Any]],
    active_liked_ids: List[int],
    min_sessions_required: int = 5,
) -> Tuple[np.ndarray, bool]:
    """Compute item-item collaborative filtering scores ONLY when sufficient interaction data exists."""
    n_items = len(index.items)
    if n_items == 0 or not active_liked_ids:
        return np.zeros(n_items, dtype=float), False

    distinct_sessions = {row.get("session_id") for row in session_interactions if row.get("session_id")}
    if len(distinct_sessions) < min_sessions_required:
        return np.zeros(n_items, dtype=float), False

    session_list = sorted(distinct_sessions)
    sess_to_row = {s: i for i, s in enumerate(session_list)}
    matrix = np.zeros((len(session_list), n_items), dtype=float)

    for row in session_interactions:
        s_idx = sess_to_row.get(row.get("session_id"))
        c_idx = index.id_to_idx.get(row.get("content_id"))
        if s_idx is not None and c_idx is not None:
            matrix[s_idx, c_idx] += float(row.get("feedback_value", 1.0))

    if np.count_nonzero(matrix) < min_sessions_required:
        return np.zeros(n_items, dtype=float), False

    item_sims = cosine_similarity(matrix.T)
    cf_scores = np.zeros(n_items, dtype=float)
    valid_seed_cols = [index.id_to_idx[cid] for cid in active_liked_ids if cid in index.id_to_idx]
    if not valid_seed_cols:
        return np.zeros(n_items, dtype=float), False

    cf_scores = np.mean(item_sims[:, valid_seed_cols], axis=1)
    max_val = float(np.max(cf_scores)) if len(cf_scores) else 0.0
    if max_val > 0:
        cf_scores = cf_scores / max_val
    return np.clip(cf_scores, 0.0, 1.0), True


def is_language_eligible(item_lang: str, language_mode: str) -> bool:
    """Check whether an item's language matches the requested target recommendation pool."""
    if language_mode == "hindi_only":
        return item_lang in {"Hindi", "Bilingual"}
    if language_mode == "english_only":
        return item_lang in {"English", "Bilingual"}
    if language_mode == "hindi_pref_english_rec":
        return item_lang in {"English", "Bilingual"}
    if language_mode == "english_pref_hindi_rec":
        return item_lang in {"Hindi", "Bilingual"}
    return True


def balance_language_results(
    ranked_items: List[Dict[str, Any]],
    language_mode: str,
    limit: int,
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """Apply balanced Hindi/English interleaving when `language_mode == 'both'`."""
    if language_mode != "both":
        chosen = ranked_items[:limit]
        notice = None
        if not chosen:
            notice = f"No matching items found for language filter '{language_mode}'."
        return chosen, notice

    hindi = [item for item in ranked_items if item.get("language") == "Hindi"]
    english = [item for item in ranked_items if item.get("language") == "English"]
    other = [item for item in ranked_items if item.get("language") not in {"Hindi", "English"}]

    selected: List[Dict[str, Any]] = []
    hi_i, en_i = 0, 0
    while len(selected) < limit and (hi_i < len(hindi) or en_i < len(english)):
        if hi_i < len(hindi):
            selected.append(hindi[hi_i])
            hi_i += 1
        if len(selected) < limit and en_i < len(english):
            selected.append(english[en_i])
            en_i += 1

    for rem in other:
        if len(selected) >= limit:
            break
        selected.append(rem)

    notice = None
    target_per_lang = max(1, limit // 2)
    hi_selected = sum(1 for x in selected if x.get("language") == "Hindi")
    en_selected = sum(1 for x in selected if x.get("language") == "English")
    if len(selected) >= 4 and (hi_selected < target_per_lang or en_selected < target_per_lang):
        notice = (
            f"Balanced target (~{target_per_lang} Hindi / ~{target_per_lang} English): "
            f"returned {hi_selected} Hindi and {en_selected} English based on available eligible matches."
        )
    return selected, notice


def diversify_ranked_candidates(
    index: CatalogFeatureIndex,
    candidates: List[Tuple[float, int, Dict[str, float]]],
    pool_limit: int = 30,
    diversity_lambda: float = 0.22,
    max_per_artist: int = 2,
) -> List[Tuple[float, int, Dict[str, float]]]:
    """MMR-style diversity re-ranking with per-artist cap to avoid repetitive recommendations."""
    if not candidates:
        return []

    remaining = list(candidates)
    selected: List[Tuple[float, int, Dict[str, float]]] = []
    artist_counts: Dict[str, int] = {}

    while remaining and len(selected) < pool_limit:
        best_pos = 0
        best_mmr = -1e9

        for pos, (base_score, idx, _) in enumerate(remaining):
            item = index.items[idx]
            artist_name = str((item.get("extra_metadata") or {}).get("artist") or "").split(",")[0].strip().lower()
            if artist_name and artist_counts.get(artist_name, 0) >= max_per_artist:
                continue

            if not selected:
                mmr_score = base_score
            else:
                sel_indices = [s[1] for s in selected]
                sims = cosine_similarity(
                    index.combined_matrix[idx : idx + 1],
                    index.combined_matrix[sel_indices],
                )[0]
                max_sim = float(np.max(sims))
                mmr_score = ((1.0 - diversity_lambda) * base_score) - (diversity_lambda * max_sim)

            if mmr_score > best_mmr:
                best_mmr = mmr_score
                best_pos = pos

        if best_mmr == -1e9:
            break

        chosen = remaining.pop(best_pos)
        selected.append(chosen)
        artist_name = str((index.items[chosen[1]].get("extra_metadata") or {}).get("artist") or "").split(",")[0].strip().lower()
        if artist_name:
            artist_counts[artist_name] = artist_counts.get(artist_name, 0) + 1

    return selected


def recommend_for_domain(
    index: CatalogFeatureIndex,
    target_content_type: str,
    preferences: Dict[str, Any],
    limit: int = 10,
    category_filter: Optional[str] = None,
    weights: Optional[HybridWeights] = None,
    session_interactions: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Generate hybrid, language-balanced, diverse, explainable recommendations for a domain."""
    w = weights or HybridWeights()
    pref_weights = preferences.get("preference_weights") or {}
    suppressed_ids: Set[int] = {int(x) for x in pref_weights.get("suppressed_ids", [])}
    liked_ids: List[int] = [int(x) for x in pref_weights.get("liked_ids", [])]
    boosted_seed_ids: List[int] = [int(x) for x in pref_weights.get("boosted_seed_ids", [])]

    language_mode = preferences.get("language_mode", "both")

    # Resolve seed indices from favourite_content titles + liked_ids + boosted_seed_ids
    fav_titles = {t.strip().lower() for t in preferences.get("favourite_content", []) if t.strip()}
    seed_indices: List[int] = []
    seed_titles: List[str] = []

    for idx, item in enumerate(index.items):
        cid = item.get("id")
        if (cid is not None and int(cid) in liked_ids) or item.get("title", "").lower() in fav_titles:
            seed_indices.append(idx)
            seed_titles.append(item["title"])
        if cid is not None and int(cid) in boosted_seed_ids:
            seed_indices.append(idx)

    # For cross-lingual preference transfer modes, prioritize seeds from source language
    if language_mode == "hindi_pref_english_rec":
        hi_seeds = [i for i in seed_indices if index.items[i].get("language") == "Hindi"]
        if hi_seeds:
            seed_indices = hi_seeds
    elif language_mode == "english_pref_hindi_rec":
        en_seeds = [i for i in seed_indices if index.items[i].get("language") == "English"]
        if en_seeds:
            seed_indices = en_seeds

    content_sims = index.item_similarity_vector(seed_indices)
    cross_sims = index.cross_domain_vibe_similarity(seed_indices)

    # Query TF-IDF vector from explicit preference profile text
    pref_query_tokens = (
        list(preferences.get("music_genres", []))
        + list(preferences.get("movie_genres", []))
        + list(preferences.get("series_genres", []))
        + list(preferences.get("favourite_artists", []))
        + list(preferences.get("movie_themes", []))
        + list(preferences.get("storytelling_style", []))
        + list(preferences.get("moods", []))
    )
    query_sims = index.query_tfidf_similarity(" ".join(pref_query_tokens))

    # Genre frequency for novelty computation
    genre_freq: Dict[str, int] = {}
    for item in index.items:
        for g in item.get("genres", []):
            genre_freq[g.lower()] = genre_freq.get(g.lower(), 0) + 1
    max_freq = max(genre_freq.values(), default=1)

    cf_scores, cf_active = compute_item_item_cf_scores(
        index=index,
        session_interactions=session_interactions or [],
        active_liked_ids=liked_ids,
    )

    pref_moods = {m.lower() for m in preferences.get("moods", [])}
    pref_genres_domain = {
        g.lower()
        for g in preferences.get(
            {"song": "music_genres", "movie": "movie_genres", "series": "series_genres"}.get(
                target_content_type, "music_genres"
            ),
            [],
        )
    }
    pref_artists = {a.lower() for a in preferences.get("favourite_artists", [])}
    pref_themes = {t.lower() for t in preferences.get("movie_themes", [])}

    fb_genres = pref_weights.get("genres", {})
    fb_moods = pref_weights.get("moods", {})
    fb_artists = pref_weights.get("artists", {})

    scored_candidates: List[Tuple[float, int, Dict[str, float]]] = []

    for idx, item in enumerate(index.items):
        if item.get("content_type") != target_content_type:
            continue
        cid = item.get("id")
        if cid is not None and int(cid) in suppressed_ids:
            continue
        if not is_language_eligible(item.get("language", "English"), language_mode):
            continue

        extra = item.get("extra_metadata") or {}
        if category_filter and category_filter.lower() != "all":
            cat_l = category_filter.lower()
            disc_tag = str(extra.get("discovery_tag", "")).lower()
            item_genres_l = [g.lower() for g in item.get("genres", [])]
            item_moods_l = [m.lower() for m in item.get("mood_tags", [])]
            if not (
                cat_l in disc_tag
                or any(cat_l in g for g in item_genres_l)
                or any(cat_l in m for m in item_moods_l)
                or cat_l == item.get("language", "").lower()
            ):
                continue

        # Explicit preference overlap
        item_genres = {g.lower() for g in item.get("genres", [])}
        item_moods = {m.lower() for m in item.get("mood_tags", [])}
        item_themes = {t.lower() for t in item.get("themes", [])}

        genre_overlap = (
            len(item_genres & pref_genres_domain) / max(1, len(pref_genres_domain))
            if pref_genres_domain
            else 0.25
        )
        theme_overlap = (
            len(item_themes & pref_themes) / max(1, len(pref_themes)) if pref_themes else 0.0
        )

        talent_str = " ".join(str(extra.get(k, "")) for k in ("artist", "director", "creator")).lower()
        artist_hit = 1.0 if any(a in talent_str for a in pref_artists) else 0.0

        # Style / energy / pacing compatibility
        style_bonus = 0.0
        if target_content_type == "song":
            music_meta = extra.get("music_analysis") or {}
            item_style = str(extra.get("style") or music_meta.get("inferred_style") or "balanced").lower()
            item_energy = str(extra.get("energy") or music_meta.get("inferred_energy") or "medium").lower()
            if preferences.get("music_style_pref", "balanced") != "balanced" and item_style == preferences.get("music_style_pref"):
                style_bonus += 0.15
            if preferences.get("music_energy_pref", "balanced") != "balanced" and item_energy == preferences.get("music_energy_pref"):
                style_bonus += 0.15
        elif target_content_type == "series":
            pacing = str(extra.get("pacing") or "balanced").lower()
            if preferences.get("series_pacing", "balanced") != "balanced" and pacing == preferences.get("series_pacing"):
                style_bonus += 0.20

        q_sim = float(query_sims[idx]) if idx < len(query_sims) else 0.0
        pref_sim = min(1.0, (0.45 * genre_overlap) + (0.25 * q_sim) + (0.20 * artist_hit) + (0.10 * theme_overlap) + style_bonus)

        mood_sim = (
            len(item_moods & pref_moods) / max(1, len(pref_moods)) if pref_moods else 0.30
        )
        content_sim = float(content_sims[idx]) if idx < len(content_sims) else 0.0
        cross_sim = float(cross_sims[idx]) if idx < len(cross_sims) else 0.0

        # Feedback weight boost normalized to [0, 1]
        raw_fb = (
            sum(float(fb_genres.get(g, 0.0)) for g in item_genres) * 0.45
            + sum(float(fb_moods.get(m, 0.0)) for m in item_moods) * 0.35
            + sum(float(fb_artists.get(a, 0.0)) for a in fb_artists if a in talent_str) * 0.50
        )
        feedback_boost = float(1.0 / (1.0 + np.exp(-raw_fb))) if raw_fb != 0.0 else 0.0
        if cf_active:
            feedback_boost = min(1.0, (0.7 * feedback_boost) + (0.3 * float(cf_scores[idx])))

        # Novelty (higher for rarer genres or underrated tags when user wants underrated/discovery)
        avg_freq = np.mean([genre_freq.get(g, 1) for g in item_genres]) if item_genres else max_freq
        novelty = float(1.0 - (avg_freq / max(1, max_freq)))
        if preferences.get("popularity_pref") == "underrated" and "underrated" in str(extra.get("discovery_tag", "")).lower():
            novelty = min(1.0, novelty + 0.35)

        total = (
            w.preference_sim * pref_sim
            + w.content_sim * content_sim
            + w.mood_sim * mood_sim
            + w.cross_domain_sim * cross_sim
            + w.feedback_boost * feedback_boost
            + w.novelty * novelty
        )

        # Slight downrank if exact item is already in seed favourite titles
        if item.get("title", "").lower() in fav_titles:
            total *= 0.85

        breakdown = {
            "preference_sim": pref_sim,
            "content_sim": content_sim,
            "mood_sim": mood_sim,
            "cross_domain_sim": cross_sim,
            "feedback_boost": feedback_boost,
            "novelty": novelty,
        }
        scored_candidates.append((float(total), idx, breakdown))

    scored_candidates.sort(key=lambda x: x[0], reverse=True)
    diversified = diversify_ranked_candidates(
        index=index,
        candidates=scored_candidates,
        pool_limit=max(limit * 3, 24),
    )

    enriched_items: List[Dict[str, Any]] = []
    for score, idx, breakdown in diversified:
        item = dict(index.items[idx])
        item["match_score"] = round(min(99.5, max(15.0, score * 100.0)), 1)
        item["cluster_id"] = index.cluster_labels[idx] if idx < len(index.cluster_labels) else 0
        item["explanation"] = build_recommendation_explanation(
            item=item,
            preferences=preferences,
            score_breakdown=breakdown,
            seed_titles=seed_titles,
        )
        enriched_items.append(item)

    balanced_items, lang_notice = balance_language_results(
        ranked_items=enriched_items,
        language_mode=language_mode,
        limit=limit,
    )

    return {
        "items": balanced_items,
        "language_notice": lang_notice,
        "collaborative_filtering_active": cf_active,
        "total_candidates": len(scored_candidates),
    }
