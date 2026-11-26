"""Cross-domain recommendation pathways (Music ↔ Movies ↔ Web Series), Discovery Chains & Unexpected Vibe."""

from typing import Any, Dict, List, Optional

import numpy as np

from recommendation_engine.algorithms.hybrid_recommender import (
    balance_language_results,
    diversify_ranked_candidates,
    is_language_eligible,
)
from recommendation_engine.explainability.explainer import build_recommendation_explanation
from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex

PATHWAY_CONFIG: Dict[str, tuple[str, str, str]] = {
    "music_to_movies": ("song", "movie", "music taste"),
    "music_to_series": ("song", "series", "music taste"),
    "movies_to_music": ("movie", "song", "movie taste"),
    "series_to_music": ("series", "song", "web series taste"),
}


def _resolve_seed_indices(
    index: CatalogFeatureIndex,
    source_domain: str,
    preferences: Dict[str, Any],
    seed_item_titles: Optional[List[str]] = None,
) -> tuple[List[int], List[str]]:
    """Find catalog indices matching user's seeds or preferences in the source domain."""
    explicit_titles = {t.strip().lower() for t in (seed_item_titles or []) if t.strip()}
    fav_titles = {t.strip().lower() for t in preferences.get("favourite_content", []) if t.strip()}
    combined_titles = explicit_titles | fav_titles

    seed_indices: List[int] = []
    seed_titles: List[str] = []

    for idx, item in enumerate(index.items):
        if item.get("content_type") != source_domain:
            continue
        if item.get("title", "").lower() in combined_titles:
            seed_indices.append(idx)
            seed_titles.append(item["title"])

    # Fall back to matching source domain items by user's genre/artist/mood profile
    if not seed_indices:
        pref_genres = {
            g.lower()
            for g in preferences.get(
                {"song": "music_genres", "movie": "movie_genres", "series": "series_genres"}.get(
                    source_domain, "music_genres"
                ),
                [],
            )
        }
        pref_moods = {m.lower() for m in preferences.get("moods", [])}
        pref_artists = {a.lower() for a in preferences.get("favourite_artists", [])}

        scored_seeds: List[tuple[int, int, str]] = []
        for idx, item in enumerate(index.items):
            if item.get("content_type") != source_domain:
                continue
            extra = item.get("extra_metadata") or {}
            talent = " ".join(str(extra.get(k, "")) for k in ("artist", "director", "creator")).lower()
            hits = (
                len({g.lower() for g in item.get("genres", [])} & pref_genres) * 2
                + len({m.lower() for m in item.get("mood_tags", [])} & pref_moods)
                + (3 if any(a in talent for a in pref_artists) else 0)
            )
            if hits > 0:
                scored_seeds.append((hits, idx, item["title"]))

        scored_seeds.sort(reverse=True)
        for _, idx, title in scored_seeds[:5]:
            seed_indices.append(idx)
            seed_titles.append(title)

    # Final fallback: pick top representative items from source domain
    if not seed_indices:
        for idx, item in enumerate(index.items):
            if item.get("content_type") == source_domain:
                seed_indices.append(idx)
                seed_titles.append(item["title"])
                if len(seed_indices) >= 3:
                    break

    return seed_indices, seed_titles


def run_cross_domain_pathway(
    index: CatalogFeatureIndex,
    pathway: str,
    preferences: Dict[str, Any],
    seed_titles_override: Optional[List[str]] = None,
    limit: int = 8,
) -> Dict[str, Any]:
    """Execute one of the 4 direct cross-domain pathways (e.g., Music -> Movies)."""
    if pathway not in PATHWAY_CONFIG:
        raise ValueError(f"Unsupported cross-domain pathway: {pathway}")

    source_domain, target_domain, pathway_label = PATHWAY_CONFIG[pathway]
    seed_indices, seed_titles = _resolve_seed_indices(
        index=index,
        source_domain=source_domain,
        preferences=preferences,
        seed_item_titles=seed_titles_override,
    )

    vibe_sims = index.cross_domain_vibe_similarity(seed_indices)
    combined_sims = index.item_similarity_vector(seed_indices)
    language_mode = preferences.get("language_mode", "both")
    pref_moods = {m.lower() for m in preferences.get("moods", [])}
    suppressed = {
        int(x) for x in (preferences.get("preference_weights") or {}).get("suppressed_ids", [])
    }

    seed_clusters = {
        index.cluster_labels[i] for i in seed_indices if i < len(index.cluster_labels)
    }

    candidates: List[tuple[float, int, Dict[str, float]]] = []
    for idx, item in enumerate(index.items):
        if item.get("content_type") != target_domain:
            continue
        if item.get("id") is not None and int(item["id"]) in suppressed:
            continue
        if not is_language_eligible(item.get("language", "English"), language_mode):
            continue

        vibe_sim = float(vibe_sims[idx])
        comb_sim = float(combined_sims[idx])
        item_moods = {m.lower() for m in item.get("mood_tags", [])}
        mood_overlap = len(item_moods & pref_moods) / max(1, len(pref_moods)) if pref_moods else 0.25
        cluster_bonus = 0.10 if (idx < len(index.cluster_labels) and index.cluster_labels[idx] in seed_clusters) else 0.0

        total = min(1.0, (0.48 * vibe_sim) + (0.32 * comb_sim) + (0.15 * mood_overlap) + cluster_bonus)
        candidates.append(
            (
                total,
                idx,
                {
                    "cross_domain_sim": vibe_sim,
                    "content_sim": comb_sim,
                    "mood_sim": mood_overlap,
                    "cluster_bonus": cluster_bonus,
                },
            )
        )

    candidates.sort(key=lambda x: x[0], reverse=True)
    diversified = diversify_ranked_candidates(index, candidates, pool_limit=max(limit * 3, 20))

    enriched: List[Dict[str, Any]] = []
    for score, idx, breakdown in diversified:
        item = dict(index.items[idx])
        item["match_score"] = round(min(99.5, max(20.0, score * 100.0)), 1)
        item["explanation"] = build_recommendation_explanation(
            item=item,
            preferences=preferences,
            score_breakdown=breakdown,
            seed_titles=seed_titles,
            pathway_label=pathway_label,
        )
        enriched.append(item)

    balanced, lang_notice = balance_language_results(enriched, language_mode, limit)
    return {
        "pathway": pathway,
        "seed_items": seed_titles,
        "recommendations": balanced,
        "language_notice": lang_notice,
    }


def build_discovery_chain(
    index: CatalogFeatureIndex,
    preferences: Dict[str, Any],
    seed_titles_override: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Generate an explainable Music -> Mood -> Movie -> Web Series -> Companion Soundtrack chain."""
    song_seeds, song_titles = _resolve_seed_indices(
        index, "song", preferences, seed_titles_override
    )
    seed_song = dict(index.items[song_seeds[0]]) if song_seeds else None

    # Step 2: Best matching movie from seed song(s)
    movie_res = run_cross_domain_pathway(index, "music_to_movies", preferences, song_titles[:2], limit=3)
    top_movie = movie_res["recommendations"][0] if movie_res["recommendations"] else None

    # Step 3: Best matching series bridged from both song & top movie
    bridge_indices = list(song_seeds)
    if top_movie and top_movie.get("external_id"):
        m_idx = index.ext_to_idx.get((top_movie["external_id"], "movie"))
        if m_idx is not None:
            bridge_indices.append(m_idx)

    vibe_sims = index.cross_domain_vibe_similarity(bridge_indices)
    language_mode = preferences.get("language_mode", "both")
    best_series = None
    best_series_score = -1.0
    for idx, item in enumerate(index.items):
        if item.get("content_type") != "series":
            continue
        if not is_language_eligible(item.get("language", "English"), language_mode):
            continue
        if vibe_sims[idx] > best_series_score:
            best_series_score = float(vibe_sims[idx])
            best_series = dict(item)
            best_series["match_score"] = round(min(99.5, best_series_score * 100.0), 1)
            best_series["explanation"] = build_recommendation_explanation(
                item=best_series,
                preferences=preferences,
                score_breakdown={"cross_domain_sim": best_series_score},
                seed_titles=[s for s in [seed_song["title"] if seed_song else None, top_movie["title"] if top_movie else None] if s],
                pathway_label="music & movie vibe",
            )

    # Step 4: Companion soundtrack song similar to the series/movie vibe (distinct from seed song)
    companion_song = None
    if best_series:
        s_idx = index.ext_to_idx.get((best_series["external_id"], "series"))
        if s_idx is not None:
            song_sims = index.cross_domain_vibe_similarity([s_idx])
            for idx in np.argsort(song_sims)[::-1]:
                cand = index.items[idx]
                if cand.get("content_type") != "song":
                    continue
                if seed_song and cand.get("external_id") == seed_song.get("external_id"):
                    continue
                if not is_language_eligible(cand.get("language", "English"), language_mode):
                    continue
                companion_song = dict(cand)
                companion_song["match_score"] = round(float(song_sims[idx]) * 100.0, 1)
                companion_song["explanation"] = build_recommendation_explanation(
                    item=companion_song,
                    preferences=preferences,
                    score_breakdown={"cross_domain_sim": float(song_sims[idx])},
                    seed_titles=[best_series["title"]],
                    pathway_label="series atmosphere",
                )
                break

    shared_moods = []
    if seed_song and top_movie:
        shared_moods = sorted(
            set(seed_song.get("mood_tags", [])) & set(top_movie.get("mood_tags", []))
        )
    if not shared_moods and seed_song:
        shared_moods = seed_song.get("mood_tags", [])[:3]

    return {
        "shared_mood_bridge": shared_moods,
        "steps": [
            {"stage": "1. Music Seed", "item": seed_song},
            {"stage": "2. Resonant Movie", "item": top_movie},
            {"stage": "3. Aligned Web Series", "item": best_series},
            {"stage": "4. Companion Soundtrack", "item": companion_song},
        ],
    }


def discover_unexpected_vibe(
    index: CatalogFeatureIndex,
    preferences: Dict[str, Any],
    limit: int = 6,
) -> List[Dict[str, Any]]:
    """'Your Unexpected Vibe': items in unexplored genres that maintain high latent vibe similarity."""
    explored_genres = {
        g.lower()
        for g in (
            list(preferences.get("music_genres", []))
            + list(preferences.get("movie_genres", []))
            + list(preferences.get("series_genres", []))
        )
    }
    language_mode = preferences.get("language_mode", "both")
    suppressed = {
        int(x) for x in (preferences.get("preference_weights") or {}).get("suppressed_ids", [])
    }

    # Build combined seed profile across all domains
    seed_indices: List[int] = []
    for ctype in ("song", "movie", "series"):
        s_idx, _ = _resolve_seed_indices(index, ctype, preferences)
        seed_indices.extend(s_idx[:2])

    vibe_sims = index.cross_domain_vibe_similarity(seed_indices)
    candidates: List[tuple[float, int, Dict[str, float]]] = []

    for idx, item in enumerate(index.items):
        if item.get("id") is not None and int(item["id"]) in suppressed:
            continue
        if not is_language_eligible(item.get("language", "English"), language_mode):
            continue

        item_genres = {g.lower() for g in item.get("genres", [])}
        # Must introduce at least one genre outside user's already-selected genres
        if explored_genres and item_genres.issubset(explored_genres):
            continue

        v_sim = float(vibe_sims[idx])
        if v_sim < 0.20:
            continue

        unexplored_ratio = (
            len(item_genres - explored_genres) / max(1, len(item_genres)) if explored_genres else 0.5
        )
        score = (0.72 * v_sim) + (0.28 * unexplored_ratio)
        candidates.append(
            (
                score,
                idx,
                {"cross_domain_sim": v_sim, "novelty": unexplored_ratio},
            )
        )

    candidates.sort(key=lambda x: x[0], reverse=True)
    # Mix across domains (song, movie, series)
    picked: List[Dict[str, Any]] = []
    domain_counts = {"song": 0, "movie": 0, "series": 0}
    max_per_domain = max(2, limit // 3 + 1)

    for score, idx, breakdown in candidates:
        item = dict(index.items[idx])
        ctype = item.get("content_type", "song")
        if domain_counts.get(ctype, 0) >= max_per_domain:
            continue
        item["match_score"] = round(min(97.0, score * 100.0), 1)
        item["explanation"] = build_recommendation_explanation(
            item=item,
            preferences=preferences,
            score_breakdown=breakdown,
            is_unexpected_discovery=True,
        )
        picked.append(item)
        domain_counts[ctype] = domain_counts.get(ctype, 0) + 1
        if len(picked) >= limit:
            break

    return picked
