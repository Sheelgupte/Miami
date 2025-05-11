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

    # New maxima / direct columns
    MAX_HOMES = 2360
    MAX_INC   = 300_000
    MAX_BOAT  = 800

    df["Real_Median_Income"] = df["Median_Income"]
    df["Real_DivRate"]       = df["Divorce Rate"]        # note: Real_DivRate
    df["Real_Home_Count"]    = df["Home1MCount"]
    df["Real_Home_Growth"]   = df["HomeValueGrowth"] * 100
    df["Real_Boat_Count"]    = df["Recreational Vessel Count"]
    df["ZIP Code"]           = df["ZIP Code"].astype(str)
    

    # ─── 2) In-page filters (3×2) ──────────────────────────────────────────────
    c1, _, c2, __, c3 = st.columns([3,1,3,1,3])
    income_med  = c1.slider("Median Income", 20_000, MAX_INC, (20_000, MAX_INC), step=5_000)
    div_rate = c2.slider("Divorce Rate (%)", 0.0, df["Real_DivRate"].max(), (0.0, df["Real_DivRate"].max()), step=0.1)
    private_sch = c3.slider("Private School Count", 0, 15, (0, 15))

    c4, ___, c5, ____, c6 = st.columns([3,1,3,1,3])
    boat_ct     = c4.slider("Recreational Vessel Count", 0, MAX_BOAT, (0, MAX_BOAT))
    homes_gt_1m = c5.slider("Homes > $1M Count", 0, MAX_HOMES, (0, MAX_HOMES))
    home_grw    = c6.slider("Home Value Growth (%)", 0.0, 100.0, (0.0, 100.0), step=1.0)

    # ─── 3) Filter Data ───────────────────────────────────────────────────────
    filtered = df[
        df["Real_Median_Income"].between(*income_med) &
        df["Real_DivRate"].between(*div_rate) &
        df["Private School Count"].between(*private_sch) &
        df["Real_Boat_Count"].between(*boat_ct) &
        df["Real_Home_Count"].between(*homes_gt_1m) &
        df["Real_Home_Growth"].between(*home_grw)
    ]

    # ─── 4) Map & Top-ZIPs side-by-side ───────────────────────────────────────
    with st.container():
        map_col, table_col = st.columns([3,2])

        # ---- 4a) Map ----
        with map_col:
            st.subheader("📍 Florida ZIP Map")
            GITHUB_BASE = "https://raw.githubusercontent.com/Sheelgupte/Miami/main/geojson"
            geojson_url = f"{GITHUB_BASE}/fl_florida_zip_codes_geo.min.json"
            try:
                geojson = requests.get(geojson_url, timeout=5).json()
            except Exception as e:
                st.error(f"Couldn’t fetch GeoJSON from:\n{geojson_url}\n\n{e}")
                return
                
            # 1) figure out the absolute threshold = the 5th‐highest wealth score
            max_s = filtered["Wealth Score"].max()
            top8 = filtered["Wealth Score"].nlargest(8)
            threshold_abs = top8.min() if len(top8) >= 8 else max_s  # fallback if <8 rows
            
            # 2) convert to a 0–1 fraction of the domain
            rel_thr = threshold_abs / max_s if max_s > 0 else 1.0
            
            # 3) build your colorscale
            colorscale = [
                [0.0, "lightblue"],   # lowest scores → lightblue
                [rel_thr, "blue"],    # up to the 5th-highest → gradient → blue
                [rel_thr, "red"],     # then everything above that → red
                [1.0, "red"],         # through the max → red
            ]

            fig_map = px.choropleth_mapbox(
                filtered,
                geojson=geojson,
                locations="ZIP Code",
                color="Wealth Score",
                range_color=(0,max_s),
                color_continuous_scale=colorscale,
                mapbox_style="mapbox://styles/mapbox/streets-v11",
                featureidkey="properties.ZCTA5CE10",
                center={"lat":27.8,"lon":-81.7},
                zoom=5.7,
                opacity=0.6,
                hover_data={
                    "Real_Median_Income": True,
                    "Real_Home_Count":    True,
                    "Private School Count": True
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
            hcol, chk = st.columns([4,2])
            with hcol: st.subheader("👑 Top ZIP Codes")
            with chk:  show_all = st.checkbox("Show all ZIPs", key="show_all")

            n = len(filtered) if show_all else 8
            topn = (
                filtered
                  .nlargest(n, "Wealth Score")
                  [[
                    "Rank",
                    "ZIP Code",
                    "Area",
                    "Real_Median_Income",
                    "Private School Count",
                    "Real_Home_Count",
                    "Wealth Score"
                  ]]
            )
            topn.columns = [
                "Rank",
                "ZIP",
                "Area",
                "Median Income",
                "Priv Schools",
                "Homes > $1M",
                "Score"
            ]

            # format Median Income as $###.##K
            topn["Median Income"] = topn["Median Income"]\
                .apply(lambda x: f"${x/1000:,.2f}K")
            # format Homes count with commas
            topn["Homes > $1M"] = topn["Homes > $1M"]\
                .astype(int)\
                .map("{:,}".format)

            # lock height & scroll
            html = topn.to_html(index=False, justify="center")
            scrollable = f"""
            <div style="height:600px; overflow-y:auto; border:1px solid #ddd; border-radius:4px;">
              {html}
            </div>
            """
            st.markdown(scrollable, unsafe_allow_html=True)

    # ─── 5) ZIP Comparison ─────────────────────────────────────────────────────
    st.subheader("🔄 ZIP Comparison")
    zip_cols = st.columns(3)
    opts = filtered["ZIP Code"].unique().tolist()
    selected_zips = []
    for i, col in enumerate(zip_cols):
        with col:
            zc = st.selectbox(f"ZIP {i+1}", opts, index=i if i<len(opts) else 0, key=f"zip{i}")
        selected_zips.append(zc)

    # ─── 6) ZIP Summaries ──────────────────────────────────────────────────────
    factors = [
        ("Real_Home_Growth",   "Home Value Growth"),
        ("Real_DivRate",       "Divorce Rate (%)"),
        ("Real_Boat_Count",    "Vessels"),
        ("Real_Median_Income", "Median Income"),
        ("Real_Home_Count",    "Homes > $1M"),
    ]

    sum_cols = st.columns(3)
    for col, zc in zip(sum_cols, selected_zips):
        row = filtered.set_index("ZIP Code").loc[zc]
        df_sum = pd.DataFrame({
            "Metric": [lbl for _, lbl in factors],
            "Value":  [row[k] for k, _ in factors]
        })
        col.markdown(f"**{zc} – {row['Area']}**")
        col.table(df_sum)


    # ─── 7) Radar & AI Insights ───────────────────────────────────────────────
    st.subheader("📊 Radar & AI Insights")
    rcol, _, icol = st.columns([3,0.5,2])

    with rcol:
        st.subheader("Radar Chart")
        radar_rows = []
        for zc in selected_zips:
            row = filtered.set_index("ZIP Code").loc[zc]
            for k,lbl in factors:
                radar_rows.append({"ZIP": zc, "Metric": lbl, "Value": row[k]})
        fig_radar = px.line_polar(
            pd.DataFrame(radar_rows),
            r="Value", theta="Metric",
            color="ZIP", line_close=True,
            labels={"Value":"Value"}
        )
        st.plotly_chart(fig_radar, use_container_width=True)

    with icol:
        st.subheader("AI Insights")
        sel = filtered.set_index("ZIP Code").loc[selected_zips]
        sentences = []

        # Highest rank
        best = sel['Rank'].idxmin(); b=sel.loc[best]
        sentences.append(f"{best} ({b['Area']}) has the highest rank (#{int(b['Rank'])}).")

        # Highest median income
        hi = sel['Real_Median_Income'].idxmax(); h=sel.loc[hi]
        sentences.append(f"{hi} ({h['Area']}) has the highest median income at ${h['Real_Median_Income']:,.0f}.")

        # Highest homes >$1M
        hm = sel['Real_Home_Count'].idxmax(); hmrow=sel.loc[hm]
        sentences.append(f"{hm} ({hmrow['Area']}) has the most homes >$1M ({int(hmrow['Real_Home_Count']):,}).")

        # Most vessels
        vs = sel['Real_Boat_Count'].idxmax(); vr=sel.loc[vs]
        sentences.append(f"{vs} ({vr['Area']}) has the most vessels ({int(vr['Real_Boat_Count'])}).")

        # Most private schools
        ps = sel['Private School Count'].idxmax(); pr=sel.loc[ps]
        sentences.append(f"{ps} ({pr['Area']}) has the most private schools ({int(pr['Private School Count'])}).")

        # Highest wealth
        ws = sel['Wealth Score'].idxmax(); wr=sel.loc[ws]
        sentences.append(f"{ws} ({wr['Area']}) has the highest wealth score of {wr['Wealth Score']:.2f}.")

        for s in sentences:
            st.write(s)
