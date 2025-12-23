import streamlit as st
import pandas as pd
import plotly.express as px
from openai import OpenAI

# =====================================================
# ⚠️ API CONFIG (HARDCODED AS REQUESTED)
# =====================================================
OPENROUTER_API_KEY = "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"
MODEL = "openai/gpt-oss-20b:free"

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY
)

# =====================================================
# STREAMLIT CONFIG
# =====================================================
st.set_page_config(
    page_title="LLM-Powered BI Platform",
    layout="wide"
)

st.title("🤖 LLM-Powered Data Analysis & BI Platform")

# =====================================================
# SAFE LLM CALL
# =====================================================
def llm(prompt: str) -> str:
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error("❌ LLM call failed")
        st.exception(e)
        return ""

# =====================================================
# SESSION STATE
# =====================================================
for key in [
    "profile",
    "top10",
    "summary",
    "eda_plan",
    "dashboard_code",
    "chat_history"
]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "chat_history" else []

# =====================================================
# SIDEBAR
# =====================================================
st.sidebar.header("⚙️ Controls")
uploaded_file = st.sidebar.file_uploader(
    "Upload CSV / Excel", ["csv", "xlsx"]
)

# =====================================================
# LOAD DATA
# =====================================================
df = None
if uploaded_file:
    df = (
        pd.read_csv(uploaded_file)
        if uploaded_file.name.endswith(".csv")
        else pd.read_excel(uploaded_file)
    )

# =====================================================
# DATA PROFILER
# =====================================================
def profile_agent(df: pd.DataFrame) -> dict:
    return {
        "rows": df.shape[0],
        "columns": list(df.columns),
        "dtypes": df.dtypes.astype(str).to_dict(),
        "missing_values": df.isnull().sum().to_dict()
    }

# =====================================================
# UI SECTIONS
# =====================================================
summary_tab, dashboard_tab, chat_tab = st.tabs(
    ["📌 Dataset Summary", "📊 Interactive Dashboard", "💬 Chatbot"]
)

# =====================================================
# 1️⃣ SUMMARY SECTION (TOP 10 + PROFILE)
# =====================================================
if df is not None:
    with summary_tab:

        if st.session_state.profile is None:
            st.session_state.profile = profile_agent(df)
            st.session_state.top10 = df.head(10)

            summary_prompt = f"""
You are a data analyst.

You are given:
1. Dataset profile (schema-level information)
2. Top 10 rows of the dataset (sample)

Your tasks:
- Summarize the dataset
- Highlight key patterns or issues visible from the sample
- Suggest exactly 3 analytical questions

Dataset Profile:
{st.session_state.profile}

Top 10 Rows:
{st.session_state.top10.to_string(index=False)}
"""

            st.session_state.summary = llm(summary_prompt)

            eda_prompt = f"""
Based ONLY on:
- Dataset profile
- Top 10 rows

Suggest EDA directions.
Do NOT assume full data distribution.
Do NOT aggregate or create new columns.

Dataset Profile:
{st.session_state.profile}

Top 10 Rows:
{st.session_state.top10.to_string(index=False)}
"""
            st.session_state.eda_plan = llm(eda_prompt)

        st.markdown("### 🔍 Dataset Sample (Top 10 Rows)")
        st.dataframe(st.session_state.top10, use_container_width=True)

        st.markdown("### 🧠 AI Summary & Insights")
        st.markdown(st.session_state.summary)

# =====================================================
# 2️⃣ DASHBOARD SECTION (UNCHANGED)
# =====================================================
if df is not None:
    with dashboard_tab:

        if st.button("🚀 Generate / Refresh Dashboard") or st.session_state.dashboard_code is None:

            dashboard_prompt = f"""
You are a BI dashboard developer.

You are given:
- Dataset profile
- Top 10 rows
- EDA plan

RULES:
- Use Plotly Express
- DataFrame name: df
- pandas available as pd
- No aggregation
- No new columns
- No file access
- Create KPI cards using st.metric
- Create 2–3 interactive charts
- Output ONLY executable Python code

Dataset Profile:
{st.session_state.profile}

Top 10 Rows:
{st.session_state.top10.to_string(index=False)}

EDA Plan:
{st.session_state.eda_plan}
"""

            st.session_state.dashboard_code = llm(dashboard_prompt)

        try:
            exec(
                st.session_state.dashboard_code,
                {},
                {"st": st, "df": df, "px": px, "pd": pd}
            )
        except Exception as e:
            st.error("❌ Dashboard execution failed")
            st.exception(e)

# =====================================================
# 3️⃣ CHATBOT (PROMPT-RETRIEVAL BASED)
# =====================================================
if df is not None:
    with chat_tab:

        for msg in st.session_state.chat_history:
            st.chat_message(msg["role"]).markdown(msg["content"])

        user_input = st.chat_input(
            "Ask about the dataset, sample, or request a plot"
        )

        if user_input:
            st.session_state.chat_history.append(
                {"role": "user", "content": user_input}
            )

            chat_prompt = f"""
You are a dataset assistant.

You can answer ONLY using:
- Dataset profile
- Top 10 rows
- Previous chat context

If a question cannot be answered reliably from this information,
explicitly say so.

Dataset Profile:
{st.session_state.profile}

Top 10 Rows:
{st.session_state.top10.to_string(index=False)}

Chat History:
{st.session_state.chat_history}

User Question:
{user_input}
"""

            reply = llm(chat_prompt)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": reply}
            )

            st.chat_message("assistant").markdown(reply)

else:
    st.info("⬅️ Upload a dataset to begin.")
