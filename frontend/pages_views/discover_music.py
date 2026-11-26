"""Module 3 — Music Discovery Engine."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

MUSIC_CATEGORIES = [
    "All",
    "Hidden Gems",
    "Hindi Indie Discoveries",
    "English Indie Discoveries",
    "Nostalgic Tracks",
    "Chill & Lo-Fi",
    "Energetic Playlist Discoveries",
    "Romantic Songs",
    "Dark & Atmospheric Music",
]


def render_discover_music(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Music Search, Personalized Song Recommendations (Mixed/Hindi/English), and Categories."""
    st.markdown("## 🎵 Music Discovery Engine")
    st.caption(
        "Personalized Hindi & English song discovery powered by metadata similarity, mood alignment, "
        "and session feedback. Audio characteristic tags are transparently labeled as model-generated estimates."
    )

    try:
        prefs = client.get_preferences(session_id)
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    st.info(
        f"Recommendations reflect your current profile · Language Mode: **{prefs.get('language_mode')}** · "
        f"Music Genres: `{', '.join(prefs.get('music_genres', [])) or 'All'}`"
    )

    tab_rec, tab_search = st.tabs(["✨ Personalized Song Recommendations", "🔍 Music Search & Filter"])

    with tab_rec:
        c1, c2, c3 = st.columns([2, 1.3, 1])
        with c1:
            selected_cat = st.selectbox("Discovery Category", MUSIC_CATEGORIES, key="music_cat")
        with c2:
            lang_override = st.selectbox(
                "View Section",
                ["Profile Default", "Mixed (Hindi + English)", "Hindi Only", "English Only"],
                key="music_lang_view",
            )
        with c3:
            st.write("")
            refresh = st.button("🔄 Regenerate Picks", key="music_regen", use_container_width=True)

        override_map = {
            "Profile Default": None,
            "Mixed (Hindi + English)": "both",
            "Hindi Only": "hindi_only",
            "English Only": "english_only",
        }
        try:
            rec_res = client.recommend_domain(
                domain="song",
                session_id=session_id,
                limit=10,
                category=selected_cat,
                language_mode_override=override_map[lang_override],
            )
            if rec_res.get("language_notice"):
                st.warning(rec_res["language_notice"])

            items = rec_res.get("items", [])
            if not items:
                st.info("No matching songs found for this category/language filter. Try broadening your selection.")
            else:
                sec_mix, sec_hi, sec_en = st.tabs(["🌐 Mixed Discovery", "🇮🇳 Hindi Picks", "🌍 English Picks"])
                with sec_mix:
                    for item in items:
                        render_content_card(client, session_id, item, key_prefix="mus_mix")
                with sec_hi:
                    hi_res = client.recommend_domain("song", session_id, limit=6, category=selected_cat, language_mode_override="hindi_only")
                    for item in hi_res.get("items", []):
                        render_content_card(client, session_id, item, key_prefix="mus_hi")
                with sec_en:
                    en_res = client.recommend_domain("song", session_id, limit=6, category=selected_cat, language_mode_override="english_only")
                    for item in en_res.get("items", []):
                        render_content_card(client, session_id, item, key_prefix="mus_en")
        except APIClientError as exc:
            st.error(str(exc))

    with tab_search:
        sc1, sc2, sc3, sc4 = st.columns([2, 1, 1, 1])
        with sc1:
            q = st.text_input("Search by song title, artist, album, or keyword", key="mus_q")
        with sc2:
            s_lang = st.selectbox("Language", ["All", "Hindi", "English"], key="mus_s_lang")
        with sc3:
            s_genre = st.selectbox("Genre", ["All"] + meta.get("music_genres", []), key="mus_s_genre")
        with sc4:
            s_mood = st.selectbox("Mood", ["All"] + meta.get("moods", []), key="mus_s_mood")

        try:
            s_res = client.search_domain("song", q=q, language=s_lang, genre=s_genre, mood=s_mood, limit=30)
            st.caption(f"Found {s_res.get('total', 0)} matching songs.")
            if not s_res.get("items"):
                st.info("No songs matched your search filters. Try clearing one of the filters.")
            for item in s_res.get("items", []):
                render_content_card(client, session_id, item, key_prefix="mus_search")
        except APIClientError as exc:
            st.error(str(exc))
