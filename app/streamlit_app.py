import streamlit as st
import pandas as pd
import requests
import io
import os
import base64
from pathlib import Path

API_URL   = os.getenv("API_URL", "http://localhost:8000")
LOGO_PATH = Path(__file__).parent / "logo.png"

st.set_page_config(
    page_title="Sentio — Prédiction d'Hospitalisation",
    page_icon=str(LOGO_PATH) if LOGO_PATH.exists() else None,
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════
# DESIGN SYSTEM — DARK GLASSMORPHISM PREMIUM
# ═══════════════════════════════════════════════════════════
st.markdown("""
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.0/css/all.min.css">

<style>
:root {
  --bg:           #F4F7F6;  /* Mockup background: light sage/grey */
  --bg-deep:      #E2EDEC;  /* Soft light teal/sage */
  --bg-surface:   #FFFFFF;  /* White card background */
  --bg-card:      #FFFFFF;
  --bg-card-h:    #E2EDEC;
  --border:       #CBDCDA;
  --border-accent:#769490;  /* Premium sage green from mockup */

  --accent:       #769490;  
  --accent-dim:   #5C7874;
  --accent-glow:  rgba(118, 148, 144, 0.15);
  --accent-light: rgba(118, 148, 144, 0.08);

  --cyan:         #89A3A0;
  --cyan-glow:    rgba(137, 163, 160, 0.12);

  --red:          #E05D6F;  /* Soft clinical pinkish red */
  --red-glow:     rgba(224, 93, 111, 0.12);
  --red-light:    rgba(224, 93, 111, 0.08);

  --text-1: #1E293B;  /* Slate dark text for readability */
  --text-2: #475569;
  --text-3: #64748B;
  --text-4: #94A3B8;

  --font-main:    'Inter', sans-serif;
  --font-display: 'Outfit', sans-serif;
  --font-mono:    'JetBrains Mono', monospace;

  --r-sm: 12px; --r-md: 24px; --r-lg: 32px;  /* Beautiful rounded mockup borders */
}

/* ── GLOBAL ── */
*, *::before, *::after { box-sizing: border-box; }

html, body,
[class*="css"],
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > section,
[data-testid="stMain"] {
    font-family: var(--font-main) !important;
    background: var(--bg) !important;
    color: var(--text-1) !important;
}

/* Animated background orbs */
[data-testid="stAppViewContainer"]::before {
    content: "";
    position: fixed;
    inset: 0;
    background: #F4F7F6;
    pointer-events: none;
    z-index: 0;
}

#MainMenu, footer { visibility: hidden; }
[data-testid="stDecoration"] { display: none; }
.block-container {
    padding: 2.2rem 2.8rem !important;
    max-width: 1380px !important;
    position: relative; z-index: 1;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: #E2EDEC !important;
    border-right: 1px solid var(--border) !important;
    box-shadow: 2px 0 15px rgba(0,0,0,0.04) !important;
}
[data-testid="stSidebar"] > div:first-child { padding-top: 0 !important; }

/* Sidebar brand */
.sb-brand {
    background: linear-gradient(180deg, rgba(20,184,166,0.04) 0%, transparent 100%);
    border-bottom: 1px solid var(--border);
    padding: 28px 20px 24px;
    text-align: center;
}
.sb-logo-wrap {
    width: 78px; height: 78px;
    border-radius: 22px;
    background: linear-gradient(135deg, rgba(20,184,166,0.08), rgba(59,130,246,0.04));
    border: 1.5px solid var(--border-accent);
    box-shadow: 0 0 28px var(--accent-glow), inset 0 1px 0 rgba(0,212,120,0.15);
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 14px;
    overflow: hidden;
    transition: box-shadow 0.3s;
}
.sb-logo-wrap:hover {
    box-shadow: 0 0 42px var(--accent-glow), inset 0 1px 0 rgba(0,212,120,0.2);
}
.sb-logo-wrap img { width: 100%; height: 100%; object-fit: cover; }

.sb-name {
    font-family: var(--font-display);
    font-size: 1.55rem; font-weight: 800;
    color: var(--text-1); letter-spacing: -0.03em;
}
.sb-name span {
    color: var(--accent);
}
.sb-tagline {
    font-size: 0.64rem; color: var(--text-3); font-weight: 500;
    text-transform: uppercase; letter-spacing: 0.14em; margin-top: 5px;
}

/* Nav */
.nav-label {
    font-size: 0.61rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.14em; color: var(--text-4);
    padding: 0 16px; margin: 20px 0 8px; display: block;
}
[data-testid="stSidebar"] .stRadio > div { gap: 3px !important; }
[data-testid="stSidebar"] .stRadio label {
    color: #475569 !important; font-size: 0.86rem !important;
    font-weight: 500 !important; padding: 10px 14px !important;
    border-radius: var(--r-sm) !important; border: 1px solid transparent !important;
    transition: all 0.18s ease !important; cursor: pointer !important;
}
[data-testid="stSidebar"] .stRadio label:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
    border-color: var(--border-accent) !important;
}

/* Status badge */
.status-badge {
    display: inline-flex; align-items: center; gap: 7px;
    padding: 6px 14px; border-radius: 100px;
    font-size: 0.74rem; font-weight: 600;
}
.online  { background: var(--accent-light); color: var(--accent); border: 1px solid var(--border-accent); }
.offline { background: rgba(251,191,36,0.08); color: #FBC02D; border: 1px solid rgba(251,191,36,0.3); }
.pulse-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.pulse-green  { background: var(--accent); animation: pulse 2s infinite; }
.pulse-orange { background: #FBC02D; animation: pulse 2s infinite; }

.sb-footer {
    margin-top: 36px; padding: 16px;
    border-top: 1px solid var(--border);
    font-size: 0.68rem; color: var(--text-4); line-height: 1.9;
}
.sb-footer strong { color: var(--text-3); }

/* ── PAGE HEADER ── */
.page-header {
    display: flex; align-items: flex-start;
    justify-content: space-between; gap: 20px;
    margin-bottom: 32px; padding-bottom: 26px;
    border-bottom: 1px solid var(--border);
}
.page-eyebrow {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.16em; color: var(--accent); margin-bottom: 8px;
    display: flex; align-items: center; gap: 7px;
}
.page-title {
    font-family: var(--font-display);
    font-size: 2.5rem; font-weight: 800;
    line-height: 1.1; letter-spacing: -0.03em;
    color: var(--text-1);
}
.page-desc {
    font-size: 0.875rem; color: var(--text-2);
    margin-top: 10px; line-height: 1.65; max-width: 500px;
}

/* ── STAT CHIPS ── */
.stat-chips { display: flex; gap: 12px; flex-shrink: 0; align-items: center; flex-wrap: wrap; justify-content: flex-end; }
.stat-chip {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 14px 20px; text-align: center;
    backdrop-filter: blur(12px); min-width: 88px; transition: all 0.22s;
}
.stat-chip:hover {
    border-color: var(--border-accent);
    box-shadow: 0 0 22px var(--accent-glow);
    transform: translateY(-2px);
}
.stat-chip-val { font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--accent); }
.stat-chip-lbl { font-size: 0.63rem; color: var(--text-3); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; margin-top: 3px; }

/* ── GLASS CARDS ── */

.card {
    background: var(--bg-surface);
    border-radius: var(--r-md);
    padding: 24px 28px;
    border: 1px solid var(--border);
    margin-bottom: 18px;
    position: relative; overflow: hidden;
    box-shadow: 0 10px 30px rgba(118, 148, 144, 0.04);
    transition: all 0.25s ease-in-out;
}
.card::before {
    display: none;
}
.card:hover {
    border-color: var(--border-accent);
    box-shadow: 0 15px 35px rgba(118, 148, 144, 0.12);
    transform: translateY(-2px);
}

.card-title {
    font-size: 0.68rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.12em; color: var(--accent);
    display: flex; align-items: center; gap: 9px;
    margin-bottom: 22px; padding-bottom: 14px;
    border-bottom: 1px solid var(--border);
}

/* ── INPUTS ── */
.stSelectbox label, .stNumberInput label, .stTextInput label {
    font-size: 0.71rem !important; font-weight: 600 !important;
    color: #475569 !important; text-transform: uppercase !important; letter-spacing: 0.07em !important;
}
.stSelectbox > div > div,
.stNumberInput > div > div > input,
.stTextInput > div > div > input {
    background: rgba(255,255,255,0.04) !important;
    border: 1px solid var(--border) !important;
    border-radius: var(--r-sm) !important;
    color: var(--text-1) !important; font-size: 0.9rem !important;
    transition: all 0.18s !important;
}
.stSelectbox > div > div:focus-within,
.stNumberInput > div > div:focus-within,
.stTextInput > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-glow) !important;
    background: rgba(0,212,120,0.04) !important;
}

/* ── BUTTON ── */

.stFormSubmitButton > button, .stButton > button {
    background: var(--accent) !important;
    color: #FFFFFF !important; border: none !important;
    border-radius: 24px !important; padding: 12px 36px !important;
    font-family: var(--font-display) !important;
    font-size: 0.92rem !important; font-weight: 600 !important;
    transition: all 0.2s ease !important; width: 100% !important;
    box-shadow: 0 6px 15px rgba(118, 148, 144, 0.18) !important;
}
.stFormSubmitButton > button:hover, .stButton > button:hover {
    background: var(--accent-dim) !important;
    box-shadow: 0 10px 22px rgba(118, 148, 144, 0.28) !important;
    color: #FFFFFF !important;
    transform: translateY(-1px);
}

.stFormSubmitButton > button:active, .stButton > button:active { transform: translateY(0) !important; }

/* ── RESULTS ── */

.result-wrap {
    border-radius: var(--r-md); padding: 42px 40px; text-align: center;
    position: relative; overflow: hidden;
    margin-top: 20px;
}
.result-high {
    background: #FFF5F5;
    border: 1.5px solid #F87171;
    box-shadow: 0 4px 15px rgba(239, 68, 68, 0.05);
}
.result-low {
    background: #F0FDF4;
    border: 1.5px solid #34D399;
    box-shadow: 0 4px 15px rgba(16, 185, 129, 0.05);
}
.result-high::before, .result-low::before {
    display: none;
}
.ring-high { background: #FEE2E2; color: #EF4444; border: 2px solid #FCA5A5; }
.ring-low  { background: #D1FAE5; color: #10B981; border: 2px solid #6EE7B7; }
.result-title-high { font-family: var(--font-display); font-size: 1.8rem; font-weight: 800; color: #B91C1C; }
.result-title-low  { font-family: var(--font-display); font-size: 1.8rem; font-weight: 800; color: #065F46; }
.prob-fill-high { height: 7px; border-radius: 100px; background: #EF4444; }
.prob-fill-low  { height: 7px; border-radius: 100px; background: #10B981; }
}
.result-subtitle { font-size: 0.88rem; color: var(--text-2); margin-top: 10px; line-height: 1.65; position: relative; z-index: 1; }
.prob-display {
    display: inline-flex; align-items: center; gap: 10px;
    margin: 22px auto 0; background: rgba(255,255,255,0.05);
    border-radius: 100px; padding: 10px 24px;
    font-size: 0.87rem; font-weight: 600; color: var(--text-2);
    border: 1px solid var(--border); backdrop-filter: blur(8px);
    position: relative; z-index: 1;
}
.prob-num { font-family: var(--font-display); font-size: 1.4rem; font-weight: 800; }
.prob-num-high { color: var(--red); }
.prob-num-low  { color: var(--accent); }
.prob-track {
    height: 7px; border-radius: 100px;
    background: rgba(255,255,255,0.06);
    margin-top: 22px; overflow: hidden;
    position: relative; z-index: 1;
    border: 1px solid rgba(255,255,255,0.04);
}
.prob-fill-high { height: 7px; border-radius: 100px; background: linear-gradient(90deg, rgba(255,77,109,0.4), var(--red)); box-shadow: 0 0 10px var(--red-glow); }
.prob-fill-low  { height: 7px; border-radius: 100px; background: linear-gradient(90deg, rgba(0,212,120,0.4), var(--accent)); box-shadow: 0 0 10px var(--accent-glow); }
.source-tag {
    display: inline-flex; align-items: center; gap: 7px;
    font-size: 0.7rem; font-weight: 600; letter-spacing: 0.05em;
    padding: 6px 14px; border-radius: 100px; margin-top: 18px;
    position: relative; z-index: 1;
}
.tag-live { background: var(--accent-light); color: var(--accent); border: 1px solid var(--border-accent); }
.tag-mock { background: rgba(251,191,36,0.08); color: #FBC02D; border: 1px solid rgba(251,191,36,0.28); }

/* ── KPI STRIP ── */
.kpi-strip { display: grid; grid-template-columns: repeat(4,1fr); gap: 14px; margin-bottom: 26px; }
.kpi-cell {
    background: var(--bg-card); border: 1px solid var(--border);
    border-radius: var(--r-md); padding: 20px 22px;
    display: flex; align-items: center; gap: 16px;
    backdrop-filter: blur(12px);
    position: relative; overflow: hidden;
    transition: all 0.22s;
}
.kpi-cell::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent);
}
.kpi-cell:hover { transform: translateY(-3px); border-color: var(--border-accent); box-shadow: 0 8px 30px rgba(0,0,0,0.4), 0 0 20px var(--accent-glow); }
.kpi-dot { width: 48px; height: 48px; border-radius: 14px; display: flex; align-items: center; justify-content: center; font-size: 1.15rem; flex-shrink: 0; }
.dot-g { background: var(--accent-light); color: var(--accent); border: 1px solid rgba(0,212,120,0.2); }
.dot-b { background: rgba(96,239,255,0.08); color: var(--cyan); border: 1px solid rgba(96,239,255,0.18); }
.dot-p { background: rgba(167,139,250,0.08); color: #A78BFA; border: 1px solid rgba(167,139,250,0.18); }
.dot-o { background: rgba(251,146,60,0.08); color: #FB923C; border: 1px solid rgba(251,146,60,0.18); }
.kpi-lbl { font-size: 0.66rem; color: var(--text-3); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
.kpi-val { font-family: var(--font-display); font-size: 1.5rem; font-weight: 800; color: var(--text-1); margin-top: 2px; }

/* ── CHIPS ── */
.chip {
    display: inline-block; background: var(--accent-light); color: var(--accent);
    border: 1px solid rgba(0,212,120,0.2); border-radius: 8px;
    padding: 5px 13px; font-size: 0.71rem; font-weight: 600;
    margin: 3px; font-family: var(--font-mono); transition: all 0.18s;
}
.chip:hover { background: rgba(0,212,120,0.14); box-shadow: 0 0 12px var(--accent-glow); }

/* ── INFO TABLE ── */
.info-row { display: flex; align-items: center; padding: 13px 0; border-bottom: 1px solid var(--border); gap: 20px; }
.info-row:last-child { border-bottom: none; }
.info-key { font-size: 0.71rem; font-weight: 600; color: var(--text-3); text-transform: uppercase; letter-spacing: 0.07em; min-width: 140px; }
.info-val { font-size: 0.9rem; font-weight: 600; color: var(--text-1); }

/* ── DIVIDER ── */
.green-rule {
    height: 1px;
    background: linear-gradient(90deg, transparent, var(--accent) 40%, var(--cyan) 60%, transparent);
    border: none; border-radius: 100px; margin: 30px 0; opacity: 0.3;
}

/* ── FILE UPLOADER ── */
[data-testid="stFileUploader"] > div {
    background: rgba(0,212,120,0.03) !important;
    border: 2px dashed rgba(0,212,120,0.22) !important;
    border-radius: var(--r-md) !important; transition: all 0.2s !important;
}
[data-testid="stFileUploader"] > div:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 0 28px var(--accent-glow) !important;
}
[data-testid="stFileUploader"] * { color: #475569 !important; }

/* ── DATAFRAME ── */
[data-testid="stDataFrame"] { border-radius: var(--r-md) !important; overflow: hidden !important; border: 1px solid var(--border) !important; }

/* ── SCROLLBAR ── */
::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: var(--bg-surface); }
::-webkit-scrollbar-thumb { background: rgba(0,212,120,0.25); border-radius: 100px; }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

/* ── ANIMATIONS ── */
@keyframes slideUp { from { opacity:0; transform:translateY(20px); } to { opacity:1; transform:translateY(0); } }
@keyframes pulse   { 0%,100% { opacity:1; } 50% { opacity:0.35; } }
@keyframes breathe { 0%,100% { opacity:0.5; transform:scale(0.95); } 50% { opacity:1; transform:scale(1.05); } }
.fade-up { animation: slideUp 0.45s cubic-bezier(0.16,1,0.3,1) both; }

/* ── NUMBER INPUT ── */
[data-testid="stNumberInput"] button {
    background: var(--bg-card) !important; border: 1px solid var(--border) !important;
    color: #475569 !important; border-radius: 8px !important;
}
[data-testid="stNumberInput"] button:hover { background: var(--bg-card-h) !important; color: var(--accent) !important; }
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

# ═══════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════
with st.sidebar:
    logo_html = '<i class="fa-solid fa-capsules" style="font-size:2rem;color:#00D478;"></i>'
    if LOGO_PATH.exists():
        logo_b64  = base64.b64encode(LOGO_PATH.read_bytes()).decode()
        logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="width:100%;height:100%;object-fit:cover;">'

    st.markdown(f"""
    <div class="sb-brand">
        <div class="sb-logo-wrap">{logo_html}</div>
        <div class="sb-name">Sen<span>tio</span></div>
        <div class="sb-tagline">Pharmacovigilance · IA</div>
    </div>""", unsafe_allow_html=True)

    st.markdown('<span class="nav-label">Navigation</span>', unsafe_allow_html=True)
    page = st.radio("", [
        "  Prédiction individuelle",
        "  Prédiction par lot",
        "  Informations du modèle",
    ], label_visibility="collapsed")

    live      = api_alive()
    dot_cls   = "pulse-green" if live else "pulse-orange"
    badge_cls = "online" if live else "offline"
    badge_lbl = "API connectée" if live else "Mode démonstration"
    st.markdown(f"""
    <div style="margin-top:28px;padding:0 4px;">
        <div class="status-badge {badge_cls}">
            <span class="pulse-dot {dot_cls}"></span>{badge_lbl}
        </div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""
    <div class="sb-footer">
        <strong>Sentio v1.0</strong><br>
        Projet Machine Learning S8<br>
        FDA FAERS · CRISP-DM
    </div>""", unsafe_allow_html=True)

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
        st.markdown("""<div class="card fade-up">
        <div class="card-title"><i class="fa-solid fa-user-circle"></i> Profil Patient</div>""",
        unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1: age     = st.number_input("Âge (années)", 0.0, 120.0, 55.0, 1.0)
        with c2: sex_s   = st.selectbox("Sexe", list(SEX_MAP.keys()))
        with c3: country = st.text_input("Code pays (ISO 2)", "US", placeholder="US, FR, DE…")
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""<div class="card fade-up">
        <div class="card-title"><i class="fa-solid fa-capsules"></i> Médicaments</div>""",
        unsafe_allow_html=True)
        c4, c5, c6, c7 = st.columns(4)
        with c4: nb_drugs = st.number_input("Total médicaments", 1, 500, 3)
        with c5: nb_susp  = st.number_input("Médicaments suspects", 0, int(nb_drugs), 1)
        with c6: route_s  = st.selectbox("Voie d'administration", list(ROUTE_MAP.keys()))
        with c7: bbw_s    = st.selectbox("Black Box Warning", list(YES_NO_MAP.keys()))
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("""<div class="card fade-up">
        <div class="card-title"><i class="fa-solid fa-shield-halved"></i> Réactions &amp; Contexte</div>""",
        unsafe_allow_html=True)
        c8, c9, c10, c11 = st.columns(4)
        with c8:  nb_react   = st.number_input("Nombre de réactions", 1, 200, 2)
        with c9:  outcome_s  = st.selectbox("Pire résultat", list(OUTCOME_MAP.keys()))
        with c10: reporter_s = st.selectbox("Déclarant", list(REPORTER_MAP.keys()))
        with c11: conco_s    = st.selectbox("Médicaments concomitants", list(YES_NO_MAP.keys()))
        st.markdown("</div>", unsafe_allow_html=True)

        submit = st.form_submit_button("Lancer l'analyse prédictive", use_container_width=True)

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

    st.markdown('<div class="card fade-up"><div class="card-title"><i class="fa-solid fa-cloud-arrow-up"></i> Importer le fichier</div>', unsafe_allow_html=True)
    uploaded = st.file_uploader("Glissez votre fichier CSV ici ou cliquez pour sélectionner", type="csv")
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
            <div class="kpi-cell"><div class="kpi-dot dot-g"><i class="fa-solid fa-bullseye"></i></div><div><div class="kpi-lbl">Accuracy</div><div class="kpi-val">{acc:.1%}</div></div></div>
            <div class="kpi-cell"><div class="kpi-dot dot-b"><i class="fa-solid fa-crosshairs"></i></div><div><div class="kpi-lbl">Précision</div><div class="kpi-val">{prec:.1%}</div></div></div>
            <div class="kpi-cell"><div class="kpi-dot dot-g"><i class="fa-solid fa-magnifying-glass"></i></div><div><div class="kpi-lbl">Rappel</div><div class="kpi-val">{rec:.1%}</div></div></div>
            <div class="kpi-cell"><div class="kpi-dot dot-p"><i class="fa-solid fa-star-half-stroke"></i></div><div><div class="kpi-lbl">F1-Score</div><div class="kpi-val">{f1:.1%}</div></div></div>
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


st.markdown("""
<style>
[data-testid="stSidebar"] * {
    color: #1E293B !important;
}
[data-testid="stSidebar"] label p {
    color: #1E293B !important;
    font-weight: 500 !important;
}


/* Rounded light input styles */
.stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
    border-radius: 20px !important;
    background-color: #FFFFFF !important;
    border: 1px solid #CBDCDA !important;
    color: #1E293B !important;
    height: 42px !important;
}
.stTextInput input:focus, .stNumberInput input:focus {
    border-color: #769490 !important;
    box-shadow: 0 0 0 2px rgba(118, 148, 144, 0.2) !important;
}
</style>
""", unsafe_allow_html=True)
