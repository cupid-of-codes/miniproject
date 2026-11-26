"""External API integrations (TMDB & MusicBrainz) with disk caching and offline fallback."""

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

from backend.core.config import get_settings
from recommendation_engine.preprocessing.text_cleaner import (
    canonicalize_moods,
    normalize_language,
    normalize_list_field,
)

logger = logging.getLogger("vibeverse.external_sources")

TMDB_GENRE_MOOD_MAP = {
    "Drama": ["Emotional", "Melancholic"],
    "Mystery": ["Mysterious", "Focused"],
    "Thriller": ["Anxious", "Dark", "Mysterious"],
    "Crime": ["Dark", "Focused"],
    "Science Fiction": ["Dreamy", "Adventurous", "Mysterious"],
    "Sci-Fi & Fantasy": ["Dreamy", "Adventurous"],
    "Romance": ["Romantic", "Emotional"],
    "Comedy": ["Happy", "Comfort"],
    "Adventure": ["Adventurous", "Hopeful"],
    "Animation": ["Dreamy", "Happy"],
    "Horror": ["Dark", "Anxious"],
}


class ExternalSourceClient:
    """Fetches real metadata from TMDB / MusicBrainz and caches responses to disk."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.cache_dir: Path = self.settings.resolve_path(self.settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() or c in {"_", "-"} else "_" for c in key)
        return self.cache_dir / f"{safe_key}.json"

    def read_cache(self, key: str, ignore_ttl: bool = False) -> Optional[List[Dict[str, Any]]]:
        """Read cached records if present (and within TTL unless offline fallback is requested)."""
        path = self._cache_path(key)
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            cached_at_str = payload.get("retrieved_at")
            if cached_at_str and not ignore_ttl:
                cached_at = datetime.fromisoformat(cached_at_str)
                if datetime.now(timezone.utc) - cached_at > timedelta(
                    hours=self.settings.cache_ttl_hours
                ):
                    return None
            return payload.get("items", [])
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Failed to read cache %s: %s", path.name, exc)
            return None

    def write_cache(self, key: str, source: str, items: List[Dict[str, Any]]) -> None:
        """Persist retrieved API items with explicit source and retrieval timestamp."""
        path = self._cache_path(key)
        payload = {
            "source": source,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "items": items,
        }
        try:
            path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        except OSError as exc:
            logger.warning("Failed to write cache %s: %s", path.name, exc)

    def fetch_tmdb_discover(
        self, media_type: str = "movie", language_code: str = "hi", pages: int = 1
    ) -> List[Dict[str, Any]]:
        """Fetch real movies or TV series from TMDB API when TMDB_API_KEY is available."""
        cache_key = f"tmdb_{media_type}_{language_code}"
        if not self.settings.tmdb_api_key or self.settings.data_mode == "local":
            return self.read_cache(cache_key, ignore_ttl=True) or []

        if self.settings.data_mode == "cache":
            return self.read_cache(cache_key, ignore_ttl=True) or []

        cached = self.read_cache(cache_key, ignore_ttl=False)
        if cached is not None:
            return cached

        endpoint = "discover/movie" if media_type == "movie" else "discover/tv"
        content_type = "movie" if media_type == "movie" else "series"
        genre_url = f"{self.settings.tmdb_base_url}/genre/{'movie' if media_type == 'movie' else 'tv'}/list"
        items: List[Dict[str, Any]] = []
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with httpx.Client(timeout=8.0) as client:
                genre_resp = client.get(
                    genre_url, params={"api_key": self.settings.tmdb_api_key, "language": "en-US"}
                )
                genre_map: Dict[int, str] = {}
                if genre_resp.status_code == 200:
                    for g in genre_resp.json().get("genres", []):
                        genre_map[g["id"]] = g["name"]

                for page in range(1, pages + 1):
                    resp = client.get(
                        f"{self.settings.tmdb_base_url}/{endpoint}",
                        params={
                            "api_key": self.settings.tmdb_api_key,
                            "with_original_language": language_code,
                            "sort_by": "popularity.desc",
                            "page": page,
                        },
                    )
                    if resp.status_code != 200:
                        logger.warning("TMDB returned status %s for %s", resp.status_code, endpoint)
                        break

                    for row in resp.json().get("results", []):
                        title = row.get("title") or row.get("name")
                        if not title:
                            continue
                        date_str = row.get("release_date") or row.get("first_air_date") or ""
                        year = int(date_str[:4]) if len(date_str) >= 4 and date_str[:4].isdigit() else None
                        genres = [genre_map[gid] for gid in row.get("genre_ids", []) if gid in genre_map]
                        inferred_moods: List[str] = []
                        for g in genres:
                            inferred_moods.extend(TMDB_GENRE_MOOD_MAP.get(g, []))
                        poster_path = row.get("poster_path")
                        items.append(
                            {
                                "external_id": f"tmdb_{content_type}_{row['id']}",
                                "title": title,
                                "content_type": content_type,
                                "language": normalize_language(language_code),
                                "release_year": year,
                                "description": row.get("overview") or "",
                                "genres": normalize_list_field(genres),
                                "mood_tags": canonicalize_moods(inferred_moods, row.get("overview", "")),
                                "themes": normalize_list_field(genres),
                                "popularity": row.get("popularity"),
                                "rating": row.get("vote_average") if row.get("vote_count", 0) > 0 else None,
                                "artwork_url": (
                                    f"{self.settings.tmdb_image_base_url}{poster_path}"
                                    if poster_path
                                    else None
                                ),
                                "source": "tmdb_api",
                                "retrieved_at": now_iso,
                                "extra_metadata": {
                                    "vote_count": row.get("vote_count"),
                                    "mood_inferred_from_genres": True,
                                },
                            }
                        )
            if items:
                self.write_cache(cache_key, "tmdb_api", items)
            return items
        except httpx.RequestError as exc:
            logger.warning("TMDB request failed (%s); falling back to cache.", exc.__class__.__name__)
            return self.read_cache(cache_key, ignore_ttl=True) or []

    def fetch_musicbrainz_recordings(self, query: str = "tag:indie", limit: int = 20) -> List[Dict[str, Any]]:
        """Fetch real music metadata from MusicBrainz WS2 (no paid key required)."""
        cache_key = f"musicbrainz_{query}_{limit}"
        if self.settings.data_mode in {"local", "cache"}:
            return self.read_cache(cache_key, ignore_ttl=True) or []

        cached = self.read_cache(cache_key, ignore_ttl=False)
        if cached is not None:
            return cached

        now_iso = datetime.now(timezone.utc).isoformat()
        items: List[Dict[str, Any]] = []
        try:
            with httpx.Client(
                timeout=8.0,
                headers={"User-Agent": self.settings.musicbrainz_user_agent},
            ) as client:
                resp = client.get(
                    f"{self.settings.musicbrainz_base_url}/recording",
                    params={"query": query, "fmt": "json", "limit": limit},
                )
                if resp.status_code != 200:
                    return self.read_cache(cache_key, ignore_ttl=True) or []
                for rec in resp.json().get("recordings", []):
                    title = rec.get("title")
                    if not title:
                        continue
                    artists = [
                        ac.get("name", "")
                        for ac in rec.get("artist-credit", [])
                        if isinstance(ac, dict) and ac.get("name")
                    ]
                    tags = [t.get("name", "") for t in rec.get("tags", []) if t.get("name")]
                    releases = rec.get("releases") or []
                    album = releases[0].get("title") if releases else None
                    date_str = releases[0].get("date", "") if releases else ""
                    year = int(date_str[:4]) if len(date_str) >= 4 and date_str[:4].isdigit() else None
                    items.append(
                        {
                            "external_id": f"mb_{rec['id']}",
                            "title": title,
                            "content_type": "song",
                            "language": "English",
                            "release_year": year,
                            "description": f"Recording by {', '.join(artists) or 'Unknown Artist'}.",
                            "genres": normalize_list_field(tags[:4] or ["Indie"]),
                            "mood_tags": canonicalize_moods(tags),
                            "themes": normalize_list_field(tags[:3]),
                            "popularity": None,
                            "rating": None,
                            "artwork_url": None,
                            "source": "musicbrainz_api",
                            "retrieved_at": now_iso,
                            "extra_metadata": {
                                "artist": ", ".join(artists),
                                "album": album,
                            },
                        }
                    )
            if items:
                self.write_cache(cache_key, "musicbrainz_api", items)
            return items
        except httpx.RequestError as exc:
            logger.warning(
                "MusicBrainz request failed (%s); falling back to cache.", exc.__class__.__name__
            )
            return self.read_cache(cache_key, ignore_ttl=True) or []
