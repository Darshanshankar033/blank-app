import streamlit as st
from openai import OpenAI

# --- Page Setup ---
st.set_page_config(page_title="OpenRouter Chat", page_icon="🎈")
st.title("🎈 OpenRouter Chat App with Memory")

# --- Initialize Session State for Chat History ---
if "messages" not in st.session_state:
    st.session_state["messages"] = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

# --- Input box ---
user_input = st.text_input("Enter your message:")

# --- Initialize OpenRouter Client ---
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"  # Replace with your key
)

# --- Display Previous Messages ---
st.subheader("💬 Chat History")
for msg in st.session_state["messages"]:
    if msg["role"] == "user":
        st.markdown(f"**You:** {msg['content']}")
    elif msg["role"] == "assistant":
        st.markdown(f"**Assistant:** {msg['content']}")

# --- Process New Input ---
if user_input:
    # Add user message to memory
    st.session_state["messages"].append({"role": "user", "content": user_input})

    try:
        with st.spinner("Thinking..."):
            completion = client.chat.completions.create(
                model="gryphe/mythomax-l2-13b:free",
                messages=st.session_state["messages"],  # full chat history
                extra_headers={
                    "HTTP-Referer": "https://yourappname.streamlit.app",
                    "X-Title": "Streamlit Chat with Memory",
                },
            )

            # Get assistant reply
            reply = completion.choices[0].message.content

            # Add reply to memory
            st.session_state["messages"].append({"role": "assistant", "content": reply})

            # Show the response
            st.markdown(f"**Assistant:** {reply}")

    except Exception as e:
        st.error(f"Error: {e}")
