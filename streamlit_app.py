import streamlit as st
from openai import OpenAI
import pdfplumber

# ---------------------------------
# ⚙️ Page Configuration
# ---------------------------------
st.set_page_config(page_title="OpenRouter Chatbot", page_icon="💬", layout="centered")

st.title("💬 OpenRouter Chatbot with Memory & File Upload")
st.caption("Chat with memory, upload documents, and get responses powered by OpenRouter!")

# ---------------------------------
# 🔑 API Key (Inline)
# ---------------------------------
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  # your key here
)

# ---------------------------------
# 🧠 Initialize Session State for Memory
# ---------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant that answers based on the chat history and uploaded file."}
    ]

if "file_context" not in st.session_state:
    st.session_state.file_context = ""

# ---------------------------------
# 📂 File Upload Section
# ---------------------------------
uploaded_file = st.file_uploader("📎 Upload a file (TXT, CSV, or PDF):", type=["txt", "csv", "pdf"])

if uploaded_file:
    file_text = ""

    if uploaded_file.type == "application/pdf":
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    file_text += text

    else:  # TXT or CSV
        file_text = uploaded_file.read().decode("utf-8", errors="ignore")

    st.session_state.file_context = file_text[:6000]  # Limit context size
    st.success(f"✅ File '{uploaded_file.name}' uploaded successfully and content added to memory!")

# ---------------------------------
# 💬 Display Chat History
# ---------------------------------
for msg in st.session_state.messages:
    if msg["role"] != "system":
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

# ---------------------------------
# 🧠 Chat Input Bar (BOTTOM)
# ---------------------------------
if user_input := st.chat_input("Type your message here..."):
    # Add user's message
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Display user's message
    with st.chat_message("user"):
        st.markdown(user_input)

    # Prepare combined context (file + chat)
    combined_prompt = user_input
    if st.session_state.file_context:
        combined_prompt = (
            f"The following file content is provided:\n\n"
            f"{st.session_state.file_context}\n\n"
            f"Now continue this chat based on both the conversation and the file content. "
            f"User says: {user_input}"
        )

    # Generate model response
    with st.chat_message("assistant"):
        with st.spinner("🤔 Thinking..."):
            try:
                completion = client.chat.completions.create(
                    model="openai/gpt-oss-20b:free",
                    messages=st.session_state.messages + [{"role": "user", "content": combined_prompt}],
                    extra_headers={
                        "HTTP-Referer": "https://your-streamlit-app-url",  # optional
                        "X-Title": "Streamlit Chatbot with Memory",
                    },
                )
                response = completion.choices[0].message.content
            except Exception as e:
                response = f"⚠️ Error: {e}"

            st.markdown(response)

    # Save assistant response in memory
    st.session_state.messages.append({"role": "assistant", "content": response})

# ---------------------------------
# 🧹 Reset Chat Option
# ---------------------------------
st.sidebar.header("⚙️ Chat Settings")
if st.sidebar.button("🗑️ Clear Chat"):
    st.session_state.messages = [
        {"role": "system", "content": "You are a helpful assistant that answers based on the chat history and uploaded file."}
    ]
    st.session_state.file_context = ""
    st.sidebar.success("Chat memory cleared!")
