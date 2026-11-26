# VibeVerse AI — MySQL Database Schema

All tables are defined in `backend/models/db_models.py` and migrated via `alembic/versions/0001_initial_schema.py`.

| Table | Purpose | Key Columns & Constraints |
|---|---|---|
| `content_items` | Unified catalog of songs, movies, and web series | `id` (PK), `external_id`, `content_type`, `language`, `release_year`, `genres` (JSON), `mood_tags` (JSON), `themes` (JSON), `extra_metadata` (JSON), `popularity` (nullable), `rating` (nullable), `source`, `retrieved_at`. Unique `(external_id, content_type)`; indexes on `(content_type, language)` and `title`. |
| `artists` | Musicians, directors, and series creators | `id` (PK), `name` (Unique), `genres` (JSON), `metadata_json` (JSON), `source`. |
| `content_artists` | Many-to-many talent links | `content_id` (FK → `content_items.id`), `artist_id` (FK → `artists.id`), `role`. |
| `user_preferences` | Anonymous session preference profiles | `session_id` (PK), `language_mode`, `music_genres`, `movie_genres`, `series_genres`, `favourite_artists`, `favourite_content`, `moods`, `music_energy_pref`, `music_style_pref`, `popularity_pref`, `movie_themes`, `series_pacing`, `storytelling_style`, `preference_weights` (JSON), `updated_at`. |
| `recommendation_history` | Logged recommendations per session | `id` (PK), `session_id`, `recommended_content_id` (FK), `recommendation_type`, `recommendation_score`, `recommendation_explanation` (JSON), `created_at`. |
| `feedback` | Session interactions driving learning | `id` (PK), `session_id`, `content_id` (FK), `feedback_type`, `feedback_value`, `created_at`. Index on `(session_id, content_id)`. |
| `saved_content` | Bookmarked discoveries | `id` (PK), `session_id`, `content_id` (FK), `saved_at`. Unique `(session_id, content_id)`. |
| `datasets` | Loaded dataset registry & provenance | `id` (PK), `name`, `content_type`, `source`, `license_info`, `record_count`, `retrieved_at`, `loaded_at`. |
| `trends` | Verifiable catalog/API metric snapshots | `id` (PK), `metric_name`, `category`, `language`, `value`, `source`, `period_label`, `retrieved_at`. |
