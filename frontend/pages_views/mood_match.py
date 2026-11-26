"""Module 7 — Mood-to-Story Matching."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

ALL_MOODS = [
    "Happy", "Sad", "Romantic", "Nostalgic", "Calm", "Energetic", "Dreamy",
    "Dark", "Mysterious", "Anxious", "Hopeful", "Melancholic", "Adventurous",
    "Comfort", "Focused", "Angry", "Emotional",
]


def render_mood_match(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render multi-mood + free-text NLP Mood-to-Story Matching across Songs, Movies, and Series."""
    st.markdown("## 🌈 Mood-to-Story Matching")
    st.caption(
        "Select one or more moods—or describe your exact aesthetic vibe in plain English—to discover "
        "synchronized Songs, Movies, and Web Series."
    )

    preset = st.session_state.pop("vv_preset_moods", None)
    default_moods = preset if preset else ["Dreamy", "Mysterious"]

    selected_moods = st.multiselect(
        "Choose one or multiple moods",
        options=ALL_MOODS,
        default=[m for m in default_moods if m in ALL_MOODS],
        key="mood_match_pills",
    )

    c1, c2 = st.columns([2.5, 1])
    with c1:
        mood_text = st.text_input(
            "Or describe your mood / atmosphere in natural language",
            placeholder="e.g., I want something quiet, emotional, slightly mysterious, and atmospheric.",
            key="mood_match_text",
        )
    with c2:
        lang_choice = st.selectbox(
            "Language Filter",
            ["Profile Default", "both", "hindi_only", "english_only"],
            key="mood_match_lang",
        )

    if st.button("✨ Match My Mood Across Music, Movies & Series", type="primary", use_container_width=True):
        st.session_state["vv_run_mood_match"] = True

    if st.session_state.get("vv_run_mood_match", True) and (selected_moods or mood_text.strip()):
        try:
            res = client.mood_match(
                session_id=session_id,
                moods=selected_moods,
                mood_text=mood_text,
                language_mode=None if lang_choice == "Profile Default" else lang_choice,
                limit_per_domain=5,
            )
            nlp = res.get("nlp_signals") or {}
            st.info(
                f"🎯 Matched Mood Signals: **{', '.join(res.get('target_moods', []))}** · "
                f"Detected Intensity: `{nlp.get('intensity', 'balanced')}`\n\n"
                f"_{res.get('note', '')}_"
            )

            t_song, t_mov, t_ser = st.tabs(["🎵 Matching Songs", "🎬 Matching Movies", "📺 Matching Web Series"])
            with t_song:
                songs = res.get("songs", [])
                if not songs:
                    st.info("No matching songs found for this mood combination.")
                for item in songs:
                    render_content_card(client, session_id, item, key_prefix="mm_song")
            with t_mov:
                movies = res.get("movies", [])
                if not movies:
                    st.info("No matching movies found for this mood combination.")
                for item in movies:
                    render_content_card(client, session_id, item, key_prefix="mm_mov")
            with t_ser:
                series = res.get("series", [])
                if not series:
                    st.info("No matching web series found for this mood combination.")
                for item in series:
                    render_content_card(client, session_id, item, key_prefix="mm_ser")
        except APIClientError as exc:
            st.error(str(exc))
    else:
        st.info("Select at least one mood or describe your vibe above to generate matches.")
