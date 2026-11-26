"""Custom Dark-Neon Gen-Z CSS theme for VibeVerse AI."""

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

:root {
    --vv-bg: #07070D;
    --vv-surface: rgba(18, 18, 30, 0.82);
    --vv-surface-hover: rgba(26, 26, 44, 0.94);
    --vv-border: rgba(255, 255, 255, 0.09);
    --vv-purple: #9D4EDD;
    --vv-pink: #FF2A85;
    --vv-cyan: #00F5D4;
    --vv-lime: #B5FF4D;
    --vv-text: #F4F4F9;
    --vv-muted: #A2A6B8;
}

/* Global Dark Canvas */
.stApp {
    background:
        radial-gradient(circle at 12% 15%, rgba(157, 78, 221, 0.16), transparent 36%),
        radial-gradient(circle at 88% 12%, rgba(0, 245, 212, 0.11), transparent 34%),
        radial-gradient(circle at 75% 85%, rgba(255, 42, 133, 0.10), transparent 38%),
        var(--vv-bg);
    color: var(--vv-text);
    font-family: 'Plus Jakarta Sans', sans-serif;
}

h1, h2, h3, h4, .vv-heading {
    font-family: 'Space Grotesk', sans-serif !important;
    letter-spacing: -0.02em;
    color: var(--vv-text) !important;
}

/* Hide Streamlit chrome clutter */
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] {
    background: rgba(7, 7, 13, 0.65);
    backdrop-filter: blur(10px);
}

/* Sidebar Styling */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0C0C16 0%, #090911 100%);
    border-right: 1px solid rgba(157, 78, 221, 0.22);
}
section[data-testid="stSidebar"] .stRadio > div {
    gap: 0.35rem;
}
section[data-testid="stSidebar"] label[data-baseweb="radio"] {
    background: rgba(255, 255, 255, 0.03);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 12px;
    padding: 0.45rem 0.75rem;
    transition: all 0.2s ease;
}
section[data-testid="stSidebar"] label[data-baseweb="radio"]:hover {
    border-color: rgba(0, 245, 212, 0.45);
    background: rgba(157, 78, 221, 0.12);
}

/* Hero Banner */
.vv-hero {
    position: relative;
    overflow: hidden;
    border-radius: 24px;
    padding: 2.5rem 2.4rem;
    background:
        linear-gradient(135deg, rgba(157, 78, 221, 0.28) 0%, rgba(18, 18, 32, 0.92) 52%, rgba(0, 245, 212, 0.16) 100%);
    border: 1px solid rgba(157, 78, 221, 0.38);
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.55), inset 0 1px 0 rgba(255, 255, 255, 0.12);
    margin-bottom: 1.5rem;
}
.vv-hero-badge {
    display: inline-block;
    padding: 0.3rem 0.85rem;
    border-radius: 999px;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background: rgba(0, 245, 212, 0.14);
    color: var(--vv-cyan);
    border: 1px solid rgba(0, 245, 212, 0.38);
    margin-bottom: 0.85rem;
}
.vv-hero-title {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 2.85rem;
    font-weight: 700;
    line-height: 1.08;
    margin: 0 0 0.55rem 0;
    background: linear-gradient(90deg, #FFFFFF 0%, #E0AAFF 48%, #00F5D4 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.vv-hero-tagline {
    font-family: 'Space Grotesk', sans-serif;
    font-size: 1.2rem;
    font-weight: 600;
    color: #FF75B5;
    margin-bottom: 0.75rem;
}
.vv-hero-desc {
    color: #D2D5E6;
    font-size: 0.98rem;
    max-width: 720px;
    line-height: 1.55;
    margin-bottom: 0;
}

/* Soundwave bars */
.vv-wave {
    display: flex;
    align-items: flex-end;
    gap: 5px;
    height: 36px;
    margin-top: 1.15rem;
}
.vv-wave span {
    display: inline-block;
    width: 5px;
    border-radius: 999px;
    background: linear-gradient(180deg, #00F5D4, #9D4EDD, #FF2A85);
    opacity: 0.85;
}

/* Glass Panels & Quick Cards */
.vv-glass {
    background: var(--vv-surface);
    border: 1px solid var(--vv-border);
    border-radius: 18px;
    padding: 1.15rem 1.25rem;
    backdrop-filter: blur(14px);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
    transition: transform 0.2s ease, border-color 0.2s ease;
}
.vv-glass:hover {
    border-color: rgba(157, 78, 221, 0.45);
}

/* Recommendation Cards by Domain */
.vv-card {
    background: rgba(16, 16, 27, 0.88);
    border-radius: 20px;
    padding: 1rem 1.1rem;
    border: 1px solid rgba(255, 255, 255, 0.08);
    box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45);
    margin-bottom: 0.65rem;
}
.vv-card-song { border-top: 3px solid #9D4EDD; }
.vv-card-movie { border-top: 3px solid #FF2A85; }
.vv-card-series { border-top: 3px solid #00F5D4; }

.vv-pill {
    display: inline-block;
    padding: 0.18rem 0.58rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 600;
    margin: 0.15rem 0.22rem 0.15rem 0;
    background: rgba(255, 255, 255, 0.06);
    color: #E5E7F2;
    border: 1px solid rgba(255, 255, 255, 0.10);
}
.vv-pill-song { background: rgba(157, 78, 221, 0.18); border-color: rgba(157, 78, 221, 0.45); color: #E0AAFF; }
.vv-pill-movie { background: rgba(255, 42, 133, 0.16); border-color: rgba(255, 42, 133, 0.45); color: #FF85B8; }
.vv-pill-series { background: rgba(0, 245, 212, 0.14); border-color: rgba(0, 245, 212, 0.42); color: #64FFEA; }
.vv-pill-lang { background: rgba(181, 255, 77, 0.12); border-color: rgba(181, 255, 77, 0.36); color: #D4FF8A; }
.vv-pill-score {
    background: linear-gradient(90deg, rgba(157, 78, 221, 0.32), rgba(0, 245, 212, 0.28));
    border-color: rgba(0, 245, 212, 0.55);
    color: #FFFFFF;
    font-family: 'Space Grotesk', sans-serif;
}

.vv-why-box {
    background: rgba(157, 78, 221, 0.09);
    border-left: 3px solid #9D4EDD;
    border-radius: 0 12px 12px 0;
    padding: 0.65rem 0.85rem;
    margin-top: 0.6rem;
    font-size: 0.84rem;
    color: #E2E4F0;
}

/* Primary Buttons */
div.stButton > button {
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.14);
    background: rgba(24, 24, 38, 0.9);
    color: #F4F4F9;
    font-weight: 600;
    transition: all 0.18s ease;
}
div.stButton > button:hover {
    border-color: #00F5D4;
    box-shadow: 0 0 14px rgba(0, 245, 212, 0.24);
    transform: translateY(-1px);
}
div.stButton > button[kind="primary"] {
    background: linear-gradient(90deg, #9D4EDD 0%, #FF2A85 100%);
    border: none;
    color: #FFFFFF;
}
div.stButton > button[kind="primary"]:hover {
    box-shadow: 0 0 20px rgba(255, 42, 133, 0.45);
}

/* Metrics & Expanders */
div[data-testid="stMetric"] {
    background: rgba(18, 18, 30, 0.78);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 16px;
    padding: 0.85rem 1rem;
}
</style>
"""


def inject_theme() -> None:
    """Inject VibeVerse AI custom CSS into Streamlit."""
    import streamlit as st

    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
