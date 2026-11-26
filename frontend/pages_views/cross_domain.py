"""Module 6 — Cross-Domain Recommendation Engine."""

import streamlit as st

from frontend.components.cards import render_content_card
from frontend.services.api_client import APIClientError, VibeVerseAPIClient

PATHWAY_LABELS = {
    "music_to_movies": ("🎵 Music → 🎬 Movies", "song", "Pick optional seed songs"),
    "music_to_series": ("🎵 Music → 📺 Web Series", "song", "Pick optional seed songs"),
    "movies_to_music": ("🎬 Movies → 🎵 Music", "movie", "Pick optional seed movies"),
    "series_to_music": ("📺 Web Series → 🎵 Music", "series", "Pick optional seed web series"),
}


def render_cross_domain(client: VibeVerseAPIClient, session_id: str) -> None:
    """Render Cross-Domain Pathways, Discovery Chain, and Your Unexpected Vibe."""
    st.markdown("## 🔀 Cross-Domain Discovery Engine")
    st.caption(
        "The heart of VibeVerse AI: connect soundtracks to cinema, series atmospheres to music, "
        "trace full cross-domain discovery chains, and explore 'Your Unexpected Vibe'."
    )

    try:
        meta = client.get_catalog_metadata()
    except APIClientError as exc:
        st.error(str(exc))
        return

    tab_path, tab_chain, tab_unexp = st.tabs(
        ["🧭 Cross-Domain Pathways", "⛓ Music → Movie → Series Chain", "✨ Your Unexpected Vibe"]
    )

    with tab_path:
        pathway = st.selectbox(
            "Select Cross-Domain Pathway",
            options=list(PATHWAY_LABELS.keys()),
            format_func=lambda k: PATHWAY_LABELS[k][0],
            key="cd_pathway",
        )
        _, seed_domain, seed_prompt = PATHWAY_LABELS[pathway]
        seed_options = meta.get("titles_by_type", {}).get(seed_domain, [])
        seed_titles = st.multiselect(
            f"{seed_prompt} (leave empty to use your active profile & liked items)",
            options=seed_options,
            key="cd_seeds",
        )

        try:
            res = client.cross_domain(session_id, pathway=pathway, seed_titles=seed_titles, limit=8)
            st.success(f"Seed Vibe Anchor: **{', '.join(res.get('seed_items', [])) or 'Profile Preferences'}**")
            if res.get("language_notice"):
                st.warning(res["language_notice"])
            for item in res.get("recommendations", []):
                render_content_card(client, session_id, item, key_prefix=f"cd_{pathway}")
        except APIClientError as exc:
            st.error(str(exc))

    with tab_chain:
        st.markdown("### ⛓ Algorithmic Cross-Domain Discovery Chain")
        st.caption("Traces a real shared-vibe path: Music Seed → Mood Bridge → Resonant Movie → Aligned Series → Companion Soundtrack.")
        chain_seeds = st.multiselect(
            "Choose starting song(s) for your chain (optional)",
            options=meta.get("titles_by_type", {}).get("song", []),
            key="cd_chain_seeds",
        )
        try:
            chain = client.discovery_chain(session_id, seed_titles=chain_seeds)
            bridge = chain.get("shared_mood_bridge", [])
            if bridge:
                st.info(f"🔗 Shared Mood Bridge: **{', '.join(bridge)}**")
            for step in chain.get("steps", []):
                st.markdown(f"#### {step['stage']}")
                if step.get("item"):
                    render_content_card(client, session_id, step["item"], key_prefix=f"chain_{step['stage'][:1]}")
                else:
                    st.caption("No matching item available for this step under current filters.")
        except APIClientError as exc:
            st.error(str(exc))

    with tab_unexp:
        st.markdown("### ✨ Your Unexpected Vibe")
        st.caption(
            "Controlled exploration: surfaces genres you haven't picked yet that still share deep "
            "emotional tone, mood, and atmospheric similarity with your profile."
        )
        try:
            unexp = client.unexpected_vibe(session_id, limit=6)
            items = unexp.get("items", [])
            if not items:
                st.info("You have already explored almost every genre in the catalog! Try resetting or narrowing preferences to discover fresh contrasts.")
            for item in items:
                render_content_card(client, session_id, item, key_prefix="cd_unexp")
        except APIClientError as exc:
            st.error(str(exc))
