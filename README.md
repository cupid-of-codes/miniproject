# VibeVerse AI

**Your vibe. Your soundtrack. Your next obsession.**

VibeVerse AI is a cross-domain music, movies, and web series intelligence and recommendation platform built with **Streamlit**, **FastAPI**, **MySQL (SQLAlchemy + Alembic)**, **Scikit-learn**, and **Plotly**. Instead of recommending songs, movies, and series in isolation, VibeVerse AI maps Hindi and English entertainment into a shared mood, theme, and storytelling space.

---

## Core Modules

1. **Home / Discovery Dashboard** — Hero banner, 6 quick discovery hub cards, instant Mood Selector, and source-attributed Spotlight & Trending sections.
2. **Personalized Entertainment Preference Engine** — Dynamic session-persisted preferences across Music, Movies, Web Series, Moods, Energy/Acoustic-vs-Electronic, Pacing, and 5 flexible Hindi/English language modes.
3. **Music Discovery Engine** — Search, Hindi/English/Mixed recommendations, discovery categories, and model-estimated audio characteristic badges.
4. **Movie Discovery Engine** — Search by title/genre/actor/director/theme/year, categories, and explainable music-aligned movie picks.
5. **Web Series Discovery Engine** — Dedicated episodic discovery with pacing, season counts, categories, and mood alignment.
6. **Cross-Domain Discovery Engine** — `Music → Movies`, `Music → Web Series`, `Movies → Music`, `Web Series → Music`, full `Music → Movie → Series → Soundtrack` discovery chains, and **Your Unexpected Vibe**.
7. **Mood-to-Story Matching** — Multi-mood chips + free-text NLP prompt matching across songs, movies, and series.
8. **Entertainment Personality Analyzer** — 7-dimension Plotly taste radar, deterministic Entertainment Archetypes, and dynamic preference breakdowns.
9. **Explainable AI ("Why This Is Your Vibe")** — Every recommendation lists the exact algorithmic signals driving its score.
10. **Trend Intelligence & Analytics** — Interactive dark-theme Plotly charts and live recommendation diversity/novelty/coverage metrics.
11. **Unified Search & Saved Discoveries** — Cross-domain search filters plus MySQL-persisted bookmarks and feedback history.

---

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Environment
```bash
copy .env.example .env
# Edit .env with your MySQL host, port, database, username, and password.
# Optionally add TMDB_API_KEY for live external movie/series enrichment.
```

### 3. Initialize MySQL & Load Datasets
```bash
python scripts/initialize_database.py
python scripts/preprocess_data.py
python scripts/load_datasets.py
```
*(Or run `alembic upgrade head` after creating the `vibeverse_ai` MySQL schema.)*

### 4. Start FastAPI Backend
```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```
Swagger API docs are available at `http://127.0.0.1:8000/docs`.

### 5. Start Streamlit Frontend
```bash
streamlit run frontend/app.py
```

---

## Running Tests
```bash
pytest tests/ -v
```

---

## Documentation
- [Architecture Overview](docs/architecture.md)
- [Database Schema](docs/database_schema.md)
- [Dataset & 3-Mode Data Guide](docs/dataset_guide.md)
- [Recommendation Engine & Evaluation](docs/recommendation_engine.md)
- [Setup Guide](docs/setup_guide.md)
