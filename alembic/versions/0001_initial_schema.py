"""Initial VibeVerse AI MySQL schema.

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-11-26 22:14:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "content_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("external_id", sa.String(length=128), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("release_year", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("mood_tags", sa.JSON(), nullable=False),
        sa.Column("themes", sa.JSON(), nullable=False),
        sa.Column("extra_metadata", sa.JSON(), nullable=False),
        sa.Column("popularity", sa.Float(), nullable=True),
        sa.Column("rating", sa.Float(), nullable=True),
        sa.Column("artwork_url", sa.String(length=512), nullable=True),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", "content_type", name="uq_external_id_type"),
    )
    op.create_index("ix_content_type_lang", "content_items", ["content_type", "language"])
    op.create_index("ix_content_title", "content_items", ["title"])

    op.create_table(
        "artists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("genres", sa.JSON(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_artist_name"),
    )

    op.create_table(
        "content_artists",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("artist_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.ForeignKeyConstraint(["artist_id"], ["artists.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("content_id", "artist_id", "role", name="uq_content_artist_role"),
    )

    op.create_table(
        "user_preferences",
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("language_mode", sa.String(length=64), nullable=False),
        sa.Column("music_genres", sa.JSON(), nullable=False),
        sa.Column("movie_genres", sa.JSON(), nullable=False),
        sa.Column("series_genres", sa.JSON(), nullable=False),
        sa.Column("favourite_artists", sa.JSON(), nullable=False),
        sa.Column("favourite_content", sa.JSON(), nullable=False),
        sa.Column("moods", sa.JSON(), nullable=False),
        sa.Column("music_energy_pref", sa.String(length=32), nullable=False),
        sa.Column("music_style_pref", sa.String(length=32), nullable=False),
        sa.Column("popularity_pref", sa.String(length=32), nullable=False),
        sa.Column("movie_themes", sa.JSON(), nullable=False),
        sa.Column("series_pacing", sa.String(length=32), nullable=False),
        sa.Column("storytelling_style", sa.JSON(), nullable=False),
        sa.Column("preference_weights", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("session_id"),
    )

    op.create_table(
        "recommendation_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("recommended_content_id", sa.Integer(), nullable=False),
        sa.Column("recommendation_type", sa.String(length=64), nullable=False),
        sa.Column("recommendation_score", sa.Float(), nullable=False),
        sa.Column("recommendation_explanation", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(
            ["recommended_content_id"], ["content_items.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rec_hist_session", "recommendation_history", ["session_id", "created_at"])

    op.create_table(
        "feedback",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("feedback_type", sa.String(length=32), nullable=False),
        sa.Column("feedback_value", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_feedback_session_content", "feedback", ["session_id", "content_id"])

    op.create_table(
        "saved_content",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("session_id", sa.String(length=64), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("saved_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["content_id"], ["content_items.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "content_id", name="uq_saved_session_content"),
    )

    op.create_table(
        "datasets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("license_info", sa.String(length=255), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), nullable=True),
        sa.Column("loaded_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "trends",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("metric_name", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=128), nullable=False),
        sa.Column("language", sa.String(length=64), nullable=False),
        sa.Column("value", sa.Float(), nullable=False),
        sa.Column("source", sa.String(length=128), nullable=False),
        sa.Column("period_label", sa.String(length=64), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_trends_metric_cat", "trends", ["metric_name", "category"])


def downgrade() -> None:
    op.drop_index("ix_trends_metric_cat", table_name="trends")
    op.drop_table("trends")
    op.drop_table("datasets")
    op.drop_table("saved_content")
    op.drop_index("ix_feedback_session_content", table_name="feedback")
    op.drop_table("feedback")
    op.drop_index("ix_rec_hist_session", table_name="recommendation_history")
    op.drop_table("recommendation_history")
    op.drop_table("user_preferences")
    op.drop_table("content_artists")
    op.drop_table("artists")
    op.drop_index("ix_content_title", table_name="content_items")
    op.drop_index("ix_content_type_lang", table_name="content_items")
    op.drop_table("content_items")
