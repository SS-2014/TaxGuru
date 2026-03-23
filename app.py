import streamlit as st
import os
from gemini_integration import call_gemini, analyze_document

st.set_page_config(page_title="Indian Tax Advisor", layout="wide")

st.title("🇮🇳 AI Income Tax Advisor")

# Session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "auto_profile" not in st.session_state:
    st.session_state.auto_profile = {}

profile = {}

# File upload
uploaded_file = st.file_uploader("Upload Payslip / Form 16", type=["jpg","jpeg","png"])

if uploaded_file:
    st.info("Analyzing document...")

    image_bytes = uploaded_file.read()

    result = analyze_document(
        image_bytes=image_bytes,
        api_key=os.environ.get("GEMINI_API_KEY"),
        mime_type=uploaded_file.type
    )

    if "error" in result:
        st.error(result["error"])
    else:
        st.success("Document analyzed!")

        multiplier = 12 if result.get("period") == "monthly" else 1

        extracted_profile = {
            "gross_salary": result.get("gross_salary", 0) * multiplier,
            "basic_salary": result.get("basic_salary", 0) * multiplier,
            "hra_received": result.get("hra", 0) * multiplier,
            "tds_deducted": result.get("tds_deducted", 0) * multiplier,
            "section_80c": result.get("section_80c_total", 0),
            "section_80d_self": result.get("section_80d", 0),
        }

        st.session_state.auto_profile = extracted_profile
        st.json(result)

# Merge profile
profile.update(st.session_state.auto_profile)

st.subheader("💬 Chat with Tax Advisor")

user_input = st.chat_input("Ask your tax question...")

if user_input:
    history = "\n".join(st.session_state.chat_history[-5:])

    full_prompt = f"""
Conversation so far:
{history}

User: {user_input}
"""

    response = call_gemini(
        full_prompt,
        api_key=os.environ.get("GEMINI_API_KEY")
    )

    st.chat_message("user").write(user_input)
    st.chat_message("assistant").write(response)

    st.session_state.chat_history.append(f"User: {user_input}")
    st.session_state.chat_history.append(f"AI: {response}")
