"""Module 11 — Unified Cross-Domain Search & Filter Hub."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient


def render_unified_search(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render unified search and multi-filter exploration across songs, movies, and web series."""
    st.markdown("## 🔎 Unified Search & Filter")
    st.caption("Search across all Songs, Movies, and Web Series simultaneously with instant filters.")

    try:
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    all_genres = sorted(
        set(meta.get("music_genres", []) + meta.get("movie_genres", []) + meta.get("series_genres", []))
    )

    c1, c2, c3 = st.columns([2.2, 1, 1])
    with c1:
        q = st.text_input("Search title, artist, director, theme, or description", key="uni_q")
    with c2:
        ctype = st.selectbox("Category", ["all", "song", "movie", "series"], key="uni_type")
    with c3:
        lang = st.selectbox("Language", ["All", "Hindi", "English"], key="uni_lang")

    f1, f2, f3, f4 = st.columns([1.2, 1.2, 1.2, 0.8])
    with f1:
        genre = st.selectbox("Genre", ["All"] + all_genres, key="uni_genre")
    with f2:
        mood = st.selectbox("Mood", ["All"] + meta.get("moods", []), key="uni_mood")
    with f3:
        theme = st.selectbox("Theme", ["All"] + meta.get("themes", []), key="uni_theme")
    with f4:
        st.write("")
        if st.button("Reset Filters", use_container_width=True):
            for k in ("uni_q", "uni_type", "uni_lang", "uni_genre", "uni_mood", "uni_theme"):
                st.session_state.pop(k, None)
            st.rerun()

    try:
        res = client.search_domain(
            ctype, q=q, language=lang, genre=genre, mood=mood, theme=theme, limit=40
        )
        st.caption(f"Showing {res.get('total', 0)} matching items across the catalog.")
        items = res.get("items", [])
        if not items:
            st.info("No results matched your filter combination. Try resetting filters.")
        for item in items:
            render_content_card(client, session_id, item, key_prefix="uni_res")
    except APIClientError as exc:
        st.error(str(exc))
