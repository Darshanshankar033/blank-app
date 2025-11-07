import streamlit as st
from openai import OpenAI
import pandas as pd
import pdfplumber

# ---------------------------------
# ⚙️ PAGE CONFIGURATION
# ---------------------------------
st.set_page_config(page_title="AI Insight Dashboard", page_icon="📊", layout="wide")

st.title("📊 AI Insight Dashboard")
st.caption("Upload your data or document, get automatic insights, chat, and visualize trends — powered by OpenRouter.")

# ---------------------------------
# 🔑 OPENROUTER CLIENT
# ---------------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  # Your key here
)

# ---------------------------------
# 🧭 PAGE LAYOUT — TWO COLUMNS
# ---------------------------------
left_col, right_col = st.columns([1, 1])

# ---------------------------------
# 📂 FILE UPLOAD SECTION
# ---------------------------------
uploaded_file = right_col.file_uploader("📎 Upload a file (CSV, TXT, or PDF):", type=["csv", "txt", "pdf"])

dataframe = None
file_content = ""

if uploaded_file:
    file_type = uploaded_file.type

    # CSV Upload
    if file_type == "text/csv":
        dataframe = pd.read_csv(uploaded_file)
        right_col.success(f"✅ CSV '{uploaded_file.name}' uploaded successfully!")
        right_col.dataframe(dataframe.head(), use_container_width=True)
        file_content = dataframe.to_csv(index=False)

    # TXT Upload
    elif file_type == "text/plain":
        file_content = uploaded_file.read().decode("utf-8", errors="ignore")
        right_col.text_area("📄 File Preview", file_content[:1000])

    # PDF Upload
    elif file_type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    file_content += text
        right_col.text_area("📄 Extracted PDF Text", file_content[:1000])

# ---------------------------------
# 🧠 AUTO INSIGHTS / SUMMARY
# ---------------------------------
with left_col:
    st.subheader("🧠 Auto Insights & Summary")

    if uploaded_file:
        with st.spinner("Generating AI insights..."):
            try:
                summary = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",  # reliable, free-tier model
                    messages=[
                        {"role": "user", "content": f"Provide a clear summary and top insights from the following data:\n\n{file_content[:6000]}"},
                    ],
                    extra_headers={
                        "HTTP-Referer": "http://localhost:8501",  # replace with your Streamlit URL when deployed
                        "X-Title": "AI Insight Dashboard",
                    },
                )
                insight_text = summary.choices[0].message.content
                st.success("✅ Insights Generated")
                st.write(insight_text)
            except Exception as e:
                st.error(f"⚠️ Error while generating insights: {e}")
    else:
        st.info("Upload a file to generate insights.")

# ---------------------------------
# 💬 CHAT INTERFACE (RIGHT COLUMN)
# ---------------------------------
right_col.subheader("💬 Chat with the AI")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages
for msg in st.session_state.messages:
    with right_col.chat_message(msg["role"]):
        right_col.markdown(msg["content"])

# Chat input (bottom bar)
if user_input := right_col.chat_input("Ask a question about your data or file..."):
    st.session_state.messages.append({"role": "user", "content": user_input})

    with right_col.chat_message("user"):
        right_col.markdown(user_input)

    # Context from file or dataset
    context = ""
    if dataframe is not None:
        context = f"Here is the dataset preview:\n{dataframe.head(10).to_csv(index=False)}"
    elif file_content:
        context = f"Here is the uploaded file content:\n{file_content[:4000]}"

    prompt = f"{context}\n\nUser question: {user_input}"

    with right_col.chat_message("assistant"):
        with right_col.spinner("🤔 Thinking..."):
            try:
                response = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=[
                        *st.session_state.messages[:-1],
                        {"role": "user", "content": prompt},
                    ],
                    extra_headers={
                        "HTTP-Referer": "http://localhost:8501",
                        "X-Title": "AI Insight Dashboard",
                    },
                )
                answer = response.choices[0].message.content
            except Exception as e:
                answer = f"⚠️ Error: {e}"

            right_col.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})

# ---------------------------------
# 📊 QUICK VISUALIZATION
# ---------------------------------
if dataframe is not None:
    with right_col.expander("📊 Quick Visualization"):
        numeric_cols = dataframe.select_dtypes(include=["number"]).columns.tolist()
        if numeric_cols:
            x_axis = st.selectbox("Select X-axis:", numeric_cols, key="x_axis")
            y_axis = st.selectbox("Select Y-axis:", numeric_cols, key="y_axis")
            st.line_chart(dataframe[[x_axis, y_axis]])
        else:
            st.info("No numeric columns available for plotting.")
