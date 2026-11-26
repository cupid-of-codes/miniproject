# VibeVerse AI — Dataset & Data Availability Guide

## 1. Three-Mode Data Strategy

VibeVerse AI supports three resilient data modes configured via `DATA_MODE` in `.env`:

1. **`auto` (Default):** Uses local curated datasets (`data/raw/`), enriches with live TMDB/MusicBrainz API data when credentials/network are available, and caches responses in `data/cache/`.
2. **`local`:** Operates strictly offline using CSV/JSON files in `data/raw/`.
3. **`cache`:** Reuses previously cached API responses in `data/cache/` alongside local datasets.

Every item and trend visualization preserves its `source` and `retrieved_at` metadata. VibeVerse AI **never** fabricates ratings, popularity metrics, review counts, or historical trends when they are missing from the underlying source.

---

## 2. Default Curated Datasets (`data/raw/`)

- `songs_curated.json`: Curated Hindi & English songs with genre, mood, theme, and style/energy metadata.
- `movies_curated.json`: Curated Hindi & English movies with director, cast, runtime, genre, mood, theme, and storytelling metadata.
- `series_curated.json`: Curated Hindi & English web series with creator, cast, season counts, pacing, genre, mood, and storytelling metadata.

> **Music Audio Feature Honesty:** Because open metadata datasets do not bundle proprietary audio DSP waveforms, inferred style/energy tags are explicitly labeled `is_model_generated_estimate: true` inside `extra_metadata.music_analysis`.

---

## 3. How to Add Your Own Dataset

1. Place a `.json` or `.csv` file in `data/raw/` (include `song`, `movie`, or `series` in the filename, or specify `content_type` per record).
2. Supported columns/keys:
   - **Required:** `title`, `content_type` (`song` | `movie` | `series`), `language` (`Hindi` | `English` | `Bilingual`)
   - **Recommended:** `external_id`, `release_year`, `genres` (list or comma-separated), `mood_tags`, `themes`, `description`, `artist` / `director` / `creator`, `artwork_url`
   - **Optional Real Metrics:** `rating`, `popularity` (leave blank/null if not from a verified source)
3. Run preprocessing & database load:
   ```bash
   python scripts/preprocess_data.py
   python scripts/load_datasets.py
   ```
