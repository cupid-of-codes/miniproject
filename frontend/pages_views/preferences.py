"""Module 2 — Personalized Entertainment Preference Engine."""

import streamlit as st

from frontend.services.api_client import APIClientError, VibeVerseAPIClient

LANGUAGE_OPTIONS = {
    "both": "Both Hindi & English (Balanced Discovery)",
    "hindi_only": "Hindi Only",
    "english_only": "English Only",
    "hindi_pref_english_rec": "Hindi Taste → Recommend English Matches",
    "english_pref_hindi_rec": "English Taste → Recommend Hindi Matches",
}


def render_preferences(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render interactive Preference Engine that updates DB state and recalculates recommendations."""
    st.markdown("## 🎚 Personalized Entertainment Preference Engine")
    st.caption(
        "Every change saved here dynamically updates your recommendation profile, cross-domain pathways, "
        "and Vibe Personality across Hindi and English entertainment."
    )

    try:
        current = client.get_preferences(session_id)
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    updated_ts = current.get("updated_at")
    st.info(
        f"Active Session: `{session_id}` · Last Profile Update: `{updated_ts or 'Default'}` · "
        f"Feedback Signals Learned: `{len((current.get('preference_weights') or {}).get('liked_ids', []))} likes / "
        f"{len((current.get('preference_weights') or {}).get('suppressed_ids', []))} hidden`"
    )

    with st.form("preferences_form"):
        st.markdown("### 🌐 Language Preference Mode")
        lang_keys = list(LANGUAGE_OPTIONS.keys())
        cur_lang = current.get("language_mode", "both")
        lang_idx = lang_keys.index(cur_lang) if cur_lang in lang_keys else 0
        language_mode = st.selectbox(
            "Choose how Hindi and English content are blended",
            options=lang_keys,
            index=lang_idx,
            format_func=lambda k: LANGUAGE_OPTIONS[k],
        )

        st.markdown("### 🎭 Core Mood Preferences")
        moods = st.multiselect(
            "Moods you resonate with",
            options=meta.get("moods", []),
            default=[m for m in current.get("moods", []) if m in meta.get("moods", [])],
        )

        col_m, col_mv, col_sr = st.columns(3, gap="medium")
        with col_m:
            st.markdown("### 🎵 Music Preferences")
            music_genres = st.multiselect(
                "Favourite Music Genres",
                options=meta.get("music_genres", []),
                default=[g for g in current.get("music_genres", []) if g in meta.get("music_genres", [])],
            )
            favourite_artists = st.multiselect(
                "Favourite Artists / Creators",
                options=meta.get("artists", []),
                default=[a for a in current.get("favourite_artists", []) if a in meta.get("artists", [])],
            )
            music_energy_pref = st.select_slider(
                "Energy Preference",
                options=["calm", "balanced", "high"],
                value=current.get("music_energy_pref", "balanced"),
            )
            music_style_pref = st.radio(
                "Acoustic vs Electronic",
                options=["acoustic", "balanced", "electronic"],
                index=["acoustic", "balanced", "electronic"].index(
                    current.get("music_style_pref", "balanced")
                ),
                horizontal=True,
            )

        with col_mv:
            st.markdown("### 🎬 Movie Preferences")
            movie_genres = st.multiselect(
                "Favourite Movie Genres",
                options=meta.get("movie_genres", []),
                default=[g for g in current.get("movie_genres", []) if g in meta.get("movie_genres", [])],
            )
            movie_themes = st.multiselect(
                "Preferred Themes",
                options=meta.get("themes", []),
                default=[t for t in current.get("movie_themes", []) if t in meta.get("themes", [])],
            )
            popularity_pref = st.radio(
                "Mainstream vs Underrated",
                options=["popular", "balanced", "underrated"],
                index=["popular", "balanced", "underrated"].index(
                    current.get("popularity_pref", "balanced")
                ),
                horizontal=True,
            )

        with col_sr:
            st.markdown("### 📺 Web Series Preferences")
            series_genres = st.multiselect(
                "Favourite Series Genres",
                options=meta.get("series_genres", []),
                default=[g for g in current.get("series_genres", []) if g in meta.get("series_genres", [])],
            )
            series_pacing = st.select_slider(
                "Preferred Series Pacing",
                options=["slow_burn", "balanced", "fast_paced"],
                value=current.get("series_pacing", "balanced"),
            )
            storytelling_opts = [
                "atmospheric", "character-driven", "plot-twist", "slow-burn",
                "investigative", "feel-good", "puzzle-box", "poetic",
            ]
            storytelling_style = st.multiselect(
                "Storytelling Preferences",
                options=storytelling_opts,
                default=[s for s in current.get("storytelling_style", []) if s in storytelling_opts],
            )

        all_titles = (
            meta.get("titles_by_type", {}).get("song", [])
            + meta.get("titles_by_type", {}).get("movie", [])
            + meta.get("titles_by_type", {}).get("series", [])
        )
        favourite_content = st.multiselect(
            "⭐ Seed Songs, Movies & Web Series You Already Love",
            options=sorted(set(all_titles)),
            default=[t for t in current.get("favourite_content", []) if t in all_titles],
        )

        save_btn = st.form_submit_button("💾 Save Preferences & Recalculate Recommendations", type="primary", use_container_width=True)

    if save_btn:
        payload = {
            "language_mode": language_mode,
            "music_genres": music_genres,
            "movie_genres": movie_genres,
            "series_genres": series_genres,
            "favourite_artists": favourite_artists,
            "favourite_content": favourite_content,
            "moods": moods,
            "music_energy_pref": music_energy_pref,
            "music_style_pref": music_style_pref,
            "popularity_pref": popularity_pref,
            "movie_themes": movie_themes,
            "series_pacing": series_pacing,
            "storytelling_style": storytelling_style,
        }
        try:
            client.update_preferences(session_id, payload)
            st.success("Preferences updated in MySQL! Recommendations and your Vibe Profile are now recalculated.")
            st.rerun()
        except APIClientError as exc:
            st.error(str(exc))

    if st.button("🔄 Reset All Preferences & Feedback Weights"):
        try:
            client.reset_preferences(session_id)
            st.toast("Preferences and learned feedback weights reset.")
            st.rerun()
        except APIClientError as exc:
            st.error(str(exc))
