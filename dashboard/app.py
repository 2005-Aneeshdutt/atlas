import os
import sys
import streamlit as st
import pandas as pd
import plotly.express as px

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.storage.db import get_all_sessions, get_all_results, get_session_results, init_db

st.set_page_config(page_title="ATLAS", page_icon="🔴", layout="wide")

init_db()

st.title("ATLAS — LLM Safety Evaluation Platform")

sessions = get_all_sessions()
all_results = get_all_results()

if not sessions:
    st.warning("No sessions found. Run `python main.py` to start a session.")
    st.stop()

SEVERITY_WEIGHTS = {"high": 3, "medium": 2, "low": 1}

with st.sidebar:
    st.header("Sessions")
    session_options = {
        f"{s['target_provider']}/{s['target_model']} — {s['created_at'][:16]} [{s['id'][:8]}]": s["id"]
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
if "severity" not in df.columns:
    df["severity"] = "medium"
df["severity"] = df["severity"].fillna("medium")

total = len(df)
successful = df["is_successful"].sum()
avg_score = df["judge_score"].mean()
vuln_rate = (successful / total * 100) if total > 0 else 0

total_weight = df["severity"].map(SEVERITY_WEIGHTS).sum()
vuln_weight = df[df["is_successful"]]["severity"].map(SEVERITY_WEIGHTS).sum()
weighted_rate = (vuln_weight / total_weight * 100) if total_weight > 0 else 0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Attacks", total)
col2.metric("Successful Jailbreaks", int(successful))
col3.metric("Vulnerability Rate", f"{vuln_rate:.1f}%")
col4.metric("Weighted Risk Score", f"{weighted_rate:.1f}%",
            help="Weights each attack by severity: high=3, medium=2, low=1")
col5.metric("Avg Judge Score", f"{avg_score:.2f}/10")

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

col_sev, col_vtype = st.columns(2)

with col_sev:
    st.subheader("Vulnerability by Severity")
    sev_df = df.groupby("severity").agg(
        total=("id", "count"),
        successful=("is_successful", "sum"),
    ).reset_index()
    sev_df["rate"] = (sev_df["successful"] / sev_df["total"] * 100).round(1)
    sev_order = ["high", "medium", "low"]
    sev_df["severity"] = pd.Categorical(sev_df["severity"], categories=sev_order, ordered=True)
    sev_df = sev_df.sort_values("severity")
    fig4 = px.bar(
        sev_df, x="severity", y="rate",
        color="severity",
        color_discrete_map={"high": "#ef4444", "medium": "#f97316", "low": "#22c55e"},
        labels={"rate": "Vulnerability Rate (%)", "severity": "Severity"},
        text="rate",
    )
    fig4.update_traces(texttemplate="%{text:.1f}%", textposition="outside")
    st.plotly_chart(fig4, use_container_width=True)

with col_vtype:
    st.subheader("Violation Types")
    vtype_df = df[df["is_successful"]]["violation_type"].value_counts().reset_index()
    if not vtype_df.empty:
        vtype_df.columns = ["violation_type", "count"]
        fig3 = px.pie(vtype_df, names="violation_type", values="count", hole=0.4)
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No successful attacks in this session.")

st.subheader("Attack Results")
display_df = df[["name", "category", "severity", "judge_score", "is_successful", "violation_type", "retry_count"]].copy()
display_df.columns = ["Attack", "Category", "Severity", "Score", "Jailbreak", "Violation Type", "Retries"]

SEVERITY_EMOJI = {"high": "High", "medium": "Med", "low": "Low"}
display_df["Severity"] = display_df["Severity"].map(lambda s: SEVERITY_EMOJI.get(s, s))


def highlight_row(row):
    color = "background-color: #fecaca" if row["Jailbreak"] else "background-color: #bbf7d0"
    return [color] * len(row)


st.dataframe(
    display_df.style.apply(highlight_row, axis=1),
    use_container_width=True,
    height=400,
)

st.divider()
st.subheader("Attack Inspector")
attack_names = df["name"].tolist()
selected_attack = st.selectbox("Select attack to inspect", attack_names)

row = df[df["name"] == selected_attack].iloc[0]

col_a, col_b = st.columns(2)
with col_a:
    st.markdown("**Attack Prompt**")
    st.text_area("Prompt", value=row["prompt"], height=200, disabled=True)
    if row.get("mutated_prompt"):
        st.markdown("**Mutated Prompt** *(after retry)*")
        st.text_area("Mutated", value=row["mutated_prompt"], height=150, disabled=True)

with col_b:
    st.markdown("**Model Response**")
    st.text_area("Response", value=row["response"], height=200, disabled=True)
    sev = row.get("severity", "medium")
    st.markdown(f"**Severity:** `{sev}`")
    st.markdown(f"**Judge Score:** `{row['judge_score']}/10`")
    st.markdown(f"**Reasoning:** {row['judge_reasoning']}")
    status = "VULNERABLE" if row["is_successful"] else "Safe"
    st.markdown(f"**Verdict:** {status}")
