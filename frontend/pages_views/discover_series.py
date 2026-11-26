"""Module 5 — Dedicated Web Series Discovery Engine."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

SERIES_CATEGORIES = [
    "All",
    "Hindi",
    "English",
    "Mystery",
    "Crime and Investigation",
    "Psychological Drama",
    "Romance",
    "Sci-Fi",
    "Fantasy",
    "Comedy",
    "Dark Stories",
    "Comfort Series",
    "Binge-Worthy Discoveries",
    "Underrated Series",
    "Series Based on Your Music Taste",
]


def render_discover_series(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render dedicated Web Series Search, Pacing/Genre Categories, and Personalized Series Picks."""
    st.markdown("## 📺 Web Series Discovery Engine")
    st.caption(
        "Dedicated episodic discovery across Hindi & English series—tailored to your pacing, narrative atmosphere, "
        "music mood, and entertainment personality."
    )

    try:
        prefs = client.get_preferences(session_id)
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    st.info(
        f"Active Profile · Pacing: **{prefs.get('series_pacing', 'balanced').replace('_', ' ').title()}** · "
        f"Language Mode: **{prefs.get('language_mode')}**"
    )

    tab_rec, tab_search = st.tabs(["🔥 Personalized Series Recommendations", "🔍 Web Series Search & Filter"])

    with tab_rec:
        c1, c2 = st.columns([2.5, 1])
        with c1:
            category = st.selectbox("Series Discovery Category", SERIES_CATEGORIES, key="ser_cat")
        with c2:
            st.write("")
            st.button("🔄 Refresh Series", key="ser_regen", use_container_width=True)

        try:
            res = client.recommend_domain("series", session_id, limit=10, category=category)
            if res.get("language_notice"):
                st.warning(res["language_notice"])
            items = res.get("items", [])
            if not items:
                st.info("No web series matched this category/language filter.")
            for item in items:
                render_content_card(client, session_id, item, key_prefix="ser_rec")
        except APIClientError as exc:
            st.error(str(exc))

    with tab_search:
        sc1, sc2, sc3, sc4 = st.columns([2, 1, 1, 1])
        with sc1:
            q = st.text_input("Search series title, creator, theme, or mood keyword", key="ser_q")
        with sc2:
            s_lang = st.selectbox("Language", ["All", "Hindi", "English"], key="ser_s_lang")
        with sc3:
            s_genre = st.selectbox("Genre", ["All"] + meta.get("series_genres", []), key="ser_s_genre")
        with sc4:
            s_mood = st.selectbox("Mood", ["All"] + meta.get("moods", []), key="ser_s_mood")

        try:
            s_res = client.search_domain("series", q=q, language=s_lang, genre=s_genre, mood=s_mood, limit=30)
            st.caption(f"Found {s_res.get('total', 0)} matching web series.")
            if not s_res.get("items"):
                st.info("No web series matched your search filters.")
            for item in s_res.get("items", []):
                render_content_card(client, session_id, item, key_prefix="ser_search")
        except APIClientError as exc:
            st.error(str(exc))
