import os
import sys
import streamlit as st
import pandas as pd

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
