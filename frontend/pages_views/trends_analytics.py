"""Module 10 — Trend Intelligence and Analytics."""

import plotly.graph_objects as go
import streamlit as st

from frontend.services.api_client import APIClientError, VibeVerseAPIClient
from frontend.utils.helpers import apply_dark_plotly_theme


def render_trends_analytics(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render data-driven Plotly visualisations across genres, languages, moods, and quality metrics."""
    st.markdown("## 📊 Trend Intelligence & Analytics")
    st.caption(
        "Interactive analytics computed strictly from loaded datasets and live session interactions—zero fabricated statistics."
    )

    try:
        trends = client.get_trends_analytics()
        pref_stats = client.get_preference_analytics(session_id)
    except APIClientError as exc:
        st.error(str(exc))
        return

    m1, m2, m3, m4 = st.columns(4)
    dom = trends.get("domain_distribution", {})
    m1.metric("Total Catalog Items", trends.get("total_items", 0))
    m2.metric("Songs", dom.get("song", 0))
    m3.metric("Movies", dom.get("movie", 0))
    m4.metric("Web Series", dom.get("series", 0))

    st.info(f"ℹ️ {trends.get('temporal_notice', '')}")

    c1, c2 = st.columns(2, gap="medium")
    with c1:
        gbl = trends.get("genre_by_language", {})
        fig_gl = go.Figure()
        fig_gl.add_trace(
            go.Bar(name="Hindi", x=gbl.get("genres", []), y=gbl.get("Hindi", []), marker_color="#9D4EDD")
        )
        fig_gl.add_trace(
            go.Bar(name="English", x=gbl.get("genres", []), y=gbl.get("English", []), marker_color="#00F5D4")
        )
        fig_gl.update_layout(barmode="group")
        apply_dark_plotly_theme(fig_gl, "Top Genres: Hindi vs English Comparison", height=390)
        st.plotly_chart(fig_gl, use_container_width=True)

    with c2:
        mood_dist = trends.get("mood_distribution", {})
        fig_md = go.Figure(
            go.Bar(
                x=list(mood_dist.keys()),
                y=list(mood_dist.values()),
                marker=dict(color="#FF2A85"),
            )
        )
        apply_dark_plotly_theme(fig_md, "Mood Distribution Across Catalog", height=390)
        st.plotly_chart(fig_md, use_container_width=True)

    c3, c4 = st.columns(2, gap="medium")
    with c3:
        cd_bridge = trends.get("cross_domain_mood_bridge", {})
        mood_names = list(cd_bridge.keys())[:12]
        fig_bridge = go.Figure()
        for domain_key, label, color in [
            ("song", "Songs", "#9D4EDD"),
            ("movie", "Movies", "#FF2A85"),
            ("series", "Web Series", "#00F5D4"),
        ]:
            fig_bridge.add_trace(
                go.Bar(
                    name=label,
                    x=mood_names,
                    y=[cd_bridge[m].get(domain_key, 0) for m in mood_names],
                    marker_color=color,
                )
            )
        fig_bridge.update_layout(barmode="stack")
        apply_dark_plotly_theme(fig_bridge, "Cross-Domain Mood Overlap (Music vs Movies vs Series)", height=390)
        st.plotly_chart(fig_bridge, use_container_width=True)

    with c4:
        lang_dist = trends.get("language_distribution", {})
        fig_lang = go.Figure(
            go.Pie(
                labels=list(lang_dist.keys()),
                values=list(lang_dist.values()),
                hole=0.52,
                marker=dict(colors=["#9D4EDD", "#00F5D4", "#B5FF4D"]),
            )
        )
        apply_dark_plotly_theme(fig_lang, "Catalog Language Balance", height=390)
        st.plotly_chart(fig_lang, use_container_width=True)

    # Release Year distribution (catalog metadata timeline)
    year_dist = trends.get("release_year_distribution", {})
    if year_dist:
        fig_yr = go.Figure(
            go.Scatter(
                x=[str(y) for y in year_dist.keys()],
                y=list(year_dist.values()),
                mode="lines+markers",
                line=dict(color="#B5FF4D", width=2.5),
                marker=dict(color="#00F5D4", size=7),
            )
        )
        apply_dark_plotly_theme(fig_yr, "Catalog Items by Release Year (Metadata Snapshot)", height=320)
        st.plotly_chart(fig_yr, use_container_width=True)

    st.markdown("### 🧪 Live Session Recommendation Quality Metrics")
    qm = pref_stats.get("quality_metrics", {})
    if qm:
        q1, q2, q3, q4 = st.columns(4)
        q1.metric("Music Diversity", qm.get("song", {}).get("diversity", 0.0))
        q2.metric("Movie Diversity", qm.get("movie", {}).get("diversity", 0.0))
        q3.metric("Series Diversity", qm.get("series", {}).get("diversity", 0.0))
        q4.metric("Catalog Coverage", qm.get("catalog_coverage", 0.0))
        st.caption(
            "Diversity = `1 - avg pairwise cosine similarity` (higher means less repetitive recommendations). "
            "Supervised Precision@K/Recall@K require explicit held-out ground-truth labels (see `docs/recommendation_engine.md`)."
        )
