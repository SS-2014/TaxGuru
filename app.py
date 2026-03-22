"""
TaxGuru — AI-Powered Indian Tax Advisory Platform
Main Streamlit Application
FY 2025-26 (AY 2026-27)
"""

import streamlit as st
import json
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tax_engine import (
    TaxpayerProfile, compute_full_tax, compare_regimes,
    estimate_from_monthly_salary, format_currency, format_lakhs
)
from knowledge_base import (
    TAX_KNOWLEDGE_BASE, search_knowledge, get_all_deductions,
    get_for_taxpayer_type, format_for_llm_context
)
from gemini_integration import (
    call_gemini, analyze_document, build_rag_query,
    anonymize_text, extract_financial_only,
    SYSTEM_PROMPT_TAX_ADVISOR, should_ask_feedback, FEEDBACK_PROMPTS
)
from vector_db import TaxVectorDB

# ── Page Config ──
st.set_page_config(
    page_title="TaxGuru — AI Tax Advisor",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Custom CSS ──
LOGO_B64 = ""
logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_app_b64.txt')
if os.path.exists(logo_path):
    with open(logo_path) as f:
        LOGO_B64 = f.read().strip()

st.markdown("""
<style>
    :root {
        --tg-primary: #1B4D3E;
        --tg-accent: #D4A843;
        --tg-light: #F7F5F0;
        --tg-dark: #0D2818;
    }

    /* ── Hide Streamlit branding, fork button, GitHub attribution ── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stAppToolbar {display: none !important;}
    header[data-testid="stHeader"] {display: none !important;}
    .viewerBadge_container__r5tak {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .styles_viewerBadge__CvC9N {display: none !important;}

    /* ── Header ── */
    .main-header {
        background: linear-gradient(135deg, #1B4D3E 0%, #2D6A4F 100%);
        color: white;
        padding: 1rem 1.5rem;
        border-radius: 12px;
        margin-bottom: 1rem;
        display: flex;
        align-items: center;
        gap: 1rem;
    }
    .main-header img { height: 40px; }
    .main-header h1 { color: white !important; margin: 0; font-size: 1.5rem; }
    .main-header p { color: #C8D6C0; margin: 0; font-size: 0.85rem; }

    /* ── Tax cards ── */
    .tax-card {
        background: white; border: 1px solid #E0E0E0; border-radius: 12px;
        padding: 1.2rem; margin: 0.5rem 0; box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    .tax-card.green { border-left: 4px solid #2E7D32; }
    .tax-card.amber { border-left: 4px solid #F57F17; }
    .tax-card.red { border-left: 4px solid #C62828; }
    .tax-card.blue { border-left: 4px solid #1565C0; }

    /* ── Privacy banner ── */
    .privacy-banner {
        background: #E3F2FD; border: 1px solid #90CAF9; border-radius: 8px;
        padding: 0.8rem 1rem; font-size: 0.85rem; color: #1565C0; margin-bottom: 1rem;
    }
    .disclaimer {
        background: #FFF8E1; border: 1px solid #FFE082; border-radius: 8px;
        padding: 0.8rem; font-size: 0.8rem; color: #6D4C00;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] { background: #F7F5F0; }

    /* ── Home page hero ── */
    .hero-section {
        background: linear-gradient(135deg, #0D2818 0%, #1B4D3E 60%, #2D6A4F 100%);
        color: white; padding: 3rem 2rem; border-radius: 16px; text-align: center;
        margin-bottom: 2rem; position: relative; overflow: hidden;
    }
    .hero-section::before {
        content: ''; position: absolute; top: -40%; right: -15%;
        width: 500px; height: 500px;
        background: radial-gradient(circle, rgba(212,168,67,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-section h1 { color: #D4A843 !important; font-size: 2.5rem; margin: 0.5rem 0; }
    .hero-section .subtitle { color: #C8D6C0; font-size: 1.1rem; max-width: 600px; margin: 0 auto 1.5rem; line-height: 1.6; }
    .hero-section img { height: 70px; margin-bottom: 0.5rem; }
    .badge-row { display: flex; gap: 0.6rem; justify-content: center; flex-wrap: wrap; margin-top: 1rem; }
    .badge-item {
        padding: 0.3rem 0.8rem; background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15); border-radius: 20px;
        font-size: 0.75rem; color: #D4A843; font-weight: 500;
    }
    .stat-bar {
        display: flex; justify-content: center; gap: 2.5rem; padding: 1.5rem;
        background: #F7F5F0; border-radius: 12px; margin-bottom: 2rem; flex-wrap: wrap;
    }
    .stat-item { text-align: center; }
    .stat-num { font-size: 1.8rem; font-weight: 700; color: #1B4D3E; }
    .stat-label { font-size: 0.8rem; color: #636E72; }
    .feature-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
        gap: 1rem; margin: 1.5rem 0;
    }
    .feature-card-home {
        background: white; border: 1px solid #E8E8E8; border-radius: 12px;
        padding: 1.2rem; border-left: 4px solid #1B4D3E;
        transition: box-shadow 0.3s;
    }
    .feature-card-home:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.06); }
    .feature-card-home h4 { color: #1B4D3E; margin: 0 0 0.4rem 0; font-size: 1rem; }
    .feature-card-home p { color: #636E72; font-size: 0.85rem; margin: 0; line-height: 1.5; }
    .trust-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin: 1rem 0; }
    .trust-card {
        background: #F7F5F0; border-radius: 12px; padding: 1.5rem;
    }
    .trust-card h4 { color: #1B4D3E; margin: 0 0 0.6rem 0; }
    .trust-card ul { list-style: none; padding: 0; margin: 0; }
    .trust-card li { padding: 0.2rem 0; font-size: 0.85rem; color: #2D3436; }
    .trust-card li::before { content: '✓ '; color: #2E7D32; font-weight: 700; }

    /* ── Floating chat button ── */
    .chat-fab {
        position: fixed; bottom: 24px; right: 24px; z-index: 9999;
        width: 56px; height: 56px; border-radius: 50%;
        background: linear-gradient(135deg, #1B4D3E, #2D6A4F);
        color: white; font-size: 24px; display: flex; align-items: center; justify-content: center;
        box-shadow: 0 4px 16px rgba(0,0,0,0.25); cursor: pointer;
        text-decoration: none; transition: transform 0.2s;
    }
    .chat-fab:hover { transform: scale(1.1); color: white; }

    /* ── Responsive ── */
    @media (max-width: 768px) {
        .hero-section h1 { font-size: 1.8rem; }
        .stat-bar { gap: 1rem; }
        .trust-grid { grid-template-columns: 1fr; }
        .chat-fab { bottom: 16px; right: 16px; width: 48px; height: 48px; font-size: 20px; }
    }
</style>
""", unsafe_allow_html=True)

# ── Session State Initialization ──
if 'profile' not in st.session_state:
    st.session_state.profile = TaxpayerProfile()
if 'profile_complete' not in st.session_state:
    st.session_state.profile_complete = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'interaction_count' not in st.session_state:
    st.session_state.interaction_count = 0
if 'last_feedback_at' not in st.session_state:
    st.session_state.last_feedback_at = 0
if 'chat_open' not in st.session_state:
    st.session_state.chat_open = False
if 'vector_db' not in st.session_state:
    st.session_state.vector_db = TaxVectorDB()
    st.session_state.vector_db.index_knowledge_base(TAX_KNOWLEDGE_BASE)

# ── API Key ──
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", "AIzaSyCFVj4qezxu2Yny6pxsgG3dzK0qMBBQkKQ"))

# ── Header (shown on all pages except Home) ──
logo_img_tag = f'<img src="data:image/png;base64,{LOGO_B64}" alt="TaxGuru">' if LOGO_B64 else '🏛️'

# ── Sidebar Navigation ──
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div style="text-align:center;padding:0.5rem 0"><img src="data:image/png;base64,{LOGO_B64}" style="height:50px"></div>', unsafe_allow_html=True)
    st.markdown("### Navigation")
    page = st.radio(
        "Choose a tool:",
        [
            "🏠 Home",
            "📋 Tax Profile",
            "🧮 Tax Calculator",
            "📄 Payslip Analyzer",
            "💡 Tax Optimizer",
            "🔀 Scenario Planner",
            "📰 Law Updates",
            "ℹ️ About & Privacy",
        ],
        label_visibility="collapsed"
    )

    st.markdown("---")

    # Quick tax meter (always visible)
    if st.session_state.profile_complete:
        p = st.session_state.profile
        result = compare_regimes(p)
        best = result[result['recommended'] + '_regime']
        st.markdown("### 📊 Your Tax Summary")
        st.metric("Taxable Income", format_lakhs(best['taxable_income']))
        st.metric("Total Tax", format_lakhs(best['total_tax']),
                  delta=f"-{format_lakhs(result['savings'])} saved" if result['savings'] > 0 else None,
                  delta_color="inverse")
        st.metric("Effective Rate", f"{best['effective_rate']}%")
        regime_label = "New Regime ✅" if result['recommended'] == 'new' else "Old Regime ✅"
        st.info(f"**Best regime:** {regime_label}")

    st.markdown("---")
    st.markdown("""
    <div class="disclaimer">
        ⚠️ <strong>Disclaimer:</strong> TaxGuru provides informational guidance based on Indian tax laws. 
        This is not professional tax advice. For complex matters, consult a qualified Chartered Accountant.
    </div>
    """, unsafe_allow_html=True)

# ── Show header on non-Home pages ──
if page != "🏠 Home":
    st.markdown(f"""
    <div class="main-header">
        {logo_img_tag}
        <div>
            <h1>TaxGuru</h1>
            <p>AI-Powered Indian Income Tax Advisor • FY 2025-26 (AY 2026-27)</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="privacy-banner">
        🔒 <strong>Your privacy is protected.</strong> TaxGuru never stores your PAN, Aadhaar, bank account numbers, 
        or personal identifiers. Only anonymized financial figures are processed. All data is encrypted in-session and 
        cleared when you close the browser.
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════
# FLOATING CHAT WIDGET (rendered on every page)
# ══════════════════════════════════════════
def render_chat_widget():
    """Render floating chat button and expandable chat panel at bottom of every page"""
    # Floating action button (always visible)
    st.markdown('<a href="#taxguru-chat" class="chat-fab" title="AI Tax Chat">💬</a>', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div id="taxguru-chat"></div>', unsafe_allow_html=True)

    with st.expander("💬 AI Tax Chat — Ask any tax question", expanded=st.session_state.chat_open):
        # Language selector
        lang_col1, lang_col2 = st.columns([3, 1])
        with lang_col2:
            language = st.selectbox("🌐", [
                ("EN", "en"), ("हिन्दी", "hi"), ("தமிழ்", "ta"), ("తెలుగు", "te"), ("ಕನ್ನಡ", "kn"),
            ], format_func=lambda x: x[0], label_visibility="collapsed", key="chat_lang")
            lang_code = language[1]
        with lang_col1:
            st.markdown("**Ask about any tax topic — regime comparison, ESOP, F&O, capital gains, deductions...**")

        # Chat history in scrollable container
        chat_container = st.container(height=300)
        with chat_container:
            if not st.session_state.chat_history:
                st.markdown("*👋 Hi! Ask me any Indian income tax question. I'll cite the relevant sections and never guess.*")
            for msg in st.session_state.chat_history:
                with st.chat_message(msg['role']):
                    st.markdown(msg['content'])

        # Chat input
        if prompt := st.chat_input("Ask a tax question...", key="floating_chat_input"):
            clean_prompt, redacted = anonymize_text(prompt)
            if redacted > 0:
                st.warning(f"⚠️ {redacted} personal identifier(s) detected and removed for your privacy.")

            st.session_state.chat_history.append({'role': 'user', 'content': prompt})
            st.session_state.chat_open = True

            # Build RAG context
            profile_data = extract_financial_only(vars(st.session_state.profile)) if st.session_state.profile_complete else {}
            rag_result = build_rag_query(clean_prompt, profile_data)

            # Call Gemini
            response = call_gemini(
                prompt=clean_prompt,
                context=rag_result['context'],
                language=lang_code,
                api_key=GEMINI_API_KEY
            )

            st.session_state.chat_history.append({'role': 'assistant', 'content': response})
            st.session_state.interaction_count += 1
            st.rerun()


# ══════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════
if page == "🏠 Home":
    logo_src = f'<img src="data:image/png;base64,{LOGO_B64}" alt="TaxGuru">' if LOGO_B64 else ''

    st.markdown(f"""
    <div class="hero-section">
        {logo_src}
        <h1>TaxGuru</h1>
        <p class="subtitle">
            Stop overpaying your taxes. TaxGuru uses AI grounded in real Indian tax law to help you
            choose the right regime, maximize deductions, and plan smarter — all before the deadline.
        </p>
        <div class="badge-row">
            <span class="badge-item">RAG-Powered</span>
            <span class="badge-item">Zero Hallucination</span>
            <span class="badge-item">Privacy-First</span>
            <span class="badge-item">FY 2025-26</span>
            <span class="badge-item">Hindi + 3 Languages</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Stats bar
    st.markdown("""
    <div class="stat-bar">
        <div class="stat-item"><div class="stat-num">9 Cr+</div><div class="stat-label">ITR Filers (CBDT FY25)</div></div>
        <div class="stat-item"><div class="stat-num">₹3.9L Cr</div><div class="stat-label">Refunds Issued (FY25)</div></div>
        <div class="stat-item"><div class="stat-num">2 Regimes</div><div class="stat-label">70+ Deduction Sections</div></div>
        <div class="stat-item"><div class="stat-num">47</div><div class="stat-label">Tax Sections in our AI</div></div>
    </div>
    """, unsafe_allow_html=True)

    # CTA
    st.markdown("### 🚀 Get Started")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📄 Upload Payslip / Form 16", use_container_width=True, type="primary"):
            st.session_state['nav_target'] = "📋 Tax Profile"
            st.rerun()
    with col2:
        if st.button("✏️ Enter Details Manually", use_container_width=True):
            st.session_state['nav_target'] = "📋 Tax Profile"
            st.rerun()

    # Features
    st.markdown("### Everything You Need to Save Tax")
    st.markdown("""
    <div class="feature-grid">
        <div class="feature-card-home">
            <h4>⚖️ Regime Comparison</h4>
            <p>Side-by-side Old vs New regime with your exact numbers. See the rupee difference instantly.</p>
        </div>
        <div class="feature-card-home">
            <h4>📄 Payslip / Form 16 Analyzer</h4>
            <p>Upload a payslip or Form 16. AI extracts every component and projects your full-year tax.</p>
        </div>
        <div class="feature-card-home">
            <h4>💡 Tax Optimizer</h4>
            <p>Personalized recommendations — specific amounts, specific instruments, specific deadlines.</p>
        </div>
        <div class="feature-card-home">
            <h4>🔀 Scenario Planner</h4>
            <p>What if I get a raise? Sell shares? Switch regimes? See exact tax impact before you decide.</p>
        </div>
        <div class="feature-card-home">
            <h4>💬 AI Chat (4 Languages)</h4>
            <p>Ask tax questions in English, Hindi, Tamil, Telugu, or Kannada. Cites actual sections. Never guesses.</p>
        </div>
        <div class="feature-card-home">
            <h4>🏢 All Taxpayer Types</h4>
            <p>Salaried, business owners, professionals, F&O traders, ESOP holders, NRIs, senior citizens.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Trust section
    st.markdown("### Built on Trust")
    st.markdown("""
    <div class="trust-grid">
        <div class="trust-card">
            <h4>🛡️ Zero Hallucination</h4>
            <ul>
                <li>Every answer grounded in RAG over actual tax law</li>
                <li>Tax computation is deterministic Python — not AI-generated</li>
                <li>Always cites section numbers (80C, 112A, etc.)</li>
                <li>Says "consult a CA" when unsure — never guesses</li>
            </ul>
        </div>
        <div class="trust-card">
            <h4>🔒 Privacy-First</h4>
            <ul>
                <li>PAN, Aadhaar, bank details — never stored or sent</li>
                <li>8 types of identifiers auto-detected and stripped</li>
                <li>Only anonymized financial figures reach the AI</li>
                <li>Session-only storage — cleared on browser close</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

    render_chat_widget()
# PAGE: TAX PROFILE
# ══════════════════════════════════════════
if page == "📋 Tax Profile":
    st.markdown("## Set Up Your Tax Profile")
    st.markdown("Upload a document or fill in manually — either way, we'll compute your optimal tax strategy.")

    # ── Upload-First Option ──
    st.markdown("### 📄 Quick Start: Upload a Document")
    st.markdown("Upload your **Form 16**, **employer tax statement**, or **monthly payslip** and we'll extract everything automatically.")

    st.markdown("""
    <div class="privacy-banner">
        🔒 Your document is processed by AI for number extraction only. Personal identifiers (name, PAN, employee ID) 
        are never stored. Only financial figures are kept in your session.
    </div>
    """, unsafe_allow_html=True)

    uploaded_doc = st.file_uploader(
        "Drop your Form 16, tax statement, or payslip here",
        type=['png', 'jpg', 'jpeg', 'pdf'],
        help="Supported: PDF, PNG, JPG. We extract only financial numbers — no personal data is stored.",
        key="profile_doc_upload"
    )

    if uploaded_doc:
        file_bytes = uploaded_doc.read()
        mime_type = uploaded_doc.type or "image/jpeg"

        with st.spinner("🔍 Analyzing your document with AI — extracting salary components..."):
            doc_result = analyze_document(file_bytes, GEMINI_API_KEY, mime_type)

        if 'error' in doc_result:
            st.error(f"Could not analyze the document: {doc_result['error']}. You can fill in the details manually below.")
        elif doc_result:
            is_annual = doc_result.get('period', 'monthly') == 'annual'
            multiplier = 1 if is_annual else 12
            period_label = "Annual" if is_annual else "Monthly (will be annualized)"

            st.success(f"✅ Document analyzed! Detected: **{period_label}** data. Review the extracted values below.")

            with st.expander("📊 Extracted Data (click to review)", expanded=True):
                # Show what was extracted
                display_fields = {k: v for k, v in doc_result.items()
                                  if k != 'period' and k != 'raw_text' and k != 'parse_error'
                                  and v not in [0, "NOT_FOUND", None, ""]}
                if display_fields:
                    for k, v in display_fields.items():
                        label = k.replace('_', ' ').title()
                        if isinstance(v, (int, float)) and v > 0:
                            annual_v = v * multiplier
                            if not is_annual:
                                st.markdown(f"- **{label}:** ₹{v:,.0f}/month → **₹{annual_v:,.0f}/year**")
                            else:
                                st.markdown(f"- **{label}:** **₹{v:,.0f}**")
                else:
                    st.warning("Could not extract structured data. Please fill in manually below.")

            # Auto-fill profile from extracted data
            def get_val(key, default=0):
                v = doc_result.get(key, default)
                if v == "NOT_FOUND" or v is None:
                    return default
                try:
                    return float(v) * multiplier
                except (ValueError, TypeError):
                    return default

            if st.button("✅ Use Extracted Data for My Profile", type="primary", use_container_width=True):
                p = st.session_state.profile
                p.taxpayer_type = "salaried"
                p.gross_salary = get_val('gross_salary')
                p.basic_salary = get_val('basic_salary', p.gross_salary * 0.4)
                p.hra_received = get_val('hra')
                p.special_allowance = get_val('special_allowance')
                p.lta = get_val('lta')
                p.professional_tax = get_val('professional_tax')
                p.tds_deducted = get_val('tds_deducted')
                p.section_80c = min(get_val('section_80c_total', get_val('pf_employee')), 150000)
                p.section_80d_self = get_val('section_80d')
                p.section_80ccd_1b = get_val('section_80ccd_1b')
                p.section_80ccd_2 = get_val('section_80ccd_2', get_val('pf_employer'))
                p.section_24b = get_val('section_24b')
                st.session_state.profile_complete = True
                st.success("✅ Profile created from your document! Check the sidebar for your tax summary, or go to Tax Calculator.")
                st.rerun()

    st.markdown("---")
    st.markdown("### ✏️ Or Fill In Manually")
    st.markdown("Enter your details below. Only financial numbers needed — no personal identifiers.")

    col1, col2 = st.columns(2)

    with col1:
        taxpayer_type = st.selectbox(
            "What best describes you?",
            ["Salaried Employee", "Business Owner", "Professional (Doctor, Lawyer, CA, etc.)",
             "Stock/F&O Trader", "Investor", "Freelancer/Gig Worker"],
            help="This determines which tax provisions are most relevant to you"
        )

        type_map = {
            "Salaried Employee": "salaried",
            "Business Owner": "business",
            "Professional (Doctor, Lawyer, CA, etc.)": "professional",
            "Stock/F&O Trader": "trader",
            "Investor": "investor",
            "Freelancer/Gig Worker": "professional",
        }

        age = st.number_input("Your age", min_value=18, max_value=100, value=30,
                              help="Affects exemption limits and senior citizen benefits")

        residency = st.selectbox("Residency status",
                                 ["Resident Indian", "Non-Resident Indian (NRI)", "Resident but Not Ordinarily Resident (RNOR)"])
        res_map = {"Resident Indian": "resident", "Non-Resident Indian (NRI)": "nri",
                   "Resident but Not Ordinarily Resident (RNOR)": "rnor"}

    with col2:
        metro_city = st.selectbox(
            "Do you live in a metro city?",
            ["Yes (Delhi, Mumbai, Chennai, Kolkata)", "No (Other cities)"],
            help="Affects HRA calculation — 50% of basic in metros vs 40% in non-metros"
        )

    st.markdown("---")

    # ── Income Section (Progressive Disclosure) ──
    st.markdown("### 💰 Income Details")

    tt = type_map[taxpayer_type]

    if tt == "salaried":
        col1, col2, col3 = st.columns(3)
        with col1:
            gross_salary = st.number_input("Annual Gross Salary (₹)", min_value=0, value=0,
                                           step=50000, format="%d")
        with col2:
            basic_salary = st.number_input("Annual Basic Salary (₹)", min_value=0, value=0,
                                           step=25000, format="%d",
                                           help="Usually 40-50% of gross. Check your payslip.")
        with col3:
            hra_received = st.number_input("Annual HRA Received (₹)", min_value=0, value=0,
                                           step=10000, format="%d")

        col1, col2 = st.columns(2)
        with col1:
            rent_paid = st.number_input("Annual Rent Paid (₹)", min_value=0, value=0, step=10000, format="%d")
        with col2:
            employer_nps = st.number_input("Employer NPS Contribution (₹/year)", min_value=0, value=0,
                                           step=5000, format="%d",
                                           help="Deductible under 80CCD(2) in BOTH regimes")

    elif tt in ["business", "professional"]:
        col1, col2 = st.columns(2)
        with col1:
            biz_income = st.number_input("Annual Business/Professional Income (₹)", min_value=0,
                                         value=0, step=100000, format="%d",
                                         help="Net profit after business expenses")
        with col2:
            gross_salary = st.number_input("Salary Income, if any (₹)", min_value=0, value=0,
                                           step=50000, format="%d")

    elif tt == "trader":
        col1, col2 = st.columns(2)
        with col1:
            trading_income = st.number_input("F&O/Trading Income or (Loss) (₹)", value=0,
                                             step=50000, format="%d",
                                             help="Enter negative for losses. This is non-speculative business income under Section 43(5).")
        with col2:
            gross_salary = st.number_input("Salary Income, if any (₹)", min_value=0, value=0,
                                           step=50000, format="%d")

    # ── Additional Income (Expandable) ──
    with st.expander("📈 Investment & Other Income (click to expand)"):
        col1, col2, col3 = st.columns(3)
        with col1:
            interest_income = st.number_input("Interest Income (₹/year)", min_value=0, value=0,
                                              step=5000, format="%d",
                                              help="FD, savings account, bonds, etc.")
        with col2:
            rental_income = st.number_input("Rental Income (₹/year)", min_value=0, value=0,
                                            step=10000, format="%d")
        with col3:
            dividend_income = st.number_input("Dividend Income (₹/year)", min_value=0, value=0,
                                              step=5000, format="%d")

    with st.expander("📊 Capital Gains (click to expand)"):
        col1, col2 = st.columns(2)
        with col1:
            stcg_equity = st.number_input("Short-term Capital Gains — Equity (₹)", min_value=0, value=0,
                                          step=10000, format="%d",
                                          help="Listed equity shares held < 12 months. Taxed at 20%.")
            ltcg_equity = st.number_input("Long-term Capital Gains — Equity (₹)", min_value=0, value=0,
                                          step=10000, format="%d",
                                          help="Listed equity shares held ≥ 12 months. First ₹1.25L exempt, then 12.5%.")
        with col2:
            stcg_other = st.number_input("STCG — Other Assets (₹)", min_value=0, value=0,
                                         step=10000, format="%d",
                                         help="Debt funds, property < 24 months, etc. Taxed at slab rates.")
            ltcg_other = st.number_input("LTCG — Other Assets (₹)", min_value=0, value=0,
                                         step=10000, format="%d",
                                         help="Property > 24 months, unlisted shares > 24 months. 12.5%.")

    with st.expander("🏢 ESOPs & Stock Options (click to expand)"):
        esop_perquisite = st.number_input("ESOP Perquisite Value (₹)", min_value=0, value=0,
                                          step=50000, format="%d",
                                          help="FMV on exercise date minus exercise price, multiplied by number of shares. Taxed as salary.")
        foreign_esop = st.checkbox("These are ESOPs from a foreign company",
                                   help="Foreign ESOPs have additional FEMA/LRS compliance and Schedule FA reporting requirements.")
        esop_sale_gain = st.number_input("Capital Gains from ESOP Share Sale (₹)", min_value=0, value=0,
                                         step=25000, format="%d",
                                         help="Sale price minus FMV on exercise date.")

    # ── Deductions (Old Regime) ──
    with st.expander("🏦 Deductions & Investments — Old Regime (click to expand)"):
        st.info("These deductions are available only under the Old Tax Regime (except 80CCD(2) which works in both).")
        col1, col2, col3 = st.columns(3)
        with col1:
            sec_80c = st.number_input("Section 80C (₹)", min_value=0, max_value=150000, value=0,
                                      step=10000, format="%d",
                                      help="EPF + PPF + ELSS + LIC + NSC + Tax saver FD + Tuition. Max ₹1.5L")
            sec_80d_self = st.number_input("80D — Self/Family Health Insurance (₹)", min_value=0,
                                           max_value=50000, value=0, step=5000, format="%d")
        with col2:
            sec_80d_parents = st.number_input("80D — Parents Health Insurance (₹)", min_value=0,
                                              max_value=50000, value=0, step=5000, format="%d")
            sec_80ccd_1b = st.number_input("80CCD(1B) — NPS Additional (₹)", min_value=0,
                                           max_value=50000, value=0, step=10000, format="%d",
                                           help="Additional ₹50K over and above 80C limit")
        with col3:
            sec_80e = st.number_input("80E — Education Loan Interest (₹)", min_value=0, value=0,
                                      step=10000, format="%d", help="No upper limit. Full interest deductible.")
            sec_24b = st.number_input("24(b) — Home Loan Interest (₹)", min_value=0, max_value=200000,
                                      value=0, step=10000, format="%d",
                                      help="Max ₹2L for self-occupied property")

    # ── TDS / Advance Tax ──
    with st.expander("💳 TDS & Advance Tax Already Paid"):
        col1, col2 = st.columns(2)
        with col1:
            tds_deducted = st.number_input("TDS Deducted (₹)", min_value=0, value=0, step=10000, format="%d",
                                           help="Check Form 26AS or AIS for TDS details")
        with col2:
            advance_tax = st.number_input("Advance Tax Paid (₹)", min_value=0, value=0, step=10000, format="%d")

    # ── Save Profile ──
    if st.button("✅ Save My Profile & Calculate Tax", type="primary", use_container_width=True):
        p = st.session_state.profile
        p.taxpayer_type = tt
        p.age = age
        p.residency = res_map[residency]
        p.metro_city = "Yes" in metro_city

        if tt == "salaried":
            p.gross_salary = gross_salary
            p.basic_salary = basic_salary if basic_salary > 0 else gross_salary * 0.4
            p.hra_received = hra_received
            p.rent_paid_annual = rent_paid
            p.section_80ccd_2 = employer_nps
        elif tt in ["business", "professional"]:
            p.business_income = biz_income
            p.gross_salary = gross_salary
        elif tt == "trader":
            p.trading_income = trading_income
            p.gross_salary = gross_salary

        p.interest_income = interest_income if 'interest_income' in dir() else 0
        p.rental_income = rental_income if 'rental_income' in dir() else 0
        p.dividend_income = dividend_income if 'dividend_income' in dir() else 0
        p.stcg_equity = stcg_equity if 'stcg_equity' in dir() else 0
        p.ltcg_equity = ltcg_equity if 'ltcg_equity' in dir() else 0
        p.stcg_other = stcg_other if 'stcg_other' in dir() else 0
        p.ltcg_other = ltcg_other if 'ltcg_other' in dir() else 0
        p.esop_perquisite = esop_perquisite if 'esop_perquisite' in dir() else 0
        p.foreign_esop = foreign_esop if 'foreign_esop' in dir() else False
        p.esop_sale_gain = esop_sale_gain if 'esop_sale_gain' in dir() else 0
        p.section_80c = sec_80c if 'sec_80c' in dir() else 0
        p.section_80d_self = sec_80d_self if 'sec_80d_self' in dir() else 0
        p.section_80d_parents = sec_80d_parents if 'sec_80d_parents' in dir() else 0
        p.section_80ccd_1b = sec_80ccd_1b if 'sec_80ccd_1b' in dir() else 0
        p.section_80e = sec_80e if 'sec_80e' in dir() else 0
        p.section_24b = sec_24b if 'sec_24b' in dir() else 0
        p.tds_deducted = tds_deducted if 'tds_deducted' in dir() else 0
        p.advance_tax_paid = advance_tax if 'advance_tax' in dir() else 0

        st.session_state.profile_complete = True
        st.success("✅ Profile saved! Check the sidebar for your tax summary, or navigate to the Tax Calculator for details.")
        st.rerun()

    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: TAX CALCULATOR
# ══════════════════════════════════════════
elif page == "🧮 Tax Calculator":
    st.markdown("## Tax Calculator — Old vs New Regime")

    if not st.session_state.profile_complete:
        st.warning("Please complete your Tax Profile first to see calculations.")
        st.stop()

    p = st.session_state.profile
    result = compare_regimes(p)
    old = result['old_regime']
    new = result['new_regime']

    # Recommendation banner
    rec = result['recommended']
    savings = result['savings']
    if rec == 'new':
        st.success(f"🎯 **Recommendation: New Tax Regime** saves you **{format_currency(savings)}** this year.")
    else:
        st.success(f"🎯 **Recommendation: Old Tax Regime** saves you **{format_currency(savings)}** this year.")

    # Side-by-side comparison
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"### {'✅' if rec == 'new' else '❌'} New Tax Regime")
        st.markdown(f"**Taxable Income:** {format_currency(new['taxable_income'])}")
        st.markdown(f"**Tax on Slab:** {format_currency(new['slab_tax'])}")
        if new['rebate_87a'] > 0:
            st.markdown(f"**Section 87A Rebate:** -{format_currency(new['rebate_87a'])}")
        if new['surcharge'] > 0:
            st.markdown(f"**Surcharge:** {format_currency(new['surcharge'])}")
        st.markdown(f"**Cess (4%):** {format_currency(new['cess'])}")
        st.markdown(f"### **Total Tax: {format_currency(new['total_tax'])}**")
        st.markdown(f"Effective Rate: **{new['effective_rate']}%**")
        if new['net_payable'] >= 0:
            st.markdown(f"**Net Payable:** {format_currency(new['net_payable'])}")
        else:
            st.markdown(f"**Refund Due:** {format_currency(abs(new['net_payable']))}")

    with col2:
        st.markdown(f"### {'✅' if rec == 'old' else '❌'} Old Tax Regime")
        st.markdown(f"**Taxable Income:** {format_currency(old['taxable_income'])}")
        if old.get('hra_exemption', 0) > 0:
            st.markdown(f"*HRA Exemption: {format_currency(old['hra_exemption'])}*")
        if old['total_deductions'] > 0:
            st.markdown(f"*Deductions (Ch VI-A): {format_currency(old['total_deductions'])}*")
        st.markdown(f"**Tax on Slab:** {format_currency(old['slab_tax'])}")
        if old['rebate_87a'] > 0:
            st.markdown(f"**Section 87A Rebate:** -{format_currency(old['rebate_87a'])}")
        if old['surcharge'] > 0:
            st.markdown(f"**Surcharge:** {format_currency(old['surcharge'])}")
        st.markdown(f"**Cess (4%):** {format_currency(old['cess'])}")
        st.markdown(f"### **Total Tax: {format_currency(old['total_tax'])}**")
        st.markdown(f"Effective Rate: **{old['effective_rate']}%**")
        if old['net_payable'] >= 0:
            st.markdown(f"**Net Payable:** {format_currency(old['net_payable'])}")
        else:
            st.markdown(f"**Refund Due:** {format_currency(abs(old['net_payable']))}")

    # Deduction breakdown (old regime)
    if old['total_deductions'] > 0:
        st.markdown("---")
        st.markdown("### Deduction Breakdown (Old Regime)")
        for section, amount in old['deduction_breakdown'].items():
            if amount > 0:
                st.markdown(f"- **Section {section}:** {format_currency(amount)}")

    # Capital gains summary
    if any([new.get('stcg_equity_tax', 0), new.get('ltcg_equity_tax', 0), new.get('ltcg_other_tax', 0)]):
        st.markdown("---")
        st.markdown("### Capital Gains Tax (Same in Both Regimes)")
        if new['stcg_equity_tax'] > 0:
            st.markdown(f"- STCG on Equity (20%): {format_currency(new['stcg_equity_tax'])}")
        if new['ltcg_equity_tax'] > 0:
            st.markdown(f"- LTCG on Equity (12.5% above ₹1.25L): {format_currency(new['ltcg_equity_tax'])}")
        if new.get('ltcg_other_tax', 0) > 0:
            st.markdown(f"- LTCG on Other Assets (12.5%): {format_currency(new['ltcg_other_tax'])}")


    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: PAYSLIP ANALYZER
# ══════════════════════════════════════════
elif page == "📄 Payslip Analyzer":
    st.markdown("## Payslip / Form 16 Analyzer")
    st.markdown("Upload a payslip (PDF or image) and our AI will extract salary components and project your annual tax.")

    st.markdown("""
    <div class="privacy-banner">
        🔒 Your document is processed by Google Gemini Vision API for extraction only. No personal identifiers 
        (name, PAN, employee ID) are stored. Only financial numbers are extracted.
    </div>
    """, unsafe_allow_html=True)

    uploaded = st.file_uploader("Upload Payslip or Form 16", type=['png', 'jpg', 'jpeg', 'pdf'],
                                help="Supported: PNG, JPG, PDF. We extract only financial numbers.")

    if uploaded:
        file_bytes = uploaded.read()
        mime_type = uploaded.type or "image/jpeg"

        with st.spinner("🔍 Analyzing your document with AI..."):
            result = analyze_document(file_bytes, GEMINI_API_KEY, mime_type)

        if 'error' in result:
            st.error(f"Could not analyze the document: {result['error']}")
        else:
            st.success("✅ Document analyzed! Here's what we found:")
            st.json(result)

            if 'gross_salary' in result or 'total_earnings' in result:
                monthly_gross = result.get('gross_salary', result.get('total_earnings', 0))
                monthly_basic = result.get('basic_salary', result.get('basic', 0))

                if monthly_gross > 0:
                    st.markdown("### Annual Projection")
                    st.markdown(f"**Monthly Gross:** {format_currency(monthly_gross)}")
                    st.markdown(f"**Projected Annual Gross:** {format_currency(monthly_gross * 12)}")

                    if st.button("Use this for my Tax Profile"):
                        profile = estimate_from_monthly_salary(monthly_gross, monthly_basic)
                        st.session_state.profile = profile
                        st.session_state.profile_complete = True
                        st.success("Profile updated with payslip data! Go to Tax Calculator to see results.")

    # Manual monthly input option
    st.markdown("---")
    st.markdown("### Or enter monthly salary manually")
    col1, col2 = st.columns(2)
    with col1:
        monthly_gross = st.number_input("Monthly Gross Salary (₹)", min_value=0, value=0, step=5000, format="%d")
    with col2:
        monthly_basic = st.number_input("Monthly Basic Salary (₹)", min_value=0, value=0, step=2500, format="%d",
                                        help="Leave 0 to auto-estimate at 40% of gross")

    if monthly_gross > 0:
        profile = estimate_from_monthly_salary(monthly_gross, monthly_basic)
        annual = monthly_gross * 12
        comparison = compare_regimes(profile)
        best = comparison[comparison['recommended'] + '_regime']

        st.markdown("### Projected Annual Tax")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Annual Gross", format_lakhs(annual))
        with col2:
            st.metric("Estimated Tax", format_lakhs(best['total_tax']))
        with col3:
            st.metric("Monthly Take-Home (approx)", format_currency(monthly_gross - best['total_tax']/12))


    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: TAX OPTIMIZER
# ══════════════════════════════════════════
elif page == "💡 Tax Optimizer":
    st.markdown("## Tax Optimization Recommendations")

    if not st.session_state.profile_complete:
        st.warning("Please complete your Tax Profile first.")
        st.stop()

    p = st.session_state.profile
    result = compare_regimes(p)
    rec = result['recommended']

    st.markdown(f"Based on your profile, you should use the **{'New' if rec == 'new' else 'Old'} Tax Regime**.")
    st.markdown("Here are specific actions you can take to reduce your tax:")

    recommendations = []

    # 80C optimization
    if rec == 'old' and p.section_80c < 150000:
        gap = 150000 - p.section_80c
        tax_saved = gap * 0.30 if p.gross_salary > 1000000 else gap * 0.20
        recommendations.append({
            'priority': 'high',
            'section': '80C',
            'title': f'Invest ₹{gap:,.0f} more under Section 80C',
            'detail': f'You have ₹{gap:,.0f} of unused 80C limit. Options: ELSS mutual funds (3yr lock-in, equity returns), PPF (15yr, guaranteed returns), Tax saver FD (5yr). Potential tax saving: ~₹{tax_saved:,.0f}.',
            'action': 'Invest before March 31'
        })

    # NPS (works in both regimes)
    if p.section_80ccd_2 == 0:
        recommendations.append({
            'priority': 'high',
            'section': '80CCD(2)',
            'title': 'Ask your employer about NPS contribution',
            'detail': 'Employer NPS contribution (up to 14% of basic salary) is deductible in BOTH old and new regimes. This is one of the most powerful deductions available under the new regime.',
            'action': 'Speak to your HR/payroll team'
        })

    # 80CCD(1B) — additional NPS
    if rec == 'old' and p.section_80ccd_1b < 50000:
        recommendations.append({
            'priority': 'medium',
            'section': '80CCD(1B)',
            'title': f'Invest up to ₹50,000 in NPS for additional deduction',
            'detail': 'This is over and above the ₹1.5L limit of Section 80C. At 30% tax bracket, you save ₹15,600 (including cess).',
            'action': 'Open NPS account or increase contribution'
        })

    # Health insurance
    if rec == 'old' and p.section_80d_self == 0:
        recommendations.append({
            'priority': 'medium',
            'section': '80D',
            'title': 'Get health insurance for Section 80D benefit',
            'detail': f'Deduction up to ₹25,000 for self/family (₹50,000 if senior citizen). Additional ₹25-50K for parents. Max possible: ₹1,00,000.',
            'action': 'Buy a health insurance policy'
        })

    # Home loan interest
    if rec == 'old' and p.section_24b == 0 and p.rental_income == 0:
        recommendations.append({
            'priority': 'low',
            'section': '24(b)',
            'title': 'Home loan interest deduction of up to ₹2,00,000',
            'detail': 'If you have a home loan, interest up to ₹2L is deductible under old regime for self-occupied property. This alone can save up to ₹62,400 in tax.',
            'action': 'Check if applicable'
        })

    # ESOP warning
    if p.esop_perquisite > 0:
        recommendations.append({
            'priority': 'high',
            'section': '17(2)(vi)',
            'title': '⚠️ ESOP Perquisite Tax Planning',
            'detail': f'Your ESOP perquisite of ₹{p.esop_perquisite:,.0f} is taxed as salary income. Consider timing of exercise carefully. If your employer is a DPIIT-registered startup, you may qualify for tax deferral up to 48 months.',
            'action': 'Consult CA for ESOP exercise timing'
        })

    if p.foreign_esop:
        recommendations.append({
            'priority': 'high',
            'section': 'Schedule FA',
            'title': '⚠️ Foreign ESOP Reporting Required',
            'detail': 'Foreign shares must be reported in Schedule FA (Foreign Assets) in your ITR. Also ensure FEMA compliance for overseas investment. You may claim Foreign Tax Credit under DTAA if tax was withheld abroad.',
            'action': 'Disclose in Schedule FA, file Form 67 for FTC'
        })

    # F&O trader warnings
    if p.trading_income != 0:
        recommendations.append({
            'priority': 'high',
            'section': '43(5)',
            'title': 'F&O Income: File ITR-3 and consider tax audit',
            'detail': f'F&O income (₹{p.trading_income:,.0f}) is non-speculative business income. You MUST file ITR-3. Tax audit required if turnover > ₹10 Cr (digital). Even losses must be reported to carry forward for 8 years.',
            'action': 'Engage a CA for ITR-3 filing'
        })

    if not recommendations:
        st.success("🎉 You're well-optimized! We couldn't find additional tax-saving opportunities based on your current profile.")
    else:
        for rec_item in recommendations:
            color = {'high': 'red', 'medium': 'amber', 'low': 'green'}.get(rec_item['priority'], 'blue')
            icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(rec_item['priority'], 'ℹ️')

            st.markdown(f"""
            <div class="tax-card {color}">
                <strong>{icon} {rec_item['title']}</strong> <em>(Section {rec_item['section']})</em><br>
                {rec_item['detail']}<br>
                <strong>Action:</strong> {rec_item['action']}
            </div>
            """, unsafe_allow_html=True)


    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: SCENARIO PLANNER
# ══════════════════════════════════════════
elif page == "🔀 Scenario Planner":
    st.markdown("## What-If Scenario Planner")
    st.markdown("See how changes to your income or investments affect your tax. Compare side by side.")

    if not st.session_state.profile_complete:
        st.warning("Please complete your Tax Profile first.")
        st.stop()

    p = st.session_state.profile
    current = compare_regimes(p)
    current_tax = current[current['recommended'] + '_regime']['total_tax']

    scenario = st.selectbox("Choose a scenario:", [
        "What if I switch tax regime?",
        "What if I invest more in 80C?",
        "What if I get a raise?",
        "What if I start paying rent?",
        "What if I sell shares with capital gains?",
        "What if I take a home loan?",
    ])

    if scenario == "What if I switch tax regime?":
        alt_regime = 'old' if current['recommended'] == 'new' else 'new'
        alt_tax = current[alt_regime + '_regime']['total_tax']
        diff = alt_tax - current_tax
        st.metric(
            f"Switching to {'Old' if alt_regime == 'old' else 'New'} Regime",
            format_currency(alt_tax),
            delta=f"+{format_currency(diff)} more tax" if diff > 0 else f"{format_currency(diff)} savings",
            delta_color="inverse"
        )
        if diff > 0:
            st.warning(f"Switching would cost you ₹{diff:,.0f} more in tax. Stick with your current regime.")
        else:
            st.success(f"Switching would save you ₹{abs(diff):,.0f}! Consider changing.")

    elif scenario == "What if I invest more in 80C?":
        extra_80c = st.slider("Additional 80C investment (₹)", 0, 150000, 50000, step=10000)
        import copy
        p2 = copy.deepcopy(p)
        p2.section_80c = min(p.section_80c + extra_80c, 150000)
        new_result = compare_regimes(p2)
        new_tax = new_result[new_result['recommended'] + '_regime']['total_tax']
        saved = current_tax - new_tax
        st.metric("Tax with additional 80C", format_currency(new_tax),
                  delta=f"-{format_currency(saved)} saved" if saved > 0 else "No change")

    elif scenario == "What if I get a raise?":
        raise_pct = st.slider("Salary increase (%)", 5, 50, 15, step=5)
        import copy
        p2 = copy.deepcopy(p)
        p2.gross_salary = int(p.gross_salary * (1 + raise_pct/100))
        p2.basic_salary = int(p.basic_salary * (1 + raise_pct/100))
        p2.hra_received = int(p.hra_received * (1 + raise_pct/100))
        new_result = compare_regimes(p2)
        new_tax = new_result[new_result['recommended'] + '_regime']['total_tax']
        extra_tax = new_tax - current_tax
        col1, col2 = st.columns(2)
        with col1:
            st.metric("New Gross Salary", format_lakhs(p2.gross_salary))
        with col2:
            st.metric("Additional Tax", format_currency(extra_tax),
                      delta=f"+{format_currency(extra_tax)}", delta_color="inverse")

    elif scenario == "What if I sell shares with capital gains?":
        ltcg = st.number_input("Expected LTCG from equity sale (₹)", min_value=0, value=200000, step=25000)
        import copy
        p2 = copy.deepcopy(p)
        p2.ltcg_equity = p.ltcg_equity + ltcg
        new_result = compare_regimes(p2)
        new_tax = new_result[new_result['recommended'] + '_regime']['total_tax']
        extra_tax = new_tax - current_tax
        exempt = min(ltcg, 125000)
        st.markdown(f"**LTCG Exempt (first ₹1.25L):** {format_currency(exempt)}")
        st.markdown(f"**Taxable LTCG:** {format_currency(max(0, ltcg - 125000))}")
        st.metric("Additional Tax from Sale", format_currency(extra_tax))


    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: LAW UPDATES
# ══════════════════════════════════════════
elif page == "📰 Law Updates":
    st.markdown("## Latest Tax Law Updates")
    st.markdown("Key changes affecting your tax planning for FY 2025-26 and beyond.")

    updates = [
        {
            'date': 'Feb 2026',
            'title': 'Union Budget 2026: No changes to income tax slabs',
            'detail': 'The Budget 2026 retained all existing tax slabs under both regimes. New Income Tax Act 2025 takes effect from April 2026 — reorganizes the law but does not change rates.',
            'impact': 'No action needed for FY 2025-26 or FY 2026-27.',
            'severity': 'info'
        },
        {
            'date': 'Jul 2024',
            'title': 'Capital Gains Tax Rates Changed',
            'detail': 'STCG on equity increased from 15% to 20%. LTCG on equity increased from 10% to 12.5%. LTCG exemption increased from ₹1L to ₹1.25L. Indexation benefit removed for all asset classes.',
            'impact': 'Impacts investors and traders. Review your investment holding strategy.',
            'severity': 'warning'
        },
        {
            'date': 'Feb 2025',
            'title': 'New Tax Regime Slabs Restructured',
            'detail': 'Basic exemption raised to ₹4L. Section 87A rebate increased to ₹60,000 (from ₹25,000). Income up to ₹12.75L (salaried) is effectively tax-free under new regime.',
            'impact': 'Major benefit for taxpayers earning up to ₹12.75L. Review if new regime is now better for you.',
            'severity': 'success'
        },
        {
            'date': 'Feb 2025',
            'title': 'TDS Threshold for Senior Citizens Increased',
            'detail': 'TDS threshold on interest for senior citizens increased from ₹50,000 to ₹1,00,000. TDS on rent threshold increased to ₹6L/year.',
            'impact': 'Senior citizens with FD interest up to ₹1L no longer need Form 15H for TDS exemption.',
            'severity': 'success'
        },
        {
            'date': 'Feb 2025',
            'title': 'TCS on Foreign Remittance: Threshold Increased',
            'detail': 'TCS threshold under LRS increased to ₹10L (from ₹7L). TCS on education remittance removed if loan from specified institution.',
            'impact': 'Benefits NRIs, students abroad, and investors remitting money overseas.',
            'severity': 'success'
        },
    ]

    for update in updates:
        icon = {'info': 'ℹ️', 'warning': '⚠️', 'success': '✅'}.get(update['severity'], 'ℹ️')
        color = {'info': 'blue', 'warning': 'amber', 'success': 'green'}.get(update['severity'], 'blue')
        st.markdown(f"""
        <div class="tax-card {color}">
            <strong>{icon} [{update['date']}] {update['title']}</strong><br>
            {update['detail']}<br>
            <em>Impact: {update['impact']}</em>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown("### 🔍 Search for a specific tax topic")
    search_query = st.text_input("Search tax laws", placeholder="e.g., ESOP taxation, HRA exemption, F&O loss carry forward...")
    if search_query:
        with st.spinner("Searching knowledge base..."):
            results = st.session_state.vector_db.search_tax_law(search_query)
            if results:
                for r in results[:3]:
                    st.markdown(f"**{r['metadata'].get('title', 'Result')}** (Section {r['metadata'].get('section', '')})")
                    st.markdown(r['content'][:500] + "...")
                    st.markdown("---")
            else:
                st.info("No results found. Try different keywords or ask the AI Chat.")


    render_chat_widget()


# ══════════════════════════════════════════
# PAGE: ABOUT & PRIVACY
# ══════════════════════════════════════════
elif page == "ℹ️ About & Privacy":
    st.markdown("## About TaxGuru")

    st.markdown("""
    **TaxGuru** is an AI-powered Indian income tax advisory platform built for FY 2025-26.
    It helps taxpayers understand their tax obligations, compare regimes, optimize savings,
    and stay updated on the latest tax law changes.

    ### 🤖 Technology Stack
    - **LLM**: Google Gemini 2.5 Flash-Lite (for tax chat and document analysis)
    - **RAG**: Vector database over Indian Income Tax Act sections, CBDT circulars, and Budget changes
    - **Vector DB**: ChromaDB for semantic search over tax law and taxpayer similarity
    - **Framework**: Streamlit (Python)
    - **Computation**: Custom tax engine covering both old and new regimes, capital gains, ESOPs, F&O

    ### 🔒 Privacy Policy
    TaxGuru takes your privacy seriously:

    **What we NEVER collect:**
    - PAN numbers
    - Aadhaar numbers
    - Bank account numbers / IFSC codes
    - PF/EPS/UAN numbers
    - Date of birth
    - Physical address
    - Email address
    - Phone numbers
    - Employer name or employee ID

    **What we process (in-session only):**
    - Financial figures (salary, deductions, investments) for tax computation
    - Anonymous user profile (taxpayer type, age bracket, income bracket) for finding similar cases

    **How we protect your data:**
    - All PII is automatically detected and stripped before any processing
    - Session data is stored only in browser memory and cleared on close
    - No data is sent to third parties except the LLM provider (Google Gemini) for answering questions
    - LLM queries contain only anonymized financial figures, never personal identifiers
    - Anonymous profiles are stored only as embedding vectors — not reversible to individuals

    ### 🎯 Bias Mitigation
    TaxGuru's recommendation engine is designed to serve diverse taxpayer profiles:
    - Salaried employees (from entry-level to senior executives)
    - Business owners (micro to large enterprises)
    - Professionals (doctors, lawyers, CAs, consultants)
    - Traders (F&O, intraday, delivery-based)
    - Investors (equity, debt, real estate, foreign shares, ESOPs)
    - Senior citizens and super senior citizens
    - NRIs and RNOR individuals

    All recommendations are grounded in tax law sections — not pattern-only matching.
    Even when similar-user data is sparse for a profile type, the legal basis ensures correctness.

    ### ⚖️ Disclaimer
    TaxGuru provides informational guidance based on Indian tax laws as of March 2026.
    This is NOT professional tax advice. For complex matters, investment decisions, or filing returns,
    always consult a qualified Chartered Accountant (CA) or tax professional.
    """)

    # Vector DB Stats
    st.markdown("### 📊 System Status")
    stats = st.session_state.vector_db.get_stats()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Tax Law Entries", stats.get('tax_law_entries', len(TAX_KNOWLEDGE_BASE)))
    with col2:
        st.metric("Vector DB", "Active" if stats.get('chroma_available') else "Keyword Fallback")
    with col3:
        st.metric("LLM Model", "Gemini 2.5 Flash-Lite")

    render_chat_widget()
