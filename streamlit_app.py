import streamlit as st
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
import seaborn as sns
from io import BytesIO

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="LLM-Powered Interactive BI Dashboard",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
    <h1 style='text-align:center;'>📊 LLM-Powered Interactive BI Dashboard</h1>
    <p style='text-align:center;color:gray;'>
    Conversational Analytics • AI BI • Exportable Reports
    </p>
    <hr>
    """,
    unsafe_allow_html=True
)

# =================================================
# OPENROUTER CLIENT
# =================================================
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)

# =================================================
# SIDEBAR CONTROLS
# =================================================
st.sidebar.header("⚙️ Controls")
uploaded_file = st.sidebar.file_uploader("Upload CSV / Excel", ["csv", "xlsx"])
auto_build_dashboard = st.sidebar.button("🤖 Auto-Build BI Dashboard")
export_report = st.sidebar.button("📄 Export BI Report")

# =================================================
# LOAD DATA
# =================================================
df = None
if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)

# =================================================
# UTILITY
# =================================================
def dataset_metadata(df):
    return f"""
Rows: {df.shape[0]}
Columns: {df.shape[1]}
Column Types:
{df.dtypes}

Missing Values:
{df.isnull().sum()}

Summary Statistics:
{df.describe(include='all')}
"""

# =================================================
# AI BI DASHBOARD GENERATOR
# =================================================
def generate_bi_dashboard_code(df):
    schema = {
        "rows": df.shape[0],
        "columns": df.columns.tolist(),
        "dtypes": df.dtypes.astype(str).to_dict()
    }

    prompt = f"""
You are a senior BI dashboard architect.

Dataset schema:
{schema}

Generate Streamlit Python code that:
- Creates KPI metrics
- Generates 2–4 charts
- Uses st.columns()
- Uses matplotlib or seaborn
- Uses DataFrame df
- Ends charts with st.pyplot(plt.gcf())
- Output ONLY executable Python code
"""

    r = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": prompt}],
    )

    code = r.choices[0].message.content
    return code.replace("```python", "").replace("```", "")

# =================================================
# LANGCHAIN-STYLE AGENTS
# =================================================
def planner_agent(query):
    prompt = f"""
Classify the request into one category:
CHAT, VISUALIZATION, EXPORT

Request:
{query}

Return only the category name.
"""
    r = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content.strip()

def coder_agent(task):
    prompt = f"""
Generate ONLY Python code using df to:
{task}

Rules:
- Use matplotlib or seaborn
- End with st.pyplot(plt.gcf())
"""
    r = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": prompt}],
    )
    return r.choices[0].message.content.replace("```python", "").replace("```", "")

# =================================================
# MAIN APP
# =================================================
if df is not None:

    # ---------------- KPIs ----------------
    st.subheader("📌 KPI Summary")
    c1, c2, c3 = st.columns(3)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Missing Values", int(df.isnull().sum().sum()))

    # ---------------- DATA ----------------
    with st.expander("🔍 Dataset Preview"):
        st.dataframe(df, use_container_width=True)

    # ---------------- INSIGHTS ----------------
    st.subheader("🧠 AI Insights")
    insight_prompt = f"Provide insights from this dataset:\n{dataset_metadata(df)}"
    insight_resp = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": insight_prompt}],
    )
    insights = insight_resp.choices[0].message.content
    st.markdown(insights)

    # ---------------- AI DASHBOARD ----------------
    if auto_build_dashboard:
        st.subheader("🤖 AI-Generated BI Dashboard")
        if "bi_code" not in st.session_state:
            st.session_state.bi_code = generate_bi_dashboard_code(df)

        try:
            exec(
                st.session_state.bi_code,
                {},
                {"st": st, "pd": pd, "plt": plt, "sns": sns, "df": df.copy()}
            )
        except Exception as e:
            st.error(f"Dashboard error: {e}")

    # ---------------- CHAT ----------------
    st.subheader("💬 Conversational Analytics")
    user_query = st.chat_input("Ask a question or request a chart")

    if user_query:
        intent = planner_agent(user_query)

        if intent == "VISUALIZATION":
            code = coder_agent(user_query)
            st.code(code, language="python")
            exec(code, {}, {"st": st, "df": df, "plt": plt, "sns": sns})
        else:
            resp = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "user", "content": user_query}],
            )
            st.markdown(resp.choices[0].message.content)

    # ---------------- EXPORT REPORT ----------------
    if export_report:
        report_text = f"""
LLM-Powered BI Report

Rows: {df.shape[0]}
Columns: {df.shape[1]}

INSIGHTS:
{insights}
"""
        st.download_button(
            "📥 Download BI Report (TXT)",
            report_text,
            file_name="BI_Report.txt"
        )

        st.download_button(
            "📥 Download Dataset Snapshot (CSV)",
            df.to_csv(index=False),
            file_name="Filtered_Data.csv"
        )

else:
    st.info("⬅️ Upload a dataset to begin.")
