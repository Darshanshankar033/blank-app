import streamlit as st
from openai import OpenAI

# Streamlit UI
st.title("🎈 My Chat App")
st.write("Talk to an OpenRouter model through this simple Streamlit UI!")

# Input field
user_input = st.text_input("Enter your message:")

# Initialize the client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",  #  replace with your actual key
)

# Only call API when user submits text
if user_input:
    with st.spinner("Generating response..."):
        try:
            completion = client.chat.completions.create(
                model="openai/gpt-oss-20b:free",
                messages=[
                    {"role": "user", "content": user_input}
                ],
                extra_headers={
                    "HTTP-Referer": "https://yourappname.streamlit.app",  # optional
                    "X-Title": "Streamlit Chatbot",  # optional
                },
            )
            st.success("Response:")
            st.write(completion.choices[0].message.content)

        except Exception as e:
            st.error(f"Error: {e}")
