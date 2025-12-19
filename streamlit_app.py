import streamlit as st
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
import seaborn as sns
import io
import contextlib

# =================================================
# PAGE CONFIG
# =================================================
st.set_page_config(
    page_title="LLM-Powered Interactive Data Analysis & Visualization",
    page_icon="📊",
    layout="wide"
)

st.markdown(
    """
    <h1 style='text-align:center;'>📊 LLM-Powered Interactive Data Analysis & Visualization</h1>
    <p style='text-align:center;color:gray;'>
    Conversational Analytics • AI-Generated BI Dashboard • Simplified Filters
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
# SIDEBAR
# =================================================
st.sidebar.header("⚙️ Controls")

uploaded_file = st.sidebar.file_uploader(
    "Upload CSV / Excel",
    type=["csv", "xlsx"]
)

mode = st.sidebar.radio(
    "Mode",
    ["💬 Chat", "🧠 Code", "⚙️ Auto"],
    index=2
)

auto_build_dashboard = st.sidebar.button("🤖 Auto-Build BI Dashboard")
clean_data_btn = st.sidebar.button("🧽 Clean Data")

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
# CLEAN DATA
# =================================================
if df is not None and clean_data_btn:
    with st.spinner("Cleaning data..."):
        df = df.drop_duplicates()
        for col in df.columns:
            if df[col].dtype in ["int64", "float64"]:
                df[col] = df[col].fillna(df[col].mean())
            else:
                df[col] = df[col].fillna(
                    df[col].mode()[0] if not df[col].mode().empty else "Unknown"
                )
        st.sidebar.success("Data cleaned successfully")

# =================================================
# DATA METADATA
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
# MAIN DASHBOARD (NO FILTERS YET)
# =================================================
if df is not None:

    # ---------------- KPIs ----------------
    st.subheader("📌 Dataset Overview (Unfiltered)")
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Rows", df.shape[0])
    k2.metric("Columns", df.shape[1])
    k3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))
    k4.metric("Missing Values", int(df.isnull().sum().sum()))

    # ---------------- AI DASHBOARD ----------------
    if auto_build_dashboard:
        st.subheader("🤖 AI-Built BI Dashboard")

        if "bi_code" not in st.session_state:
            with st.spinner("AI is designing dashboard..."):
                st.session_state.bi_code = generate_bi_dashboard_code(df)

        try:
            exec_env = {
                "st": st,
                "pd": pd,
                "plt": plt,
                "sns": sns,
                "filtered_df": df.copy(),
            }
            exec(st.session_state.bi_code, {}, exec_env)
        except Exception as e:
            st.error(f"Dashboard error: {e}")

    # ---------------- INSIGHTS ----------------
    st.subheader("🧠 Automated Insights")
    with st.spinner("Generating insights..."):
        resp = client.chat.completions.create(
            model="openai/gpt-oss-20b:free",
            messages=[{
                "role": "user",
                "content": f"Provide insights for this dataset:\n{dataset_metadata(df)}"
            }],
        )
        st.markdown(resp.choices[0].message.content)

    # ---------------- CHAT ----------------
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("💬 Conversational Analytics")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask questions or request charts...")

    if user_prompt:
        st.session_state.chat_history.append({"role": "user", "content": user_prompt})

        viz_words = ["plot", "chart", "graph", "bar", "line", "scatter", "heatmap"]
        run_code = (mode == "🧠 Code") or (mode == "⚙️ Auto" and any(w in user_prompt.lower() for w in viz_words))

        if run_code:
            code_prompt = f"""
Generate ONLY Python code using df to:
{user_prompt}
End with st.pyplot(plt.gcf())
"""
            resp = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "user", "content": code_prompt}],
            )
            code = resp.choices[0].message.content
            for fence in ("```python", "```", "`"):
                code = code.replace(fence, "")
            st.code(code, language="python")
            exec(code, {}, {"st": st, "pd": pd, "plt": plt, "sns": sns, "df": df.copy()})
            st.session_state.chat_history.append({"role": "assistant", "content": code})
        else:
            resp = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[{"role": "user", "content": dataset_metadata(df) + user_prompt}],
            )
            st.markdown(resp.choices[0].message.content)

    # =================================================
    # 🎛️ SIMPLIFIED SLICERS (AT THE END)
    # =================================================
    st.markdown("---")
    st.subheader("🎛️ Optional Filters (Simplified)")

    filtered_df = df.copy()

    # Categorical slicers (limited)
    cat_cols = [
        c for c in df.select_dtypes(include="object").columns
        if df[c].nunique() <= 20
    ]

    for col in cat_cols[:3]:  # limit slicers
        selected = st.multiselect(
            f"Filter {col}",
            options=df[col].unique(),
            default=df[col].unique()
        )
        filtered_df = filtered_df[filtered_df[col].isin(selected)]

    # Numeric slicers
    num_cols = df.select_dtypes(include="number").columns.tolist()
    for col in num_cols[:2]:
        min_val, max_val = float(df[col].min()), float(df[col].max())
        selected_range = st.slider(
            f"Filter {col}",
            min_value=min_val,
            max_value=max_val,
            value=(min_val, max_val)
        )
        filtered_df = filtered_df[
            (filtered_df[col] >= selected_range[0]) &
            (filtered_df[col] <= selected_range[1])
        ]

    st.caption(f"Filtered rows: {filtered_df.shape[0]}")

else:
    st.info("⬅️ Upload a dataset to start.")
