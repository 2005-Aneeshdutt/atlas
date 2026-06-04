import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.db import get_all_sessions, get_all_results, get_session_results, init_db

st.set_page_config(page_title="ATLAS", page_icon="🔴", layout="wide")

init_db()

st.title("ATLAS - LLM Safety Evaluation Platform")

sessions = get_all_sessions()
all_results = get_all_results()

if not sessions:
    st.warning("No sessions found. Run `python main.py` to start a session.")
    st.stop()

with st.sidebar:
    st.header("Sessions")
    session_options = {
        f"{s['target_provider']}/{s['target_model']} - {s['created_at'][:16]} [{s['id'][:8]}]": s["id"]
        for s in sessions
    }
    selected_label = st.selectbox("Select session", list(session_options.keys()))
    selected_id = session_options[selected_label]
    st.divider()
    st.caption(f"Total sessions: {len(sessions)}")
    st.caption(f"Total attacks run: {len(all_results)}")

results = get_session_results(selected_id)
df = pd.DataFrame(results)

if df.empty:
    st.warning("No results for this session.")
    st.stop()

df["is_successful"] = df["is_successful"].astype(bool)

total = len(df)
successful = df["is_successful"].sum()
avg_score = df["judge_score"].mean()
vuln_rate = (successful / total * 100) if total > 0 else 0

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Attacks", total)
col2.metric("Successful Jailbreaks", int(successful))
col3.metric("Vulnerability Rate", f"{vuln_rate:.1f}%")
col4.metric("Avg Judge Score", f"{avg_score:.2f}/10")

st.divider()

col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Results by Category")
    cat_df = df.groupby("category").agg(
        total=("id", "count"),
        successful=("is_successful", "sum"),
    ).reset_index()
    cat_df["safe"] = cat_df["total"] - cat_df["successful"]
    fig = px.bar(
        cat_df, x="category", y=["successful", "safe"], barmode="stack",
        color_discrete_map={"successful": "#ef4444", "safe": "#22c55e"},
        labels={"value": "Count", "variable": ""},
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    st.subheader("Judge Score Distribution")
    fig2 = px.histogram(
        df, x="judge_score", nbins=10,
        color="is_successful",
        color_discrete_map={True: "#ef4444", False: "#22c55e"},
        labels={"judge_score": "Score (0-10)", "is_successful": "Jailbreak"},
    )
    st.plotly_chart(fig2, use_container_width=True)

st.subheader("Violation Types")
vtype_df = df[df["is_successful"]]["violation_type"].value_counts().reset_index()
if not vtype_df.empty:
    vtype_df.columns = ["violation_type", "count"]
    fig3 = px.pie(vtype_df, names="violation_type", values="count", hole=0.4)
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No successful attacks in this session.")
