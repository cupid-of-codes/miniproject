"""Frontend session, artwork fallback, and Plotly styling utilities."""

import base64
import html
import uuid
from typing import Any, Dict

import plotly.graph_objects as go
import streamlit as st

DOMAIN_COLORS = {
    "song": ("#9D4EDD", "#3C096C", "SONG"),
    "movie": ("#FF2A85", "#590D22", "MOVIE"),
    "series": ("#00F5D4", "#0B3954", "WEB SERIES"),
}


def get_session_id() -> str:
    """Return persistent anonymous session UUID synchronized with URL query params."""
    if "vv_session_id" not in st.session_state:
        query_sid = st.query_params.get("session")
        if query_sid and isinstance(query_sid, str) and len(query_sid) >= 8:
            st.session_state["vv_session_id"] = query_sid[:64]
        else:
            new_sid = f"vv_{uuid.uuid4().hex[:16]}"
            st.session_state["vv_session_id"] = new_sid
            st.query_params["session"] = new_sid
    return st.session_state["vv_session_id"]


def build_fallback_artwork_uri(item: Dict[str, Any]) -> str:
    """Create a sleek inline SVG poster/album fallback data URI when no external artwork exists."""
    ctype = item.get("content_type", "song")
    c1, c2, badge = DOMAIN_COLORS.get(ctype, ("#9D4EDD", "#141428", "VIBE"))
    title = html.escape(item.get("title", "VibeVerse"))[:26]
    lang = html.escape(item.get("language", ""))
    year = html.escape(str(item.get("release_year") or ""))
    initials = "".join(word[0].upper() for word in item.get("title", "V").split()[:2]) or "VV"

    svg = f"""<svg xmlns='http://www.w3.org/2000/svg' width='360' height='220' viewBox='0 0 360 220'>
      <defs>
        <linearGradient id='g' x1='0%' y1='0%' x2='100%' y2='100%'>
          <stop offset='0%' stop-color='{c2}'/>
          <stop offset='60%' stop-color='#121224'/>
          <stop offset='100%' stop-color='{c1}' stop-opacity='0.65'/>
        </linearGradient>
      </defs>
      <rect width='360' height='220' rx='18' fill='url(#g)'/>
      <circle cx='300' cy='46' r='58' fill='{c1}' fill-opacity='0.18'/>
      <circle cx='54' cy='180' r='44' fill='{c1}' fill-opacity='0.14'/>
      <text x='24' y='38' fill='{c1}' font-family='Arial, sans-serif' font-size='12' font-weight='700' letter-spacing='2'>{badge} · {lang}</text>
      <text x='24' y='125' fill='#FFFFFF' fill-opacity='0.18' font-family='Arial, sans-serif' font-size='72' font-weight='800'>{html.escape(initials)}</text>
      <text x='24' y='175' fill='#FFFFFF' font-family='Arial, sans-serif' font-size='20' font-weight='700'>{title}</text>
      <text x='24' y='198' fill='#B8BCD0' font-family='Arial, sans-serif' font-size='12'>{year}</text>
    </svg>"""
    encoded = base64.b64encode(svg.encode("utf-8")).decode("ascii")
    return f"data:image/svg+xml;base64,{encoded}"


def apply_dark_plotly_theme(fig: go.Figure, title: str = "", height: int = 380) -> go.Figure:
    """Apply consistent dark-neon styling to Plotly charts."""
    fig.update_layout(
        title=dict(text=title, font=dict(family="Space Grotesk, sans-serif", size=17, color="#F4F4F9")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(16, 16, 28, 0.65)",
        font=dict(family="Plus Jakarta Sans, sans-serif", color="#D2D5E6", size=12),
        height=height,
        margin=dict(l=30, r=25, t=52, b=35),
        legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#D2D5E6")),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.1)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.07)", zerolinecolor="rgba(255,255,255,0.1)")
    return fig
