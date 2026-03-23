import streamlit as st
import os
from gemini_integration import run_agent, analyze_document

st.set_page_config(page_title="AI Tax Advisor", layout="wide")

st.title("🇮🇳 AI Tax Advisor (Agent Powered)")

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "auto_profile" not in st.session_state:
    st.session_state.auto_profile = {}

uploaded_file = st.file_uploader("Upload Payslip", type=["jpg","jpeg","png"])

if uploaded_file:
    st.info("Analyzing...")

    result = analyze_document(
        uploaded_file.read(),
        api_key=os.environ.get("GEMINI_API_KEY")
    )

    if "error" in result:
        st.error(result["error"])
    else:
        st.success("Extracted!")
        st.session_state.auto_profile = result
        st.json(result)

st.subheader("💬 Ask anything")

user_input = st.chat_input("Type your question...")

if user_input:
    response = run_agent(
        user_input,
        api_key=os.environ.get("GEMINI_API_KEY")
    )

    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(response)

    st.session_state.chat_history.append(user_input)
    st.session_state.chat_history.append(response)
