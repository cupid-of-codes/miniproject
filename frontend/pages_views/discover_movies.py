"""Module 4 — Movie Discovery Engine."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

MOVIE_CATEGORIES = [
    "All",
    "Hindi",
    "English",
    "Feel-Good Movies",
    "Emotional Movies",
    "Romantic Movies",
    "Psychological Thrillers",
    "Mystery Movies",
    "Sci-Fi",
    "Dark Cinema",
    "Comfort Movies",
    "Underrated Movies",
    "Hidden Gems",
]


def render_discover_movies(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Movie Search, Categories, and Music-Aware Personalized Movie Recommendations."""
    st.markdown("## 🎬 Movie Discovery Engine")
    st.caption(
        "Hindi & English cinema curated from your music taste, preferred themes, mood, and feedback history."
    )

    try:
        prefs = client.get_preferences(session_id)
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    st.info(
        f"Active Profile · Language Mode: **{prefs.get('language_mode')}** · "
        f"Movie Genres: `{', '.join(prefs.get('movie_genres', [])) or 'All'}`"
    )

    tab_rec, tab_search = st.tabs(["🎯 Personalized Movie Recommendations", "🔍 Movie Search & Filter"])

    with tab_rec:
        c1, c2 = st.columns([2.5, 1])
        with c1:
            category = st.selectbox("Movie Discovery Category", MOVIE_CATEGORIES, key="mov_cat")
        with c2:
            st.write("")
            st.button("🔄 Refresh Movies", key="mov_regen", use_container_width=True)

        try:
            res = client.recommend_domain("movie", session_id, limit=10, category=category)
            if res.get("language_notice"):
                st.warning(res["language_notice"])
            items = res.get("items", [])
            if not items:
                st.info("No movies matched this category with your current language filter.")
            for item in items:
                render_content_card(client, session_id, item, key_prefix="mov_rec")
        except APIClientError as exc:
            st.error(str(exc))

    with tab_search:
        sc1, sc2, sc3, sc4, sc5 = st.columns([2, 1, 1, 1, 1])
        with sc1:
            q = st.text_input("Search title, actor, director, theme, or keyword", key="mov_q")
        with sc2:
            s_lang = st.selectbox("Language", ["All", "Hindi", "English"], key="mov_s_lang")
        with sc3:
            s_genre = st.selectbox("Genre", ["All"] + meta.get("movie_genres", []), key="mov_s_genre")
        with sc4:
            s_mood = st.selectbox("Mood", ["All"] + meta.get("moods", []), key="mov_s_mood")
        with sc5:
            year_min = st.number_input("From Year", min_value=1950, max_value=2026, value=1990, key="mov_ymin")

        try:
            s_res = client.search_domain(
                "movie", q=q, language=s_lang, genre=s_genre, mood=s_mood, year_min=int(year_min), limit=30
            )
            st.caption(f"Found {s_res.get('total', 0)} matching movies.")
            if not s_res.get("items"):
                st.info("No movies matched your search criteria.")
            for item in s_res.get("items", []):
                render_content_card(client, session_id, item, key_prefix="mov_search")
        except APIClientError as exc:
            st.error(str(exc))
