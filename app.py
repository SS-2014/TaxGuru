"""
TaxGuru — AI-Powered Indian Tax Advisory Platform v4
"""
import streamlit as st
import json, sys, os, copy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tax_engine import (TaxpayerProfile, compute_full_tax, compare_regimes,
    estimate_from_monthly_salary, format_currency, format_lakhs)
from knowledge_base import (TAX_KNOWLEDGE_BASE, search_knowledge, format_for_llm_context)
from gemini_integration import (call_gemini, analyze_document, build_rag_query,
    anonymize_text, extract_financial_only)
from vector_db import TaxVectorDB

st.set_page_config(page_title="TaxGuru — AI Tax Advisor", page_icon="🏛️",
    layout="wide", initial_sidebar_state="expanded")

# Load logo
LOGO_B64 = ""
_lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_app_b64.txt')
if os.path.exists(_lp):
    with open(_lp) as f: LOGO_B64 = f.read().strip()

# ── Nuclear CSS — hide EVERY piece of Streamlit branding ──
st.markdown("""<style>
/* === HIDE ALL STREAMLIT BRANDING === */
#MainMenu, footer, header,
.stAppToolbar,
[data-testid="stHeader"],
[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],
[data-testid="stDecoration"],
.stDeployButton,
.viewerBadge_container__r5tak,
.styles_viewerBadge__CvC9N,
div.viewerBadge_link__qRIco,
section[data-testid="stSidebar"] > div > div > div > div > div:last-child a[href*="streamlit"],
iframe[title="streamlit_badge"],
/* The "Made with Streamlit" and GitHub user attribution */
._profileContainer_gzau3_53,
.stMainBlockContainer + div,
div[class*="StatusWidget"],
button[kind="header"],
div[data-testid="stToolbar"]
{ display:none !important; visibility:hidden !important; height:0 !important;
  overflow:hidden !important; position:absolute !important; top:-9999px !important; }

/* Remove bottom padding where branding was */
.stApp > header { display:none !important; }
.stApp { margin-top: -2rem; }
[data-testid="stBottomBlockContainer"] { padding-bottom: 0.5rem !important; }

/* === THEME === */
:root { --tg:#1B4D3E; --acc:#D4A843; --lt:#F7F5F0; --dk:#0D2818; }
[data-testid="stSidebar"] { background:#F7F5F0; }
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p { font-size:0.9rem; }

/* Header bar */
.hdr{background:linear-gradient(135deg,#1B4D3E,#2D6A4F);color:#fff;
  padding:0.6rem 1rem;border-radius:8px;margin-bottom:0.8rem;
  display:flex;align-items:center;gap:0.7rem}
.hdr img{height:32px} .hdr h2{color:#fff!important;margin:0;font-size:1.2rem}
.hdr p{color:#a8c5b6;margin:0;font-size:0.75rem}

/* Cards */
.tc{background:#fff;border:1px solid #e0e0e0;border-radius:10px;padding:1rem;margin:0.4rem 0;
  box-shadow:0 1px 4px rgba(0,0,0,0.04)}
.tc.green{border-left:4px solid #2E7D32} .tc.amber{border-left:4px solid #F57F17}
.tc.red{border-left:4px solid #C62828} .tc.blue{border-left:4px solid #1565C0}
.privacy-banner{background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;
  padding:0.5rem 0.8rem;font-size:0.78rem;color:#1565C0;margin-bottom:0.8rem}
.disclaimer{background:#FFF8E1;border:1px solid #FFE082;border-radius:6px;
  padding:0.5rem;font-size:0.72rem;color:#6D4C00}

/* === HOME PAGE === */
.hero{background:linear-gradient(145deg,#0D2818 0%,#163D2E 40%,#1B4D3E 70%,#2D6A4F 100%);
  color:#fff;padding:1.8rem 1.5rem 1.5rem;border-radius:14px;text-align:center;margin-bottom:1rem;
  position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-20%;right:-8%;width:300px;height:300px;
  background:radial-gradient(circle,rgba(212,168,67,0.12)0%,transparent 60%);border-radius:50%}
.hero *{position:relative;z-index:1}
/* Logo: large with white glow so it pops on dark green */
.hero img{height:130px;margin-bottom:0.3rem;
  filter:drop-shadow(0 0 20px rgba(255,255,255,0.4)) drop-shadow(0 0 40px rgba(255,255,255,0.2))}
.hero h1{color:#D4A843!important;font-size:2.4rem;margin:0.2rem 0;
  text-shadow:0 2px 8px rgba(0,0,0,0.3)}
.hero .sub{color:#c8d6c0;font-size:0.95rem;max-width:560px;margin:0.3rem auto 0.8rem;line-height:1.5}
.badges{display:flex;gap:0.4rem;justify-content:center;flex-wrap:wrap;margin-top:0.6rem}
.bdg{padding:0.2rem 0.6rem;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);
  border-radius:14px;font-size:0.68rem;color:#D4A843;font-weight:500}

.stats{display:flex;justify-content:center;gap:2rem;padding:0.8rem;background:#F7F5F0;
  border-radius:10px;margin-bottom:1rem;flex-wrap:wrap}
.si{text-align:center} .sn{font-size:1.4rem;font-weight:700;color:#1B4D3E}
.sl{font-size:0.7rem;color:#636E72}

.fgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:0.8rem;margin:0.8rem 0}
.fcard{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:0.8rem;
  border-left:3px solid #1B4D3E}
.fcard h4{color:#1B4D3E;margin:0 0 0.2rem;font-size:0.85rem}
.fcard p{color:#636E72;font-size:0.75rem;margin:0;line-height:1.4}

.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:0.8rem;margin:0.6rem 0}
.tcard{background:#F7F5F0;border-radius:8px;padding:1rem}
.tcard h4{color:#1B4D3E;margin:0 0 0.4rem;font-size:0.9rem}
.tcard ul{list-style:none;padding:0;margin:0}
.tcard li{padding:0.1rem 0;font-size:0.78rem;color:#2D3436}
.tcard li::before{content:'✓ ';color:#2E7D32;font-weight:700}

@media(max-width:900px){.fgrid{grid-template-columns:1fr 1fr} .tgrid{grid-template-columns:1fr}}
@media(max-width:600px){.fgrid{grid-template-columns:1fr}}
</style>""", unsafe_allow_html=True)

# ── Session State ──
for k, v in {'profile': TaxpayerProfile(), 'profile_complete': False, 'chat_history': [],
    'interaction_count': 0, 'show_chat': False, 'active_page': '🏠 Home'}.items():
    if k not in st.session_state: st.session_state[k] = v
if 'vector_db' not in st.session_state:
    st.session_state.vector_db = TaxVectorDB()
    st.session_state.vector_db.index_knowledge_base(TAX_KNOWLEDGE_BASE)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

def go_to(p): st.session_state.active_page = p

NAV = ["🏠 Home","📋 Tax Profile","🧮 Tax Calculator","📄 Payslip Analyzer",
    "💡 Tax Optimizer","🔀 Scenario Planner","📰 Law Updates","ℹ️ About & Privacy"]

# ═══════════════════════════════════
# SIDEBAR: Nav + Tax Summary + Chat
# ═══════════════════════════════════
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div style="text-align:center;padding:0.2rem 0"><img src="data:image/png;base64,{LOGO_B64}" style="height:40px"></div>', unsafe_allow_html=True)

    page = st.radio("", NAV,
        index=NAV.index(st.session_state.active_page) if st.session_state.active_page in NAV else 0,
        label_visibility="collapsed")
    st.session_state.active_page = page

    # Tax summary
    if st.session_state.profile_complete:
        st.markdown("---")
        p = st.session_state.profile; r = compare_regimes(p); b = r[r['recommended']+'_regime']
        st.markdown("**📊 Tax Summary**")
        st.metric("Tax", format_lakhs(b['total_tax']),
            delta=f"-{format_lakhs(r['savings'])}" if r['savings']>0 else None, delta_color="inverse")
        st.caption(f"Taxable: {format_lakhs(b['taxable_income'])} | Rate: {b['effective_rate']}% | {'New' if r['recommended']=='new' else 'Old'} ✅")

    st.markdown("---")

    # ── CHAT IN SIDEBAR ──
    st.markdown("**💬 AI Tax Chat**")
    lang = st.selectbox("Language", [("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],
        format_func=lambda x: x[0], label_visibility="collapsed", key="sb_lang")

    chat_box = st.container(height=250)
    with chat_box:
        if not st.session_state.chat_history:
            st.caption("Ask any Indian tax question. I cite sections and never guess.")
        for m in st.session_state.chat_history:
            with st.chat_message(m['role']): st.markdown(m['content'])

    if prompt := st.chat_input("Tax question...", key="sb_chat"):
        clean, n = anonymize_text(prompt)
        if n: st.toast(f"⚠️ {n} identifier(s) removed for privacy")
        st.session_state.chat_history.append({'role':'user','content':prompt})

        if not GEMINI_API_KEY:
            resp = "⚠️ API key not set. Add GEMINI_API_KEY in app Settings → Secrets."
        else:
            prof = extract_financial_only(vars(st.session_state.profile)) if st.session_state.profile_complete else {}
            rag = build_rag_query(clean, prof)
            resp = call_gemini(prompt=clean, context=rag['context'], language=lang[1], api_key=GEMINI_API_KEY)

        st.session_state.chat_history.append({'role':'assistant','content':resp})
        st.rerun()

    st.markdown('<div class="disclaimer">⚠️ Not professional tax advice. Consult a CA for complex matters.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════
# HEADER (non-Home pages)
# ═══════════════════════════════════
if page != "🏠 Home":
    _l = f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f'<div class="hdr">{_l}<div><h2>TaxGuru</h2><p>AI Tax Advisor • FY 2025-26</p></div></div>', unsafe_allow_html=True)
    st.markdown('<div class="privacy-banner">🔒 TaxGuru never stores PAN, Aadhaar, or bank details. Only anonymized figures processed in-session.</div>', unsafe_allow_html=True)


# ═══════════════════════════════════
# HOME
# ═══════════════════════════════════
if page == "🏠 Home":
    _l = f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""<div class="hero">{_l}
    <h1>TaxGuru</h1>
    <p class="sub">Stop overpaying your taxes. AI grounded in real Indian tax law — choose the right regime,
    maximize deductions, plan smarter.</p>
    <div class="badges"><span class="bdg">RAG-Powered</span><span class="bdg">Zero Hallucination</span>
    <span class="bdg">Privacy-First</span><span class="bdg">FY 2025-26</span><span class="bdg">Hindi + 3 Languages</span></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="stats">
    <div class="si"><div class="sn">9 Cr+</div><div class="sl">ITR Filers (CBDT FY25)</div></div>
    <div class="si"><div class="sn">₹3.9L Cr</div><div class="sl">Refunds Issued</div></div>
    <div class="si"><div class="sn">2 Regimes</div><div class="sl">70+ Sections</div></div>
    <div class="si"><div class="sn">47</div><div class="sl">Tax Sections in AI</div></div>
    </div>""", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Upload Payslip / Form 16", use_container_width=True, type="primary"):
            go_to("📋 Tax Profile"); st.rerun()
    with c2:
        if st.button("✏️ Enter Details Manually", use_container_width=True):
            go_to("📋 Tax Profile"); st.rerun()

    st.markdown("""<div class="fgrid">
    <div class="fcard"><h4>⚖️ Regime Comparison</h4><p>Side-by-side Old vs New. Exact rupee difference.</p></div>
    <div class="fcard"><h4>📄 Form 16 Analyzer</h4><p>Upload → AI extracts → full-year projection.</p></div>
    <div class="fcard"><h4>💡 Tax Optimizer</h4><p>Specific amounts, instruments, deadlines.</p></div>
    <div class="fcard"><h4>🔀 Scenario Planner</h4><p>Raise? Sale? Regime switch? See impact.</p></div>
    <div class="fcard"><h4>💬 AI Chat</h4><p>English + Hindi + Tamil + Telugu + Kannada.</p></div>
    <div class="fcard"><h4>🏢 All Taxpayers</h4><p>Salaried, business, traders, ESOP, NRI, seniors.</p></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="tgrid">
    <div class="tcard"><h4>🛡️ Zero Hallucination</h4><ul>
    <li>RAG over actual Income Tax Act sections</li>
    <li>Deterministic Python tax engine — not AI-generated numbers</li>
    <li>Cites section numbers (80C, 112A, 43(5)...)</li>
    <li>Says "consult a CA" when unsure</li></ul></div>
    <div class="tcard"><h4>🔒 Privacy-First</h4><ul>
    <li>PAN, Aadhaar, bank details — never stored</li>
    <li>8 identifier types auto-stripped before AI sees anything</li>
    <li>Session-only — cleared on browser close</li>
    <li>No data shared with third parties</li></ul></div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════
# TAX PROFILE
# ═══════════════════════════════════
elif page == "📋 Tax Profile":
    st.markdown("## Set Up Your Tax Profile")

    st.markdown("#### 📄 Quick Start: Upload a Document")
    up = st.file_uploader("Form 16, tax statement, or payslip", type=['png','jpg','jpeg','pdf'], key="pf_up")
    if up:
        fb=up.read(); mt=up.type or "image/jpeg"
        if not GEMINI_API_KEY:
            st.error("⚠️ API key not set. Add GEMINI_API_KEY in Settings → Secrets. Use manual entry below.")
        else:
            with st.spinner("🔍 Analyzing..."):
                doc = analyze_document(fb, GEMINI_API_KEY, mt)
            if 'error' in doc:
                st.error(f"Error: {doc['error']}. Use manual entry.")
            else:
                ann = doc.get('period','monthly')=='annual'; mult=1 if ann else 12
                st.success(f"✅ {'Annual' if ann else 'Monthly'} data extracted:")
                for k,v in doc.items():
                    if k not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{k.replace('_',' ').title()}:** ₹{v:,.0f}" + (f" → ₹{v*mult:,.0f}/yr" if not ann else ""))
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
                    st.session_state.profile_complete=True; go_to("🧮 Tax Calculator"); st.rerun()

    st.markdown("---")
    st.markdown("#### ✏️ Or Fill In Manually")
    c1,c2=st.columns(2)
    with c1:
        taxpayer_type=st.selectbox("Type",["Salaried","Business Owner","Professional","F&O Trader","Investor","Freelancer"])
        tmap={"Salaried":"salaried","Business Owner":"business","Professional":"professional",
            "F&O Trader":"trader","Investor":"investor","Freelancer":"professional"}
        age=st.number_input("Age",18,100,30)
        residency=st.selectbox("Residency",["Resident","NRI","RNOR"])
        rmap={"Resident":"resident","NRI":"nri","RNOR":"rnor"}
    with c2:
        metro=st.selectbox("Metro?",["Yes (Del/Mum/Che/Kol)","No"])

    tt=tmap[taxpayer_type]
    gross_salary=basic_salary=hra_received=rent_paid=employer_nps=biz_income=trading_income=0
    interest_income=rental_income=dividend_income=stcg_equity=ltcg_equity=stcg_other=ltcg_other=0
    esop_perquisite=0; foreign_esop=False
    sec_80c=sec_80d_self=sec_80d_parents=sec_80ccd_1b=sec_80e=sec_24b=tds_deducted=advance_tax=0

    st.markdown("##### Income")
    if tt=="salaried":
        c1,c2,c3=st.columns(3)
        with c1: gross_salary=st.number_input("Gross Salary (₹/yr)",0,value=0,step=50000,format="%d")
        with c2: basic_salary=st.number_input("Basic (₹/yr)",0,value=0,step=25000,format="%d")
        with c3: hra_received=st.number_input("HRA (₹/yr)",0,value=0,step=10000,format="%d")
        c1,c2=st.columns(2)
        with c1: rent_paid=st.number_input("Rent Paid (₹/yr)",0,value=0,step=10000,format="%d")
        with c2: employer_nps=st.number_input("Employer NPS (₹/yr)",0,value=0,step=5000,format="%d",help="80CCD(2) — BOTH regimes")
    elif tt in ("business","professional"):
        c1,c2=st.columns(2)
        with c1: biz_income=st.number_input("Business Income (₹)",0,value=0,step=100000,format="%d")
        with c2: gross_salary=st.number_input("Salary if any (₹)",0,value=0,step=50000,format="%d")
    elif tt=="trader":
        c1,c2=st.columns(2)
        with c1: trading_income=st.number_input("F&O Income/(Loss) (₹)",value=0,step=50000,format="%d")
        with c2: gross_salary=st.number_input("Salary if any (₹)",0,value=0,step=50000,format="%d")

    with st.expander("📈 Other Income / Capital Gains / ESOPs"):
        c1,c2,c3=st.columns(3)
        with c1: interest_income=st.number_input("Interest (₹/yr)",0,value=0,step=5000,format="%d")
        with c2: rental_income=st.number_input("Rental (₹/yr)",0,value=0,step=10000,format="%d")
        with c3: dividend_income=st.number_input("Dividend (₹/yr)",0,value=0,step=5000,format="%d")
        c1,c2=st.columns(2)
        with c1: stcg_equity=st.number_input("STCG Equity (₹)",0,value=0,step=10000,format="%d")
        with c2: ltcg_equity=st.number_input("LTCG Equity (₹)",0,value=0,step=10000,format="%d")
        esop_perquisite=st.number_input("ESOP Perquisite (₹)",0,value=0,step=50000,format="%d")
        foreign_esop=st.checkbox("Foreign ESOPs")

    with st.expander("🏦 Deductions (Old Regime)"):
        c1,c2,c3=st.columns(3)
        with c1: sec_80c=st.number_input("80C (₹)",0,150000,0,step=10000,format="%d")
        with c2: sec_80d_self=st.number_input("80D Self (₹)",0,50000,0,step=5000,format="%d")
        with c3: sec_80ccd_1b=st.number_input("80CCD(1B) NPS (₹)",0,50000,0,step=10000,format="%d")
        c1,c2=st.columns(2)
        with c1: sec_80e=st.number_input("80E Edu Loan (₹)",0,value=0,step=10000,format="%d")
        with c2: sec_24b=st.number_input("24(b) Home Loan (₹)",0,200000,0,step=10000,format="%d")

    with st.expander("💳 TDS & Advance Tax"):
        c1,c2=st.columns(2)
        with c1: tds_deducted=st.number_input("TDS (₹)",0,value=0,step=10000,format="%d")
        with c2: advance_tax=st.number_input("Advance Tax (₹)",0,value=0,step=10000,format="%d")

    if st.button("✅ Save & Calculate", type="primary", use_container_width=True):
        p=st.session_state.profile; p.taxpayer_type=tt; p.age=age; p.residency=rmap[residency]
        p.metro_city="Yes" in metro
        p.gross_salary=gross_salary; p.basic_salary=basic_salary if basic_salary else gross_salary*0.4
        p.hra_received=hra_received; p.rent_paid_annual=rent_paid; p.section_80ccd_2=employer_nps
        p.business_income=biz_income; p.trading_income=trading_income
        p.interest_income=interest_income; p.rental_income=rental_income; p.dividend_income=dividend_income
        p.stcg_equity=stcg_equity; p.ltcg_equity=ltcg_equity; p.stcg_other=stcg_other; p.ltcg_other=ltcg_other
        p.esop_perquisite=esop_perquisite; p.foreign_esop=foreign_esop
        p.section_80c=sec_80c; p.section_80d_self=sec_80d_self; p.section_80d_parents=0
        p.section_80ccd_1b=sec_80ccd_1b; p.section_80e=sec_80e; p.section_24b=sec_24b
        p.tds_deducted=tds_deducted; p.advance_tax_paid=advance_tax
        st.session_state.profile_complete=True; go_to("🧮 Tax Calculator"); st.rerun()


# ═══════════════════════════════════
# TAX CALCULATOR
# ═══════════════════════════════════
elif page == "🧮 Tax Calculator":
    st.markdown("## Old vs New Regime")
    if not st.session_state.profile_complete:
        st.warning("Complete Tax Profile first.")
        if st.button("→ Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()
    p=st.session_state.profile; r=compare_regimes(p)
    old=r['old_regime']; new=r['new_regime']; rec=r['recommended']; sav=r['savings']
    st.success(f"🎯 **{'New' if rec=='new' else 'Old'} Regime saves you {format_currency(sav)}**")

    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"### {'✅' if rec=='new' else ''} New Regime")
        st.markdown(f"Taxable: **{format_currency(new['taxable_income'])}**")
        st.markdown(f"Slab: {format_currency(new['slab_tax'])}")
        if new['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(new['rebate_87a'])}")
        st.markdown(f"Cess: {format_currency(new['cess'])}")
        st.markdown(f"**Total: {format_currency(new['total_tax'])} ({new['effective_rate']}%)**")
    with c2:
        st.markdown(f"### {'✅' if rec=='old' else ''} Old Regime")
        st.markdown(f"Taxable: **{format_currency(old['taxable_income'])}**")
        if old.get('hra_exemption',0)>0: st.caption(f"HRA exempt: {format_currency(old['hra_exemption'])}")
        if old['total_deductions']>0: st.caption(f"Deductions: {format_currency(old['total_deductions'])}")
        st.markdown(f"Slab: {format_currency(old['slab_tax'])}")
        if old['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(old['rebate_87a'])}")
        st.markdown(f"Cess: {format_currency(old['cess'])}")
        st.markdown(f"**Total: {format_currency(old['total_tax'])} ({old['effective_rate']}%)**")

    if old['total_deductions']>0:
        with st.expander("Deduction Breakdown"):
            for s,a in old['deduction_breakdown'].items():
                if a>0: st.markdown(f"- **{s}:** {format_currency(a)}")


# ═══════════════════════════════════
# PAYSLIP ANALYZER
# ═══════════════════════════════════
elif page == "📄 Payslip Analyzer":
    st.markdown("## Payslip / Form 16 Analyzer")
    up=st.file_uploader("Upload document",type=['png','jpg','jpeg','pdf'])
    if up and GEMINI_API_KEY:
        with st.spinner("🔍 Analyzing..."): doc=analyze_document(up.read(),GEMINI_API_KEY,up.type or "image/jpeg")
        if 'error' in doc: st.error(doc['error'])
        else: st.success("✅ Extracted:"); st.json(doc)
    elif up: st.error("API key not set.")

    st.markdown("---")
    st.markdown("#### Monthly salary → annual tax")
    c1,c2=st.columns(2)
    with c1: mg=st.number_input("Monthly Gross (₹)",0,value=0,step=5000,format="%d")
    with c2: mb=st.number_input("Monthly Basic (₹)",0,value=0,step=2500,format="%d")
    if mg>0:
        pr=estimate_from_monthly_salary(mg,mb); comp=compare_regimes(pr); b=comp[comp['recommended']+'_regime']
        c1,c2,c3=st.columns(3)
        with c1: st.metric("Annual",format_lakhs(mg*12))
        with c2: st.metric("Tax",format_lakhs(b['total_tax']))
        with c3: st.metric("Take-Home/mo",format_currency(mg-b['total_tax']/12))


# ═══════════════════════════════════
# TAX OPTIMIZER
# ═══════════════════════════════════
elif page == "💡 Tax Optimizer":
    st.markdown("## Tax Optimizer")
    if not st.session_state.profile_complete:
        st.warning("Complete Tax Profile first.")
        if st.button("→ Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()
    p=st.session_state.profile; r=compare_regimes(p); rec=r['recommended']
    recs=[]
    if rec=='old' and p.section_80c<150000:
        g=150000-p.section_80c; s=g*0.30 if p.gross_salary>1000000 else g*0.20
        recs.append(('high','80C',f'Invest ₹{g:,.0f} more',f'ELSS/PPF/FD. Save ~₹{s:,.0f}','Before Mar 31'))
    if p.section_80ccd_2==0:
        recs.append(('high','80CCD(2)','Employer NPS','Works in BOTH regimes — up to 14% of basic','Ask HR'))
    if p.esop_perquisite>0:
        recs.append(('high','17(2)(vi)',f'ESOP: ₹{p.esop_perquisite:,.0f}','Taxed as salary. Time exercise carefully.','Consult CA'))
    if p.foreign_esop:
        recs.append(('high','Schedule FA','Foreign ESOP disclosure','Mandatory. FEMA compliance. File Form 67 for FTC.','Disclose in ITR'))
    if p.trading_income!=0:
        recs.append(('high','43(5)','F&O: File ITR-3','Non-speculative business income. Report even losses.','Engage CA'))
    if rec=='old' and p.section_80d_self==0:
        recs.append(('medium','80D','Health insurance','Up to ₹25K self + ₹50K parents','Buy policy'))
    if not recs: st.success("🎉 Well optimized!")
    for pri,sec,t,d,a in recs:
        col={'high':'red','medium':'amber'}.get(pri,'green')
        ico={'high':'🔴','medium':'🟡'}.get(pri,'🟢')
        st.markdown(f'<div class="tc {col}"><b>{ico} {t}</b> <em>({sec})</em><br>{d}<br><b>→ {a}</b></div>',unsafe_allow_html=True)


# ═══════════════════════════════════
# SCENARIO PLANNER
# ═══════════════════════════════════
elif page == "🔀 Scenario Planner":
    st.markdown("## Scenario Planner")
    if not st.session_state.profile_complete:
        st.warning("Complete Tax Profile first.")
        if st.button("→ Tax Profile"): go_to("📋 Tax Profile"); st.rerun()
        st.stop()
    p=st.session_state.profile; cur=compare_regimes(p); ct=cur[cur['recommended']+'_regime']['total_tax']
    sc=st.selectbox("Scenario:",["Switch regime?","More 80C?","Raise?","Sell shares?"])
    if sc=="Switch regime?":
        alt='old' if cur['recommended']=='new' else 'new'
        at=cur[alt+'_regime']['total_tax']; d=at-ct
        st.metric(f"{'Old' if alt=='old' else 'New'} Regime",format_currency(at),
            delta=f"+{format_currency(d)}" if d>0 else format_currency(d),delta_color="inverse")
    elif sc=="More 80C?":
        ex=st.slider("Extra 80C (₹)",0,150000,50000,10000)
        p2=copy.deepcopy(p); p2.section_80c=min(p.section_80c+ex,150000)
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        st.metric("Tax",format_currency(t2),delta=f"-{format_currency(ct-t2)}" if ct>t2 else "Same")
    elif sc=="Raise?":
        pct=st.slider("Raise %",5,50,15,5)
        p2=copy.deepcopy(p); p2.gross_salary=int(p.gross_salary*(1+pct/100))
        p2.basic_salary=int(p.basic_salary*(1+pct/100))
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        st.metric("New Salary",format_lakhs(p2.gross_salary))
        st.metric("Extra Tax",format_currency(t2-ct))
    elif sc=="Sell shares?":
        lg=st.number_input("LTCG (₹)",0,value=200000,step=25000)
        p2=copy.deepcopy(p); p2.ltcg_equity+=lg; r2=compare_regimes(p2)
        st.metric("Tax on sale",format_currency(r2[r2['recommended']+'_regime']['total_tax']-ct))


# ═══════════════════════════════════
# LAW UPDATES
# ═══════════════════════════════════
elif page == "📰 Law Updates":
    st.markdown("## Law Updates")
    for dt,t,d,imp,col in [
        ('Feb 2026','No slab changes FY26-27','New IT Act 2025 effective Apr 2026. No rate changes.','No action','blue'),
        ('Jul 2024','Capital Gains rates changed','STCG 15→20%. LTCG 10→12.5%. Indexation removed.','Review strategy','amber'),
        ('Feb 2025','New regime restructured','Exemption ₹4L. Rebate ₹60K. Up to ₹12.75L tax-free.','Check regime','green'),
    ]:
        ico={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
        st.markdown(f'<div class="tc {col}"><b>{ico} [{dt}] {t}</b><br>{d}<br><em>{imp}</em></div>',unsafe_allow_html=True)

    sq=st.text_input("🔍 Search tax topics")
    if sq:
        for r in st.session_state.vector_db.search_tax_law(sq)[:3]:
            st.markdown(f"**{r['metadata'].get('title','')}** ({r['metadata'].get('section','')})")
            st.markdown(r['content'][:300]+"..."); st.markdown("---")


# ═══════════════════════════════════
# ABOUT
# ═══════════════════════════════════
elif page == "ℹ️ About & Privacy":
    st.markdown("## About TaxGuru")
    st.markdown("""**TaxGuru** — AI tax advisory for FY 2025-26.

**Tech:** Gemini 2.5 Flash-Lite + Google Search Grounding • 47-entry ChromaDB RAG (all-MiniLM-L6-v2) • 3 AI Agents (Tax Advisor, Document Parser, Law Update) • Streamlit + v0.dev design • Vibe coded with Claude

**Privacy:** PAN/Aadhaar/bank never stored. 8 PII types auto-stripped. Session-only. No third-party sharing.

**Bias:** Serves all profiles — salaried, business, professional, trader, investor, senior, NRI. Recommendations grounded in tax law sections.

*Not professional tax advice. Consult a CA.*""")
    stats=st.session_state.vector_db.get_stats()
    c1,c2,c3=st.columns(3)
    with c1: st.metric("KB Entries",stats.get('tax_law_entries',len(TAX_KNOWLEDGE_BASE)))
    with c2: st.metric("Vector DB","Active" if stats.get('chroma_available') else "Fallback")
    with c3: st.metric("LLM","Gemini Flash-Lite")
