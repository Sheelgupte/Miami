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

    # ─── 1) Load & prepare data ────────────────────────────────────────────────
    base = Path(__file__).parent
    df = pd.read_csv(base / "FL_Wealth_Ranking_Data.csv")

    # derive “real” metrics directly from your columns
    df["Real_Median_Income"]  = df["Median_Income"]
    df["Real_Mean_Income"]    = df["Mean_Income"]
    df["Real_Home_Count"]     = df["Home1MCount"]
    df["Real_Home_Growth"]    = df["HomeValueGrowth"] * 100
    df["Real_Boat_Count"]     = df["Recreational Vessel Count"]
    df["Real_Divorce_Rate"]   = df["Divorce Rate"] * 100  # decimal→%
    df["ZIP Code"]            = df["ZIP Code"].astype(str)

    # ─── 2) In-page filters (dynamic 3×2 grid) ────────────────────────────────
    # compute each slider’s min/max from the full dataset
    min_med, max_med   = int(df["Real_Median_Income"].min()), int(df["Real_Median_Income"].max())
    min_mean, max_mean = int(df["Real_Mean_Income"].min()),   int(df["Real_Mean_Income"].max())
    min_priv, max_priv = int(df["Private School Count"].min()), int(df["Private School Count"].max())
    min_boat, max_boat = int(df["Real_Boat_Count"].min()),    int(df["Real_Boat_Count"].max())
    min_homes, max_homes = int(df["Real_Home_Count"].min()),  int(df["Real_Home_Count"].max())
    min_grw, max_grw   = float(df["Real_Home_Growth"].min()), float(df["Real_Home_Growth"].max())
    min_div, max_div   = float(df["Real_Divorce_Rate"].min()), float(df["Real_Divorce_Rate"].max())

    c1, _, c2, __, c3 = st.columns([3,1,3,1,3])
    income_med  = c1.slider("Median Income", min_med, max_med, (min_med, max_med), step=5000)
    income_mean = c2.slider("Mean Income",   min_mean, max_mean, (min_mean, max_mean), step=5000)
    private_sch = c3.slider("Private School Count", min_priv, max_priv, (min_priv, max_priv))

    c4, ___, c5, ____, c6 = st.columns([3,1,3,1,3])
    boat_ct      = c4.slider("Recreational Vessel Count", min_boat, max_boat, (min_boat, max_boat))
    homes_gt_1m  = c5.slider("Homes > $1M Count",        min_homes, max_homes, (min_homes, max_homes))
    home_grw     = c6.slider("Home Value Growth (%)",   min_grw, max_grw, (min_grw, max_grw))
    divorce_rt   = c6.slider("Divorce Rate (%)",        min_div, max_div, (min_div, max_div))

    # ─── 3) Filter Data ───────────────────────────────────────────────────────
    filtered = df[
        df["Real_Median_Income"].between(*income_med) &
        df["Real_Mean_Income"].between(*income_mean) &
        df["Private School Count"].between(*private_sch) &
        df["Real_Boat_Count"].between(*boat_ct) &
        df["Real_Home_Count"].between(*homes_gt_1m) &
        df["Real_Home_Growth"].between(*home_grw) &
        df["Real_Divorce_Rate"].between(*divorce_rt)
    ]

    # recompute “1 = highest wealth” rank on the filtered set
    filtered = filtered.copy()
    filtered["Rank"] = (
        filtered["Wealth Score"]
          .rank(method="first", ascending=False)
          .astype(int)
    )

    # ─── 4) Map & Top-ZIPs side by side ───────────────────────────────────────
    with st.container():
        map_col, table_col = st.columns([3,2])

        # ---- 4a) Map ----
        with map_col:
            st.subheader("📍 Florida ZIP Map")

            # fetch GeoJSON
            GITHUB_BASE = "https://raw.githubusercontent.com/Sheelgupte/Miami/main/geojson"
            geojson_url = f"{GITHUB_BASE}/fl_florida_zip_codes_geo.min.json"
            try:
                gz = requests.get(geojson_url, timeout=5).json()
            except Exception as e:
                st.error(f"Couldn’t fetch GeoJSON from:\n{geojson_url}\n\n{e}")
                return

            # only top-5 wealth ZIPs in red
            max_s        = filtered["Wealth Score"].max()
            top5_scores  = filtered["Wealth Score"].nlargest(5)
            thr_abs      = top5_scores.min() if len(top5_scores)>=5 else max_s
            thr_rel      = thr_abs / max_s if max_s>0 else 1.0

            colorscale = [
                [0.0, "lightblue"],
                [thr_rel, "blue"],
                [thr_rel, "red"],
                [1.0, "red"],
            ]

            fig_map = px.choropleth_mapbox(
                filtered,
                geojson=gz,
                locations="ZIP Code",
                color="Wealth Score",
                range_color=(0, max_s),
                color_continuous_scale=colorscale,
                mapbox_style="mapbox://styles/mapbox/streets-v11",
                featureidkey="properties.ZCTA5CE10",
                center={"lat":27.8,"lon":-81.7},
                zoom=5.7,
                opacity=0.6,
                hover_data={
                    "Real_Median_Income": True,
                    "Real_Home_Count":    True,
                    "Real_Divorce_Rate":  True
                }
            )
            fig_map.update_traces(
                marker_line_width=0.2,
                marker_line_color='rgba(0,0,0,0.05)'
            )
            fig_map.update_layout(height=600, margin={"l":0,"r":0,"t":0,"b":0})
            st.plotly_chart(fig_map, use_container_width=True)

        # ---- 4b) Top ZIPs table ----
        with table_col:
            hdr, chk = st.columns([4,2])
            with hdr: st.subheader("👑 Top ZIP Codes")
            with chk:  show_all = st.checkbox("Show all ZIPs", key="show_all")

            n = len(filtered) if show_all else 5
            topn = (
                filtered
                  .nlargest(n, "Wealth Score")
                  [[
                    "Rank",
                    "ZIP Code",
                    "Area",
                    "Real_Median_Income",
                    "Real_Divorce_Rate",
                    "Real_Home_Count",
                    "Wealth Score"
                  ]]
            )
            topn.columns = [
                "Rank",
                "ZIP",
                "Area",
                "Median Income",
                "Divorce Rate (%)",
                "Homes > $1M",
                "Score"
            ]

            # format Median Income and Homes
            topn["Median Income"] = topn["Median Income"]\
                .apply(lambda x: f"${x/1000:,.2f}K")
            topn["Homes > $1M"]   = topn["Homes > $1M"]\
                .astype(int).map("{:,}".format)
            topn["Divorce Rate (%)"] = topn["Divorce Rate (%)"]\
                .map(lambda x: f"{x:.1f}%")

            # lock table to map height with scroll
            html = topn.to_html(index=False, justify="center")
            st.markdown(
                f"<div style='height:600px; overflow-y:auto; border:1px solid #ddd; border-radius:4px;'>"
                + html +
                "</div>",
                unsafe_allow_html=True
            )

    # ─── 5) ZIP Comparison ─────────────────────────────────────────────────────
    st.subheader("🔄 ZIP Comparison")
    zip_cols = st.columns(3)
    opts = filtered["ZIP Code"].unique().tolist()
    selected_zips = []
    for i,col in enumerate(zip_cols):
        with col:
            z = st.selectbox(f"ZIP {i+1}", opts, index=(i if i<len(opts) else 0), key=f"zip{i+1}")
        selected_zips.append(z)

    # ─── 6) ZIP Summaries ──────────────────────────────────────────────────────
    summary_factors = [
        ("HomeValueGrowth",  "Home Value Growth"),
        ("Wealth Score",     "Wealth Score"),
        ("Recreational Vessel Count", "Vessels"),
        ("Median_Income",    "Median Income"),
        ("Real_Divorce_Rate","Divorce Rate (%)"),
        ("Real_Home_Count",  "Homes > $1M")
    ]
    sum_cols = st.columns(3)
    for col, zc in zip(sum_cols, selected_zips):
        row = filtered.set_index("ZIP Code").loc[zc]
        df_sum = pd.DataFrame({
            "Metric": [lbl for _,lbl in summary_factors],
            "Value":  [row[k] for k,_ in summary_factors]
        })
        col.markdown(f"**{zc} – {row['Area']}**")
        col.table(df_sum)

    # ─── 7) Radar & AI Insights ───────────────────────────────────────────────
    st.subheader("📊 Radar & AI Insights")

    # radar uses divorce instead of wealth
    radar_factors = [
        ("HomeValueGrowth",  "Home Value Growth"),
        ("Real_Divorce_Rate","Divorce Rate (%)"),
        ("Recreational Vessel Count", "Vessels"),
        ("Median_Income",    "Median Income"),
        ("Mean_Income",      "Mean Income"),
        ("Real_Home_Count",  "Homes > $1M")
    ]

    rcol, _, icol = st.columns([3,0.5,2])
    with rcol:
        st.subheader("Radar Chart")
        radar_rows = []
        for zc in selected_zips:
            data = filtered.set_index("ZIP Code").loc[zc]
            for key,label in radar_factors:
                radar_rows.append({"ZIP": zc, "Metric": label, "Value": data[key]})
        radar_df = pd.DataFrame(radar_rows)
        fig_r = px.line_polar(
            radar_df, r="Value", theta="Metric",
            color="ZIP", line_close=True,
            labels={"Value":"Value"}
        )
        st.plotly_chart(fig_r, use_container_width=True)

    # AI Insights: add 7th sentence about divorce
    with icol:
        st.subheader("AI Insights")
        sel = filtered.set_index("ZIP Code").loc[selected_zips]
        sentences = []

        # 1) highest rank
        best = sel['Rank'].idxmin(); b = sel.loc[best]
        sentences.append(f"{best} ({b['Area']}) has the highest rank (#{int(b['Rank'])}).")

        # 2) highest median income
        hi = sel['Real_Median_Income'].idxmax(); h = sel.loc[hi]
        sentences.append(f"{hi} ({h['Area']}) has the highest median income at ${h['Real_Median_Income']:,.0f}.")

        # 3) highest homes >$1M
        hm = sel['Real_Home_Count'].idxmax(); hmrow = sel.loc[hm]
        sentences.append(f"{hm} ({hmrow['Area']}) has the most homes >$1M ({int(hmrow['Real_Home_Count']):,}).")

        # 4) most vessels
        vs = sel['Real_Boat_Count'].idxmax(); vr = sel.loc[vs]
        sentences.append(f"{vs} ({vr['Area']}) has the most vessels ({int(vr['Real_Boat_Count'])}).")

        # 5) most private schools
        ps = sel['Private School Count'].idxmax(); pr=sel.loc[ps]
        sentences.append(f"{ps} ({pr['Area']}) has the most private schools ({int(pr['Private School Count'])}).")

        # 6) highest wealth
        ws = sel['Wealth Score'].idxmax(); wr=sel.loc[ws]
        sentences.append(f"{ws} ({wr['Area']}) has the highest wealth score of {wr['Wealth Score']:.2f}.")

        # 7) highest divorce rate
        dr = sel['Real_Divorce_Rate'].idxmax(); drw = sel.loc[dr]
        sentences.append(f"{dr} ({drw['Area']}) has the highest divorce rate of {drw['Real_Divorce_Rate']:.1f}%.")

        for s in sentences:
            st.write(s)
