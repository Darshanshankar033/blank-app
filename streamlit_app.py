import streamlit as st
import pandas as pd
from openai import OpenAI

# --- Page Config ---
st.set_page_config(page_title="OpenRouter Chat", page_icon="🎈", layout="wide")
st.title("🎈 OpenRouter Chat App with Memory + Full File Reading")

# --- Initialize Chat Memory ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": "You are a helpful assistant that can also analyze full uploaded files."}
    ]

# --- Initialize OpenRouter Client ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"  # Replace with your OpenRouter key
)

# --- Display Chat History ---
st.subheader("💬 Chat History")
chat_container = st.container()
with chat_container:
    for msg in st.session_state["messages"]:
        if msg["role"] == "user":
            st.markdown(f"**🧑 You:** {msg['content']}")
        elif msg["role"] == "assistant":
            st.markdown(f"**🤖 Assistant:** {msg['content']}")

# --- Spacer ---
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown("---")

# --- User Input Section ---
user_input = st.text_input("💬 Type your message:", key="input_box")

# --- File Upload + Clear Chat Below Input ---
col1, col2 = st.columns([3, 1])

with col1:
    uploaded_file = st.file_uploader("📎 Upload a file (CSV, TXT, or PDF)", type=["csv", "txt", "pdf"])

with col2:
    if st.button("🧹 Clear Chat"):
        st.session_state["messages"] = [
            {"role": "system", "content": "You are a helpful assistant that can also analyze full uploaded files."}
        ]
        st.success("Chat and file cleared!")

# --- Read Full File Content ---
file_content = ""
if uploaded_file:
    st.success(f"✅ Uploaded: {uploaded_file.name}")

    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
        st.subheader("📄 CSV Preview")
        st.dataframe(df)
        file_content = df.to_csv(index=False)  # full CSV

    elif uploaded_file.name.endswith(".txt"):
        file_content = uploaded_file.read().decode("utf-8")
        st.text_area("📄 Full TXT Content", file_content, height=300)

    elif uploaded_file.name.endswith(".pdf"):
        try:
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(uploaded_file)
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() or ""
            file_content = text
            st.text_area("📄 Full PDF Text", file_content, height=300)
        except ImportError:
            st.warning("⚠️ PyPDF2 not installed. Run `pip install PyPDF2` to enable PDF support.")

# --- Chat Logic ---
if user_input:
    full_message = user_input
    if file_content:
        # Limit to avoid hitting LLM context limit (optional)
        trimmed_content = file_content[:10000]  # 10K chars safe limit
        full_message += f"\n\n(Attached file content for analysis):\n{trimmed_content}"

    st.session_state["messages"].append({"role": "user", "content": full_message})

    try:
        with st.spinner("🤔 Thinking..."):
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=st.session_state["messages"],
                extra_headers={
                    "HTTP-Referer": "https://yourappname.streamlit.app",
                    "X-Title": "Chat with Memory and Full File Reading",
                },
            )
            reply = completion.choices[0].message.content
            st.session_state["messages"].append({"role": "assistant", "content": reply})
            st.markdown(f"**🤖 Assistant:** {reply}")

    except Exception as e:
        st.error(f"Error: {e}")
