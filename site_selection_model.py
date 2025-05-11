# site_selection_model.py

import streamlit as st
import pandas as pd
import plotly.express as px
import requests
from pathlib import Path

# ─── Configure your Mapbox token ─────────────────────────────────────────────
px.set_mapbox_access_token(
    "pk.eyJ1Ijoic3BpcmF0ZWNoIiwiYSI6ImNtOHp6czZ1ZzBmNHcyanM4MnRkcHQ2dTUifQ.r4eSgGg09379mRWiUchnvg"
)

def render():
    st.title("Miami Family Law Group – Location Analysis")

    # ─── CSS tweaks ────────────────────────────────────────────────────────────
    st.markdown("""
    <style>
      [data-testid="stDataFrame"] table,
      [data-testid="stDataFrame"] th,
      [data-testid="stDataFrame"] td {
        border: 1px solid #ddd !important;
      }
      [data-testid="stSlider"] input[type="range"],
      [data-testid="stRangeSlider"] input[type="range"] {
        accent-color: #1f77b4 !important;
      }
      div[data-testid="stSlider"] label,
      div[data-testid="stRangeSlider"] label {
        font-size: 18px !important;
        font-weight: 600 !important;
      }
    </style>
    """, unsafe_allow_html=True)

    # ─── 1) Load & prepare data ────────────────────────────────────────────────
    base = Path(__file__).parent
    df = pd.read_csv(base / "FL_Wealth_Ranking_Data.csv")

    # derive only the columns we need and rename for clarity
    df["Real_Median_Income"]  = df["Median_Income"]
    df["Real_DivRate"]        = df["Divorce Rate"]          # new slider
    df["Real_HH_200K"]        = df["Household200Kcount"]    # new >200K households
    df["Real_Home_Growth"]    = df["HomeValueGrowth"] * 100
    df["Real_Boat_Count"]     = df["Recreational Vessel Count"]
    df["ZIP Code"]            = df["ZIP Code"].astype(str)

    # compute slider bounds from data
    min_inc, max_inc     = int(df["Real_Median_Income"].min()), int(df["Real_Median_Income"].max())
    min_div, max_div     = float(df["Real_DivRate"].min()),      float(df["Real_DivRate"].max())
    min_priv, max_priv   = int(df["Private School Count"].min()), int(df["Private School Count"].max())
    min_vessel, max_vessel = int(df["Real_Boat_Count"].min()),    int(df["Real_Boat_Count"].max())
    min_hh200, max_hh200 = int(df["Real_HH_200K"].min()),        int(df["Real_HH_200K"].max())
    min_grw, max_grw     = float(df["Real_Home_Growth"].min()),   float(df["Real_Home_Growth"].max())

    # ─── 2) In-page filters (3×2 grid) ─────────────────────────────────────────
    c1, _, c2, __, c3 = st.columns([3,1,3,1,3])
    income_med  = c1.slider(
        "Median Income", 
        min_inc, max_inc, 
        (min_inc, max_inc), step=5000
    )
    div_rate    = c2.slider(
        "Divorce Rate (%)", 
        min_div, max_div, 
        (min_div, max_div), step=0.1
    )
    private_sch = c3.slider(
        "Private School Count", 
        min_priv, max_priv, 
        (min_priv, max_priv)
    )

    c4, ___, c5, ____, c6 = st.columns([3,1,3,1,3])
    boat_ct     = c4.slider(
        "Recreational Vessel Count", 
        min_vessel, max_vessel, 
        (min_vessel, max_vessel)
    )
    hh200       = c5.slider(
        "Households > $200K", 
        min_hh200, max_hh200, 
        (min_hh200, max_hh200)
    )
    home_grw    = c6.slider(
        "Home Value Growth (%)", 
        min_grw, max_grw, 
        (min_grw, max_grw), step=1.0
    )

    # ─── 3) Filter Data ───────────────────────────────────────────────────────
    filtered = df[
        df["Real_Median_Income"].between(*income_med) &
        df["Real_DivRate"].between(*div_rate) &
        df["Private School Count"].between(*private_sch) &
        df["Real_Boat_Count"].between(*boat_ct) &
        df["Real_HH_200K"].between(*hh200) &
        df["Real_Home_Growth"].between(*home_grw)
    ]

    # re-calc rank so 1 = highest Wealth Score
    filtered = filtered.copy()
    filtered["Rank"] = (
        filtered["Wealth Score"]
                .rank(method="first", ascending=False)
                .astype(int)
    )

    # ─── 4) Map & Top-ZIPs side-by-side ───────────────────────────────────────
    with st.container():
        map_col, table_col = st.columns([3,2])

        # 4a) Choropleth
        with map_col:
            st.subheader("📍 Florida ZIP Map")
            GITHUB_BASE = "https://raw.githubusercontent.com/Sheelgupte/Miami/main/geojson"
            geojson_url = f"{GITHUB_BASE}/fl_florida_zip_codes_geo.min.json"
            try:
                geojson = requests.get(geojson_url, timeout=5).json()
            except Exception as e:
                st.error(f"Couldn’t fetch GeoJSON:\n{e}")
                return

            max_s     = filtered["Wealth Score"].max()
            cutoff    = filtered["Wealth Score"].nlargest(5).min() if len(filtered)>=5 else max_s
            frac_cut  = cutoff / max_s if max_s>0 else 1.0

            colorscale = [
                [0.0, "lightblue"],
                [frac_cut, "blue"],
                [frac_cut, "red"],
                [1.0, "red"],
            ]

            fig_map = px.choropleth_mapbox(
                filtered, geojson=geojson,
                locations="ZIP Code", color="Wealth Score",
                range_color=(0, max_s),
                color_continuous_scale=colorscale,
                mapbox_style="mapbox://styles/mapbox/streets-v11",
                featureidkey="properties.ZCTA5CE10",
                center={"lat":27.8,"lon":-81.7}, zoom=5.7, opacity=0.6,
                hover_data={
                    "Real_Median_Income": True,
                    "Real_HH_200K":       True,
                    "Real_DivRate":       True
                }
            )
            fig_map.update_traces(
                marker_line_width=0.2,
                marker_line_color="rgba(0,0,0,0.05)"
            )
            fig_map.update_layout(height=600, margin={"l":0,"r":0,"t":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

        # 4b) Top ZIPs table
        with table_col:
            hcol, chk = st.columns([4,2])
            with hcol:
                st.subheader("👑 Top ZIP Codes")
            with chk:
                show_all = st.checkbox("Show all ZIPs", key="show_all")

            n = len(filtered) if show_all else 5
            topn = (
                filtered
                  .nlargest(n, "Wealth Score")[
                    ["Rank","ZIP Code","Area",
                     "Real_Median_Income","Real_DivRate",
                     "Real_HH_200K","Wealth Score"]
                  ]
            )
            topn.columns = [
                "Rank","ZIP","Area",
                "Median Income","Divorce Rate (%)",
                "Households > $200K","Score"
            ]

            topn["Median Income"]      = topn["Median Income"].apply(lambda x: f"${x/1000:,.2f}K")
            topn["Households > $200K"] = topn["Households > $200K"].map("{:,}".format)
            topn["Divorce Rate (%)"]   = topn["Divorce Rate (%)"].map(lambda x: f"{x:.1f}%")

            html = topn.to_html(index=False, justify="center")
            st.markdown(
                f"<div style='height:600px; overflow-y:auto; border:1px solid #ddd; border-radius:4px;'>{html}</div>",
                unsafe_allow_html=True
            )

    # ─── 5) ZIP Comparison ─────────────────────────────────────────────────────
    st.subheader("🔄 ZIP Comparison")
    zip_cols = st.columns(3)
    opts = filtered["ZIP Code"].unique().tolist()
    selected_zips = []
    for i, col in enumerate(zip_cols):
        with col:
            idx = i if i < len(opts) else len(opts)-1
            zc  = st.selectbox(f"ZIP {i+1}", opts, index=idx, key=f"zip{i}")
        selected_zips.append(zc)

    # ─── 6) ZIP Summaries ──────────────────────────────────────────────────────
    factors = [
        ("Real_Home_Growth",  "Home Value Growth"),
        ("Real_DivRate",      "Divorce Rate (%)"),
        ("Real_Boat_Count",   "Vessels"),
        ("Real_Median_Income","Median Income"),
        ("Real_HH_200K",      "Households > $200K"),
    ]
    sum_cols = st.columns(3)
    for col, zc in zip(sum_cols, selected_zips):
        row    = filtered.set_index("ZIP Code").loc[zc]
        df_sum = pd.DataFrame({
            "Metric": [lbl for _,lbl in factors],
            "Value":  [row[k] for k,_ in factors]
        })
        col.markdown(f"**{zc} – {row['Area']}**")
        col.table(df_sum)

    # ─── 7) Radar & AI Insights ───────────────────────────────────────────────
    st.subheader("📊 Radar & AI Insights")
    rcol, _, icol = st.columns([3,0.5,2])

    with rcol:
        st.subheader("Radar Chart")
        rows = []
        for zc in selected_zips:
            r = filtered.set_index("ZIP Code").loc[zc]
            for k, lbl in factors:
                rows.append({"ZIP": zc, "Metric": lbl, "Value": r[k]})
        fig_r = px.line_polar(pd.DataFrame(rows), r="Value", theta="Metric",
                              color="ZIP", line_close=True, labels={"Value":"Value"})
        st.plotly_chart(fig_r, use_container_width=True)

    with icol:
        st.subheader("AI Insights")
        sel = filtered.set_index("ZIP Code").loc[selected_zips]
        sents = []

        best = sel["Rank"].idxmin(); br = sel.loc[best]
        sents.append(f"{best} ({br['Area']}) has the highest rank (#{int(br['Rank'])}).")

        hi   = sel["Real_Median_Income"].idxmax(); hr = sel.loc[hi]
        sents.append(f"{hi} ({hr['Area']}) has the highest median income at ${hr['Real_Median_Income']:,.0f}.")

        dv   = sel["Real_DivRate"].idxmax(); dr = sel.loc[dv]
        sents.append(f"{dv} ({dr['Area']}) has the highest divorce rate of {dr['Real_DivRate']:.1f}%.")

        hh   = sel["Real_HH_200K"].idxmax(); hhrow = sel.loc[hh]
        sents.append(f"{hh} ({hhrow['Area']}) has the most households >$200K ({int(hhrow['Real_HH_200K']):,}).")

        vs   = sel["Real_Boat_Count"].idxmax(); vr = sel.loc[vs]
        sents.append(f"{vs} ({vr['Area']}) has the most vessels ({int(vr['Real_Boat_Count'])}).")

        gr   = sel["Real_Home_Growth"].idxmax(); grw = sel.loc[gr]
        sents.append(f"{gr} ({grw['Area']}) has the highest home value growth at {grw['Real_Home_Growth']:.1f}%.")

        for sentence in sents:
            st.write(sentence)
