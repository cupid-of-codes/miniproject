"""Module 1 — Home / Discovery Dashboard."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

QUICK_MOODS = [
    "Happy", "Sad", "Romantic", "Chill", "Energetic", "Nostalgic",
    "Focused", "Dreamy", "Dark", "Mysterious", "Adventurous",
    "Comfort", "Angry", "Melancholic",
]

DISCOVERY_CARDS = [
    ("🎵 Music Discovery", "Hindi & English tracks tuned to your artists, genres & audio vibe.", "Discover Music", "#9D4EDD"),
    ("🎬 Movie Discovery", "Cinema matched to your soundtrack, storytelling style & mood.", "Discover Movies", "#FF2A85"),
    ("📺 Web Series Discovery", "Binge-worthy Hindi & English series matched to your pacing.", "Discover Web Series", "#00F5D4"),
    ("🌈 Mood Matching", "Describe your vibe in words or chips—get songs, films & series.", "Mood Match", "#B5FF4D"),
    ("🧬 My Vibe Profile", "Explore your entertainment archetype and 7-dimension taste radar.", "My Vibe Profile", "#C77DFF"),
    ("🔀 Cross-Domain Discovery", "Turn songs into movies, series into soundtracks & unexpected gems.", "Cross-Domain Discovery", "#FF75B5"),
]


def render_home(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Hero Banner, Quick Discovery Cards, Quick Mood Selector, and Trending Entertainment."""
    st.markdown(
        """
        <div class="vv-hero">
            <div class="vv-hero-badge">✦ Cross-Domain Entertainment Intelligence</div>
            <div class="vv-hero-title">VibeVerse AI</div>
            <div class="vv-hero-tagline">Your vibe. Your soundtrack. Your next obsession.</div>
            <p class="vv-hero-desc">
                Bridge the gap between what you listen to and what you watch. VibeVerse AI analyzes your
                music mood, genres, storytelling taste, and Hindi/English language preferences to surface
                connected songs, movies, and web series—with explainable AI insights on every pick.
            </p>
            <div class="vv-wave">
                <span style="height:14px;"></span><span style="height:26px;"></span>
                <span style="height:34px;"></span><span style="height:18px;"></span>
                <span style="height:30px;"></span><span style="height:22px;"></span>
                <span style="height:36px;"></span><span style="height:16px;"></span>
                <span style="height:28px;"></span><span style="height:20px;"></span>
                <span style="height:32px;"></span><span style="height:14px;"></span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    cta1, cta2, cta3 = st.columns([1.2, 1.2, 2.6])
    with cta1:
        if st.button("⚡ Discover My Vibe", type="primary", use_container_width=True):
            st.session_state["vv_nav"] = "Cross-Domain Discovery"
            st.rerun()
    with cta2:
        if st.button("🎛 Explore Entertainment", use_container_width=True):
            st.session_state["vv_nav"] = "Discover Music"
            st.rerun()
    with cta3:
        if st.button("🎚 Customize Preferences", use_container_width=True):
            st.session_state["vv_nav"] = "Preferences"
            st.rerun()

    st.markdown("### 🚀 Quick Discovery Hub")
    row1 = st.columns(3, gap="medium")
    row2 = st.columns(3, gap="medium")
    for idx, (title, desc, target_nav, accent) in enumerate(DISCOVERY_CARDS):
        col = row1[idx] if idx < 3 else row2[idx - 3]
        with col:
            st.markdown(
                f"""
                <div class="vv-glass" style="border-top: 3px solid {accent}; min-height: 120px;">
                    <h4 style="margin:0 0 0.35rem 0;">{title}</h4>
                    <p style="color:#B4B8CC; font-size:0.86rem; margin:0;">{desc}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"Open {target_nav} →", key=f"home_card_{idx}", use_container_width=True):
                st.session_state["vv_nav"] = target_nav
                st.rerun()

    st.markdown("### 🎭 Quick Mood Selector")
    st.caption("Pick your current mood to preview cross-domain songs, movies, and series immediately.")
    selected_mood = st.pills(
        "Select a mood",
        options=QUICK_MOODS,
        selection_mode="single",
        key="home_quick_mood",
        label_visibility="collapsed",
    )
    if selected_mood:
        col_go, col_full = st.columns([2, 1])
        with col_go:
            st.info(f"Showing instant cross-domain picks for **{selected_mood}** mood.")
        with col_full:
            if st.button("Open Full Mood-to-Story Studio →", use_container_width=True):
                st.session_state["vv_preset_moods"] = [selected_mood]
                st.session_state["vv_nav"] = "Mood Match"
                st.rerun()

        try:
            mood_res = client.mood_match(session_id, moods=[selected_mood], limit_per_domain=2)
            t1, t2, t3 = st.tabs(["🎵 Songs", "🎬 Movies", "📺 Web Series"])
            with t1:
                for item in mood_res.get("songs", []):
                    render_content_card(client, session_id, item, key_prefix="home_mood_s")
            with t2:
                for item in mood_res.get("movies", []):
                    render_content_card(client, session_id, item, key_prefix="home_mood_m")
            with t3:
                for item in mood_res.get("series", []):
                    render_content_card(client, session_id, item, key_prefix="home_mood_sr")
        except APIClientError as exc:
            st.warning(str(exc))

    st.markdown("### 🔥 Spotlight & Trending Entertainment")
    try:
        trending = client.get_trending()
        st.caption(f"📊 Source Note: {trending.get('data_source_note', '')}")
        datasets = trending.get("datasets", [])
        if datasets:
            with st.expander("📁 Active Data Sources & Retrieval Timestamps"):
                for ds in datasets[:6]:
                    st.write(
                        f"• **{ds['name']}** ({ds['content_type']}) — `{ds['source']}` · "
                        f"{ds['record_count']} records · Retrieved: `{ds.get('retrieved_at') or 'Local Snapshot'}`"
                    )

        tab_songs, tab_movies, tab_series, tab_hi, tab_en = st.tabs(
            ["🎵 Songs", "🎬 Movies", "📺 Web Series", "🇮🇳 Popular Hindi", "🌍 Popular English"]
        )
        with tab_songs:
            for item in trending.get("trending_songs", []):
                render_content_card(client, session_id, item, key_prefix="tr_song")
        with tab_movies:
            for item in trending.get("trending_movies", []):
                render_content_card(client, session_id, item, key_prefix="tr_mov")
        with tab_series:
            for item in trending.get("trending_series", []):
                render_content_card(client, session_id, item, key_prefix="tr_ser")
        with tab_hi:
            for item in trending.get("popular_hindi", []):
                render_content_card(client, session_id, item, key_prefix="tr_hi")
        with tab_en:
            for item in trending.get("popular_english", []):
                render_content_card(client, session_id, item, key_prefix="tr_en")
    except APIClientError as exc:
        st.error(str(exc))
