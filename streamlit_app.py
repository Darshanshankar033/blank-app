import streamlit as st
from openai import OpenAI
import pandas as pd
import pdfplumber
import matplotlib.pyplot as plt
import seaborn as sns
import io
import contextlib
import re

# -------------------------------
# ⚙️ PAGE CONFIG
# -------------------------------
st.set_page_config(page_title="AI Insight Dashboard", page_icon="📊", layout="wide")
st.title("📊 AI Insight Dashboard with AI Code Generator & Data Cleaner")
st.caption("Upload your dataset, let AI write Python visualization code, clean your data, and run it instantly.")

# -------------------------------
# 🔑 OPENROUTER API CLIENT
# -------------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  # Replace with your valid key
)

# -------------------------------
# 🧭 LAYOUT
# -------------------------------
left_col, right_col = st.columns([1, 1])

# -------------------------------
# 📂 FILE UPLOAD
# -------------------------------
uploaded_file = right_col.file_uploader("📎 Upload a dataset (CSV, TXT, or PDF):", type=["csv", "txt", "pdf"])
dataframe = None
file_content = ""

if uploaded_file:
    if uploaded_file.type == "text/csv":
        dataframe = pd.read_csv(uploaded_file)
        right_col.success(f"✅ CSV '{uploaded_file.name}' uploaded successfully!")
        right_col.dataframe(dataframe.head(), use_container_width=True)
        file_content = dataframe.to_csv(index=False)
    elif uploaded_file.type == "text/plain":
        file_content = uploaded_file.read().decode("utf-8", errors="ignore")
        right_col.text_area("📄 File Preview", file_content[:1000])
    elif uploaded_file.type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    file_content += text
        right_col.text_area("📄 Extracted PDF Text", file_content[:1000])

# -------------------------------
# 🧹 CLEAN DATA BUTTON
# -------------------------------
if dataframe is not None:
    if st.button("🧽 Clean Data"):
        with st.spinner("Cleaning data..."):
            df = dataframe.copy()
            # Remove duplicates
            df = df.drop_duplicates()
            # Replace missing numeric values with mean, categorical with mode
            for col in df.columns:
                if df[col].dtype in ['float64', 'int64']:
                    df[col] = df[col].fillna(df[col].mean())
                else:
                    df[col] = df[col].fillna(df[col].mode()[0] if not df[col].mode().empty else "Unknown")
            st.success("✅ Data cleaned successfully!")
            st.write("### 🧾 Cleaned Data Preview")
            st.dataframe(df.head(), use_container_width=True)
            dataframe = df  # Update cleaned data

# -------------------------------
# 🧠 AUTO INSIGHTS / SUMMARY
# -------------------------------
with left_col:
    st.subheader("🧠 Auto Insights & Summary")
    if uploaded_file:
        with st.spinner("Generating AI insights..."):
            try:
                summary = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[
                        {"role": "user", "content": f"Summarize the following dataset or text:\n\n{file_content[:6000]}"},
                    ],
                    extra_headers={
                        "HTTP-Referer": "http://localhost:8501",
                        "X-Title": "AI Insight Dashboard",
                    },
                )
                insight_text = summary.choices[0].message.content
                st.success("✅ Summary Generated")
                st.write(insight_text)
            except Exception as e:
                st.error(f"⚠️ Error generating insights: {e}")
    else:
        st.info("Upload a file to get AI-generated insights.")

# -------------------------------
# 💬 CODE GENERATOR + EXECUTOR
# -------------------------------
right_col.subheader("💬 Ask AI to Generate and Run Code")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for msg in st.session_state.messages:
    with right_col.chat_message(msg["role"]):
        right_col.markdown(msg["content"])

# Input from user
if user_prompt := right_col.chat_input("Ask: 'Plot sales vs profit' or 'Show correlation heatmap'..."):
    st.session_state.messages.append({"role": "user", "content": user_prompt})

    with right_col.chat_message("user"):
        right_col.markdown(user_prompt)

    context = ""
    if dataframe is not None:
        context = f"Columns available: {', '.join(dataframe.columns)}. The dataframe is called df."

    full_prompt = f"""
You are an expert Python data analyst using Streamlit, pandas, matplotlib, and seaborn.
Dataset info: {context}

Generate **only executable Python code** (no explanations, no markdown fences) that performs the user request:
'{user_prompt}'

Rules:
- Use the variable 'df' for the dataframe.
- Always end the code with `st.pyplot(plt.gcf())` to display the visualization.
- Import matplotlib.pyplot as plt and seaborn as sns if needed.
- No markdown or triple backticks, only raw code.
"""

    with right_col.chat_message("assistant"):
        with st.spinner("🧠 Generating Python code..."):
            try:
                completion = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[{"role": "user", "content": full_prompt}],
                    extra_headers={
                        "HTTP-Referer": "http://localhost:8501",
                        "X-Title": "AI Insight Dashboard",
                    },
                )
                generated_code = completion.choices[0].message.content.strip()
            except Exception as e:
                generated_code = f"# Error generating code: {e}"

            # Clean any markdown or non-code text
            for fence in ("```python", "```py", "```", "`"):
                generated_code = generated_code.replace(fence, "")
            generated_code = re.sub(r"^Python code.*", "", generated_code, flags=re.IGNORECASE)

            st.markdown("### 🧩 Generated Python Code:")
            st.code(generated_code, language="python")

            # --- EXECUTE THE GENERATED CODE SAFELY ---
            if dataframe is not None:
                try:
                    df = dataframe.copy()
                    safe_locals = {"st": st, "pd": pd, "plt": plt, "sns": sns, "df": df}
                    with contextlib.redirect_stdout(io.StringIO()):
                        exec(generated_code, {}, safe_locals)
                except SyntaxError as e:
                    st.error(f"⚠️ Syntax error in generated code: {e}")
                    st.text_area("🔍 Cleaned Code", generated_code, height=200)
                except Exception as e:
                    st.error(f"⚠️ Error executing generated code: {e}")
                    st.text_area("🔍 Cleaned Code", generated_code, height=200)
            else:
                st.info("⚠️ Please upload a CSV dataset first.")

    st.session_state.messages.append({"role": "assistant", "content": generated_code})
