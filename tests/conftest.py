"""Shared pytest fixtures for VibeVerse AI test suite."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database.session import Base
from backend.models.db_models import ContentItem, DatasetRecord
from backend.services.catalog_service import invalidate_catalog_cache
from recommendation_engine.preprocessing.dataset_loader import load_all_datasets


@pytest.fixture(scope="module")
def seeded_db_session_factory():
    """Create an isolated SQLAlchemy test DB seeded with the full curated Hindi/English catalog."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

    items, summaries = load_all_datasets(include_external=False)
    with TestingSession() as db:
        for item in items:
            db.add(
                ContentItem(
                    external_id=item["external_id"],
                    title=item["title"],
                    content_type=item["content_type"],
                    language=item["language"],
                    release_year=item["release_year"],
                    description=item["description"],
                    genres=item["genres"],
                    mood_tags=item["mood_tags"],
                    themes=item["themes"],
                    extra_metadata=item["extra_metadata"],
                    popularity=item["popularity"],
                    rating=item["rating"],
                    artwork_url=item["artwork_url"],
                    source=item["source"],
                )
            )
        for s in summaries:
            db.add(
                DatasetRecord(
                    name=s["name"],
                    content_type=s["content_type"],
                    source=s["source"],
                    license_info=s["license_info"],
                    record_count=s["record_count"],
                )
            )
        db.commit()

    invalidate_catalog_cache()
    yield TestingSession
    invalidate_catalog_cache()
    engine.dispose()
