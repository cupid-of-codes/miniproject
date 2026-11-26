"""Module 11/12 — Saved Discoveries & Feedback History."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient


def render_saved_discoveries(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Saved Discoveries and Session Feedback History stored in MySQL."""
    st.markdown("## 💾 Saved Discoveries")
    st.caption("Your bookmarked songs, movies, and web series persisted in MySQL for this session.")

    tab_saved, tab_fb = st.tabs(["⭐ Saved Collection", "📝 Feedback History"])

    with tab_saved:
        try:
            res = client.get_saved(session_id)
            items = res.get("items", [])
            if not items:
                st.info("You haven't saved any discoveries yet. Click '💾 Save' on any song, movie, or web series card!")
            else:
                f1, f2 = st.columns(2)
                with f1:
                    dom_filter = st.selectbox("Filter by Type", ["All", "song", "movie", "series"], key="sav_dom")
                with f2:
                    lang_filter = st.selectbox("Filter by Language", ["All", "Hindi", "English"], key="sav_lang")

                filtered = [
                    i for i in items
                    if (dom_filter == "All" or i.get("content_type") == dom_filter)
                    and (lang_filter == "All" or i.get("language") == lang_filter)
                ]
                st.caption(f"Showing {len(filtered)} of {len(items)} saved items.")
                for item in filtered:
                    render_content_card(
                        client, session_id, item, key_prefix="sav_card", show_remove_saved=True
                    )
        except APIClientError as exc:
            st.error(str(exc))

    with tab_fb:
        try:
            fb_res = client.get_feedback(session_id)
            fb_items = fb_res.get("items", [])
            if not fb_items:
                st.info("No feedback recorded yet in this session.")
            else:
                for row in fb_items:
                    st.markdown(
                        f"- **{row['title']}** ({row['content_type']} · {row['language']}) → "
                        f"`{row['feedback_type']}` (weight Δ `{row['feedback_value']:+}`)"
                    )
        except APIClientError as exc:
            st.error(str(exc))
