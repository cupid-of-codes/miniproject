"""Reusable Gen-Z recommendation card & interactive feedback components."""

import html
from typing import Any, Dict

import streamlit as st

from frontend.services.api_client import APIClientError, VibeVerseAPIClient
from frontend.utils.helpers import build_fallback_artwork_uri


def _talent_line(item: Dict[str, Any]) -> str:
    extra = item.get("extra_metadata") or {}
    ctype = item.get("content_type", "song")
    if ctype == "song":
        artist = extra.get("artist") or "Independent Artist"
        album = extra.get("album")
        return f"🎤 {artist}" + (f" · 💿 {album}" if album else "")
    if ctype == "movie":
        director = extra.get("director")
        runtime = extra.get("runtime_min")
        parts = []
        if director:
            parts.append(f"🎬 {director}")
        if runtime:
            parts.append(f"⏱ {runtime} min")
        return " · ".join(parts) if parts else "🎬 Feature Film"
    creator = extra.get("creator")
    seasons = extra.get("seasons")
    pacing = extra.get("pacing")
    parts = []
    if creator:
        parts.append(f"📺 {creator}")
    if seasons:
        parts.append(f"{seasons} Season{'s' if seasons > 1 else ''}")
    if pacing:
        parts.append(str(pacing).replace("_", " ").title())
    return " · ".join(parts) if parts else "📺 Web Series"


def render_content_card(
    client: VibeVerseAPIClient,
    session_id: str,
    item: Dict[str, Any],
    key_prefix: str,
    show_remove_saved: bool = False,
) -> None:
    """Render a domain-styled recommendation/discovery card with feedback & explainability."""
    ctype = item.get("content_type", "song")
    card_cls = f"vv-card vv-card-{ctype}"
    pill_cls = f"vv-pill vv-pill-{ctype}"
    domain_label = {"song": "SONG", "movie": "MOVIE", "series": "WEB SERIES"}.get(ctype, "ITEM")

    artwork = item.get("artwork_url") or build_fallback_artwork_uri(item)
    title_esc = html.escape(item.get("title", "Untitled"))
    lang_esc = html.escape(item.get("language", ""))
    year_str = f" · {item['release_year']}" if item.get("release_year") else ""
    talent_esc = html.escape(_talent_line(item))
    desc_esc = html.escape(item.get("description", ""))

    genre_pills = "".join(
        f"<span class='vv-pill'>{html.escape(g)}</span>" for g in item.get("genres", [])[:4]
    )
    mood_pills = "".join(
        f"<span class='vv-pill {pill_cls}'>{html.escape(m)}</span>"
        for m in item.get("mood_tags", [])[:4]
    )

    score_pill = ""
    if item.get("match_score") is not None:
        score_pill = f"<span class='vv-pill vv-pill-score'>⚡ {item['match_score']}% Vibe Match</span>"

    rating_pill = ""
    if item.get("rating") is not None:
        rating_pill = f"<span class='vv-pill'>⭐ {round(float(item['rating']), 1)}/10</span>"

    extra = item.get("extra_metadata") or {}
    music_est_pill = ""
    if ctype == "song" and extra.get("music_analysis"):
        ma = extra["music_analysis"]
        music_est_pill = (
            f"<span class='vv-pill' title='Model-generated estimate from metadata'>"
            f"🎛 Est: {html.escape(str(ma.get('inferred_style', '')).title())} · "
            f"{html.escape(str(ma.get('inferred_energy', '')).title())}</span>"
        )

    explanation = item.get("explanation") or {}
    why_html = ""
    if explanation.get("reasons"):
        why_lines = "<br/>".join(f"• {html.escape(r)}" for r in explanation["reasons"][:3])
        why_html = f"<div class='vv-why-box'><strong>Why This Is Your Vibe:</strong><br/>{why_lines}</div>"

    with st.container():
        st.markdown(f"<div class='{card_cls}'>", unsafe_allow_html=True)
        col_img, col_body = st.columns([1, 2.6], gap="medium")
        with col_img:
            st.image(artwork, use_container_width=True)
        with col_body:
            st.markdown(
                f"""
                <div>
                    <span class='vv-pill {pill_cls}'>{domain_label}</span>
                    <span class='vv-pill vv-pill-lang'>{lang_esc}{year_str}</span>
                    {score_pill}
                    {rating_pill}
                    {music_est_pill}
                </div>
                <h4 style='margin:0.35rem 0 0.2rem 0;'>{title_esc}</h4>
                <div style='color:#A2A6B8; font-size:0.85rem; margin-bottom:0.45rem;'>{talent_esc}</div>
                <div style='margin-bottom:0.4rem;'>{genre_pills} {mood_pills}</div>
                <p style='color:#D8DBE8; font-size:0.9rem; line-height:1.45; margin-bottom:0.4rem;'>{desc_esc}</p>
                {why_html}
                """,
                unsafe_allow_html=True,
            )

        content_id = item.get("id")
        if content_id is not None:
            btn_cols = st.columns(7 if show_remove_saved else 6)
            actions = [
                ("👍 Like", "like"),
                ("👎 Dislike", "dislike"),
                ("💾 Save", "save"),
                ("✨ More", "more_like_this"),
                ("➖ Less", "less_like_this"),
                ("🚫 Hide", "not_interested"),
            ]
            for col, (label, fb_type) in zip(btn_cols[:6], actions):
                with col:
                    if st.button(label, key=f"{key_prefix}_{content_id}_{fb_type}", use_container_width=True):
                        try:
                            client.submit_feedback(session_id, int(content_id), fb_type)
                            st.toast(f"Recorded '{label}' for {item.get('title')} — updating your vibe!")
                            st.rerun()
                        except APIClientError as exc:
                            st.error(str(exc))

            if show_remove_saved:
                with btn_cols[6]:
                    if st.button("🗑 Remove", key=f"{key_prefix}_{content_id}_rm", use_container_width=True):
                        try:
                            client.delete_saved(session_id, int(content_id))
                            st.toast(f"Removed {item.get('title')} from Saved Discoveries.")
                            st.rerun()
                        except APIClientError as exc:
                            st.error(str(exc))

        with st.expander("🔍 Full Metadata & Source Attribution"):
            meta_col1, meta_col2 = st.columns(2)
            with meta_col1:
                st.write("**Themes:**", ", ".join(item.get("themes", [])) or "N/A")
                if extra.get("cast"):
                    st.write("**Cast:**", ", ".join(extra["cast"]) if isinstance(extra["cast"], list) else extra["cast"])
                if extra.get("storytelling_style"):
                    st.write("**Storytelling Style:**", extra["storytelling_style"])
            with meta_col2:
                st.write("**Source:**", item.get("source", "local_dataset"))
                st.write("**Retrieved At:**", item.get("retrieved_at") or "Local Dataset Snapshot")
                if extra.get("music_analysis"):
                    st.caption(extra["music_analysis"].get("estimation_basis", ""))

        st.markdown("</div>", unsafe_allow_html=True)
