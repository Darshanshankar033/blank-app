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
    Universal Dataset Support • AI Governance • Cloud Safe
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

MODEL_NAME = "openai/gpt-oss-20b:free"

# =================================================
# SIDEBAR CONTROLS
# =================================================
st.sidebar.header("⚙️ Controls")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV / Excel Dataset",
    ["csv", "xlsx"]
)

auto_build_dashboard = st.sidebar.button("🤖 Auto-Build BI Dashboard")
export_report = st.sidebar.button("📄 Export BI Report")

# =================================================
# LOAD DATA (SINGLE SOURCE OF TRUTH)
# =================================================
df = None
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        else:
            df = pd.read_excel(uploaded_file)
    except Exception as e:
        st.error("Failed to load dataset.")
        st.exception(e)

# =================================================
# DATASET METADATA (SAFE FOR ALL TYPES)
# =================================================
def dataset_metadata(df):
    return {
        "rows": int(df.shape[0]),
        "columns": list(df.columns),
        "dtypes": {c: str(df[c].dtype) for c in df.columns},
        "missing_values": df.isnull().sum().to_dict()
    }

# =================================================
# 🔒 SANITIZER — BLOCK ALL UNSAFE OPERATIONS
# =================================================
def sanitize_generated_code(code: str) -> str:
    forbidden_patterns = [
        # File I/O
        "read_csv", "read_excel", ".csv", ".xlsx", "open(",

        # Aggregation / derivation
        "groupby", "value_counts", "reset_index", "agg(",
        "sum(", "mean(", "median(", "count(",

        # Date parsing / transformation
        "to_datetime", "strftime", "strptime",
        "dayfirst", "format=", "errors=",

        # Column creation / modification
        "df[", ".assign(", ".apply(", ".map(",
    ]

    for pattern in forbidden_patterns:
        if pattern in code:
            raise ValueError(f"❌ Forbidden operation detected: {pattern}")

    return code

# =================================================
# AI BI DASHBOARD GENERATOR (UNIVERSAL & STRICT)
# =================================================
def generate_bi_dashboard_code(df):
    meta = dataset_metadata(df)

    prompt = f"""
You are a senior BI dashboard architect.

DATASET METADATA:
{meta}

STRICT GOVERNANCE RULES (MUST FOLLOW):
- Use ONLY the existing DataFrame `df`
- DO NOT read files
- DO NOT create, derive, or modify columns
- DO NOT aggregate data
- DO NOT parse or convert dates
- Treat all non-numeric columns as categorical strings
- DO NOT assume column meaning or semantics
- DO NOT use groupby, value_counts, agg, to_datetime

ALLOWED VISUALS ONLY:
- Histogram of ONE numeric column
- Boxplot of ONE numeric column
- Scatter plot between TWO numeric columns
- Simple bar chart using ONE categorical column AS-IS (no aggregation)

TASK:
Generate Streamlit Python code that:
1. Displays 3–4 KPI metrics using ONLY:
   - df.shape
   - df.isnull()
2. Creates 2–3 allowed charts
3. Uses st.columns() for layout
4. Uses matplotlib or seaborn
5. Ends each chart with st.pyplot(plt.gcf())
6. Outputs ONLY executable Python code (no markdown, no explanation)
"""

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )

    code = response.choices[0].message.content.strip()
    for fence in ("```python", "```", "`"):
        code = code.replace(fence, "")
    return code

# =================================================
# MAIN APPLICATION
# =================================================
if df is not None:

    # ---------------- KPI SUMMARY ----------------
    st.subheader("📌 Dataset KPI Summary")

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", df.shape[0])
    k2.metric("Columns", df.shape[1])
    k3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))
    k4.metric("Missing Values", int(df.isnull().sum().sum()))

    # ---------------- DATA PREVIEW ----------------
    with st.expander("🔍 Dataset Preview"):
        st.dataframe(df, use_container_width=True)

    # ---------------- AI INSIGHTS (METADATA-ONLY) ----------------
    st.subheader("🧠 AI Insights")

    insight_prompt = f"""
Analyze the dataset using ONLY this metadata.
Do NOT assume column meaning.

METADATA:
{dataset_metadata(df)}

Provide high-level observations about:
- Data size
- Data types
- Missing values
"""

    insights = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": insight_prompt}],
    ).choices[0].message.content

    st.markdown(insights)

    # ---------------- AI-GENERATED BI DASHBOARD ----------------
    if auto_build_dashboard:
        st.subheader("🤖 AI-Generated BI Dashboard")

        if "bi_code" not in st.session_state:
            with st.spinner("Safely generating dashboard..."):
                st.session_state.bi_code = generate_bi_dashboard_code(df)

        try:
            safe_code = sanitize_generated_code(st.session_state.bi_code)
            exec(
                safe_code,
                {},
                {"st": st, "pd": pd, "plt": plt, "sns": sns, "df": df.copy()}
            )
        except Exception as e:
            st.error("Dashboard generation blocked due to governance rules.")
            st.exception(e)

    # ---------------- CONVERSATIONAL ANALYTICS ----------------
    st.subheader("💬 Conversational Analytics")

    user_query = st.chat_input("Ask about the dataset or request a simple chart")

    if user_query:
        if any(k in user_query.lower() for k in ["plot", "chart", "graph"]):
            code_prompt = f"""
Generate ONLY Python code using DataFrame `df` to:
{user_query}

RULES:
- No aggregation
- No column creation
- No data transformation
- Use existing columns only
- End with st.pyplot(plt.gcf())
"""
            code = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": code_prompt}],
            ).choices[0].message.content

            code = sanitize_generated_code(
                code.replace("```python", "").replace("```", "")
            )

            st.code(code, language="python")
            exec(code, {}, {"st": st, "df": df, "plt": plt, "sns": sns})

        else:
            reply = client.chat.completions.create(
                model=MODEL_NAME,
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
