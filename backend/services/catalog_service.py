"""Backend service layer coordinating database catalog, ML feature index, search, and analytics."""

from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from backend.repositories.vibeverse_repo import VibeVerseRepository
from recommendation_engine.feature_engineering.vectorizer import CatalogFeatureIndex
from recommendation_engine.preprocessing.text_cleaner import CANONICAL_MOODS

_INDEX_CACHE: Dict[int, CatalogFeatureIndex] = {}


def get_catalog_index(db: Session) -> CatalogFeatureIndex:
    """Build or reuse an in-memory CatalogFeatureIndex synced with DB content count."""
    repo = VibeVerseRepository(db)
    items = repo.list_all_content()
    cache_key = len(items)
    cached = _INDEX_CACHE.get(cache_key)
    if cached is not None and len(cached.items) == len(items):
        return cached
    index = CatalogFeatureIndex(items)
    _INDEX_CACHE.clear()
    _INDEX_CACHE[cache_key] = index
    return index


def invalidate_catalog_cache() -> None:
    """Clear cached feature index when catalog contents change."""
    _INDEX_CACHE.clear()


def search_catalog(
    items: List[Dict[str, Any]],
    content_type: Optional[str] = None,
    query: Optional[str] = None,
    language: Optional[str] = None,
    genre: Optional[str] = None,
    mood: Optional[str] = None,
    theme: Optional[str] = None,
    category: Optional[str] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    min_rating: Optional[float] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    """Filter and search catalog items across all supported fields."""
    q_lower = (query or "").strip().lower()
    lang_lower = (language or "").strip().lower()
    genre_lower = (genre or "").strip().lower()
    mood_lower = (mood or "").strip().lower()
    theme_lower = (theme or "").strip().lower()
    cat_lower = (category or "").strip().lower()

    results: List[Tuple[int, Dict[str, Any]]] = []
    for item in items:
        if content_type and content_type != "all" and item.get("content_type") != content_type:
            continue
        if lang_lower and lang_lower not in {"all", "both"}:
            if item.get("language", "").lower() != lang_lower and item.get("language", "").lower() != "bilingual":
                continue

        item_genres = [g.lower() for g in item.get("genres", [])]
        item_moods = [m.lower() for m in item.get("mood_tags", [])]
        item_themes = [t.lower() for t in item.get("themes", [])]
        extra = item.get("extra_metadata") or {}
        disc_tag = str(extra.get("discovery_tag", "")).lower()

        if genre_lower and genre_lower != "all" and not any(genre_lower in g for g in item_genres):
            continue
        if mood_lower and mood_lower != "all" and not any(mood_lower in m for m in item_moods):
            continue
        if theme_lower and theme_lower != "all" and not any(theme_lower in t for t in item_themes):
            continue
        if cat_lower and cat_lower != "all":
            if not (
                cat_lower in disc_tag
                or any(cat_lower in g for g in item_genres)
                or any(cat_lower in m for m in item_moods)
                or cat_lower == item.get("language", "").lower()
            ):
                continue

        year = item.get("release_year")
        if year_min is not None and (year is None or year < year_min):
            continue
        if year_max is not None and (year is None or year > year_max):
            continue

        rating = item.get("rating")
        if min_rating is not None and (rating is None or rating < min_rating):
            continue

        relevance = 1
        if q_lower:
            talent_blob = " ".join(
                str(extra.get(k, "")) for k in ("artist", "album", "director", "creator", "cast")
            ).lower()
            searchable = " ".join(
                [
                    item.get("title", "").lower(),
                    " ".join(item_genres),
                    " ".join(item_moods),
                    " ".join(item_themes),
                    item.get("description", "").lower(),
                    talent_blob,
                ]
            )
            if q_lower not in searchable:
                continue
            relevance = 3 if q_lower in item.get("title", "").lower() else (
                2 if q_lower in talent_blob else 1
            )

        results.append((relevance, item))

    results.sort(key=lambda pair: (pair[0], pair[1].get("release_year") or 0), reverse=True)
    return [item for _, item in results[:limit]]


def get_catalog_metadata(items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Return distinct genres, moods, artists, themes, and titles for dynamic UI controls."""
    music_genres, movie_genres, series_genres = set(), set(), set()
    artists, themes = set(), set()
    titles_by_type: Dict[str, List[str]] = {"song": [], "movie": [], "series": []}

    for item in items:
        ctype = item.get("content_type", "song")
        if ctype in titles_by_type:
            titles_by_type[ctype].append(item["title"])
        for g in item.get("genres", []):
            if ctype == "song":
                music_genres.add(g)
            elif ctype == "movie":
                movie_genres.add(g)
            elif ctype == "series":
                series_genres.add(g)
        for t in item.get("themes", []):
            themes.add(t)
        extra = item.get("extra_metadata") or {}
        for k in ("artist", "director", "creator"):
            val = extra.get(k)
            if isinstance(val, str):
                for name in val.split(","):
                    if name.strip():
                        artists.add(name.strip())

    return {
        "music_genres": sorted(music_genres),
        "movie_genres": sorted(movie_genres),
        "series_genres": sorted(series_genres),
        "moods": CANONICAL_MOODS,
        "artists": sorted(artists),
        "themes": sorted(themes),
        "titles_by_type": {k: sorted(v) for k, v in titles_by_type.items()},
    }


def build_trending_overview(repo: VibeVerseRepository, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build factual trending & spotlight overview strictly from loaded/API-sourced data."""
    datasets = repo.list_datasets()
    songs = [i for i in items if i["content_type"] == "song"]
    movies = [i for i in items if i["content_type"] == "movie"]
    series = [i for i in items if i["content_type"] == "series"]

    def _pick_spotlight(pool: List[Dict[str, Any]], count: int = 4) -> List[Dict[str, Any]]:
        with_pop = [x for x in pool if x.get("popularity") is not None]
        if with_pop:
            with_pop.sort(key=lambda x: x["popularity"], reverse=True)
            return with_pop[:count]
        # Otherwise sort deterministically by most recent release_year (interleaving Hindi & English)
        hindi = sorted([x for x in pool if x["language"] == "Hindi"], key=lambda x: x.get("release_year") or 0, reverse=True)
        english = sorted([x for x in pool if x["language"] == "English"], key=lambda x: x.get("release_year") or 0, reverse=True)
        out: List[Dict[str, Any]] = []
        hi_i, en_i = 0, 0
        while len(out) < count and (hi_i < len(hindi) or en_i < len(english)):
            if hi_i < len(hindi):
                out.append(hindi[hi_i]); hi_i += 1
            if len(out) < count and en_i < len(english):
                out.append(english[en_i]); en_i += 1
        return out

    has_live_popularity = any(i.get("popularity") is not None for i in items)
    return {
        "has_live_popularity": has_live_popularity,
        "data_source_note": (
            "Sorted by live API popularity metrics."
            if has_live_popularity
            else "Sorted by recent catalog releases from the curated local dataset (live external popularity metrics not configured; zero fake metrics generated)."
        ),
        "datasets": datasets,
        "trending_songs": _pick_spotlight(songs, 4),
        "trending_movies": _pick_spotlight(movies, 4),
        "trending_series": _pick_spotlight(series, 4),
        "popular_hindi": _pick_spotlight([i for i in items if i["language"] == "Hindi"], 6),
        "popular_english": _pick_spotlight([i for i in items if i["language"] == "English"], 6),
    }


def compute_catalog_analytics(repo: VibeVerseRepository, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compute real analytics across genres, languages, moods, domains, and cross-domain links."""
    genre_by_lang: Dict[str, Counter] = {"Hindi": Counter(), "English": Counter()}
    genre_by_domain: Dict[str, Counter] = {"song": Counter(), "movie": Counter(), "series": Counter()}
    mood_counts = Counter()
    domain_counts = Counter()
    language_counts = Counter()
    year_counts = Counter()
    cross_domain_mood_matrix: Dict[str, Dict[str, int]] = {}

    for item in items:
        ctype = item.get("content_type", "song")
        lang = item.get("language", "English")
        domain_counts[ctype] += 1
        language_counts[lang] += 1
        if item.get("release_year"):
            year_counts[int(item["release_year"])] += 1

        for g in item.get("genres", []):
            if lang in genre_by_lang:
                genre_by_lang[lang][g] += 1
            if ctype in genre_by_domain:
                genre_by_domain[ctype][g] += 1

        for m in item.get("mood_tags", []):
            mood_counts[m] += 1
            if m not in cross_domain_mood_matrix:
                cross_domain_mood_matrix[m] = {"song": 0, "movie": 0, "series": 0}
            if ctype in cross_domain_mood_matrix[m]:
                cross_domain_mood_matrix[m][ctype] += 1

    all_genres = genre_by_lang["Hindi"] + genre_by_lang["English"]
    top_genres = [g for g, _ in all_genres.most_common(12)]

    return {
        "total_items": len(items),
        "domain_distribution": dict(domain_counts),
        "language_distribution": dict(language_counts),
        "top_genres": dict(all_genres.most_common(15)),
        "genre_by_language": {
            "genres": top_genres,
            "Hindi": [genre_by_lang["Hindi"].get(g, 0) for g in top_genres],
            "English": [genre_by_lang["English"].get(g, 0) for g in top_genres],
        },
        "genre_by_domain": {
            "song": dict(genre_by_domain["song"].most_common(8)),
            "movie": dict(genre_by_domain["movie"].most_common(8)),
            "series": dict(genre_by_domain["series"].most_common(8)),
        },
        "mood_distribution": dict(mood_counts.most_common(18)),
        "cross_domain_mood_bridge": cross_domain_mood_matrix,
        "release_year_distribution": dict(sorted(year_counts.items())),
        "datasets": repo.list_datasets(),
        "temporal_notice": (
            "Release-year distribution reflects catalog metadata only. True temporal user-engagement trend curves require historical time-series interaction logs."
        ),
    }
