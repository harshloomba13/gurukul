import streamlit as st
import requests
import os
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Madhushala", layout="centered")
st.title("🍷 Madhushala Event Agent")

if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Ask about bookings, events, menus...")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                headers = {
                    "X-Api-Key": os.getenv("API_KEY"),  # Add API key from environment variable
                    "Content-Type": "application/json"
                }
                res = requests.post(
                    "https://madhushala-api.onrender.com/agent", 
                    json={"message": prompt},
                    headers=headers
                )
                reply = res.json().get("response", "Sorry, something went wrong.")
            except Exception as e:
                reply = f"❌ Error: {str(e)}"
            st.markdown(reply)
            st.session_state.messages.append({"role": "assistant", "content": reply})
