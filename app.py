import streamlit as st
import os
from gemini_integration import call_agent, analyze_document

st.set_page_config(page_title="AI Tax Advisor", layout="wide")

st.title("🇮🇳 AI Tax Advisor (Smart Agent)")

# =========================
# SESSION STATE
# =========================
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "user_profile" not in st.session_state:
    st.session_state.user_profile = {}

# =========================
# FILE UPLOAD (PAYSLIP)
# =========================
uploaded_file = st.file_uploader("Upload Payslip", type=["jpg","jpeg","png"])

if uploaded_file:
    st.info("Analyzing payslip...")

    result = analyze_document(
        uploaded_file.read(),
        api_key=os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"),
        mime_type=uploaded_file.type
    )

    if "error" in result:
        st.error(result["error"])
    else:
        st.success("Payslip processed!")

        multiplier = 12 if result.get("period") == "monthly" else 1

        profile = {
            "gross_salary": result.get("gross_salary", 0) * multiplier,
            "basic_salary": result.get("basic_salary", 0) * multiplier,
            "hra_received": result.get("hra", 0) * multiplier,
            "tds_deducted": result.get("tds_deducted", 0) * multiplier,
            "section_80c": result.get("section_80c_total", 0),
            "section_80d": result.get("section_80d", 0),
        }

        st.session_state.user_profile = profile
        st.json(profile)

# =========================
# CHAT UI
# =========================
st.subheader("💬 Ask your tax or finance question")

user_input = st.chat_input("Ask anything...")

if user_input:
    response = call_agent(
        user_input,
        api_key=os.environ.get("GEMINI_API_KEY") or st.secrets.get("GEMINI_API_KEY"),
        user_profile=st.session_state.user_profile
    )

    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(response)

    st.session_state.chat_history.append(user_input)
    st.session_state.chat_history.append(response)
