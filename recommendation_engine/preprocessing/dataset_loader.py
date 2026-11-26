"""Dataset loading, validation, normalization, and multi-mode merging."""

import csv
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.core.config import get_settings
from recommendation_engine.preprocessing.external_sources import ExternalSourceClient
from recommendation_engine.preprocessing.text_cleaner import (
    canonicalize_moods,
    infer_music_characteristics,
    normalize_language,
    normalize_list_field,
)

logger = logging.getLogger("vibeverse.dataset_loader")

REQUIRED_ITEM_FIELDS = ("external_id", "title", "content_type", "language")


def validate_and_normalize_record(
    raw: Dict[str, Any],
    default_content_type: str,
    default_source: str,
    retrieved_at: Optional[datetime] = None,
) -> Optional[Dict[str, Any]]:
    """Validate and normalize a single entertainment item without inventing ratings/popularity."""
    title = str(raw.get("title") or "").strip()
    if not title:
        return None

    content_type = str(raw.get("content_type") or default_content_type).strip().lower()
    if content_type not in {"song", "movie", "series"}:
        return None

    ext_id = str(raw.get("external_id") or f"{content_type}_{title.lower().replace(' ', '_')}").strip()
    language = normalize_language(str(raw.get("language") or "English"))

    release_year = raw.get("release_year")
    try:
        release_year = int(release_year) if release_year not in (None, "", "null") else None
    except (ValueError, TypeError):
        release_year = None

    genres = normalize_list_field(raw.get("genres"))
    description = str(raw.get("description") or "").strip()
    mood_tags = canonicalize_moods(raw.get("mood_tags"), fallback_text=description)
    themes = normalize_list_field(raw.get("themes"))

    extra_metadata = dict(raw.get("extra_metadata") or {})
    for talent_key in ("artist", "album", "director", "creator", "cast"):
        if raw.get(talent_key) and talent_key not in extra_metadata:
            extra_metadata[talent_key] = raw[talent_key]

    if content_type == "song":
        extra_metadata["music_analysis"] = infer_music_characteristics(
            {
                "genres": genres,
                "mood_tags": mood_tags,
                "description": description,
                "extra_metadata": extra_metadata,
            }
        )

    # Preserve real popularity/rating ONLY when actually supplied by a real source
    popularity = None
    if raw.get("popularity") not in (None, "", "null"):
        try:
            popularity = float(raw["popularity"])
        except (ValueError, TypeError):
            popularity = None

    rating = None
    if raw.get("rating") not in (None, "", "null"):
        try:
            rating = float(raw["rating"])
        except (ValueError, TypeError):
            rating = None

    rec_retrieved_at = raw.get("retrieved_at") or (
        retrieved_at.isoformat() if retrieved_at else datetime.now(timezone.utc).isoformat()
    )

    return {
        "external_id": ext_id[:128],
        "title": title[:255],
        "content_type": content_type,
        "language": language,
        "release_year": release_year,
        "description": description,
        "genres": genres,
        "mood_tags": mood_tags,
        "themes": themes,
        "extra_metadata": extra_metadata,
        "popularity": popularity,
        "rating": rating,
        "artwork_url": raw.get("artwork_url") or None,
        "source": str(raw.get("source") or default_source),
        "retrieved_at": rec_retrieved_at,
    }


def load_file_records(file_path: Path, default_content_type: str) -> List[Dict[str, Any]]:
    """Load records from a local JSON or CSV dataset file."""
    if not file_path.exists():
        logger.warning("Dataset file not found: %s", file_path)
        return []

    records: List[Dict[str, Any]] = []
    suffix = file_path.suffix.lower()
    if suffix == ".json":
        data = json.loads(file_path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("items", [])
        if isinstance(data, list):
            records = data
    elif suffix == ".csv":
        with file_path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                records.append(dict(row))
    else:
        logger.warning("Unsupported dataset format %s for %s", suffix, file_path)
        return []

    file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime, tz=timezone.utc)
    normalized: List[Dict[str, Any]] = []
    for raw in records:
        item = validate_and_normalize_record(
            raw=raw,
            default_content_type=default_content_type,
            default_source="vibeverse_curated_local_dataset",
            retrieved_at=file_mtime,
        )
        if item is not None:
            normalized.append(item)
    return normalized


def load_all_datasets(include_external: bool = False) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Load local datasets plus optional API/cached sources, deduplicated by (external_id, content_type).

    Returns `(items, dataset_summaries)`.
    """
    settings = get_settings()
    raw_dir = settings.resolve_path(settings.raw_data_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    file_specs = [
        ("songs_curated.json", "song", "Curated Hindi & English Songs Metadata"),
        ("movies_curated.json", "movie", "Curated Hindi & English Movies Metadata"),
        ("series_curated.json", "series", "Curated Hindi & English Web Series Metadata"),
    ]

    merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
    dataset_summaries: List[Dict[str, Any]] = []

    for filename, ctype, desc in file_specs:
        path = raw_dir / filename
        loaded = load_file_records(path, ctype)
        for item in loaded:
            merged[(item["external_id"], item["content_type"])] = item
        dataset_summaries.append(
            {
                "name": desc,
                "content_type": ctype,
                "source": "vibeverse_curated_local_dataset",
                "license_info": "Curated factual metadata (no fabricated ratings/trends)",
                "record_count": len(loaded),
                "retrieved_at": datetime.now(timezone.utc),
            }
        )

    # Also ingest any additional user-dropped custom CSV/JSON files in data/raw/
    known_names = {f for f, _, _ in file_specs}
    for custom_path in sorted(raw_dir.iterdir()):
        if custom_path.name in known_names or custom_path.suffix.lower() not in {".csv", ".json"}:
            continue
        inferred_type = "song" if "song" in custom_path.stem.lower() else (
            "series" if "series" in custom_path.stem.lower() else "movie"
        )
        loaded = load_file_records(custom_path, inferred_type)
        for item in loaded:
            merged[(item["external_id"], item["content_type"])] = item
        dataset_summaries.append(
            {
                "name": custom_path.stem,
                "content_type": inferred_type,
                "source": f"custom_local_file:{custom_path.name}",
                "license_info": "User-supplied local dataset",
                "record_count": len(loaded),
                "retrieved_at": datetime.now(timezone.utc),
            }
        )

    if include_external and settings.data_mode != "local":
        ext_client = ExternalSourceClient()
        external_batches = [
            ("TMDB Hindi Movies", "movie", "tmdb_api", ext_client.fetch_tmdb_discover("movie", "hi", 1)),
            ("TMDB English Movies", "movie", "tmdb_api", ext_client.fetch_tmdb_discover("movie", "en", 1)),
            ("TMDB Hindi Series", "series", "tmdb_api", ext_client.fetch_tmdb_discover("tv", "hi", 1)),
            ("TMDB English Series", "series", "tmdb_api", ext_client.fetch_tmdb_discover("tv", "en", 1)),
            ("MusicBrainz Indie", "song", "musicbrainz_api", ext_client.fetch_musicbrainz_recordings("tag:indie", 15)),
        ]
        for label, ctype, src, batch in external_batches:
            valid_count = 0
            for raw in batch:
                norm = validate_and_normalize_record(raw, ctype, src)
                if norm:
                    merged[(norm["external_id"], norm["content_type"])] = norm
                    valid_count += 1
            if valid_count:
                dataset_summaries.append(
                    {
                        "name": label,
                        "content_type": ctype,
                        "source": src,
                        "license_info": "External API / Cached Snapshot",
                        "record_count": valid_count,
                        "retrieved_at": datetime.now(timezone.utc),
                    }
                )

    return list(merged.values()), dataset_summaries
