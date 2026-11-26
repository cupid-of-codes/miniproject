"""Module 8 — Entertainment Personality Analyzer (My Vibe Profile)."""

import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import APIClientError, VibeVerseAPIClient
from frontend.utils.helpers import apply_dark_plotly_theme


def render_vibe_profile(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Entertainment Archetype, 7-Dimension Radar Chart, and Preference Breakdowns."""
    st.markdown("## 🧬 My Vibe Profile — Entertainment Personality Analyzer")

    c_hdr, c_btn = st.columns([3, 1])
    with c_hdr:
        st.caption("Reflects your live entertainment preferences, moods, and feedback history.")
    with c_btn:
        if st.button("🔄 Recalculate Profile", use_container_width=True):
            try:
                client.analyze_personality(session_id)
                st.rerun()
            except APIClientError as exc:
                st.error(str(exc))

    try:
        profile = client.get_personality(session_id)
    except APIClientError as exc:
        st.error(str(exc))
        return

    st.markdown(
        f"""
        <div class="vv-hero" style="padding:1.8rem 2rem;">
            <div class="vv-hero-badge">✦ Your Entertainment Archetype</div>
            <div class="vv-hero-title" style="font-size:2.2rem;">{profile.get('archetype', 'The Explorer')}</div>
            <div class="vv-hero-tagline" style="color:#00F5D4;">{profile.get('archetype_tagline', '')}</div>
            <p class="vv-hero-desc">{profile.get('explanation', '')}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"ℹ️ {profile.get('disclaimer', '')}")

    dimensions = profile.get("dimensions", [])
    col_radar, col_bars = st.columns([1.25, 1], gap="large")

    with col_radar:
        axes = [d["axis"] for d in dimensions]
        scores = [d["score"] for d in dimensions]
        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=scores + [scores[0]] if scores else [],
                theta=axes + [axes[0]] if axes else [],
                fill="toself",
                fillcolor="rgba(157, 78, 221, 0.28)",
                line=dict(color="#00F5D4", width=2.5),
                marker=dict(color="#FF2A85", size=7),
                name="Vibe Signature",
            )
        )
        fig_radar.update_layout(
            polar=dict(
                bgcolor="rgba(16,16,28,0.65)",
                radialaxis=dict(visible=True, range=[0, 100], gridcolor="rgba(255,255,255,0.12)", tickfont=dict(color="#A2A6B8")),
                angularaxis=dict(gridcolor="rgba(255,255,255,0.12)", tickfont=dict(color="#F4F4F9")),
            )
        )
        apply_dark_plotly_theme(fig_radar, "7-Dimension Entertainment Vibe Radar", height=420)
        st.plotly_chart(fig_radar, use_container_width=True)

    with col_bars:
        st.markdown("### 🎛 Dimension Spectrum")
        for d in dimensions:
            st.markdown(
                f"**{d['axis']}** — `{d['left_label']}` vs `{d['right_label']}` (**{d['score']}%**)"
            )
            st.progress(min(100, max(0, int(round(d["score"])))) / 100.0)

    breakdowns = profile.get("breakdowns", {})
    b1, b2, b3 = st.columns(3, gap="medium")

    with b1:
        top_genres = breakdowns.get("top_genres", {})
        if top_genres:
            fig_g = go.Figure(
                go.Bar(
                    x=list(top_genres.values()),
                    y=list(top_genres.keys()),
                    orientation="h",
                    marker=dict(color="#9D4EDD"),
                )
            )
            apply_dark_plotly_theme(fig_g, "Top Genre Affinities", height=320)
            st.plotly_chart(fig_g, use_container_width=True)
        else:
            st.info("Select genres or like items to populate genre affinities.")

    with b2:
        mood_dist = breakdowns.get("mood_distribution", {})
        if mood_dist:
            fig_m = go.Figure(
                go.Bar(
                    x=list(mood_dist.keys()),
                    y=list(mood_dist.values()),
                    marker=dict(color="#FF2A85"),
                )
            )
            apply_dark_plotly_theme(fig_m, "Mood Distribution", height=320)
            st.plotly_chart(fig_m, use_container_width=True)
        else:
            st.info("Select moods or interact with items to view mood distribution.")

    with b3:
        dom_bal = breakdowns.get("domain_balance", {})
        fig_d = go.Figure(
            go.Pie(
                labels=list(dom_bal.keys()),
                values=list(dom_bal.values()),
                hole=0.55,
                marker=dict(colors=["#9D4EDD", "#FF2A85", "#00F5D4"]),
            )
        )
        apply_dark_plotly_theme(fig_d, "Music vs Movies vs Series Interest", height=320)
        st.plotly_chart(fig_d, use_container_width=True)
