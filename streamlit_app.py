import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

# ======================================================
# CONFIG
# ======================================================
st.set_page_config(
    page_title="LLM-Powered Data Analysis Platform",
    layout="wide"
)

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=st.secrets["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"]
)

MODEL = "openai/gpt-oss-20b:free"

# ======================================================
# HELPERS
# ======================================================
def llm(prompt):
    return client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}]
    ).choices[0].message.content

def dataset_profile(df):
    return {
        "rows": df.shape[0],
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing": df.isnull().sum().to_dict()
    }

# ======================================================
# SESSION STATE
# ======================================================
if "chat_memory" not in st.session_state:
    st.session_state.chat_memory = []

if "dashboard_code" not in st.session_state:
    st.session_state.dashboard_code = None

# ======================================================
# SIDEBAR
# ======================================================
st.sidebar.title("⚙️ Controls")
uploaded_file = st.sidebar.file_uploader("Upload CSV / Excel", ["csv", "xlsx"])
send_email = st.sidebar.button("📧 Send Summary & Dashboard (Agent)")

# ======================================================
# LOAD DATA
# ======================================================
df = None
if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

# ======================================================
# UI LAYOUT
# ======================================================
st.title("🤖 LLM-Powered Data Analysis Platform")

summary_tab, dashboard_tab, chat_tab = st.tabs(
    ["📌 Dataset Summary", "📊 Interactive Dashboard", "💬 Chat with Data"]
)

# ======================================================
# 1️⃣ SUMMARY SECTION
# ======================================================
if df is not None:
    with summary_tab:
        st.subheader("📌 Dataset Summary")

        profile = dataset_profile(df)

        # ---- Prompt 1: Dataset Understanding
        understanding_prompt = f"""
You are a data analyst.
Understand the dataset structure below (no assumptions).

{profile}
"""
        understanding = llm(understanding_prompt)

        # ---- Prompt 2: Summary + Questions
        summary_prompt = f"""
Using the dataset understanding below, produce:
1. A concise dataset summary
2. 3 insightful questions a user might ask

Dataset Understanding:
{understanding}
"""
        summary_output = llm(summary_prompt)

        st.markdown(summary_output)

# ======================================================
# 2️⃣ DASHBOARD SECTION
# ======================================================
if df is not None:
    with dashboard_tab:
        st.subheader("📊 AI-Generated Interactive Dashboard")

        if st.button("🚀 Generate Dashboard") or st.session_state.dashboard_code:

            if st.session_state.dashboard_code is None:

                # ---- Prompt 3: EDA Planning
                eda_prompt = f"""
Given the dataset below, suggest EDA insights
WITHOUT aggregations or feature engineering.

{profile}
"""
                eda_plan = llm(eda_prompt)

                # ---- Prompt 4: Dashboard Code Generator
                dashboard_prompt = f"""
You are a BI dashboard developer.

Dataset profile:
{profile}

EDA plan:
{eda_plan}

RULES:
- Use Plotly Express
- Use DataFrame df
- No new columns
- No aggregation
- No file access
- Create KPI cards + 2–3 charts
- Output ONLY Python code

Example allowed:
px.histogram, px.box, px.scatter, px.bar (raw)
"""

                st.session_state.dashboard_code = llm(dashboard_prompt)

            # ---- Execute Dashboard Code
            try:
                exec(
                    st.session_state.dashboard_code,
                    {},
                    {"st": st, "df": df, "px": px}
                )
            except Exception as e:
                st.error("Dashboard generation failed.")
                st.exception(e)

# ======================================================
# 3️⃣ CHAT SECTION
# ======================================================
if df is not None:
    with chat_tab:
        st.subheader("💬 Conversational Analytics")

        for msg in st.session_state.chat_memory:
            st.chat_message(msg["role"]).markdown(msg["content"])

        user_input = st.chat_input("Ask about data, request a plot, or stats")

        if user_input:
            st.session_state.chat_memory.append({"role": "user", "content": user_input})

            chat_prompt = f"""
You are a data assistant.

Dataset profile:
{profile}

Conversation so far:
{st.session_state.chat_memory}

User request:
{user_input}

If a plot is requested:
- Generate Plotly code using df
- Otherwise explain in text
"""

            reply = llm(chat_prompt)
            st.session_state.chat_memory.append({"role": "assistant", "content": reply})
            st.chat_message("assistant").markdown(reply)

# ======================================================
# 4️⃣ EMAIL AGENT (STUB)
# ======================================================
if send_email and df is not None:
    st.sidebar.success("📧 Email agent triggered (stub).")

    email_prompt = f"""
Create an executive-ready email summary including:
- Dataset overview
- Key insights
- Description of dashboard visuals

Dataset profile:
{profile}
"""

    email_content = llm(email_prompt)

    st.sidebar.text_area("📨 Email Preview", email_content, height=300)
