# VibeVerse AI — System Architecture

## 1. Layered Modular Architecture

VibeVerse AI separates concerns across four clean layers:

1. **Frontend Layer (`frontend/`):**
   - Built strictly with **Streamlit**, custom CSS (`frontend/styles/theme.py`), and **Plotly** dark-theme charts.
   - Communicates exclusively with FastAPI over HTTP via `VibeVerseAPIClient` (`frontend/services/api_client.py`).
   - Maintains an anonymous session UUID in URL query params + `st.session_state` (`frontend/utils/helpers.py`)—no login, registration, or admin portal.

2. **Backend API Layer (`backend/`):**
   - Built with **FastAPI** and **Pydantic v2** (`backend/schemas/api_schemas.py`).
   - Routes (`backend/api/routes/`) delegate orchestration to `backend/services/catalog_service.py` and `backend/repositories/vibeverse_repo.py`.
   - Global exception handlers in `backend/main.py` prevent leaking database credentials or stack traces to clients.

3. **Machine Learning & Recommendation Layer (`recommendation_engine/`):**
   - `preprocessing/`: Text normalization, canonical mood mapping, honest metadata-based music characteristic estimation, and 3-mode dataset loading (`auto`, `local`, `cache`).
   - `feature_engineering/`: `CatalogFeatureIndex` combining TF-IDF n-grams (`(1, 2)`), a shared 29-dimensional cross-domain vibe vector, cosine similarity, and K-Means clustering.
   - `algorithms/`: Hybrid scoring (`HybridWeights`), MMR-style diversity re-ranking, 5-mode language balancing, optional item-item collaborative filtering (active only with `>= 5` distinct session interactions), and transparent feedback weight updates.
   - `cross_domain/`: `music_to_movies`, `music_to_series`, `movies_to_music`, `series_to_music`, multi-stage discovery chains, and `discover_unexpected_vibe`.
   - `mood_matching/`: NLP keyword/intensity extraction + multi-mood cross-domain matching.
   - `personality/`: 7 entertainment preference dimensions + deterministic archetype classification.
   - `explainability/`: Structured `"Why This Is Your Vibe"` explanation builder.
   - `evaluation/`: Intra-list diversity, catalog coverage, self-information novelty, and ground-truth ranking metrics (`Precision@K`, `Recall@K`, `Hit Rate@K`) when relevance labels exist.

4. **Database Layer (`backend/database/`, `backend/models/`, `alembic/`):**
   - **MySQL** accessed through **SQLAlchemy 2.x** (`mysql+pymysql`) and migrated via **Alembic**.
