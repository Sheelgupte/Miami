# labor_planning.py

import sqlite3
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

# ─── DB Connection & ensure tables ─────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DB_PATH  = BASE_DIR / "labor_model.db"
conn     = sqlite3.connect(DB_PATH, check_same_thread=False)
c        = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS forecast_series (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT,
    value REAL
)""")
c.execute("""CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    labor_model_id INTEGER,
    name TEXT,
    fte_needed REAL DEFAULT 0
)""")
c.execute("""CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    labor_model_id INTEGER,
    name TEXT,
    type TEXT,
    linked_driver TEXT,
    time_per_unit REAL,
    frequency_per_period REAL,
    primary_role TEXT
)""")
conn.commit()

# ─── Internal nav state ────────────────────────────────────────────────────────
if "lp_page" not in st.session_state:
    st.session_state.lp_page = "landing"

def _goto(page):
    st.session_state.lp_page = page
    st.rerun()

# ─── 1) Summary landing ─────────────────────────────────────────────────────────
def _show_landing():
    st.header("🛠️ Labor Models Summary")

    df = pd.read_sql("""
      SELECT m.id AS model_id, m.name AS Model,
             IFNULL(SUM(r.fte_needed),0) AS Total_FTE
      FROM labor_models m
      LEFT JOIN roles r ON r.labor_model_id=m.id
      GROUP BY m.id,m.name
    """, conn)

    if df.empty:
        st.info("No labor models defined yet.")
    else:
        st.table(df[["Model","Total_FTE"]].rename(columns={"Total_FTE":"Total FTE"}))
        fig = px.bar(df, x="Model", y="Total_FTE", labels={"Total_FTE":"Total FTE"})
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("➕ Upload Model Components"):
            _goto("upload")
    with col2:
        if st.button("📈 View Forecast History"):
            _goto("forecast")

# ─── 2) Upload components ───────────────────────────────────────────────────────
def _show_upload():
    st.header("📥 Upload Model Components")

    # — Forecast Driver —
    st.subheader("1. Forecast Driver")
    st.markdown("**Required columns**: `WeekStart` (date), `Value` (numeric)")
    fc_file = st.file_uploader("Upload Forecast Excel", type=["xlsx","xls"], key="lp_fc")
    if fc_file:
        df_fc = pd.read_excel(fc_file, header=None, usecols=[0,1], names=["WeekStart","Value"])
        df_fc["WeekStart"] = pd.to_datetime(df_fc["WeekStart"])
        st.dataframe(df_fc, use_container_width=True)
        if st.button("▶️ Process Forecast Upload"):
            # replace prior series
            c.execute("DELETE FROM forecast_series")
            for _, r in df_fc.iterrows():
                c.execute(
                  "INSERT INTO forecast_series (week_start,value) VALUES (?,?)",
                  (r["WeekStart"].strftime("%Y-%m-%d"), float(r["Value"]))
                )
            conn.commit()
            st.success("✅ Forecast series loaded.")
            _goto("landing")
            return

    st.markdown("---")

    # — Roles —
    st.subheader("2. Roles")
    st.markdown("**Required columns**: `name`, `labor_model_id`")
    roles_file = st.file_uploader("Upload Roles Excel", type=["xlsx","xls"], key="lp_roles")
    if roles_file:
        df_roles = pd.read_excel(roles_file)
        st.dataframe(df_roles, use_container_width=True)
        if st.button("▶️ Process Roles Upload"):
            for _, r in df_roles.iterrows():
                c.execute(
                  "INSERT OR REPLACE INTO roles (labor_model_id,name,fte_needed) VALUES (?,?,0)",
                  (int(r["labor_model_id"]), r["name"])
                )
            conn.commit()
            st.success("✅ Roles loaded.")
            _goto("landing")
            return

    st.markdown("---")

    # — Tasks —
    st.subheader("3. Tasks")
    st.markdown(
        "**Required columns**:\n"
        "- `labor_model_id`\n"
        "- `Taskname`\n"
        "- `Type` (`Fixed`/`Variable`)\n"
        "- `Linked Driver`\n"
        "- `TPU` (Time per Unit)\n"
        "- `Frequency` (per period)\n"
        "- `Role` (Primary Role)"
    )
    tasks_file = st.file_uploader("Upload Tasks Excel", type=["xlsx","xls"], key="lp_tasks")
    if tasks_file:
        df_tasks = pd.read_excel(tasks_file)
        st.dataframe(df_tasks, use_container_width=True)
        if st.button("▶️ Process Tasks Upload"):
            for _, t in df_tasks.iterrows():
                c.execute(
                  "INSERT OR REPLACE INTO tasks "
                  "(labor_model_id,name,type,linked_driver,time_per_unit,frequency_per_period,primary_role) "
                  "VALUES (?,?,?,?,?,?,?)",
                  (
                    int(t["labor_model_id"]),
                    t["Taskname"],
                    t["Type"],
                    t["Linked Driver"],
                    float(t["TPU"]),
                    float(t["Frequency"]),
                    t["Role"]
                  )
                )
            conn.commit()
            st.success("✅ Tasks loaded.")
            _goto("landing")
            return

    st.markdown("---")
    if st.button("← Back to Summary"):
        _goto("landing")

# ─── 3) Forecast history (read‐only) ─────────────────────────────────────────────
def _show_forecast():
    st.header("📈 Forecast History")
    df = pd.read_sql("SELECT week_start, value FROM forecast_series ORDER BY week_start", conn)
    if df.empty:
        st.info("No forecast series uploaded yet.")
    else:
        df["week_start"] = pd.to_datetime(df["week_start"])
        st.line_chart(df.set_index("week_start")["value"])
    if st.button("← Back to Summary"):
        _goto("landing")

# ─── 4) Public render ───────────────────────────────────────────────────────────
def render():
    page = st.session_state.lp_page
    if page == "landing":
        _show_landing()
    elif page == "upload":
        _show_upload()
    elif page == "forecast":
        _show_forecast()
