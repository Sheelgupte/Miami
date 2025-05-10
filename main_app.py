import os
import json
import zipfile
from pathlib import Path

import streamlit as st

# ─── 0. App Setup ────────────────────────────────────────────────────────────────
st.set_page_config(page_title="Workforce AI Dashboard", layout="wide")

# Base directory for relative paths
BASE_DIR = Path(__file__).parent

# Hard-coded credentials (for demo)
CREDENTIALS = {
    "user@example.com": "password123"
}

# Initialize session state
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# ─── 1. Login Page ──────────────────────────────────────────────────────────────
def login_page():
    st.markdown("<h1 style='text-align:center;'>🔐 Workforce AI Login</h1>", unsafe_allow_html=True)
    with st.form("login_form", clear_on_submit=False):
        email = st.text_input("📧 Email", value="user@example.com")
        pwd   = st.text_input("🔑 Password", type="password", value="password123")
        submitted = st.form_submit_button("Login")
    if submitted:
        if email in CREDENTIALS and CREDENTIALS[email] == pwd:
            st.session_state.authenticated = True
            st.session_state.user = email
            st.rerun()
        else:
            st.error("❌ Invalid email or password")

# ─── 2. Logout Button ────────────────────────────────────────────────────────────
def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

# ─── 3. Dashboard Rendering ─────────────────────────────────────────────────────
def dashboard():
    # Sidebar logo + logout
    logo_path = BASE_DIR / "workforce_ai_logo.png"
    if logo_path.exists():
        # increased from 150 to 200 px
        st.sidebar.image(str(logo_path), width=200)
    logout_button()

    # ─── Sidebar CSS tweaks ──────────────────────────────────────────────────────
    st.sidebar.markdown("""
    <style>
      /* enlarge the "Models" header */
      .css-1v3fvcr h2 { font-size:24px !important; }
      /* enlarge each radio option label */
      [data-testid="stRadio"] label {
        font-size: 18px !important;
        font-weight: 500 !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # ─── Model selector in left sidebar ─────────────────────────────────────────
    st.sidebar.markdown("<h2 style='margin-bottom:8px;'>Models</h2>", unsafe_allow_html=True)
    model_choice = st.sidebar.radio(
        "",
        [
            "Site Selection Model",
            "Labor Planning",
            "Labor Potential",
            "Hiring Optimization",
            "Network Optimization"
        ],
        index=0
    )

    # ─── Global CSS for cards ────────────────────────────────────────────────────
    st.markdown("""
    <style>
      main .block-container {
        box-sizing: border-box !important;
        max-width: calc(95% - 4rem) !important;
        padding: 1rem 2rem !important;
        margin: 0 auto !important;
      }
      div[data-testid="stPlotlyChart"],
      div[data-testid="stDataFrame"] {
        box-sizing: border-box !important;
        background-color: #f2f2f2 !important;
        border-radius: 8px !important;
        padding: 20px !important;
        margin-bottom: 20px !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # ─── Render the chosen module ────────────────────────────────────────────────
    if model_choice == "Site Selection Model":
        from site_selection_model import render as render_site_selection
        render_site_selection()
    elif model_choice == "Labor Planning":
        import labor_planning; labor_planning.render()
    elif model_choice == "Labor Potential":
        import labor_potential; labor_potential.render()
    elif model_choice == "Hiring Optimization":
        import hiring_optimization; hiring_optimization.render()
    elif model_choice == "Network Optimization":
        import network_optimization; network_optimization.render()

# ─── 4. App Entry ───────────────────────────────────────────────────────────────
if not st.session_state.authenticated:
    login_page()
else:
    dashboard()
