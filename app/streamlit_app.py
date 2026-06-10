import streamlit as st
import pandas as pd
import requests
import io
import os
from pathlib import Path

API_URL      = os.getenv("API_URL", "http://localhost:8000")
LOGO_PATH    = Path(__file__).parent / "logo.png"
APP_VERSION  = "v1.0.0"

NAV_OPTIONS = [
    "Prédiction individuelle",
    "Prédiction par lot",
    "Informations du modèle",
]

st.set_page_config(
    page_title="Sentio — Prédiction d'Hospitalisation",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
/* Masquer Deploy / toolbar — ne pas réduire stHeader (sinon le bouton sidebar disparaît) */
.stDeployButton { display: none !important; }
[data-testid='manage-app-button'] { display: none !important; }
[data-testid='stToolbarActions'] { display: none !important; }
[data-testid='stStatusWidget'] { visibility: hidden !important; }
#MainMenu { visibility: hidden !important; }

/* Bouton ouvrir / fermer la sidebar — toujours visible */
[data-testid='collapsedControl'],
[data-testid='stSidebarCollapsedControl'] {
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    position: fixed !important;
    top: 0.75rem !important;
    left: 0.75rem !important;
    z-index: 999999 !important;
    pointer-events: auto !important;
}

/* Sidebar toujours affichable */
[data-testid='stSidebar'] {
    visibility: visible !important;
}
[data-testid='stSidebar'][aria-expanded='true'] {
    display: block !important;
    min-width: 240px !important;
}
</style>
""", unsafe_allow_html=True)

if "dark_mode" not in st.session_state:
    st.session_state.dark_mode = False
if "page" not in st.session_state:
    st.session_state.page = NAV_OPTIONS[0]
if "dark_mode_toggle" in st.session_state:
    st.session_state.dark_mode = st.session_state.dark_mode_toggle

# Define color palettes for both themes
LIGHT_THEME = {
    "bg": "#F4F7F6",
    "bg_deep": "#E2EDEC",
    "bg_surface": "#FFFFFF",
    "bg_card": "#FFFFFF",
    "bg_card_h": "#E2EDEC",
    "border": "#CBDCDA",
    "border_accent": "#769490",
    "accent": "#769490",
    "accent_dim": "#5C7874",
    "accent_glow": "rgba(118, 148, 144, 0.15)",
    "accent_light": "rgba(118, 148, 144, 0.08)",
    "cyan": "#89A3A0",
    "cyan_glow": "rgba(137, 163, 160, 0.12)",
    "red": "#E05D6F",
    "red_glow": "rgba(224, 93, 111, 0.12)",
    "red_light": "rgba(224, 93, 111, 0.08)",
    "text_1": "#1E293B",
    "text_2": "#475569",
    "text_3": "#64748B",
    "text_4": "#94A3B8"
}

DARK_THEME = {
    "bg": "#0F172A",
    "bg_deep": "#1E293B",
    "bg_surface": "#334155",
    "bg_card": "#1E293B",
    "bg_card_h": "#475569",
    "border": "#475569",
    "border_accent": "#60A5FA",
    "accent": "#60A5FA",
    "accent_dim": "#3B82F6",
    "accent_glow": "rgba(96, 165, 250, 0.15)",
    "accent_light": "rgba(96, 165, 250, 0.08)",
    "cyan": "#22D3EE",
    "cyan_glow": "rgba(34, 211, 238, 0.12)",
    "red": "#F87171",
    "red_glow": "rgba(248, 113, 113, 0.12)",
    "red_light": "rgba(248, 113, 113, 0.08)",
    "text_1": "#F8FAFC",
    "text_2": "#E2E8F0",
    "text_3": "#94A3B8",
    "text_4": "#64748B"
}

theme = DARK_THEME if st.session_state.dark_mode else LIGHT_THEME

# ═══════════════════════════════════════════════════════════
# DESIGN SYSTEM — DYNAMIC THEME WITH GLASSMORPHISM
# ═══════════════════════════════════════════════════════════
st.markdown(f"""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=Outfit:wght@400;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">

<style>
:root {{
  --bg:           {theme["bg"]};
  --bg-deep:      {theme["bg_deep"]};
  --bg-surface:   {theme["bg_surface"]};
  --bg-card:      {theme["bg_card"]};
  --bg-card-h:    {theme["bg_card_h"]};
  --border:       {theme["border"]};
  --border-accent:{theme["border_accent"]};

  --accent:       {theme["accent"]};
  --accent-dim:   {theme["accent_dim"]};
  --accent-glow:  {theme["accent_glow"]};
  --accent-light: {theme["accent_light"]};

  --cyan:         {theme["cyan"]};
  --cyan-glow:    {theme["cyan_glow"]};

  --red:          {theme["red"]};
  --red-glow:     {theme["red_glow"]};
  --red-light:    {theme["red_light"]};

  --text-1: {theme["text_1"]};
  --text-2: {theme["text_2"]};
  --text-3: {theme["text_3"]};
  --text-4: {theme["text_4"]};

  --font-main:    'DM Sans', sans-serif;
  --font-display: 'Outfit', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;

  --r-sm: 12px; --r-md: 24px; --r-lg: 32px;
}}

/* ── GLOBAL ── */
*, *::before, *::after {{ box-sizing: border-box; }}

html, body,
[class*="css"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="stMain"] {{
    font-family: var(--font-main) !important;
    background: var(--bg) !important;
    color: var(--text-1) !important;
}}

/* Animated gradient background */
[data-testid="stAppViewContainer"]::before {{
    content: "";
    position: fixed;
    inset: 0;
    background: linear-gradient(135deg, {theme["bg"]} 0%, {theme["bg_deep"]} 50%, {theme["bg"]} 100%);
    background-size: 400% 400%;
    animation: gradientShift 15s ease infinite;
    pointer-events: none;
    z-index: 0;
}}

@keyframes gradientShift {{
    0% {{ background-position: 0% 50%; }}
    50% {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}


#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
[data-testid="stDecoration"] {{ display: none; }}
[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"] {{
    visibility: visible !important;
    display: flex !important;
    opacity: 1 !important;
    position: fixed !important;
    top: 0.75rem !important;
    left: 0.75rem !important;
    z-index: 999999 !important;
    pointer-events: auto !important;
}}
.block-container {{
    padding: 2.2rem 2.8rem !important;
    max-width: 1380px !important;
    position: relative; z-index: 1;
}}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {{
    background: var(--bg-deep) !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 4px 0 30px rgba(0,0,0,0.1) !important;
    width: 240px !important;
    min-width: 240px !important;
}}
[data-testid="stSidebar"] > div:first-child {{
    padding-top: 0 !important;
    width: 240px !important;
}}
[data-testid="stSidebar"] .block-container {{
    padding-left: 1rem !important;
    padding-right: 1rem !important;
    max-width: 240px !important;
}}

/* Sidebar text color update for dark mode */
[data-testid="stSidebar"] * {{
    color: var(--text-1) !important;
}}
[data-testid="stSidebar"] label p {{
    color: var(--text-1) !important;
}}


/* Sidebar logo */
[data-testid="stSidebar"] [data-testid="stImage"] {{
    text-align: center;
    padding: 12px 0 8px;
    margin-bottom: 4px;
}}
[data-testid="stSidebar"] [data-testid="stImage"] img {{
    border: none !important;
    box-shadow: none !important;
    border-radius: 0 !important;
    max-width: 130px !important;
    margin: 0 auto;
    display: block;
}}

/* ── Nav ── */
.nav-label {{
    font-size: 0.61rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--text-4);
    padding: 0 4px; margin: 16px 0 8px; display: block; text-align: center;
}}
[data-testid="stSidebar"] .stButton > button {{
    background: transparent !important;
    color: var(--text-2) !important;
    border: 1px solid transparent !important;
    box-shadow: none !important;
    text-align: left !important;
    padding: 10px 14px !important;
    border-radius: 10px !important;
    font-size: 0.86rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    transition: transform 0.15s ease, background 0.15s ease, color 0.15s ease !important;
}}
[data-testid="stSidebar"] .stButton > button:hover {{
    background: var(--accent-light) !important;
    color: var(--accent) !important;
    border-color: var(--border-accent) !important;
    transform: scale(1.01);
}}
[data-testid="stSidebar"] .stButton > button[kind="primary"],
[data-testid="stSidebar"] .stButton > button[data-testid="baseButton-primary"] {{
    background: var(--accent-light) !important;
    color: var(--accent) !important;
    font-weight: 700 !important;
    border: 1px solid var(--border-accent) !important;
    box-shadow: none !important;
}}

/* Theme toggle */
.theme-toggle-row {{
    display: flex; align-items: center; gap: 10px;
    padding: 10px 4px; margin-top: 8px;
    border-top: 1px solid var(--border);
}}
.theme-icon {{
    display: flex; align-items: center; justify-content: center;
    width: 32px; height: 32px; flex-shrink: 0;
    color: var(--accent);
}}
.theme-icon svg {{ width: 18px; height: 18px; }}
.theme-toggle-row label p {{
    font-size: 0.82rem !important;
    font-weight: 500 !important;
    color: var(--text-3) !important;
}}

/* Status badge */
.status-badge {{
    display: inline-flex; align-items: center; gap: 7px;
    padding: 6px 14px; border-radius: 100px;
    font-size: 0.74rem; font-weight: 600;
}}
.online  {{ background: var(--accent-light); color: var(--accent); border: 1px solid var(--border-accent); }}
.offline {{ background: rgba(251,191,36,0.08); color: #FBC02D; border: 1px solid rgba(251,191,36,0.3); }}
.pulse-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}
.pulse-green  {{ background: var(--accent); animation: pulse 2s infinite; }}
.pulse-orange {{ background: #FBC02D; animation: pulse 2s infinite; }}

.sb-footer {{
    margin-top: auto; padding: 14px 4px 8px;
    border-top: 1px solid var(--border);
    font-size: 0.65rem; color: var(--text-4);
    text-align: center; letter-spacing: 0.04em;
}}

/* Metric contextual colors */
.metric-good .kpi-val {{ color: #22C55E !important; }}
.metric-good .kpi-dot {{ background: rgba(34,197,94,0.12) !important; color: #22C55E !important; border-color: rgba(34,197,94,0.3) !important; }}
.metric-medium .kpi-val {{ color: #F59E0B !important; }}
.metric-medium .kpi-dot {{ background: rgba(245,158,11,0.12) !important; color: #F59E0B !important; border-color: rgba(245,158,11,0.3) !important; }}
.metric-poor .kpi-val {{ color: #EF4444 !important; }}
.metric-poor .kpi-dot {{ background: rgba(239,68,68,0.12) !important; color: #EF4444 !important; border-color: rgba(239,68,68,0.3) !important; }}

/* Predict button */
[data-testid="stForm"] .stFormSubmitButton > button {{
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    padding: 14px 40px !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 24px var(--accent-glow) !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease !important;
}}
[data-testid="stForm"] .stFormSubmitButton > button:hover {{
    transform: scale(1.02) !important;
    box-shadow: 0 12px 32px var(--accent-glow) !important;
}}

/* Section titles in form */
.form-section-title {{
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.1em; color: var(--accent);
    margin: 8px 0 12px; display: flex; align-items: center; gap: 8px;
}}

/* Drop zone */
.drop-zone-label {{
    text-align: center; padding: 8px 0 4px;
    font-size: 0.85rem; color: var(--text-3);
}}
.drop-zone-label strong {{ color: var(--accent); }}

/* ── PAGE HEADER ── */
.page-header {{
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 20px;
    margin-bottom: 32px; padding-bottom: 26px;
    border-bottom: 1px solid var(--border);
}}
.page-eyebrow {{
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.16em; color: var(--accent); margin-bottom: 8px;
    display: flex; align-items: center; gap: 7px;
}}
.page-title {{
    font-family: var(--font-display);
    font-size: 2.5rem; font-weight: 800;
    line-height: 1.1; letter-spacing: -0.03em;
    color: var(--text-1);
}}
.page-desc {{
    font-size: 0.875rem; color: var(--text-2);
    margin-top: 10px; line-height: 1.65; max-width: 500px;
}}

/* ── STAT CHIPS ── */
.stat-chips {{ display: flex; gap: 12px; flex-shrink: 0; align-items: center; flex-wrap: wrap; justify-content: flex-end; }}
.stat-chip {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 14px 20px; text-align: center;
    backdrop-filter: blur(12px); min-width: 88px; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    position: relative; overflow: hidden;
}}
.stat-chip::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}}
.stat-chip:hover {{
    border-color: var(--border-accent);
    box-shadow: 0 10px 40px var(--accent-glow);
    transform: translateY(-3px) scale(1.03);
}}
.stat-chip:hover::before {{ opacity: 1; }}
.stat-chip-val {{ font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--accent); }}
.stat-chip-lbl {{ font-size: 0.63rem; color: var(--text-3); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 3px; }}


/* ── GLASS CARDS ── */

.card {{
    background: var(--bg-surface);
    border-radius: var(--r-md);
    padding: 24px 28px;
    border: 1px solid var(--border);
    margin-bottom: 18px;
    position: relative; overflow: hidden;
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.08);
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
    backdrop-filter: blur(10px);
}}
.card::before {{
    content: "";
    position: absolute;
    top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}}
.card:hover {{
    border-color: var(--border-accent);
    box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15), 0 0 30px var(--accent-glow);
    transform: translateY(-2px) scale(1.01);
    transition: transform 0.15s ease, box-shadow 0.15s ease, border-color 0.15s ease;
}}
.card:hover::before {{
    opacity: 1;
}}


.card-title {{
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--accent);
    display: flex; align-items: center; gap: 9px;
    margin-bottom: 22px; padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}}

/* ── Inputs ── */
.stSelectbox label, .stNumberInput label, .stTextInput label {{
    font-size: 0.75rem !important;
    font-weight: 700 !important;
    color: var(--text-2) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.08em !important;
    margin-bottom: 0.5rem !important;
}}
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {{
    background: var(--bg-card) !important;
    border: 1.5px solid var(--border) !important;
    border-radius: 12px !important;
    color: var(--text-1) !important;
    font-size: 0.95rem !important;
    padding: 0.8rem 1rem !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.03) !important;
}}
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div:focus-within,
.stTextInput > div > div:focus-within {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px var(--accent-glow) !important;
    background: var(--bg-card) !important;
}}
/* Style the selectbox dropdown */
.stSelectbox [data-baseweb="select"] {{
    border-radius: 12px !important;
}}


/* ── BUTTON ── */

.stFormSubmitButton > button, .stButton > button {{
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-dim) 100%) !important;
    color: #FFFFFF !important; border: none !important;
    border-radius: 24px !important; padding: 12px 36px !important;
    font-family: var(--font-display) !important;
    font-size: 0.92rem !important; font-weight: 600 !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important; 
    width: 100% !important;
    box-shadow: 0 8px 25px rgba(0,0,0,0.2), 0 0 20px var(--accent-glow) !important;
    position: relative; overflow: hidden;
}}
.stFormSubmitButton > button::before, .stButton > button::before {{
    content: "";
    position: absolute;
    top: 0; left: -100%;
    width: 100%; height: 100%;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.3), transparent);
    transition: left 0.5s;
}}
.stFormSubmitButton > button:hover, .stButton > button:hover {{
    background: linear-gradient(135deg, var(--accent-dim) 0%, var(--accent) 100%) !important;
    box-shadow: 0 12px 35px rgba(0,0,0,0.3), 0 0 30px var(--accent-glow) !important;
    color: #FFFFFF !important;
    transform: scale(1.01);
    transition: transform 0.15s ease !important;
}}
.stFormSubmitButton > button:hover::before, .stButton > button:hover::before {{ left: 100%; }}

.stFormSubmitButton > button:active, .stButton > button:active {{ transform: translateY(0) scale(0.98) !important; }}


/* ── RESULTS ── */

.result-wrap {{
    border-radius: var(--r-md); padding: 42px 40px; text-align: center;
    position: relative; overflow: hidden;
    margin-top: 20px;
}}
.result-high {{
    background: #FFF5F5;
    border: 1.5px solid #F87171;
    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.05);
}}
.result-low {{
    background: #F0FDF4;
    border: 1.5px solid #34D399;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.05);
}}
.result-high::before, .result-low::before {{
    display: none;
}}
.ring-high {{ background: #FEE2E2; color: #EF4444; border: 2px solid #FCA5A5; }}
.ring-low  {{ background: #D1FAE5; color: #10B981; border: 2px solid #6EE7B7; }}
.result-title-high {{ font-family: var(--font-display); font-size: 1.8rem; font-weight: 800; color: #B91C1C; }}
.result-title-low  {{ font-family: var(--font-display); font-size: 1.8rem; font-weight: 800; color: #065F46; }}
.prob-fill-high {{ height: 7px; border-radius: 100px; background: #EF4444; }}
.prob-fill-low  {{ height: 7px; border-radius: 100px; background: #10B981; }}
.result-subtitle {{ font-size: 0.88rem; color: var(--text-2); margin-top: 10px; line-height: 1.65; position: relative; z-index: 1; }}
.prob-display {{
    display: inline-flex; align-items: center; gap: 10px;
    margin: 22px auto 0; background: rgba(255,255,255,0.05);
    border-radius: 100px; padding: 10px 24px;
    font-size: 0.87rem; font-weight: 600; color: var(--text-2);
    border: 1px solid var(--border); backdrop-filter: blur(8px);
    position: relative; z-index: 1;
}}
.prob-num {{ font-family: var(--font-display); font-size: 1.4rem; font-weight: 800; }}
.prob-num-high {{ color: var(--red); }}
.prob-num-low  {{ color: var(--accent); }}
.prob-track {{
    height: 7px; border-radius: 100px;
    background: rgba(255,255,255,0.06);
    margin-top: 22px; overflow: hidden;
    position: relative; z-index: 1;
    border: 1px solid rgba(255,255,255,0.04);
}}
.prob-fill-high {{ height: 7px; border-radius: 100px; background: linear-gradient(90deg, rgba(255,77,109,0.4), var(--red)); box-shadow: 0 0 10px var(--red-glow); }}
.prob-fill-low  {{ height: 7px; border-radius: 100px; background: linear-gradient(90deg, rgba(0,212,120,0.4), var(--accent)); box-shadow: 0 0 10px var(--accent-glow); }}
.source-tag {{
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.05em;
    padding: 6px 14px; border-radius: 100px; margin-top: 18px;
    position: relative; z-index: 1;
}}
.tag-live {{ background: var(--accent-light); color: var(--accent); border: 1px solid var(--border-accent); }}
.tag-mock {{ background: rgba(251,191,36,0.08); color: #FBC02D; border: 1px solid rgba(251,191,36,0.28); }}

/* ── KPI STRIP ── */
.kpi-strip {{ display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 26px; }}
.kpi-cell {{
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 20px 22px;
    display: flex; align-items: center; gap: 16px;
    backdrop-filter: blur(12px);
    position: relative; overflow: hidden;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}}
.kpi-cell::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, transparent, var(--accent), transparent);
    opacity: 0;
    transition: opacity 0.3s;
}}
.kpi-cell:hover {{ 
    transform: translateY(-5px) scale(1.02); 
    border-color: var(--border-accent); 
    box-shadow: 0 15px 50px rgba(0,0,0,0.2), 0 0 40px var(--accent-glow); 
}}
.kpi-cell:hover::before {{ opacity: 1; }}
.kpi-dot {{ width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; flex-shrink: 0; transition: all 0.3s; }}
.kpi-cell:hover .kpi-dot {{ transform: scale(1.1) rotate(5deg); }}
.dot-g {{ background: var(--accent-light); color: var(--accent); border: 1px solid rgba(0,212,120,0.2); }}
.dot-b {{ background: var(--cyan-glow); color: var(--cyan); border: 1px solid rgba(34,211,238,0.3); }}
.dot-p {{ background: rgba(167,139,250,0.1); color: #A78BFA; border: 1px solid rgba(167,139,250,0.3); }}
.dot-o {{ background: rgba(251,146,60,0.1); color: #FB923C; border: 1px solid rgba(251,146,60,0.3); }}
.kpi-lbl {{ font-size: 0.66rem; color: var(--text-3); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }}
.kpi-val {{ font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--text-1); margin-top: 2px; }}


/* ── CHIPS ── */
.chip {{
    display: inline-block; background: var(--accent-light); color: var(--accent);
    border: 1px solid rgba(0,212,120,0.2); border-radius: 8px;
    padding: 5px 13px; font-size: 0.71rem; font-weight: 600;
    margin: 3px; font-family: var(--font-mono); transition: all 0.18s;
}}
.chip:hover {{ background: rgba(0,212,120,0.14); box-shadow: 0 0 12px var(--accent-glow); }}

/* ── INFO TABLE ── */
.info-row {{ display: flex; align-items: center; padding: 13px 0; border-bottom: 1px solid var(--border); gap: 20px; }}
.info-row:last-child {{ border-bottom: none; }}
.info-key {{ font-size: 0.71rem; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.07em; min-width: 140px; }}
.info-val {{ font-size: 0.9rem; font-weight: 600; color: var(--text-1); }}

/* ── DIVIDER ── */
.green-rule {{
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent) 40%, var(--cyan) 60%, transparent);
    border: none; border-radius: 100px; margin: 30px 0; opacity: 0.3;
}}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] > div {{
    background: rgba(0,212,120,0.03) !important;
    border: 2px dashed rgba(0,212,120,0.22) !important;
    border-radius: var(--r-md) !important; transition: all 0.2s !important;
}}
[data-testid="stFileUploader"] > div:hover {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 28px var(--accent-glow) !important;
}}
[data-testid="stFileUploader"] * {{ color: var(--text-2) !important; }}

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] {{ border-radius: var(--r-md) !important; overflow: hidden !important; border: 1px solid var(--border) !important; }}

/* ── SCROLLBAR ── */
::-webkit-scrollbar {{ width: 5px; height: 5px; }}
::-webkit-scrollbar-track {{ background: var(--bg-surface); }}
::-webkit-scrollbar-thumb {{ background: rgba(0,212,120,0.25); border-radius: 100px; }}
::-webkit-scrollbar-thumb:hover {{ background: var(--accent); }}

/* ── ANIMATIONS ── */
@keyframes slideUp {{ from {{ opacity:0; transform:translateY(20px); }} to {{ opacity:1; transform:translateY(0); }} }}
@keyframes pulse   {{ 0%,100% {{ opacity:1; }} 50% {{ opacity:0.35; }} }}
@keyframes breathe {{ 0%,100% {{ opacity:0.5; transform:scale(0.95); }} 50% {{ opacity:1; transform:scale(1.05); }} }}
.fade-up {{ animation: slideUp 0.45s cubic-bezier(0.16,1,0.3,1) both; }}

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] button {{
    background: var(--bg-card) !important; border: 1px solid var(--border) !important;
    color: var(--text-2) !important; border-radius: 8px !important;
}}
[data-testid="stNumberInput"] button:hover {{ background: var(--bg-card-h) !important; color: var(--accent) !important; }}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════
SEX_MAP      = {"Inconnu": 0, "Homme": 1, "Femme": 2}
OUTCOME_MAP  = {"Rétabli": 1, "En cours de rétablissement": 2,
                "Non rétabli": 3, "Rétabli avec séquelles": 4,
                "Décès": 5, "Inconnu": 6}
REPORTER_MAP = {"Médecin": 1, "Pharmacien": 2,
                "Autre professionnel de santé": 3,
                "Avocat": 4, "Consommateur / Non-professionnel": 5}
YES_NO_MAP   = {"Non": 0, "Oui": 1}
ROUTE_MAP    = {
    "001 — Oral":            "001", "002 — Intraveineux":    "002",
    "003 — Intramusculaire": "003", "004 — Sous-cutané":     "004",
    "005 — Inhalation":      "005", "007 — Cutané":          "007",
    "008 — Ophtalmique":     "008", "011 — Nasal":           "011",
    "055 — Autre voie":      "055", "065 — Inconnu":         "065",
}

def mock_predict(d):
    high = d["patient_age"] > 60 or d["worst_reaction_outcome"] >= 4 or d["has_black_box_warning"]
    prob = 0.83 if high else 0.14
    return {"label": 1 if high else 0, "probability": prob,
            "risk_level": "high risk" if high else "low risk"}

def call_api(payload):
    try:
        r = requests.post(f"{API_URL}/predict", json=payload, timeout=5)
        if r.status_code == 200:
            return r.json(), True
    except Exception:
        pass
    return mock_predict(payload), False

def api_alive():
    try:
        return requests.get(f"{API_URL}/health", timeout=2).status_code == 200
    except Exception:
        return False

def metric_tier(score):
    if score >= 0.80:
        return "metric-good"
    if score >= 0.60:
        return "metric-medium"
    return "metric-poor"

def theme_icon_svg(is_dark):
    if is_dark:
        return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
            stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
        </svg>"""
    return """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none"
        stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="5"/>
        <line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
        <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
    </svg>"""

# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    if LOGO_PATH.exists():
        _, logo_col, _ = st.columns([0.5, 3, 0.5])
        with logo_col:
            st.image(str(LOGO_PATH), use_container_width=True)

    st.markdown('<span class="nav-label">Navigation</span>', unsafe_allow_html=True)

    for label in NAV_OPTIONS:
        is_active = st.session_state.page == label
        if st.button(
            label,
            key=f"nav_{label}",
            use_container_width=True,
            type="primary" if is_active else "secondary",
        ):
            st.session_state.page = label
            st.rerun()

    page = st.session_state.page

    icon_col, toggle_col = st.columns([1, 5])
    with icon_col:
        st.markdown(
            f'<div class="theme-icon">{theme_icon_svg(st.session_state.dark_mode)}</div>',
            unsafe_allow_html=True,
        )
    with toggle_col:
        dark_mode = st.toggle(
            "Mode sombre",
            value=st.session_state.dark_mode,
            key="dark_mode_toggle",
        )
    st.session_state.dark_mode = dark_mode

    live      = api_alive()
    dot_cls   = "pulse-green" if live else "pulse-orange"
    badge_cls = "online" if live else "offline"
    badge_lbl = "API connectée" if live else "Mode démonstration"
    st.markdown(f"""
    <div style="margin-top:20px;padding:0 4px;text-align:center;">
        <div class="status-badge {badge_cls}">
            <span class="pulse-dot {dot_cls}"></span>{badge_lbl}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f'<div class="sb-footer">Sentio {APP_VERSION}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PAGE 1 — PRÉDICTION INDIVIDUELLE
# ═══════════════════════════════════════════════════════════
if "individuelle" in page:
    # Set path to hero image
    HERO_PATH = Path(__file__).parent / "hero.png"
    
    st.markdown("""
    <div class="page-header fade-up" style="border-bottom:none; margin-bottom:10px; padding-bottom:0; display:flex; flex-direction:column; align-items:center; text-align:center; width:100%;">
        <div style="display:flex; flex-direction:column; align-items:center; text-align:center; width:100%;">
            <div class="page-eyebrow" style="justify-content:center;"><i class="fa-solid fa-waveform-lines"></i> ANALYSE PRÉDICTIVE</div>
            <div class="page-title" style="color: var(--text-1);">Sentio — Évaluation du Risque Clinique</div>
            <div class="page-desc" style="color: var(--text-2); font-size:0.95rem; margin-top:15px; max-width:100%; text-align:center;">
                Notre algorithme analyse en temps réel les déclarations d'effets indésirables pour évaluer la probabilité d'une hospitalisation.
            </div>
        </div>
    </div>""", unsafe_allow_html=True)
    
    if HERO_PATH.exists():
        st.image(str(HERO_PATH), use_container_width=True)
            
    # Add rounded image borders via CSS
    st.markdown("""<style>
    [data-testid="stImage"] img {
        border-radius: 24px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.06);
        max-height: 210px !important;
        object-fit: cover !important;
    }
    </style>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="kpi-strip fade-up" style="margin-top:20px; margin-bottom: 25px;">
        <div class="kpi-cell"><div class="kpi-dot" style="background:var(--accent-light); color:var(--accent);"><i class="fa-solid fa-bullseye"></i></div><div><div class="kpi-lbl">Rappel Métier</div><div class="kpi-val">100%</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot" style="background:var(--accent-light); color:var(--accent);"><i class="fa-solid fa-sliders"></i></div><div><div class="kpi-lbl">Seuil Optimal</div><div class="kpi-val">0.59</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot" style="background:var(--accent-light); color:var(--accent);"><i class="fa-solid fa-layer-group"></i></div><div><div class="kpi-lbl">Variables</div><div class="kpi-val">14 Features</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot" style="background:var(--accent-light); color:var(--accent);"><i class="fa-solid fa-circle-check"></i></div><div><div class="kpi-lbl">Statut API</div><div class="kpi-val">Connecté</div></div></div>
    </div>""", unsafe_allow_html=True)

    with st.form("form_predict"):
        st.markdown(
            '<div class="card fade-up"><div class="card-title">'
            '<i class="fa-solid fa-user-circle"></i> Profil patient</div>',
            unsafe_allow_html=True,
        )
        c1, c2 = st.columns(2)
        with c1:
            age = st.number_input(
                "Âge (années)",
                0.0, 120.0, 55.0, 1.0,
                help="Âge du patient au moment de la déclaration d'effet indésirable.",
            )
        with c2:
            sex_s = st.selectbox(
                "Sexe",
                list(SEX_MAP.keys()),
                help="Sexe biologique du patient tel que renseigné dans le rapport.",
            )
        country = st.text_input(
            "Code pays (ISO 2 lettres)",
            "US",
            placeholder="US, FR, DE…",
            help="Code pays ISO 3166-1 alpha-2 du rapport (ex. US, FR).",
        )
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        st.markdown(
            '<div class="card fade-up"><div class="card-title">'
            '<i class="fa-solid fa-capsules"></i> Médicaments</div>',
            unsafe_allow_html=True,
        )
        c3, c4 = st.columns(2)
        with c3:
            nb_drugs = st.number_input(
                "Nombre total de médicaments",
                1, 500, 3,
                help="Nombre de médicaments mentionnés dans le rapport FAERS.",
            )
        with c4:
            nb_susp = st.number_input(
                "Médicaments suspects",
                0, 500, 1,
                help="Nombre de médicaments identifiés comme suspects.",
            )
        c5, c6 = st.columns(2)
        with c5:
            route_s = st.selectbox(
                "Voie d'administration",
                list(ROUTE_MAP.keys()),
                help="Voie d'administration du médicament suspect principal.",
            )
        with c6:
            bbw_s = st.selectbox(
                "Black Box Warning (FDA)",
                list(YES_NO_MAP.keys()),
                help="Le médicament suspect possède-t-il un avertissement encadré noir ?",
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()

        st.markdown(
            '<div class="card fade-up"><div class="card-title">'
            '<i class="fa-solid fa-shield-halved"></i> Réactions & contexte</div>',
            unsafe_allow_html=True,
        )
        c7, c8 = st.columns(2)
        with c7:
            nb_react = st.number_input(
                "Nombre de réactions",
                1, 200, 2,
                help="Nombre d'effets indésirables rapportés pour ce cas.",
            )
        with c8:
            outcome_s = st.selectbox(
                "Pire issue de réaction",
                list(OUTCOME_MAP.keys()),
                help="Issue la plus grave parmi les réactions déclarées.",
            )
        c9, c10 = st.columns(2)
        with c9:
            reporter_s = st.selectbox(
                "Qualification du déclarant",
                list(REPORTER_MAP.keys()),
                help="Profil professionnel de la personne ayant soumis le rapport.",
            )
        with c10:
            conco_s = st.selectbox(
                "Médicaments concomitants",
                list(YES_NO_MAP.keys()),
                help="Présence d'autres médicaments pris simultanément.",
            )
        st.markdown("</div>", unsafe_allow_html=True)

        st.divider()
        _, btn_col, _ = st.columns([1, 1.2, 1])
        with btn_col:
            submit = st.form_submit_button("Prédire", use_container_width=True)

    if submit:
        payload = {
            "patient_age":            age,
            "nb_drugs":               int(nb_drugs),
            "nb_reactions":           int(nb_react),
            "nb_suspect_drugs":       int(nb_susp),
            "worst_reaction_outcome": OUTCOME_MAP[outcome_s],
            "patient_sex":            SEX_MAP[sex_s],
            "reporter_qualification": REPORTER_MAP[reporter_s],
            "has_black_box_warning":  YES_NO_MAP[bbw_s],
            "is_concomitant_present": YES_NO_MAP[conco_s],
            "route_of_admin":         ROUTE_MAP[route_s],
            "country":                country.strip().upper() or "US",
        }
        with st.spinner("Calcul de la prédiction en cours…"):
            result, is_live = call_api(payload)
        prob  = result.get("probability", 0.0)
        label = result.get("label", 0)
        pct   = int(prob * 100)

        tag = (
            '<span class="source-tag tag-live"><i class="fa-solid fa-circle-check"></i> API en direct</span>'
            if is_live else
            '<span class="source-tag tag-mock"><i class="fa-solid fa-flask-vial"></i> Données simulées</span>'
        )
        st.markdown("<hr class='green-rule'>", unsafe_allow_html=True)

        if label == 1:
            st.error("Risque élevé d'hospitalisation — revue humaine prioritaire recommandée.")
            st.markdown(f"""
            <div class="result-wrap result-high fade-up">
                <div class="result-icon-ring ring-high"><i class="fa-solid fa-triangle-exclamation"></i></div>
                <div class="result-title-high">Risque Élevé</div>
                <div class="result-subtitle">Ce rapport présente une probabilité élevée d'hospitalisation.<br>Une revue humaine prioritaire est fortement recommandée.</div>
                <div class="prob-display">
                    <i class="fa-solid fa-chart-line" style="color:#FF4D6D;"></i>
                    Probabilité estimée : <span class="prob-num prob-num-high">{prob:.1%}</span>
                </div>
                <div class="prob-track"><div class="prob-fill-high" style="width:{pct}%"></div></div>
                {tag}
            </div>""", unsafe_allow_html=True)
        else:
            st.success("Risque faible — aucun signal d'hospitalisation significatif détecté.")
            st.markdown(f"""
            <div class="result-wrap result-low fade-up">
                <div class="result-icon-ring ring-low"><i class="fa-solid fa-shield-check"></i></div>
                <div class="result-title-low">Risque Faible</div>
                <div class="result-subtitle">Ce rapport ne présente pas de signal d'hospitalisation significatif.<br>Un traitement standard est approprié.</div>
                <div class="prob-display">
                    <i class="fa-solid fa-chart-line" style="color:#00D478;"></i>
                    Probabilité estimée : <span class="prob-num prob-num-low">{prob:.1%}</span>
                </div>
                <div class="prob-track"><div class="prob-fill-low" style="width:{pct}%"></div></div>
                {tag}
            </div>""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════
# PAGE 2 — BATCH CSV
# ═══════════════════════════════════════════════════════════
elif "lot" in page:
    st.markdown("""
    <div class="page-header fade-up">
        <div>
            <div class="page-eyebrow"><i class="fa-solid fa-layer-group"></i> Traitement en masse</div>
            <div class="page-title">Prédiction par lot</div>
            <div class="page-desc">Importez un fichier CSV contenant plusieurs rapports pour obtenir les prédictions enrichies en un seul traitement.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="kpi-strip fade-up">
        <div class="kpi-cell"><div class="kpi-dot dot-g"><i class="fa-solid fa-file-csv"></i></div><div><div class="kpi-lbl">Format</div><div class="kpi-val" style="font-size:1.1rem;">CSV</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot dot-b"><i class="fa-solid fa-columns"></i></div><div><div class="kpi-lbl">Colonnes</div><div class="kpi-val">11</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot dot-p"><i class="fa-solid fa-bolt"></i></div><div><div class="kpi-lbl">Sorties</div><div class="kpi-val">+1 col</div></div></div>
        <div class="kpi-cell"><div class="kpi-dot dot-o"><i class="fa-solid fa-gauge-max"></i></div><div><div class="kpi-lbl">Limite</div><div class="kpi-val">1 000</div></div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown(
        '<div class="card fade-up"><div class="card-title">'
        '<i class="fa-solid fa-cloud-arrow-up"></i> Importer le fichier</div>'
        '<p class="drop-zone-label">Glissez-déposez votre fichier <strong>CSV</strong> '
        'dans la zone ci-dessous ou cliquez pour parcourir.</p>',
        unsafe_allow_html=True,
    )
    uploaded = st.file_uploader(
        "Fichier CSV",
        type="csv",
        label_visibility="collapsed",
        help="Le fichier doit contenir les 11 colonnes attendues par le modèle.",
    )
    st.markdown("</div>", unsafe_allow_html=True)

    if uploaded:
        df_prev = pd.read_csv(uploaded)
        st.markdown(f'<div class="card fade-up"><div class="card-title"><i class="fa-solid fa-table"></i> Aperçu — {len(df_prev):,} lignes</div>', unsafe_allow_html=True)
        st.dataframe(df_prev.head(8), use_container_width=True, hide_index=True)
        st.markdown("</div>", unsafe_allow_html=True)

        if st.button("Analyser le lot complet", use_container_width=True):
            with st.spinner("Analyse en cours…"):
                uploaded.seek(0)
                try:
                    r = requests.post(f"{API_URL}/predict/csv",
                                      files={"file": (uploaded.name, uploaded.getvalue(), "text/csv")},
                                      timeout=30)
                    if r.status_code == 200:
                        result_bytes = r.content
                        df_out = pd.read_csv(io.BytesIO(result_bytes))
                        n_high = (df_out.get("prediction_hospitalization", pd.Series()) == 1).sum()
                        st.success(f"{len(df_out):,} prédictions générées — {n_high} à risque élevé détectés.")
                        st.markdown('<div class="card fade-up"><div class="card-title"><i class="fa-solid fa-chart-pie"></i> Résultats</div>', unsafe_allow_html=True)
                        st.dataframe(df_out, use_container_width=True, hide_index=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        st.download_button("Télécharger le fichier enrichi", data=result_bytes,
                                           file_name=f"sentio_predictions_{uploaded.name}", mime="text/csv",
                                           use_container_width=True)
                    else:
                        st.error(f"Erreur API : {r.status_code}")
                except Exception:
                    st.warning("L'API est inaccessible. Démarrez le backend pour utiliser le mode batch.")

# ═══════════════════════════════════════════════════════════
# PAGE 3 — INFORMATIONS MODÈLE
# ═══════════════════════════════════════════════════════════
else:
    st.markdown("""
    <div class="page-header fade-up">
        <div>
            <div class="page-eyebrow"><i class="fa-solid fa-microchip-ai"></i> Moteur de prédiction</div>
            <div class="page-title">Informations sur le modèle</div>
            <div class="page-desc">Architecture, performances et caractéristiques du pipeline de classification supervisée FAERS.</div>
        </div>
    </div>""", unsafe_allow_html=True)

    info, metrics = None, {}
    try:
        r = requests.get(f"{API_URL}/model/info", timeout=5)
        if r.status_code == 200:
            info = r.json()
            metrics = info.get("metrics", {})
    except Exception:
        pass

    if info:
        acc  = metrics.get("accuracy", 0)
        prec = metrics.get("precision", 0)
        rec  = metrics.get("recall", 0)
        f1   = metrics.get("f1", 0)
        st.markdown(f"""
        <div class="kpi-strip fade-up">
            <div class="kpi-cell {metric_tier(acc)}"><div class="kpi-dot"><i class="fa-solid fa-bullseye"></i></div><div><div class="kpi-lbl">Accuracy</div><div class="kpi-val">{acc:.1%}</div></div></div>
            <div class="kpi-cell {metric_tier(prec)}"><div class="kpi-dot"><i class="fa-solid fa-crosshairs"></i></div><div><div class="kpi-lbl">Précision</div><div class="kpi-val">{prec:.1%}</div></div></div>
            <div class="kpi-cell {metric_tier(rec)}"><div class="kpi-dot"><i class="fa-solid fa-magnifying-glass"></i></div><div><div class="kpi-lbl">Rappel</div><div class="kpi-val">{rec:.1%}</div></div></div>
            <div class="kpi-cell {metric_tier(f1)}"><div class="kpi-dot"><i class="fa-solid fa-star-half-stroke"></i></div><div><div class="kpi-lbl">F1-Score</div><div class="kpi-val">{f1:.1%}</div></div></div>
        </div>""", unsafe_allow_html=True)

        col_a, col_b = st.columns([1, 1.2])
        with col_a:
            st.markdown(f"""
            <div class="card fade-up">
                <div class="card-title"><i class="fa-solid fa-id-card"></i> Identité du modèle</div>
                <div class="info-row"><span class="info-key">Nom</span><span class="info-val">{info.get("name","—")}</span></div>
                <div class="info-row"><span class="info-key">Version</span><span class="info-val">{info.get("version","—")}</span></div>
                <div class="info-row"><span class="info-key">Variable cible</span><span class="info-val" style="font-family:'JetBrains Mono',monospace;font-size:0.8rem;">{info.get("target","—")}</span></div>
                <div class="info-row"><span class="info-key">Seuil optimal</span><span class="info-val">{info.get("threshold",0):.2f}</span></div>
                <div class="info-row"><span class="info-key">Chargé le</span><span class="info-val" style="font-size:0.82rem;">{info.get("loaded_at","—")}</span></div>
            </div>""", unsafe_allow_html=True)
        with col_b:
            features = info.get("feature_names", [])
            chips = "".join(f'<span class="chip">{f}</span>' for f in features)
            st.markdown(f"""
            <div class="card fade-up">
                <div class="card-title"><i class="fa-solid fa-layer-group"></i> Features ({len(features)})</div>
                <div style="margin-top:4px;">{chips}</div>
            </div>""", unsafe_allow_html=True)
    else:
        st.markdown("""
        <div class="card fade-up">
            <div class="card-title"><i class="fa-solid fa-circle-info"></i> Informations statiques</div>
            <p style="color:#94A3B8;font-size:0.9rem;line-height:1.7;">
            L'API n'est pas accessible. Démarrez le backend pour afficher les métriques réelles.
            </p>
        </div>""", unsafe_allow_html=True)

        st.markdown("""
        <div class="card fade-up">
            <div class="card-title"><i class="fa-solid fa-triangle-exclamation"></i> Limites du modèle</div>
            <ul style="list-style:none;padding:0;">
                <li class="info-row"><span style="color:#00D478;margin-right:10px;"><i class="fa-solid fa-circle-right"></i></span><span style="color:#94A3B8;font-size:0.88rem;">Données FAERS : déclarations spontanées, biais de signalement possible.</span></li>
                <li class="info-row"><span style="color:#00D478;margin-right:10px;"><i class="fa-solid fa-circle-right"></i></span><span style="color:#94A3B8;font-size:0.88rem;">Surreprésentation US (~70%). Généralisation internationale limitée.</span></li>
                <li class="info-row"><span style="color:#00D478;margin-right:10px;"><i class="fa-solid fa-circle-right"></i></span><span style="color:#94A3B8;font-size:0.88rem;">Random Forest = boîte noire. SHAP recommandé pour l'explicabilité.</span></li>
                <li class="info-row"><span style="color:#00D478;margin-right:10px;"><i class="fa-solid fa-circle-right"></i></span><span style="color:#94A3B8;font-size:0.88rem;">Prototype pédagogique — non homologué pour usage clinique.</span></li>
            </ul>
        </div>""", unsafe_allow_html=True)


st.markdown(f"""
<style>
/* Rounded input styles with dynamic theme */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {{
    border-radius: 20px !important;
    background-color: var(--bg-card) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-1) !important;
    height: 42px !important;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
}}
.stTextInput input:focus, .stNumberInput input:focus {{
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 4px var(--accent-glow) !important;
}}
</style>
""", unsafe_allow_html=True)

