"""Streamlit main application for VibeVerse AI."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

st.set_page_config(
    page_title="VibeVerse AI — Your Vibe. Your Soundtrack.",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

from frontend.pages_views.cross_domain import render_cross_domain
from frontend.pages_views.discover_movies import render_discover_movies
from frontend.pages_views.discover_music import render_discover_music
from frontend.pages_views.discover_series import render_discover_series
from frontend.pages_views.home import render_home
from frontend.pages_views.mood_match import render_mood_match
from frontend.pages_views.preferences import render_preferences
from frontend.pages_views.saved_discoveries import render_saved_discoveries
from frontend.pages_views.trends_analytics import render_trends_analytics
from frontend.pages_views.unified_search import render_unified_search
from frontend.pages_views.vibe_profile import render_vibe_profile
from frontend.services.api_client import APIClientError, VibeVerseAPIClient
from frontend.styles.theme import inject_theme
from frontend.utils.helpers import get_session_id

NAV_ITEMS = [
    "Home",
    "Discover Music",
    "Discover Movies",
    "Discover Web Series",
    "Mood Match",
    "Cross-Domain Discovery",
    "Unified Search",
    "My Vibe Profile",
    "Trends & Insights",
    "Saved Discoveries",
    "Preferences",
]

NAV_LABELS = {
    "Home": "🏠 Home",
    "Discover Music": "🎵 Discover Music",
    "Discover Movies": "🎬 Discover Movies",
    "Discover Web Series": "📺 Discover Web Series",
    "Mood Match": "🌈 Mood Match",
    "Cross-Domain Discovery": "🔀 Cross-Domain Discovery",
    "Unified Search": "🔎 Unified Search",
    "My Vibe Profile": "🧬 My Vibe Profile",
    "Trends & Insights": "📊 Trends & Insights",
    "Saved Discoveries": "💾 Saved Discoveries",
    "Preferences": "🎚 Preferences",
}


def main() -> None:
    inject_theme()
    session_id = get_session_id()
    client = VibeVerseAPIClient()

    if "vv_nav" not in st.session_state or st.session_state["vv_nav"] not in NAV_ITEMS:
        st.session_state["vv_nav"] = "Home"

    with st.sidebar:
        st.markdown(
            """
            <div style="padding:0.4rem 0 0.8rem 0;">
                <div style="font-family:'Space Grotesk',sans-serif; font-size:1.5rem; font-weight:700;
                     background:linear-gradient(90deg,#FFFFFF,#E0AAFF,#00F5D4);
                     -webkit-background-clip:text; -webkit-text-fill-color:transparent;">
                    🎧 VibeVerse AI
                </div>
                <div style="color:#A2A6B8; font-size:0.78rem;">Your vibe. Your soundtrack. Your next obsession.</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        selected = st.radio(
            "Navigation",
            options=NAV_ITEMS,
            index=NAV_ITEMS.index(st.session_state["vv_nav"]),
            format_func=lambda k: NAV_LABELS[k],
            label_visibility="collapsed",
        )
        if selected != st.session_state["vv_nav"]:
            st.session_state["vv_nav"] = selected
            st.rerun()

        st.divider()
        try:
            health = client.health()
            db_status = str(health.get("database_status", ""))
            is_mysql = "mysql" in db_status and db_status.startswith("connected")
            badge_color = "#00F5D4" if is_mysql else ("#B5FF4D" if db_status.startswith("connected") else "#FF2A85")
            st.markdown(
                f"<div style='font-size:0.78rem; color:#B8BCD0;'>"
                f"<span style='color:{badge_color};'>●</span> API: <b>{health.get('status', '').upper()}</b><br/>"
                f"DB: <code>{db_status}</code><br/>"
                f"Catalog: <b>{health.get('content_count') or 0}</b> items<br/>"
                f"Session: <code>{session_id[:12]}</code>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if not is_mysql and db_status.startswith("connected"):
                st.caption("⚠️ Running on local SQLite fallback (MySQL not active on port 3306).")
        except APIClientError as exc:
            st.warning(str(exc))

    active_page = st.session_state["vv_nav"]
    page_dispatch = {
        "Home": render_home,
        "Discover Music": render_discover_music,
        "Discover Movies": render_discover_movies,
        "Discover Web Series": render_discover_series,
        "Mood Match": render_mood_match,
        "Cross-Domain Discovery": render_cross_domain,
        "Unified Search": render_unified_search,
        "My Vibe Profile": render_vibe_profile,
        "Trends & Insights": render_trends_analytics,
        "Saved Discoveries": render_saved_discoveries,
        "Preferences": render_preferences,
    }
    page_dispatch[active_page](client, session_id)


if __name__ == "__main__":
    main()
