# VibeVerse AI — Setup Guide

## Prerequisites
- **Python 3.10+** (verified on `Python 3.13.15`)
- **MySQL 8.0+** (or MariaDB 10.6+) running locally or remotely

## Step-by-Step Installation

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure `.env`:**
   ```bash
   copy .env.example .env
   ```
   Update `MYSQL_HOST`, `MYSQL_PORT`, `MYSQL_DATABASE`, `MYSQL_USER`, and `MYSQL_PASSWORD`.
   - Leave `TMDB_API_KEY` empty to run in local curated + MusicBrainz/cache mode, or supply a TMDB v3 API key for live movie/series enrichment.

3. **Initialize MySQL Schema & Tables:**
   ```bash
   python scripts/initialize_database.py
   ```
   Alternatively, create the database in MySQL and run Alembic migrations:
   ```bash
   alembic upgrade head
   ```

4. **Preprocess & Load Datasets into MySQL:**
   ```bash
   python scripts/preprocess_data.py
   python scripts/load_datasets.py
   ```
   Pass `--external` to `load_datasets.py` if you want to pull live TMDB/MusicBrainz records as well.

5. **Launch FastAPI & Streamlit (two terminals):**
   Terminal 1 (Backend API):
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000
   ```
   Terminal 2 (Frontend UI):
   ```bash
   streamlit run frontend/app.py
   ```
