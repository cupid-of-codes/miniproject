"""Initialize the MySQL database and create/migrate all VibeVerse AI tables."""

import logging
import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.core.config import get_settings
from backend.core.logging_config import setup_logging
from backend.database.session import Base, engine
from backend.models import db_models  # noqa: F401


def initialize_database() -> bool:
    """Create the MySQL schema if absent, then create/verify all tables."""
    settings = get_settings()
    logger = setup_logging(settings.log_level)

    if not settings.database_url_override:
        try:
            server_engine = create_engine(
                settings.mysql_server_url,
                connect_args={"connect_timeout": 5},
                pool_pre_ping=True,
            )
            with server_engine.connect() as conn:
                db_name = settings.mysql_database.replace("`", "")
                conn.execute(
                    text(
                        f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                        "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                    )
                )
                conn.commit()
            server_engine.dispose()
            logger.info("Verified MySQL database '%s'", settings.mysql_database)
        except SQLAlchemyError as exc:
            logger.error("Could not connect to MySQL server: %s", exc.__class__.__name__)
            print(
                f"ERROR: Could not connect to MySQL server at {settings.mysql_host}:{settings.mysql_port}. "
                "Verify MySQL is running and credentials in .env are valid."
            )
            return False

    try:
        Base.metadata.create_all(bind=engine)
        logger.info("All VibeVerse AI database tables are initialized.")
        print("SUCCESS: VibeVerse AI database tables initialized.")
        return True
    except SQLAlchemyError as exc:
        logger.error("Schema initialization failed: %s", exc.__class__.__name__)
        print(f"ERROR: Table creation failed ({exc.__class__.__name__}).")
        return False


if __name__ == "__main__":
    success = initialize_database()
    sys.exit(0 if success else 1)
