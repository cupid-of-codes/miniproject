"""CLI script to load normalized datasets and real dataset trends into MySQL."""

import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import get_settings
from backend.core.logging_config import setup_logging
from backend.database.session import SessionLocal
from backend.models.db_models import (
    Artist,
    ContentArtist,
    ContentItem,
    DatasetRecord,
    TrendRecord,
)
from recommendation_engine.preprocessing.dataset_loader import load_all_datasets


def _parse_dt(val) -> datetime | None:
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val:
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            return None
    return None


def load_into_mysql(include_external: bool = False) -> bool:
    """Upsert content items, artists, dataset metadata, and real catalog trends into MySQL."""
    settings = get_settings()
    logger = setup_logging(settings.log_level)

    items, summaries = load_all_datasets(include_external=include_external)
    if not items:
        logger.error("No dataset records found to load.")
        return False

    try:
        with SessionLocal() as db:
            artist_cache: Dict[str, Artist] = {
                a.name: a for a in db.scalars(select(Artist)).all()
            }

            upserted = 0
            for item in items:
                existing = db.scalar(
                    select(ContentItem).where(
                        ContentItem.external_id == item["external_id"],
                        ContentItem.content_type == item["content_type"],
                    )
                )
                if existing is None:
                    existing = ContentItem(
                        external_id=item["external_id"],
                        content_type=item["content_type"],
                    )
                    db.add(existing)

                existing.title = item["title"]
                existing.language = item["language"]
                existing.release_year = item["release_year"]
                existing.description = item["description"]
                existing.genres = item["genres"]
                existing.mood_tags = item["mood_tags"]
                existing.themes = item["themes"]
                existing.extra_metadata = item["extra_metadata"]
                existing.popularity = item["popularity"]
                existing.rating = item["rating"]
                existing.artwork_url = item["artwork_url"]
                existing.source = item["source"]
                existing.retrieved_at = _parse_dt(item.get("retrieved_at"))
                db.flush()

                # Link artists/directors/creators
                extra = item.get("extra_metadata") or {}
                talent_entries: List[tuple[str, str]] = []
                for field, role in [("artist", "artist"), ("director", "director"), ("creator", "creator")]:
                    raw_val = extra.get(field)
                    if isinstance(raw_val, str):
                        for name in [n.strip() for n in raw_val.split(",") if n.strip()]:
                            talent_entries.append((name, role))

                for name, role in talent_entries:
                    artist_obj = artist_cache.get(name)
                    if artist_obj is None:
                        artist_obj = Artist(
                            name=name[:255],
                            genres=item["genres"],
                            metadata_json={},
                            source=item["source"],
                        )
                        db.add(artist_obj)
                        db.flush()
                        artist_cache[name] = artist_obj

                    link_exists = db.scalar(
                        select(ContentArtist).where(
                            ContentArtist.content_id == existing.id,
                            ContentArtist.artist_id == artist_obj.id,
                            ContentArtist.role == role,
                        )
                    )
                    if link_exists is None:
                        db.add(
                            ContentArtist(
                                content_id=existing.id,
                                artist_id=artist_obj.id,
                                role=role,
                            )
                        )
                upserted += 1

            # Record dataset registry entries
            for summary in summaries:
                db.add(
                    DatasetRecord(
                        name=summary["name"][:128],
                        content_type=summary["content_type"],
                        source=summary["source"][:128],
                        license_info=summary["license_info"][:255],
                        record_count=summary["record_count"],
                        retrieved_at=_parse_dt(summary.get("retrieved_at")),
                    )
                )

            # Populate verifiable catalog-derived genre trends (zero fabricated stats)
            genre_lang_counts = Counter()
            for item in items:
                for g in item.get("genres", []):
                    genre_lang_counts[(g, item["language"])] += 1

            now_naive = datetime.now(timezone.utc).replace(tzinfo=None)
            for (genre, lang), count in genre_lang_counts.items():
                db.add(
                    TrendRecord(
                        metric_name="catalog_genre_count",
                        category=genre[:128],
                        language=lang[:64],
                        value=float(count),
                        source="loaded_catalog_aggregation",
                        period_label="current_snapshot",
                        retrieved_at=now_naive,
                    )
                )

            db.commit()
            dialect = db.bind.dialect.name if db.bind is not None else "database"
            logger.info("Loaded %d content items into %s.", upserted, dialect)
            print(f"SUCCESS: Upserted {upserted} content items into {dialect}.")
            return True
    except SQLAlchemyError as exc:
        logger.error("Failed loading datasets into database: %s", exc.__class__.__name__)
        print(f"ERROR: Could not load datasets into database ({exc.__class__.__name__}).")
        return False


if __name__ == "__main__":
    use_external = "--external" in sys.argv
    ok = load_into_mysql(include_external=use_external)
    sys.exit(0 if ok else 1)
