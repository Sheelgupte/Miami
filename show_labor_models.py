# ─── Show Labor Models (replace your old version) ─────────────────────────────
def show_labor_models():
    st.title("🛠️ Manage Labor Models")
    st.write("Define your models manually or bulk‐upload Roles & Tasks via Excel.")

    # — Roles bulk upload —
    st.subheader("📥 Upload Roles via Excel")
    st.markdown("Your Excel **must** include these columns exactly:")
    st.markdown("""
    - `labor_model_id` (int, FK)  
    - `name` (e.g. `Server`, `Cook`)  
    - `fte_needed` (float)
    """)
    roles_file = st.file_uploader("Select Roles Excel", type=["xlsx","xls"], key="roles_upload")
    if roles_file:
        df_roles = pd.read_excel(roles_file)
        st.dataframe(df_roles, use_container_width=True)

        if st.button("▶️ Process Roles Upload"):
            for _, row in df_roles.iterrows():
                c.execute("""
                  INSERT OR REPLACE INTO roles
                  (labor_model_id,name,fte_needed)
                  VALUES (?,?,?)
                """, (
                  int(row["labor_model_id"]),
                  row["name"],
                  float(row["fte_needed"])
                ))
            conn.commit()
            st.success("✅ Roles bulk‐loaded.")
            st.experimental_rerun()

    st.markdown("---")

    # — Tasks bulk upload —
    st.subheader("📥 Upload Tasks via Excel")
    st.markdown("Your Excel **must** include these columns exactly:")
    st.markdown("""
    - `labor_model_id` (int, FK)  
    - `Task`  
    - `Type` (`Fixed`/`Variable`)  
    - `Linked Driver`  
    - `Time per Unit` (hours per unit)  
    - `Frequency per Period` (for Fixed)  
    - `Duration` (hrs, for Fixed)  
    - `Primary Role`
    """)
    tasks_file = st.file_uploader("Select Tasks Excel", type=["xlsx","xls"], key="tasks_upload")
    if tasks_file:
        df_tasks = pd.read_excel(tasks_file)
        st.dataframe(df_tasks, use_container_width=True)

        if st.button("▶️ Process Tasks Upload"):
            # You’ll need a tasks table – this is just a stub example
            for _, row in df_tasks.iterrows():
                c.execute("""
                  INSERT OR REPLACE INTO tasks
                  (labor_model_id, name, type, linked_driver, time_per_unit,
                   frequency_per_period, duration, primary_role)
                  VALUES (?,?,?,?,?,?,?,?)
                """, (
                  int(row["labor_model_id"]),
                  row["Task"],
                  row["Type"],
                  row["Linked Driver"],
                  float(row.get("Time per Unit") or 0),
                  float(row.get("Frequency per Period") or 0),
                  float(row.get("Duration") or 0),
                  row["Primary Role"]
                ))
            conn.commit()
            st.success("✅ Tasks bulk‐loaded.")

    st.markdown("---")
    if st.button("← Back to Landing"):
        go_to("Landing")
