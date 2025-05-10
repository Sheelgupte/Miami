# site_selection_model.py

import streamlit as st
import pandas as pd
import plotly.express as px
import json, zipfile
from pathlib import Path

# ─── Configure Mapbox token ────────────────────────────────────────────────────
px.set_mapbox_access_token(
    "pk.eyJ1Ijoic3BpcmF0ZWNoIiwiYSI6ImNtOHp6czZ1ZzBmNHcyanM4MnRkcHQ2dTUifQ.r4eSgGg09379mRWiUchnvg"
)
def render():
    st.title("Miami Family Law Group – Location Analysis")

   # ─── CSS tweaks ─────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
      /* light-grey borders on tables */
      [data-testid="stDataFrame"] table,
      [data-testid="stDataFrame"] th,
      [data-testid="stDataFrame"] td {
        border: 1px solid #ddd !important;
      }
      /* blue sliders */
      [data-testid="stSlider"] input[type="range"],
      [data-testid="stRangeSlider"] input[type="range"] {
        accent-color: #1f77b4 !important;
      }
      /* larger, bold slider labels */
      div[data-testid="stSlider"] label,
      div[data-testid="stRangeSlider"] label {
        font-size: 18px !important;
        font-weight: 600 !important;
      }
    </style>
    """, unsafe_allow_html=True)
    # ─── 1) Load & prepare data ───────────────────────────────────────────────
    base = Path(__file__).parent
    df = pd.read_csv(base / "FL_Wealth_Ranking_Data.csv")

    MAX_HOME, MAX_INC, MAX_BOAT = 5_000_000, 300_000, 15
    df["Real_Median_Income"] = df["Median_Income"] * MAX_INC
    df["Real_Mean_Income"]   = df["Mean_Income"]   * MAX_INC
    df["Real_Home_Value"]    = df["HomeValue_2025_03"] * MAX_HOME
    df["Real_Home_Growth"]   = df["HomeValueGrowth"]   * 100
    df["Real_Boat_Count"]    = df["Recreational Vessel Count"] * MAX_BOAT
    df["ZIP Code"]           = df["ZIP Code"].astype(str)

    # ─── 2) In‐page filters (3×2 layout with spacing) ─────────────────────────

    col1, gap1, col2, gap2, col3 = st.columns([3, 1, 3, 1, 3])
    income_med  = col1.slider("Median Income", 20_000, MAX_INC, (20_000, MAX_INC), step=5_000)
    income_mean = col2.slider("Mean Income",   20_000, MAX_INC, (20_000, MAX_INC), step=5_000)
    private_sch = col3.slider("Private School Count", 0, 15, (0, 15))

    col4, gap3, col5, gap4, col6 = st.columns([3, 1, 3, 1, 3])
    boat_ct  = col4.slider("Recreational Vessel Count", 0, 15, (0, 15))
    home_val = col5.slider("Home Value", 100_000, MAX_HOME, (100_000, MAX_HOME), step=100_000)
    home_grw = col6.slider("Home Value Growth (%)", 0.0, 100.0, (0.0, 100.0), step=1.0)

    # ─── 3) Apply filters ───────────────────────────────────────────────────────
 
    filtered = df[
        df["Real_Median_Income"].between(*income_med) &
        df["Real_Mean_Income"].between(*income_mean) &
        df["Private School Count"].between(*private_sch) &
        df["Real_Boat_Count"].between(*boat_ct) &
        df["Real_Home_Value"].between(*home_val) &
        df["Real_Home_Growth"].between(*home_grw)
    ]

    # ─── 4) Map & Top ZIPs side by side ────────────────────────────────────────
    with st.container():
        col_map, col_table = st.columns([3, 2])

        # ---- Map (left) ----
        with col_map:
            # load per‐state GeoJSON or fallback
            st.subheader("📍 Florida ZIP Map")
            fname = "fl_florida_zip_codes_geo.min.json"
            geojson = None
            geo_dir = base / "State-zip-code-GeoJSON-master"
            if (geo_dir / fname).exists():
                geojson = json.loads((geo_dir / fname).read_text())
            elif (base / "jsonfile.zip").exists():
                with zipfile.ZipFile(base / "jsonfile.zip") as z:
                    member = f"State-zip-code-GeoJSON-master/{fname}"
                    if member in z.namelist():
                        geojson = json.loads(z.read(member))
            if geojson is None:
                fallback = base / "zip_codes_geojson.json"
                if fallback.exists():
                    geojson = json.loads(fallback.read_text())
                else:
                    st.error("GeoJSON not found.")
                    return

            # custom colorscale: lightblue up to 0.6, then bright red
            colorscale = [
                [0.0, "lightblue"],
                [0.4, "blue"],
                [0.4, "red"],
                [1.0, "red"],
            ]

            fig_map = px.choropleth_mapbox(
                filtered,
                geojson=geojson,
                locations="ZIP Code",
                color="Wealth Score",
                range_color=(0, 1),
                color_continuous_scale=colorscale,
                mapbox_style="mapbox://styles/mapbox/streets-v11",
                featureidkey="properties.ZCTA5CE10",
                center={"lat": 27.8, "lon": -81.7},
                zoom=5.7,
                opacity=0.6,
                hover_data={
                    "Real_Median_Income": True,
                    "Real_Home_Value": True,
                    "Private School Count": True
                }
            )
            # make ZIP boundaries nearly transparent
            fig_map.update_traces(
                marker_line_width=0.2,
                marker_line_color='rgba(0,0,0,0.05)',
                selector=dict(type='choroplethmapbox')
            )
            fig_map.update_layout(height=600, margin={"l":0, "r":0, "t":0, "b":0})
            st.plotly_chart(fig_map, use_container_width=True)

        # ---- Top ZIPs table (right) ----
        with col_table:
            hdr_col, chk_col = st.columns([4, 2])
            with hdr_col:
                st.subheader("👑 Top ZIP Codes")
            with chk_col:
                show_all = st.checkbox("Show all ZIPs", key="show_all")

            n = len(filtered) if show_all else 5
            topn = filtered.nlargest(n, "Wealth Score")[[
                "ZIP Code",
                "Geographic Area Name",
                "Real_Median_Income",
                "Private School Count",
                "Real_Home_Value",
                "Wealth Score"
            ]]
            topn.columns = [
                "ZIP",
                "Area",
                "Median Income",
                "Priv Schools",
                "Home Value",
                "Score"
            ]
            st.dataframe(topn, height=600, use_container_width=True)

    # ─── 5) ZIP Comparison selectors ────────────────────────────────────────────
    st.subheader("🔄 ZIP Comparison")
    zip_cols = st.columns(3)
    opts = filtered["ZIP Code"].unique().tolist()
    selected_zips = []
    for i, col in enumerate(zip_cols):
        default_idx = i if i < len(opts) else 0
        with col:
            zc = col.selectbox(f"ZIP {i+1}", opts, index=default_idx, key=f"zip{i+1}")
        selected_zips.append(zc)

    # ─── 6) ZIP Summaries ───────────────────────────────────────────────────────
    sum_cols = st.columns(3)
    factors = [
        ("HomeValue_2025_03",         "Home Value"),
        ("HomeValueGrowth",           "Home Value Growth"),
        ("Wealth Score",              "Wealth Score"),
        ("Recreational Vessel Count", "Vessels"),
        ("Median_Income",             "Median Income"),
        ("Mean_Income",               "Mean Income")
    ]
    for col, zc in zip(sum_cols, selected_zips):
        row = filtered.set_index("ZIP Code").loc[zc]
        df_sum = pd.DataFrame({
            "Metric": [label for _, label in factors],
            "Value":  [row[key] for key, _ in factors]
        })
        col.markdown(f"**{zc} – {row['Geographic Area Name']}**")
        col.table(df_sum)

    # ─── 7) Radar Chart & AI Insights ──────────────────────────────────────────
    st.subheader("📊 Radar & AI Insights")
    radar_col, spacer, insights_col = st.columns([3, 0.5, 2])

    with radar_col:
        st.subheader("Radar Chart")
        radar_rows = []
        for zc in selected_zips:
            row = filtered.set_index("ZIP Code").loc[zc]
            for key, label in factors:
                radar_rows.append({"ZIP": zc, "Metric": label, "Value": row[key]})
        radar_df = pd.DataFrame(radar_rows)
        fig_radar = px.line_polar(
            radar_df,
            r="Value",
            theta="Metric",
            color="ZIP",
            line_close=True,
            labels={"Value": "Value"}
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with insights_col:
        st.subheader("AI Insights")
        sel_df = filtered.set_index("ZIP Code").loc[selected_zips]
        sentences = []

        br_zip = sel_df['Rank'].idxmin(); br = sel_df.loc[br_zip]
        sentences.append(f"{br_zip} ({br['Geographic Area Name']}) has the highest rank (#{int(br['Rank'])}) among selected ZIPs.")

        bi_zip = sel_df['Real_Median_Income'].idxmax(); bi = sel_df.loc[bi_zip]
        sentences.append(f"{bi_zip} ({bi['Geographic Area Name']}) has the highest median income at ${bi['Real_Median_Income']:,.0f}.")

        bh_zip = sel_df['Real_Home_Value'].idxmax(); bh = sel_df.loc[bh_zip]
        sentences.append(f"{bh_zip} ({bh['Geographic Area Name']}) has the highest average home value at ${bh['Real_Home_Value']:,.0f}.")

        bv_zip = sel_df['Real_Boat_Count'].idxmax(); bv = sel_df.loc[bv_zip]
        sentences.append(f"{bv_zip} ({bv['Geographic Area Name']}) has the most recreational vessels with approximately {int(bv['Real_Boat_Count'])}.")

        ps_zip = sel_df['Private School Count'].idxmax(); ps = sel_df.loc[ps_zip]
        sentences.append(f"{ps_zip} ({ps['Geographic Area Name']}) has the most private schools with {int(ps['Private School Count'])}.")

        ws_zip = sel_df['Wealth Score'].idxmax(); ws = sel_df.loc[ws_zip]
        sentences.append(f"{ws_zip} ({ws['Geographic Area Name']}) has the highest wealth score of {ws['Wealth Score']:.2f}.")

        for s in sentences:
            st.write(s)
