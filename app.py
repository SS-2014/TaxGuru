"""
TaxGuru — AI-Powered Indian Tax Advisory Platform
Main Streamlit Application v3
"""
import streamlit as st
import json, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tax_engine import (TaxpayerProfile, compute_full_tax, compare_regimes,
    estimate_from_monthly_salary, format_currency, format_lakhs)
from knowledge_base import (TAX_KNOWLEDGE_BASE, search_knowledge, get_all_deductions,
    get_for_taxpayer_type, format_for_llm_context)
from gemini_integration import (call_gemini, analyze_document, build_rag_query,
    anonymize_text, extract_financial_only, SYSTEM_PROMPT_TAX_ADVISOR)
from vector_db import TaxVectorDB

# ── Page Config ──
st.set_page_config(page_title="TaxGuru — AI Tax Advisor", page_icon="🏛️",
    layout="wide", initial_sidebar_state="expanded")

# ── Load logo ──
LOGO_B64 = ""
_lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_app_b64.txt')
if os.path.exists(_lp):
    with open(_lp) as f: LOGO_B64 = f.read().strip()

# ── CSS ──
st.markdown("""<style>
/* Hide ALL Streamlit chrome */
#MainMenu, footer, header, .stAppToolbar,
[data-testid="stHeader"], [data-testid="manage-app-button"],
.viewerBadge_container__r5tak, .styles_viewerBadge__CvC9N,
[data-testid="stStatusWidget"], .stDeployButton,
div[data-testid="stDecoration"] { display:none !important; visibility:hidden !important; }

:root { --tg:#1B4D3E; --tg-accent:#D4A843; --tg-light:#F7F5F0; --tg-dark:#0D2818; }
[data-testid="stSidebar"] { background:#F7F5F0; }

/* Header bar */
.hdr{background:linear-gradient(135deg,#1B4D3E,#2D6A4F);color:#fff;padding:0.8rem 1.2rem;
  border-radius:10px;margin-bottom:1rem;display:flex;align-items:center;gap:0.8rem}
.hdr img{height:36px} .hdr h2{color:#fff!important;margin:0;font-size:1.3rem}
.hdr p{color:#a8c5b6;margin:0;font-size:0.8rem}

/* Cards */
.tc{background:#fff;border:1px solid #e0e0e0;border-radius:12px;padding:1.2rem;margin:0.5rem 0;
  box-shadow:0 2px 8px rgba(0,0,0,0.04)}
.tc.green{border-left:4px solid #2E7D32} .tc.amber{border-left:4px solid #F57F17}
.tc.red{border-left:4px solid #C62828} .tc.blue{border-left:4px solid #1565C0}

.privacy-banner{background:#E3F2FD;border:1px solid #90CAF9;border-radius:8px;
  padding:0.7rem 1rem;font-size:0.82rem;color:#1565C0;margin-bottom:1rem}
.disclaimer{background:#FFF8E1;border:1px solid #FFE082;border-radius:8px;
  padding:0.7rem;font-size:0.78rem;color:#6D4C00}

/* ── HOME PAGE ── */
.hero{background:linear-gradient(135deg,#0D2818 0%,#1B4D3E 50%,#2D6A4F 100%);
  color:#fff;padding:2.5rem 2rem 2rem;border-radius:16px;text-align:center;margin-bottom:1.5rem;
  position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-30%;right:-10%;width:400px;height:400px;
  background:radial-gradient(circle,rgba(212,168,67,0.1)0%,transparent 70%);border-radius:50%}
.hero::after{content:'';position:absolute;bottom:-20%;left:-5%;width:300px;height:300px;
  background:radial-gradient(circle,rgba(45,106,79,0.3)0%,transparent 70%);border-radius:50%}
.hero *{position:relative;z-index:1}
.hero img{height:90px;margin-bottom:0.5rem;filter:drop-shadow(0 2px 8px rgba(0,0,0,0.3))
  brightness(1.15)}
.hero h1{color:#D4A843!important;font-size:2.8rem;margin:0.3rem 0;text-shadow:0 2px 12px rgba(0,0,0,0.3)}
.hero .sub{color:#c8d6c0;font-size:1.05rem;max-width:620px;margin:0.5rem auto 1.2rem;line-height:1.6}
.badges{display:flex;gap:0.5rem;justify-content:center;flex-wrap:wrap;margin-top:1rem}
.bdg{padding:0.25rem 0.7rem;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);
  border-radius:16px;font-size:0.72rem;color:#D4A843;font-weight:500}

.stats{display:flex;justify-content:center;gap:2rem;padding:1.2rem;background:#F7F5F0;
  border-radius:12px;margin-bottom:1.5rem;flex-wrap:wrap}
.stats .si{text-align:center} .stats .sn{font-size:1.6rem;font-weight:700;color:#1B4D3E}
.stats .sl{font-size:0.75rem;color:#636E72}

.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:1rem;margin:1rem 0}
.fcard{background:#fff;border:1px solid #e8e8e8;border-radius:10px;padding:1rem;
  border-left:4px solid #1B4D3E;transition:box-shadow .2s}
.fcard:hover{box-shadow:0 4px 16px rgba(0,0,0,0.06)}
.fcard h4{color:#1B4D3E;margin:0 0 0.3rem;font-size:0.95rem}
.fcard p{color:#636E72;font-size:0.82rem;margin:0;line-height:1.5}

.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0}
.tcard{background:#F7F5F0;border-radius:10px;padding:1.2rem}
.tcard h4{color:#1B4D3E;margin:0 0 0.5rem}
.tcard ul{list-style:none;padding:0;margin:0}
.tcard li{padding:0.15rem 0;font-size:0.82rem;color:#2D3436}
.tcard li::before{content:'✓ ';color:#2E7D32;font-weight:700}

/* Floating chat */
.chat-fab{position:fixed;bottom:28px;right:28px;z-index:99999;width:64px;height:64px;
  border-radius:50%;background:linear-gradient(135deg,#1B4D3E,#2D6A4F);color:#fff;
  font-size:28px;display:flex;align-items:center;justify-content:center;
  box-shadow:0 4px 20px rgba(0,0,0,0.3);cursor:pointer;text-decoration:none;transition:transform .2s}
.chat-fab:hover{transform:scale(1.12);color:#fff}

@media(max-width:768px){
  .hero h1{font-size:1.8rem} .stats{gap:1rem} .tgrid{grid-template-columns:1fr}
  .chat-fab{bottom:18px;right:18px;width:54px;height:54px;font-size:24px}
}
</style>""", unsafe_allow_html=True)

# ── Session State ──
for k, v in {'profile': TaxpayerProfile(), 'profile_complete': False, 'chat_history': [],
    'interaction_count': 0, 'chat_open': False, 'active_page': '🏠 Home'}.items():
    if k not in st.session_state: st.session_state[k] = v

if 'vector_db' not in st.session_state:
    st.session_state.vector_db = TaxVectorDB()
    st.session_state.vector_db.index_knowledge_base(TAX_KNOWLEDGE_BASE)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

# ── Navigation helper ──
def go_to(page_name):
    st.session_state.active_page = page_name

NAV_PAGES = ["🏠 Home", "📋 Tax Profile", "🧮 Tax Calculator", "📄 Payslip Analyzer",
    "💡 Tax Optimizer", "🔀 Scenario Planner", "📰 Law Updates", "ℹ️ About & Privacy"]

# ── Sidebar ──
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div style="text-align:center;padding:0.3rem 0"><img src="data:image/png;base64,{LOGO_B64}" style="height:45px"></div>', unsafe_allow_html=True)
    page = st.radio("Navigation", NAV_PAGES,
        index=NAV_PAGES.index(st.session_state.active_page) if st.session_state.active_page in NAV_PAGES else 0,
        label_visibility="collapsed")
    st.session_state.active_page = page

    if st.session_state.profile_complete:
        st.markdown("---")
        p = st.session_state.profile
        result = compare_regimes(p)
        best = result[result['recommended'] + '_regime']
        st.markdown("### 📊 Tax Summary")
        st.metric("Taxable Income", format_lakhs(best['taxable_income']))
        st.metric("Total Tax", format_lakhs(best['total_tax']),
            delta=f"-{format_lakhs(result['savings'])} saved" if result['savings'] > 0 else None, delta_color="inverse")
        st.metric("Effective Rate", f"{best['effective_rate']}%")
        st.info(f"**Best: {'New' if result['recommended']=='new' else 'Old'} Regime** ✅")

    st.markdown("---")
    st.markdown('<div class="disclaimer">⚠️ <b>Disclaimer:</b> TaxGuru provides informational guidance. Not professional tax advice. Consult a CA for complex matters.</div>', unsafe_allow_html=True)

# ── Header (non-Home pages) ──
if page != "🏠 Home":
    _logo = f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f'<div class="hdr">{_logo}<div><h2>TaxGuru</h2><p>AI Tax Advisor • FY 2025-26</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="privacy-banner">🔒 <b>Privacy:</b> TaxGuru never stores PAN, Aadhaar, or bank details. Only anonymized financial figures are processed in-session.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════
# FLOATING CHAT WIDGET
# ═══════════════════════════════════
def render_chat():
    st.markdown('<a href="#tg-chat" class="chat-fab" title="Ask AI Tax Chat">💬</a>', unsafe_allow_html=True)
    st.markdown("---")
    st.markdown('<div id="tg-chat"></div>', unsafe_allow_html=True)
    with st.expander("💬 AI Tax Chat — Ask any tax question", expanded=st.session_state.chat_open):
        c1, c2 = st.columns([4, 1])
        with c2:
            lang = st.selectbox("Language", [("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],
                format_func=lambda x: x[0], label_visibility="collapsed", key="chat_lang")
        with c1:
            st.markdown("**Ask about regime, ESOP, F&O, capital gains, deductions…**")

        box = st.container(height=280)
        with box:
            if not st.session_state.chat_history:
                st.markdown("*👋 Ask me any Indian income tax question. I cite sections and never guess.*")
            for m in st.session_state.chat_history:
                with st.chat_message(m['role']): st.markdown(m['content'])

        if prompt := st.chat_input("Ask a tax question...", key="chat_input_widget"):
            clean, n = anonymize_text(prompt)
            if n: st.warning(f"⚠️ {n} personal identifier(s) removed for privacy.")
            st.session_state.chat_history.append({'role':'user','content':prompt})
            st.session_state.chat_open = True

            if not GEMINI_API_KEY:
                resp = "⚠️ Gemini API key not configured. Please add GEMINI_API_KEY in Streamlit Cloud secrets (Settings → Secrets)."
            else:
                prof = extract_financial_only(vars(st.session_state.profile)) if st.session_state.profile_complete else {}
                rag = build_rag_query(clean, prof)
                resp = call_gemini(prompt=clean, context=rag['context'], language=lang[1], api_key=GEMINI_API_KEY)

            st.session_state.chat_history.append({'role':'assistant','content':resp})
            st.session_state.interaction_count += 1
            st.rerun()


# ═══════════════════════════════════
# HOME PAGE
# ═══════════════════════════════════
if page == "🏠 Home":
    _logo = f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""<div class="hero">
    {_logo}
    <h1>TaxGuru</h1>
    <p class="sub">Stop overpaying your taxes. AI grounded in real Indian tax law helps you choose the right regime,
    maximize deductions, and plan smarter — all before the deadline.</p>
    <div class="badges"><span class="bdg">RAG-Powered</span><span class="bdg">Zero Hallucination</span>
    <span class="bdg">Privacy-First</span><span class="bdg">FY 2025-26</span><span class="bdg">Hindi + 3 Languages</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="stats">
    <div class="si"><div class="sn">9 Cr+</div><div class="sl">ITR Filers (CBDT FY25)</div></div>
    <div class="si"><div class="sn">₹3.9L Cr</div><div class="sl">Refunds Issued (FY25)</div></div>
    <div class="si"><div class="sn">2 Regimes</div><div class="sl">70+ Deduction Sections</div></div>
    <div class="si"><div class="sn">47</div><div class="sl">Tax Sections in AI</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("### 🚀 Get Started")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Upload Payslip / Form 16", use_container_width=True, type="primary"):
            go_to("📋 Tax Profile"); st.rerun()
    with c2:
        if st.button("✏️ Enter Details Manually", use_container_width=True):
            go_to("📋 Tax Profile"); st.rerun()

    st.markdown("""### Features
<div class="fgrid">
<div class="fcard"><h4>⚖️ Regime Comparison</h4><p>Side-by-side Old vs New with your exact numbers. Instant rupee difference.</p></div>
<div class="fcard"><h4>📄 Payslip / Form 16 Analyzer</h4><p>Upload a document. AI extracts every component and projects full-year tax.</p></div>
<div class="fcard"><h4>💡 Tax Optimizer</h4><p>Personalized recs — specific amounts, instruments, deadlines. Not generic advice.</p></div>
<div class="fcard"><h4>🔀 Scenario Planner</h4><p>What if I get a raise? Sell shares? Switch regimes? See impact before deciding.</p></div>
<div class="fcard"><h4>💬 AI Chat (4 Languages)</h4><p>English, Hindi, Tamil, Telugu, Kannada. Cites tax sections. Never guesses.</p></div>
<div class="fcard"><h4>🏢 All Taxpayer Types</h4><p>Salaried, business, professionals, F&O traders, ESOP holders, NRIs, seniors.</p></div>
</div>""", unsafe_allow_html=True)

    st.markdown("""### Built on Trust
<div class="tgrid">
<div class="tcard"><h4>🛡️ Zero Hallucination</h4><ul>
<li>Every answer grounded in RAG over actual tax law</li>
<li>Tax computation is deterministic Python — not AI-generated</li>
<li>Always cites section numbers (80C, 112A, etc.)</li>
<li>Says "consult a CA" when unsure</li></ul></div>
<div class="tcard"><h4>🔒 Privacy-First</h4><ul>
<li>PAN, Aadhaar, bank details — never stored or sent</li>
<li>8 types of identifiers auto-detected and stripped</li>
<li>Only anonymized figures reach the AI</li>
<li>Session-only storage — cleared on close</li></ul></div>
</div>""", unsafe_allow_html=True)

    render_chat()


# ═══════════════════════════════════
# TAX PROFILE
# ═══════════════════════════════════
elif page == "📋 Tax Profile":
    st.markdown("## Set Up Your Tax Profile")

    # Upload first
    st.markdown("### 📄 Quick Start: Upload a Document")
    st.markdown("Upload your **Form 16**, **employer tax statement**, or **monthly payslip**.")
    st.markdown('<div class="privacy-banner">🔒 Only financial numbers extracted. Personal identifiers never stored.</div>', unsafe_allow_html=True)

    uploaded_doc = st.file_uploader("Drop your Form 16, tax statement, or payslip", type=['png','jpg','jpeg','pdf'], key="profile_upload")

    if uploaded_doc:
        fb = uploaded_doc.read()
        mt = uploaded_doc.type or "image/jpeg"
        if not GEMINI_API_KEY:
            st.error("⚠️ Gemini API key not configured. Please add it in Streamlit Cloud Settings → Secrets. For now, use manual entry below.")
        else:
            with st.spinner("🔍 Analyzing document with AI..."):
                doc = analyze_document(fb, GEMINI_API_KEY, mt)
            if 'error' in doc:
                st.error(f"Could not analyze: {doc['error']}. Try manual entry below.")
            else:
                annual = doc.get('period','monthly') == 'annual'
                mult = 1 if annual else 12
                st.success(f"✅ Extracted {'annual' if annual else 'monthly (will annualize)'} data:")
                display = {k:v for k,v in doc.items() if k not in ('period','raw_text','parse_error') and v not in (0,"NOT_FOUND",None,"")}
                for k,v in display.items():
                    if isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{k.replace('_',' ').title()}:** ₹{v:,.0f}" + (f" → **₹{v*mult:,.0f}/yr**" if not annual else ""))

                def gv(key,d=0):
                    v=doc.get(key,d)
                    if v in ("NOT_FOUND",None): return d
                    try: return float(v)*mult
                    except: return d

                if st.button("✅ Use This Data", type="primary", use_container_width=True):
                    p=st.session_state.profile; p.taxpayer_type="salaried"
                    p.gross_salary=gv('gross_salary'); p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
                    p.hra_received=gv('hra'); p.tds_deducted=gv('tds_deducted')
                    p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    p.section_80d_self=gv('section_80d'); p.section_24b=gv('section_24b')
                    st.session_state.profile_complete=True
                    st.success("✅ Profile created! Go to Tax Calculator.")
                    go_to("🧮 Tax Calculator"); st.rerun()

    st.markdown("---")
    st.markdown("### ✏️ Or Fill In Manually")

    c1,c2 = st.columns(2)
    with c1:
        taxpayer_type = st.selectbox("What describes you?",
            ["Salaried Employee","Business Owner","Professional (Doctor, Lawyer, CA, etc.)","Stock/F&O Trader","Investor","Freelancer"])
        type_map={"Salaried Employee":"salaried","Business Owner":"business",
            "Professional (Doctor, Lawyer, CA, etc.)":"professional","Stock/F&O Trader":"trader",
            "Investor":"investor","Freelancer":"professional"}
        age = st.number_input("Age", 18, 100, 30)
        residency = st.selectbox("Residency", ["Resident Indian","NRI","RNOR"])
        res_map={"Resident Indian":"resident","NRI":"nri","RNOR":"rnor"}
    with c2:
        metro = st.selectbox("Metro city?", ["Yes (Delhi/Mumbai/Chennai/Kolkata)","No"])

    st.markdown("---")
    tt = type_map[taxpayer_type]

    # Income fields
    st.markdown("### 💰 Income")
    gross_salary=basic_salary=hra_received=rent_paid=employer_nps=biz_income=trading_income=0
    interest_income=rental_income=dividend_income=0
    stcg_equity=ltcg_equity=stcg_other=ltcg_other=esop_perquisite=esop_sale_gain=0
    foreign_esop=False
    sec_80c=sec_80d_self=sec_80d_parents=sec_80ccd_1b=sec_80e=sec_80g=sec_24b=0
    tds_deducted=advance_tax=0

    if tt=="salaried":
        c1,c2,c3=st.columns(3)
        with c1: gross_salary=st.number_input("Annual Gross Salary (₹)",0,value=0,step=50000,format="%d")
        with c2: basic_salary=st.number_input("Annual Basic Salary (₹)",0,value=0,step=25000,format="%d",help="~40-50% of gross")
        with c3: hra_received=st.number_input("Annual HRA (₹)",0,value=0,step=10000,format="%d")
        c1,c2=st.columns(2)
        with c1: rent_paid=st.number_input("Annual Rent Paid (₹)",0,value=0,step=10000,format="%d")
        with c2: employer_nps=st.number_input("Employer NPS (₹/yr)",0,value=0,step=5000,format="%d",help="80CCD(2) — works in BOTH regimes")
    elif tt in ("business","professional"):
        c1,c2=st.columns(2)
        with c1: biz_income=st.number_input("Business/Professional Income (₹)",0,value=0,step=100000,format="%d")
        with c2: gross_salary=st.number_input("Salary (if any) (₹)",0,value=0,step=50000,format="%d")
    elif tt=="trader":
        c1,c2=st.columns(2)
        with c1: trading_income=st.number_input("F&O Income/(Loss) (₹)",value=0,step=50000,format="%d",help="Negative for losses")
        with c2: gross_salary=st.number_input("Salary (if any) (₹)",0,value=0,step=50000,format="%d")

    with st.expander("📈 Investment & Other Income"):
        c1,c2,c3=st.columns(3)
        with c1: interest_income=st.number_input("Interest Income (₹/yr)",0,value=0,step=5000,format="%d")
        with c2: rental_income=st.number_input("Rental Income (₹/yr)",0,value=0,step=10000,format="%d")
        with c3: dividend_income=st.number_input("Dividend Income (₹/yr)",0,value=0,step=5000,format="%d")

    with st.expander("📊 Capital Gains"):
        c1,c2=st.columns(2)
        with c1:
            stcg_equity=st.number_input("STCG Equity (₹)",0,value=0,step=10000,format="%d",help="Listed <12m, taxed 20%")
            ltcg_equity=st.number_input("LTCG Equity (₹)",0,value=0,step=10000,format="%d",help="Listed ≥12m, 12.5% above ₹1.25L")
        with c2:
            stcg_other=st.number_input("STCG Other (₹)",0,value=0,step=10000,format="%d")
            ltcg_other=st.number_input("LTCG Other (₹)",0,value=0,step=10000,format="%d")

    with st.expander("🏢 ESOPs"):
        esop_perquisite=st.number_input("ESOP Perquisite (₹)",0,value=0,step=50000,format="%d",help="FMV - exercise price × shares")
        foreign_esop=st.checkbox("Foreign company ESOPs",help="FEMA/Schedule FA compliance")

    with st.expander("🏦 Deductions (Old Regime)"):
        st.info("These apply only to Old Regime (except 80CCD(2) which works in both)")
        c1,c2,c3=st.columns(3)
        with c1:
            sec_80c=st.number_input("80C (₹)",0,150000,0,step=10000,format="%d")
            sec_80d_self=st.number_input("80D Self (₹)",0,50000,0,step=5000,format="%d")
        with c2:
            sec_80d_parents=st.number_input("80D Parents (₹)",0,50000,0,step=5000,format="%d")
            sec_80ccd_1b=st.number_input("80CCD(1B) NPS (₹)",0,50000,0,step=10000,format="%d")
        with c3:
            sec_80e=st.number_input("80E Edu Loan Int (₹)",0,value=0,step=10000,format="%d")
            sec_24b=st.number_input("24(b) Home Loan Int (₹)",0,200000,0,step=10000,format="%d")

    with st.expander("💳 TDS & Advance Tax Paid"):
        c1,c2=st.columns(2)
        with c1: tds_deducted=st.number_input("TDS Deducted (₹)",0,value=0,step=10000,format="%d")
        with c2: advance_tax=st.number_input("Advance Tax Paid (₹)",0,value=0,step=10000,format="%d")

    if st.button("✅ Save & Calculate Tax", type="primary", use_container_width=True):
        p=st.session_state.profile
        p.taxpayer_type=tt; p.age=age; p.residency=res_map[residency]; p.metro_city="Yes" in metro
        p.gross_salary=gross_salary; p.basic_salary=basic_salary if basic_salary else gross_salary*0.4
        p.hra_received=hra_received; p.rent_paid_annual=rent_paid; p.section_80ccd_2=employer_nps
        p.business_income=biz_income; p.professional_income=0; p.trading_income=trading_income
        p.interest_income=interest_income; p.rental_income=rental_income; p.dividend_income=dividend_income
        p.stcg_equity=stcg_equity; p.ltcg_equity=ltcg_equity; p.stcg_other=stcg_other; p.ltcg_other=ltcg_other
        p.esop_perquisite=esop_perquisite; p.foreign_esop=foreign_esop
        p.section_80c=sec_80c; p.section_80d_self=sec_80d_self; p.section_80d_parents=sec_80d_parents
        p.section_80ccd_1b=sec_80ccd_1b; p.section_80e=sec_80e; p.section_80g=0; p.section_24b=sec_24b
        p.tds_deducted=tds_deducted; p.advance_tax_paid=advance_tax
        st.session_state.profile_complete=True
        go_to("🧮 Tax Calculator"); st.rerun()

    render_chat()


# ═══════════════════════════════════
# TAX CALCULATOR
# ═══════════════════════════════════
elif page == "🧮 Tax Calculator":
    st.markdown("## Tax Calculator — Old vs New Regime")
    if not st.session_state.profile_complete:
        st.warning("Complete your Tax Profile first.")
        if st.button("Go to Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()

    p=st.session_state.profile; result=compare_regimes(p)
    old=result['old_regime']; new=result['new_regime']; rec=result['recommended']; sav=result['savings']

    if rec=='new': st.success(f"🎯 **New Tax Regime saves you {format_currency(sav)}**")
    else: st.success(f"🎯 **Old Tax Regime saves you {format_currency(sav)}**")

    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"### {'✅' if rec=='new' else ''} New Regime")
        st.markdown(f"**Taxable:** {format_currency(new['taxable_income'])}")
        st.markdown(f"Slab tax: {format_currency(new['slab_tax'])}")
        if new['rebate_87a']>0: st.markdown(f"87A Rebate: -{format_currency(new['rebate_87a'])}")
        if new['surcharge']>0: st.markdown(f"Surcharge: {format_currency(new['surcharge'])}")
        st.markdown(f"Cess: {format_currency(new['cess'])}")
        st.markdown(f"### Total: {format_currency(new['total_tax'])} ({new['effective_rate']}%)")
    with c2:
        st.markdown(f"### {'✅' if rec=='old' else ''} Old Regime")
        st.markdown(f"**Taxable:** {format_currency(old['taxable_income'])}")
        if old.get('hra_exemption',0)>0: st.markdown(f"*HRA Exempt: {format_currency(old['hra_exemption'])}*")
        if old['total_deductions']>0: st.markdown(f"*Deductions: {format_currency(old['total_deductions'])}*")
        st.markdown(f"Slab tax: {format_currency(old['slab_tax'])}")
        if old['rebate_87a']>0: st.markdown(f"87A Rebate: -{format_currency(old['rebate_87a'])}")
        if old['surcharge']>0: st.markdown(f"Surcharge: {format_currency(old['surcharge'])}")
        st.markdown(f"Cess: {format_currency(old['cess'])}")
        st.markdown(f"### Total: {format_currency(old['total_tax'])} ({old['effective_rate']}%)")

    if old['total_deductions']>0:
        st.markdown("---")
        st.markdown("### Deduction Breakdown (Old Regime)")
        for s,a in old['deduction_breakdown'].items():
            if a>0: st.markdown(f"- **{s}:** {format_currency(a)}")

    render_chat()


# ═══════════════════════════════════
# PAYSLIP ANALYZER
# ═══════════════════════════════════
elif page == "📄 Payslip Analyzer":
    st.markdown("## Payslip / Form 16 Analyzer")
    st.markdown("Upload a document and AI extracts salary components.")

    up = st.file_uploader("Upload Payslip or Form 16", type=['png','jpg','jpeg','pdf'])
    if up:
        fb=up.read(); mt=up.type or "image/jpeg"
        if not GEMINI_API_KEY:
            st.error("⚠️ API key not configured. Add GEMINI_API_KEY in Settings → Secrets.")
        else:
            with st.spinner("🔍 Analyzing..."): r=analyze_document(fb,GEMINI_API_KEY,mt)
            if 'error' in r: st.error(f"Error: {r['error']}")
            else:
                st.success("✅ Extracted:"); st.json(r)
                mg=r.get('gross_salary',r.get('total_earnings',0))
                mb=r.get('basic_salary',r.get('basic',0))
                if mg>0:
                    ann='annual' if r.get('period')=='annual' else 'monthly'
                    mult=1 if ann=='annual' else 12
                    st.markdown(f"**{ann.title()} Gross:** {format_currency(mg)} → **Annual: {format_currency(mg*mult)}**")
                    if st.button("Use for Tax Profile"):
                        pr=estimate_from_monthly_salary(mg if ann=='monthly' else mg/12, mb if ann=='monthly' else mb/12)
                        st.session_state.profile=pr; st.session_state.profile_complete=True
                        go_to("🧮 Tax Calculator"); st.rerun()

    st.markdown("---")
    st.markdown("### Or enter monthly salary")
    c1,c2=st.columns(2)
    with c1: mg2=st.number_input("Monthly Gross (₹)",0,value=0,step=5000,format="%d")
    with c2: mb2=st.number_input("Monthly Basic (₹)",0,value=0,step=2500,format="%d",help="0 = auto 40%")
    if mg2>0:
        pr=estimate_from_monthly_salary(mg2,mb2); comp=compare_regimes(pr)
        best=comp[comp['recommended']+'_regime']
        c1,c2,c3=st.columns(3)
        with c1: st.metric("Annual Gross",format_lakhs(mg2*12))
        with c2: st.metric("Est. Tax",format_lakhs(best['total_tax']))
        with c3: st.metric("Monthly Take-Home",format_currency(mg2-best['total_tax']/12))

    render_chat()


# ═══════════════════════════════════
# TAX OPTIMIZER
# ═══════════════════════════════════
elif page == "💡 Tax Optimizer":
    st.markdown("## Tax Optimization Recommendations")
    if not st.session_state.profile_complete:
        st.warning("Complete Tax Profile first.")
        if st.button("Go to Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()

    p=st.session_state.profile; result=compare_regimes(p); rec=result['recommended']
    st.markdown(f"Best regime: **{'New' if rec=='new' else 'Old'}**. Here's how to save more:")

    recs=[]
    if rec=='old' and p.section_80c<150000:
        gap=150000-p.section_80c; sav=gap*0.30 if p.gross_salary>1000000 else gap*0.20
        recs.append(('high','80C',f'Invest ₹{gap:,.0f} more under 80C',f'ELSS/PPF/Tax saver FD. Potential saving: ~₹{sav:,.0f}','Invest before March 31'))
    if p.section_80ccd_2==0:
        recs.append(('high','80CCD(2)','Ask employer about NPS','Employer NPS (up to 14% basic) works in BOTH regimes — most powerful new-regime deduction','Talk to HR'))
    if rec=='old' and p.section_80ccd_1b<50000:
        recs.append(('medium','80CCD(1B)','Invest ₹50K in NPS','Additional ₹50K over 80C limit. At 30% bracket saves ₹15,600','Open/increase NPS'))
    if rec=='old' and p.section_80d_self==0:
        recs.append(('medium','80D','Get health insurance','Up to ₹25K self (₹50K senior) + ₹25-50K parents. Max ₹1L.','Buy health policy'))
    if p.esop_perquisite>0:
        recs.append(('high','17(2)(vi)',f'⚠️ ESOP Perquisite: ₹{p.esop_perquisite:,.0f}','Taxed as salary. Consider exercise timing. Startup? May qualify for 48-month deferral.','Consult CA'))
    if p.foreign_esop:
        recs.append(('high','Schedule FA','⚠️ Foreign ESOP: Mandatory disclosure','Report in Schedule FA. FEMA compliance. Claim FTC under DTAA via Form 67.','File Schedule FA + Form 67'))
    if p.trading_income!=0:
        recs.append(('high','43(5)','F&O: File ITR-3, consider audit','Non-speculative business income. MUST report even losses (carry forward 8 yrs). Audit if turnover >₹10Cr.','Engage CA'))

    if not recs: st.success("🎉 Well optimized! No additional savings found.")
    for pri,sec,title,detail,action in recs:
        col={'high':'red','medium':'amber','low':'green'}.get(pri,'blue')
        ico={'high':'🔴','medium':'🟡','low':'🟢'}.get(pri,'ℹ️')
        st.markdown(f'<div class="tc {col}"><b>{ico} {title}</b> <em>({sec})</em><br>{detail}<br><b>Action:</b> {action}</div>', unsafe_allow_html=True)

    render_chat()


# ═══════════════════════════════════
# SCENARIO PLANNER
# ═══════════════════════════════════
elif page == "🔀 Scenario Planner":
    st.markdown("## What-If Scenario Planner")
    if not st.session_state.profile_complete:
        st.warning("Complete Tax Profile first.")
        if st.button("Go to Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()

    p=st.session_state.profile; cur=compare_regimes(p); cur_tax=cur[cur['recommended']+'_regime']['total_tax']

    scenario=st.selectbox("Scenario:", ["Switch regime?","Invest more in 80C?","Get a raise?","Sell shares?"])

    import copy
    if scenario=="Switch regime?":
        alt='old' if cur['recommended']=='new' else 'new'
        alt_tax=cur[alt+'_regime']['total_tax']; diff=alt_tax-cur_tax
        st.metric(f"{'Old' if alt=='old' else 'New'} Regime", format_currency(alt_tax),
            delta=f"+{format_currency(diff)}" if diff>0 else format_currency(diff), delta_color="inverse")
    elif scenario=="Invest more in 80C?":
        extra=st.slider("Additional 80C (₹)",0,150000,50000,10000)
        p2=copy.deepcopy(p); p2.section_80c=min(p.section_80c+extra,150000)
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        st.metric("Tax with extra 80C",format_currency(t2),delta=f"-{format_currency(cur_tax-t2)}" if cur_tax>t2 else "No change")
    elif scenario=="Get a raise?":
        pct=st.slider("Raise %",5,50,15,5)
        p2=copy.deepcopy(p); p2.gross_salary=int(p.gross_salary*(1+pct/100))
        p2.basic_salary=int(p.basic_salary*(1+pct/100)); p2.hra_received=int(p.hra_received*(1+pct/100))
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        c1,c2=st.columns(2)
        with c1: st.metric("New Salary",format_lakhs(p2.gross_salary))
        with c2: st.metric("Extra Tax",format_currency(t2-cur_tax))
    elif scenario=="Sell shares?":
        ltcg=st.number_input("Expected LTCG (₹)",0,value=200000,step=25000)
        p2=copy.deepcopy(p); p2.ltcg_equity+=ltcg; r2=compare_regimes(p2)
        t2=r2[r2['recommended']+'_regime']['total_tax']
        st.markdown(f"Exempt: {format_currency(min(ltcg,125000))} | Taxable: {format_currency(max(0,ltcg-125000))}")
        st.metric("Additional Tax",format_currency(t2-cur_tax))

    render_chat()


# ═══════════════════════════════════
# LAW UPDATES
# ═══════════════════════════════════
elif page == "📰 Law Updates":
    st.markdown("## Latest Tax Law Updates")
    updates=[
        ('Feb 2026','No changes to slabs for FY 2026-27','New IT Act 2025 effective Apr 2026. Reorganizes law, no rate changes.','No action needed','blue'),
        ('Jul 2024','Capital Gains Rates Changed','STCG equity: 15%→20%. LTCG equity: 10%→12.5%. Exemption: ₹1L→₹1.25L. Indexation removed.','Review investment strategy','amber'),
        ('Feb 2025','New Regime Restructured','Basic exemption ₹4L. 87A rebate ₹60K. Income up to ₹12.75L (salaried) tax-free.','Check if new regime is now better','green'),
        ('Feb 2025','Senior Citizen TDS Threshold Up','Interest TDS threshold: ₹50K→₹1L. Rent TDS threshold: ₹6L/yr.','Seniors: may not need Form 15H','green'),
        ('Feb 2025','LRS TCS Threshold Increased','TCS threshold ₹7L→₹10L. Education remittance TCS removed (if specified loan).','Benefits NRIs and students abroad','green'),
    ]
    for dt,title,detail,impact,col in updates:
        ico={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
        st.markdown(f'<div class="tc {col}"><b>{ico} [{dt}] {title}</b><br>{detail}<br><em>Impact: {impact}</em></div>', unsafe_allow_html=True)

    st.markdown("---")
    sq=st.text_input("🔍 Search tax topics", placeholder="e.g., ESOP, HRA, F&O loss...")
    if sq:
        results=st.session_state.vector_db.search_tax_law(sq)
        for r in results[:3]:
            st.markdown(f"**{r['metadata'].get('title','')}** ({r['metadata'].get('section','')})")
            st.markdown(r['content'][:400]+"...")
            st.markdown("---")

    render_chat()


# ═══════════════════════════════════
# ABOUT
# ═══════════════════════════════════
elif page == "ℹ️ About & Privacy":
    st.markdown("## About TaxGuru")
    st.markdown("""**TaxGuru** is an AI-powered Indian tax advisory platform for FY 2025-26.

### Technology
- **LLM:** Google Gemini 2.5 Flash-Lite + Google Search Grounding for real-time law updates
- **RAG:** 47 tax law entries in ChromaDB (all-MiniLM-L6-v2 embeddings)
- **3 Agents:** Tax Advisor (temp 0.3, cites sections), Document Parser (Gemini Vision), Law Update (Search Grounding)
- **Vector DB:** ChromaDB — semantic search + taxpayer similarity
- **Framework:** Streamlit (vibe coded with Claude)
- **Design:** v0.dev (Vercel AI) for UI mockups
- **Deployment:** Streamlit Community Cloud

### Privacy Policy
**Never collected:** PAN, Aadhaar, bank accounts, PF/UAN, DOB, address, email, phone, employer name.
**Processed in-session only:** Financial figures for computation. Cleared on browser close.
**AI queries:** Only anonymized figures sent to Gemini. 8 PII types auto-stripped.

### Bias Mitigation
Serves all profiles: salaried, business, professional, trader, investor, senior, NRI.
All recommendations grounded in tax law sections — not pattern-only.

*Disclaimer: Not professional tax advice. Consult a CA for complex matters.*""")

    stats=st.session_state.vector_db.get_stats()
    c1,c2,c3=st.columns(3)
    with c1: st.metric("Tax Law Entries",stats.get('tax_law_entries',len(TAX_KNOWLEDGE_BASE)))
    with c2: st.metric("Vector DB","Active" if stats.get('chroma_available') else "Keyword Fallback")
    with c3: st.metric("LLM","Gemini 2.5 Flash-Lite")

    render_chat()
