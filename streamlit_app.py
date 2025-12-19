import streamlit as st
import pandas as pd
from openai import OpenAI
import matplotlib.pyplot as plt
import seaborn as sns
import io
import contextlib
import re

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
    Conversational Analytics • BI-Style Dashboard • AI-Driven Insights
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
    api_key="YOUR_OPENROUTER_API_KEY"
)

# =================================================
# SIDEBAR CONTROLS
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

st.sidebar.caption(
    "💬 Chat → text only\n"
    "🧠 Code → always generate & run code\n"
    "⚙️ Auto → AI decides"
)

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
# DATA CLEANING
# =================================================
if df is not None:
    if st.sidebar.button("🧽 Clean Data"):
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
# DATA METADATA (FULL DATA USED)
# =================================================
def dataset_metadata(df: pd.DataFrame) -> str:
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
# MAIN DASHBOARD
# =================================================
if df is not None:

    # ---------------- KPI CARDS ----------------
    st.subheader("📌 Dataset Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Rows", df.shape[0])
    c2.metric("Columns", df.shape[1])
    c3.metric("Numeric Columns", len(df.select_dtypes(include="number").columns))
    c4.metric("Missing Values", int(df.isnull().sum().sum()))

    # ---------------- DATA TABLE ----------------
    with st.expander("🔍 View Dataset (Interactive Table)"):
        st.dataframe(df, use_container_width=True)

    # ---------------- AUTO INSIGHTS ----------------
    st.subheader("🧠 Automated Insights (Full Dataset)")
    with st.spinner("Generating insights using full dataset metadata..."):
        meta = dataset_metadata(df)
        insight_prompt = f"""
You are a senior data analyst.

Using the dataset metadata below, provide:
1. High-level summary
2. Key patterns and trends
3. Data quality issues
4. Business insights (if applicable)

Dataset Metadata:
{meta}
"""
        insight_response = client.chat.completions.create(
            model="mistralai/mixtral-8x7b",
            messages=[{"role": "user", "content": insight_prompt}],
            extra_headers={
                "HTTP-Referer": "http://localhost:8501",
                "X-Title": "LLM BI Dashboard",
            },
        )
        st.markdown(insight_response.choices[0].message.content)

    # =================================================
    # CHAT MEMORY
    # =================================================
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    st.subheader("💬 Conversational Analytics")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_prompt = st.chat_input("Ask questions or request charts (e.g., 'Plot sales vs profit')")

    if user_prompt:
        st.session_state.chat_history.append(
            {"role": "user", "content": user_prompt}
        )

        with st.chat_message("user"):
            st.markdown(user_prompt)

        # Decide execution mode
        viz_keywords = [
            "plot", "chart", "graph", "visualize", "draw",
            "bar", "line", "scatter", "histogram", "boxplot", "heatmap"
        ]
        wants_code = any(k in user_prompt.lower() for k in viz_keywords)

        run_code = (
            mode == "🧠 Code" or
            (mode == "⚙️ Auto" and wants_code)
        )

        dataset_context = f"Columns: {', '.join(df.columns)}"

        # ---------------- CODE MODE ----------------
        if run_code:
            code_prompt = f"""
You are an expert Python data analyst.

Dataset info:
{dataset_context}

Generate ONLY executable Python code (no markdown, no explanation) to perform:
{user_prompt}

Rules:
- DataFrame name is df
- Use matplotlib / seaborn
- End with st.pyplot(plt.gcf())
"""
            with st.chat_message("assistant"):
                with st.spinner("Generating and executing visualization code..."):
                    response = client.chat.completions.create(
                        model="mistralai/mixtral-8x7b",
                        messages=[{"role": "user", "content": code_prompt}],
                        extra_headers={
                            "HTTP-Referer": "http://localhost:8501",
                            "X-Title": "LLM BI Dashboard",
                        },
                    )

                    generated_code = response.choices[0].message.content.strip()

                    # Clean fences
                    for fence in ("```python", "```", "`"):
                        generated_code = generated_code.replace(fence, "")

                    st.markdown("### 🧩 Generated Python Code")
                    st.code(generated_code, language="python")

                    try:
                        safe_locals = {
                            "st": st,
                            "pd": pd,
                            "plt": plt,
                            "sns": sns,
                            "df": df.copy(),
                        }
                        with contextlib.redirect_stdout(io.StringIO()):
                            exec(generated_code, {}, safe_locals)
                    except Exception as e:
                        st.error(f"Error executing code: {e}")
                        st.text_area("Debug Code", generated_code, height=200)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": generated_code}
            )

        # ---------------- CHAT MODE ----------------
        else:
            chat_prompt = f"""
You are a data analysis assistant.

Dataset Metadata:
{dataset_metadata(df)}

User Question:
{user_prompt}
"""
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    reply = client.chat.completions.create(
                        model="mistralai/mixtral-8x7b",
                        messages=[{"role": "user", "content": chat_prompt}],
                        extra_headers={
                            "HTTP-Referer": "http://localhost:8501",
                            "X-Title": "LLM BI Dashboard",
                        },
                    )
                    answer = reply.choices[0].message.content
                    st.markdown(answer)

            st.session_state.chat_history.append(
                {"role": "assistant", "content": answer}
            )

else:
    st.info("⬅️ Upload a dataset from the sidebar to start analysis.")
