import streamlit as st
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
import seaborn as sns

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
    Conversational Analytics • AI-Generated BI Dashboard • Governance Safe
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

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV / Excel",
    ["csv", "xlsx"]
)

auto_build_dashboard = st.sidebar.button("🤖 Auto-Build BI Dashboard")
export_report = st.sidebar.button("📄 Export BI Report")

# =================================================
# LOAD DATA
# =================================================
df = None
if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

# =================================================
# METADATA
# =================================================
def dataset_metadata(df):
    return f"""
Rows: {df.shape[0]}
Columns: {df.shape[1]}

Column Names:
{list(df.columns)}

Data Types:
{df.dtypes}
"""

# =================================================
# 🔒 SANITIZER (STRICT)
# =================================================
def sanitize_generated_code(code: str) -> str:
    forbidden = [
        "read_csv", "read_excel", ".csv", ".xlsx", "open(",
        "groupby", "value_counts", "reset_index", "agg(",
        "Frequency", "Count", "Total"
    ]
    for f in forbidden:
        if f in code:
            raise ValueError(f"❌ Forbidden operation detected: {f}")
    return code

# =================================================
# AI BI DASHBOARD GENERATOR (STRICT)
# =================================================
def generate_bi_dashboard_code(df):
    schema = {
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
        "categorical_columns": df.select_dtypes(exclude="number").columns.tolist()
    }

    prompt = f"""
You are a senior BI dashboard architect.

Dataset schema:
{schema}

STRICT RULES (MUST FOLLOW):
- Use ONLY existing columns
- DO NOT create new or derived columns
- DO NOT aggregate data
- DO NOT use groupby, value_counts, agg
- Use DataFrame `df` ONLY

ALLOWED VISUALS:
- Histogram (one numeric column)
- Boxplot (one numeric column)
- Scatter plot (two numeric columns)
- Simple bar chart using ONE categorical column AS-IS

TASK:
Generate Streamlit Python code that:
1. Shows 3–4 KPI metrics using df.shape or df.isnull
2. Creates 2–3 allowed charts
3. Uses st.columns() for layout
4. Uses matplotlib or seaborn
5. Ends each chart with st.pyplot(plt.gcf())
6. Outputs ONLY executable Python code
"""

    response = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": prompt}],
    )

    code = response.choices[0].message.content.strip()
    for fence in ("```python", "```", "`"):
        code = code.replace(fence, "")
    return code

# =================================================
# MAIN APP
# =================================================
if df is not None:

    # ---------------- KPIs ----------------
    st.subheader("📌 KPI Summary")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", df.shape[0])
    k2.metric("Columns", df.shape[1])
    k3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))
    k4.metric("Missing Values", int(df.isnull().sum().sum()))

    # ---------------- DATA PREVIEW ----------------
    with st.expander("🔍 Dataset Preview"):
        st.dataframe(df, use_container_width=True)

    # ---------------- AI INSIGHTS ----------------
    st.subheader("🧠 AI Insights")

    insight_prompt = f"""
Provide high-level insights using ONLY the dataset metadata below.
Do NOT assume any column meaning.

{dataset_metadata(df)}
"""

    insights = client.chat.completions.create(
        model="openai/gpt-oss-20b:free",
        messages=[{"role": "user", "content": insight_prompt}],
    ).choices[0].message.content

    st.markdown(insights)

    # ---------------- AI BI DASHBOARD ----------------
    if auto_build_dashboard:
        st.subheader("🤖 AI-Generated BI Dashboard")

        if "bi_code" not in st.session_state:
            with st.spinner("Generating dashboard safely..."):
                st.session_state.bi_code = generate_bi_dashboard_code(df)

        try:
            safe_code = sanitize_generated_code(st.session_state.bi_code)
            exec(
                safe_code,
                {},
                {"st": st, "pd": pd, "plt": plt, "sns": sns, "df": df.copy()}
            )
        except Exception as e:
            st.error("Dashboard generation blocked due to rule violation.")
            st.exception(e)

    # ---------------- CHAT ----------------
    st.subheader("💬 Conversational Analytics")

    user_query = st.chat_input("Ask a question or request a simple chart")

    if user_query:
        if any(k in user_query.lower() for k in ["plot", "chart", "graph"]):
            code_prompt = f"""
Generate ONLY Python code using DataFrame `df` to:
{user_query}

RULES:
- No aggregation
- No new columns
- Use existing columns only
- End with st.pyplot(plt.gcf())
"""
            code = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "user", "content": code_prompt}],
            ).choices[0].message.content

            code = sanitize_generated_code(code.replace("```python", "").replace("```", ""))
            st.code(code, language="python")
            exec(code, {}, {"st": st, "df": df, "plt": plt, "sns": sns})

        else:
            reply = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "user", "content": user_query}],
            ).choices[0].message.content
            st.markdown(reply)

    # ---------------- EXPORT ----------------
    if export_report:
        report = f"""
LLM-Powered BI Report

Rows: {df.shape[0]}
Columns: {df.shape[1]}

INSIGHTS:
{insights}
"""
        st.download_button(
            "📥 Download BI Report (TXT)",
            report,
            file_name="BI_Report.txt"
        )

        st.download_button(
            "📥 Download Dataset Snapshot (CSV)",
            df.to_csv(index=False),
            file_name="Dataset.csv"
        )

else:
    st.info("⬅️ Upload a dataset to start.")
