"""
TaxGuru v5 — Full rebuild
Nav: horizontal top bar (not sidebar)
Chat: sidebar = dedicated agent panel (Karthik/Kavya)
Multi-profile: up to 5 family members
User-facing copy: no jargon
"""
import streamlit as st
import json, sys, os, copy, random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tax_engine import (TaxpayerProfile, compute_full_tax, compare_regimes,
    estimate_from_monthly_salary, format_currency, format_lakhs)
from knowledge_base import (TAX_KNOWLEDGE_BASE, search_knowledge, format_for_llm_context)
from gemini_integration import (call_gemini, analyze_document, build_rag_query,
    anonymize_text, extract_financial_only)
from vector_db import TaxVectorDB

st.set_page_config(page_title="TaxGuru", page_icon="🏛️", layout="wide",
    initial_sidebar_state="expanded")

LOGO_B64 = ""
_lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_app_b64.txt')
if os.path.exists(_lp):
    with open(_lp) as f: LOGO_B64 = f.read().strip()

# ── CSS ──
st.markdown("""<style>
/* NUKE all Streamlit branding */
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
._profileContainer_gzau3_53,div[class*="StatusWidget"],button[kind="header"],
div[data-testid="stToolbar"],iframe[title*="streamlit"]
{display:none!important;visibility:hidden!important;height:0!important;overflow:hidden!important}
.stApp>header{display:none!important}
[data-testid="stBottomBlockContainer"]{padding-bottom:0!important}

/* Sidebar = Chat Agent */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#0D2818 0%,#1B4D3E 100%);min-width:320px}
[data-testid="stSidebar"] *{color:#e0e0e0!important}
[data-testid="stSidebar"] .stMarkdown p{color:#c8d6c0!important;font-size:0.85rem}
[data-testid="stSidebar"] .stChatMessage{background:rgba(255,255,255,0.06)!important;border-radius:8px}
[data-testid="stSidebar"] [data-testid="stChatMessageContent"] p{color:#f0f0f0!important}
[data-testid="stSidebar"] .stSelectbox label,.stTextInput label{color:#a0b8a8!important}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3{color:#D4A843!important}

/* Nav bar */
.nav-bar{display:flex;gap:0.3rem;padding:0.4rem 0;margin-bottom:0.8rem;flex-wrap:wrap;
  border-bottom:2px solid #e8e8e8}
.nav-btn{padding:0.4rem 0.9rem;border-radius:6px 6px 0 0;font-size:0.82rem;font-weight:600;
  cursor:pointer;border:1px solid #e0e0e0;border-bottom:none;background:#fff;color:#1B4D3E;
  text-decoration:none;transition:all 0.15s}
.nav-btn:hover{background:#F7F5F0}
.nav-btn.active{background:#1B4D3E;color:#fff;border-color:#1B4D3E}

/* Hero */
.hero{background:linear-gradient(145deg,#0D2818,#1B4D3E 50%,#2D6A4F);color:#fff;
  padding:1.5rem 1.5rem 1.2rem;border-radius:14px;text-align:center;margin-bottom:1rem;
  position:relative;overflow:hidden}
.hero::before{content:'';position:absolute;top:-20%;right:-8%;width:280px;height:280px;
  background:radial-gradient(circle,rgba(212,168,67,0.12),transparent 60%);border-radius:50%}
.hero *{position:relative;z-index:1}
.hero img{height:80px;margin-bottom:0.2rem;
  filter:drop-shadow(0 0 25px rgba(255,255,255,0.5)) drop-shadow(0 0 50px rgba(255,255,255,0.25)) brightness(1.2)}
.hero h1{color:#D4A843!important;font-size:2rem;margin:0.1rem 0}
.hero .sub{color:#c8d6c0;font-size:0.9rem;max-width:520px;margin:0.2rem auto 0.6rem;line-height:1.5}
.badges{display:flex;gap:0.35rem;justify-content:center;flex-wrap:wrap;margin:0.4rem 0}
.bdg{padding:0.15rem 0.5rem;background:rgba(255,255,255,0.1);border:1px solid rgba(255,255,255,0.2);
  border-radius:12px;font-size:0.65rem;color:#D4A843}
.stats{display:flex;justify-content:center;gap:1.8rem;padding:0.6rem 0;margin-top:0.4rem;flex-wrap:wrap}
.si{text-align:center} .sn{font-size:1.2rem;font-weight:700;color:#D4A843}
.sl{font-size:0.62rem;color:#a0b8a8}

/* Cards */
.tc{background:#fff;border:1px solid #e0e0e0;border-radius:8px;padding:0.9rem;margin:0.3rem 0;
  box-shadow:0 1px 3px rgba(0,0,0,0.04)}
.tc.green{border-left:3px solid #2E7D32} .tc.amber{border-left:3px solid #F57F17}
.tc.red{border-left:3px solid #C62828} .tc.blue{border-left:3px solid #1565C0}

.fgrid{display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;margin:0.6rem 0}
.fcard{background:#fff;border:1px solid #e8e8e8;border-radius:8px;padding:0.7rem;
  border-left:3px solid #1B4D3E}
.fcard h4{color:#1B4D3E;margin:0 0 0.15rem;font-size:0.82rem}
.fcard p{color:#636E72;font-size:0.72rem;margin:0;line-height:1.4}

.tgrid{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0}
.tcard{background:#F7F5F0;border-radius:8px;padding:0.8rem}
.tcard h4{color:#1B4D3E;margin:0 0 0.3rem;font-size:0.85rem}
.tcard ul{list-style:none;padding:0;margin:0}
.tcard li{padding:0.1rem 0;font-size:0.75rem;color:#2D3436}
.tcard li::before{content:'✓ ';color:#2E7D32;font-weight:700}

.privacy-banner{background:#E3F2FD;border:1px solid #90CAF9;border-radius:6px;
  padding:0.4rem 0.7rem;font-size:0.75rem;color:#1565C0;margin-bottom:0.6rem}

@media(max-width:900px){.fgrid{grid-template-columns:1fr 1fr} .tgrid{grid-template-columns:1fr}}
@media(max-width:600px){.fgrid{grid-template-columns:1fr} .nav-bar{gap:0.2rem} .nav-btn{font-size:0.7rem;padding:0.3rem 0.5rem}}
</style>""", unsafe_allow_html=True)

# ── Session State ──
defaults = {'profiles': {}, 'active_profile': 'Me', 'chat_history': [],
    'interaction_count': 0, 'page': 'Home', 'agent_name': random.choice(['Karthik','Kavya'])}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v
if 'Me' not in st.session_state.profiles:
    st.session_state.profiles['Me'] = {'profile': TaxpayerProfile(), 'complete': False}
if 'vector_db' not in st.session_state:
    st.session_state.vector_db = TaxVectorDB()
    st.session_state.vector_db.index_knowledge_base(TAX_KNOWLEDGE_BASE)

GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.environ.get("GEMINI_API_KEY", ""))

def cur_profile():
    name = st.session_state.active_profile
    if name not in st.session_state.profiles:
        st.session_state.profiles[name] = {'profile': TaxpayerProfile(), 'complete': False}
    return st.session_state.profiles[name]

AGENT = st.session_state.agent_name

# ═══════════════════════════════════
# SIDEBAR = CHAT AGENT
# ═══════════════════════════════════
with st.sidebar:
    if LOGO_B64:
        st.markdown(f'<div style="text-align:center;padding:0.3rem 0 0.1rem"><img src="data:image/png;base64,{LOGO_B64}" style="height:35px;filter:brightness(1.3) drop-shadow(0 0 8px rgba(255,255,255,0.3))"></div>', unsafe_allow_html=True)

    st.markdown(f"### 💬 {AGENT} — Your Tax Agent")

    lang = st.selectbox("Language", [("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],
        format_func=lambda x: x[0], label_visibility="collapsed", key="chat_lang")

    chat_box = st.container(height=350)
    with chat_box:
        if not st.session_state.chat_history:
            st.markdown(f"👋 Hi, I'm **{AGENT}**! Ask me anything about Indian income tax — which regime to pick, how ESOPs are taxed, F&O rules, deductions, capital gains — I'll cite the exact section and never make things up.")
        for m in st.session_state.chat_history:
            with st.chat_message(m['role'], avatar="🧑‍💼" if m['role']=='assistant' else None):
                st.markdown(m['content'])

    if prompt := st.chat_input(f"Ask {AGENT} anything...", key="agent_input"):
        clean, n = anonymize_text(prompt)
        if n: st.toast(f"🔒 {n} personal detail(s) removed for your privacy")
        st.session_state.chat_history.append({'role':'user','content':prompt})
        if not GEMINI_API_KEY:
            resp = f"⚠️ I'm not connected yet. The admin needs to add the API key in Settings → Secrets."
        else:
            cp = cur_profile()
            prof = extract_financial_only(vars(cp['profile'])) if cp['complete'] else {}
            rag = build_rag_query(clean, prof)
            resp = call_gemini(prompt=clean, context=rag['context'], language=lang[1], api_key=GEMINI_API_KEY)
        st.session_state.chat_history.append({'role':'assistant','content':resp})
        st.rerun()

    st.markdown("---")
    st.caption(f"💡 *{AGENT} is an AI assistant grounded in the Income Tax Act. Always verify important decisions with a Chartered Accountant.*")


# ═══════════════════════════════════
# MAIN AREA: NAV + CONTENT
# ═══════════════════════════════════

# Profile selector + nav
top_c1, top_c2 = st.columns([3, 1])
with top_c2:
    # Multi-profile selector
    profile_names = list(st.session_state.profiles.keys())
    if len(profile_names) < 5:
        profile_names.append("+ Add family member")
    sel = st.selectbox("Profile", profile_names, index=profile_names.index(st.session_state.active_profile)
        if st.session_state.active_profile in profile_names else 0, label_visibility="collapsed")
    if sel == "+ Add family member":
        new_name = st.text_input("Name for this profile", key="new_prof_name")
        if new_name and st.button("Add"):
            st.session_state.profiles[new_name] = {'profile': TaxpayerProfile(), 'complete': False}
            st.session_state.active_profile = new_name; st.rerun()
    else:
        st.session_state.active_profile = sel

# Nav tabs
pages = ["Home","Tax Profile","Calculator","Payslip Analyzer","Optimizer","Scenarios","Law Updates","About"]
with top_c1:
    cols = st.columns(len(pages))
    for i, p in enumerate(pages):
        with cols[i]:
            if st.button(p, key=f"nav_{p}", use_container_width=True,
                type="primary" if st.session_state.page == p else "secondary"):
                st.session_state.page = p; st.rerun()

page = st.session_state.page
cp = cur_profile()

# ═══════════════════════════════════
# HOME
# ═══════════════════════════════════
if page == "Home":
    _l = f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""<div class="hero">{_l}
    <h1>TaxGuru</h1>
    <p class="sub">Stop overpaying. AI that knows Indian tax law helps you pick the right regime,
    find every deduction, and plan ahead.</p>
    <div class="badges"><span class="bdg">Always Accurate</span><span class="bdg">Your Data Stays Private</span>
    <span class="bdg">FY 2025-26 Updated</span><span class="bdg">Works in Hindi</span></div>
    <div class="stats">
    <div class="si"><div class="sn">9 Cr+</div><div class="sl">ITR Filers in India</div></div>
    <div class="si"><div class="sn">₹3.9L Cr</div><div class="sl">Tax Refunds in FY25</div></div>
    <div class="si"><div class="sn">2 Regimes</div><div class="sl">70+ Sections</div></div>
    <div class="si"><div class="sn">47</div><div class="sl">Tax Rules in our AI</div></div>
    </div></div>""", unsafe_allow_html=True)

    st.markdown("#### Set up your tax profile (one-time, takes 2 minutes)")
    st.caption("Upload a document or enter your details. You only need to do this once — then all tools work automatically.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("📄 Upload Payslip / Form 16", use_container_width=True, type="primary"):
            st.session_state.page = "Tax Profile"; st.rerun()
    with c2:
        if st.button("✏️ Enter Details Manually", use_container_width=True):
            st.session_state.page = "Tax Profile"; st.rerun()

    st.markdown("""<div class="fgrid">
    <div class="fcard"><h4>⚖️ Regime Comparison</h4><p>See exactly how much you save under Old vs New — in rupees, not percentages.</p></div>
    <div class="fcard"><h4>📄 Document Upload</h4><p>Drop your payslip or Form 16. We read it and fill in everything for you.</p></div>
    <div class="fcard"><h4>💡 Savings Finder</h4><p>Specific recommendations: what to invest, how much, by when.</p></div>
    <div class="fcard"><h4>🔀 What-If Scenarios</h4><p>Getting a raise? Selling shares? See the tax impact before you act.</p></div>
    <div class="fcard"><h4>💬 Tax Agent</h4><p>Ask """ + AGENT + """ anything in English, Hindi, Tamil, Telugu, or Kannada.</p></div>
    <div class="fcard"><h4>👨‍👩‍👧‍👦 Family Profiles</h4><p>Create up to 5 profiles for spouse, parents — compare and plan together.</p></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="tgrid">
    <div class="tcard"><h4>🛡️ Always Accurate</h4><ul>
    <li>Your tax numbers are calculated by a precise engine — not guessed by AI</li>
    <li>Every answer cites the actual section of the Income Tax Act</li>
    <li>When unsure, we tell you to check with a CA — we never make things up</li>
    <li>Updated with Budget 2025 and Budget 2026 changes</li></ul></div>
    <div class="tcard"><h4>🔒 Your Data Stays Private</h4><ul>
    <li>We never see your PAN, Aadhaar, address, date of birth, phone, or email</li>
    <li>Bank account numbers and PF/UAN details are never stored</li>
    <li>Your employer name and employee ID are stripped automatically</li>
    <li>Everything clears when you close the browser — nothing is saved</li></ul></div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════
# TAX PROFILE
# ═══════════════════════════════════
elif page == "Tax Profile":
    pname = st.session_state.active_profile
    st.markdown(f"## Tax Profile: {pname}")

    st.markdown("#### 📄 Upload a document")
    st.caption("Drop your Form 16, employer tax statement, or any monthly payslip. We'll read it and fill everything in.")
    up = st.file_uploader("Form 16, tax statement, or payslip", type=['png','jpg','jpeg','pdf'], key="pf_up", label_visibility="collapsed")
    if up:
        if not GEMINI_API_KEY:
            st.error("⚠️ AI not connected. Use manual entry below or ask the admin to add the API key.")
        else:
            with st.spinner(f"🔍 {AGENT} is reading your document..."):
                doc = analyze_document(up.read(), GEMINI_API_KEY, up.type or "image/jpeg")
            if 'error' in doc: st.error(f"Couldn't read it: {doc['error']}. Try manual entry.")
            else:
                ann=doc.get('period','monthly')=='annual'; mult=1 if ann else 12
                st.success(f"✅ Got it! {'Annual' if ann else 'Monthly'} data found:")
                for k,v in doc.items():
                    if k not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{k.replace('_',' ').title()}:** ₹{v:,.0f}" + (f" → ₹{v*mult:,.0f}/yr" if not ann else ""))
                def gv(key,d=0):
                    v=doc.get(key,d)
                    if v in ("NOT_FOUND",None): return d
                    try: return float(v)*mult
                    except: return d
                if st.button("✅ Looks right — use this", type="primary", use_container_width=True):
                    p=cp['profile']; p.taxpayer_type="salaried"
                    p.gross_salary=gv('gross_salary'); p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
                    p.hra_received=gv('hra'); p.tds_deducted=gv('tds_deducted')
                    p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    cp['complete']=True; st.session_state.page="Calculator"; st.rerun()

    st.markdown("---")
    st.markdown("#### ✏️ Or fill in manually")

    c1,c2=st.columns(2)
    with c1:
        tt_label=st.selectbox("I am a...",["Salaried Employee","Business Owner","Professional (Doctor/Lawyer/CA)","F&O Trader","Investor","Freelancer"])
        tmap={"Salaried Employee":"salaried","Business Owner":"business","Professional (Doctor/Lawyer/CA)":"professional",
            "F&O Trader":"trader","Investor":"investor","Freelancer":"professional"}
        age=st.number_input("Age",18,100,30)
        res=st.selectbox("Residency",["Resident","NRI","RNOR"])
        rmap={"Resident":"resident","NRI":"nri","RNOR":"rnor"}
    with c2:
        metro=st.selectbox("Metro city?",["Yes (Delhi/Mumbai/Chennai/Kolkata)","No"])
    tt=tmap[tt_label]

    gross_salary=basic_salary=hra_received=rent_paid=employer_nps=biz_income=trading_income=0
    interest_income=rental_income=dividend_income=stcg_equity=ltcg_equity=0
    esop_perquisite=0; foreign_esop=False
    sec_80c=sec_80d_self=sec_80ccd_1b=sec_80e=sec_24b=tds_deducted=advance_tax=0

    if tt=="salaried":
        c1,c2,c3=st.columns(3)
        with c1: gross_salary=st.number_input("Gross Salary (₹/yr)",0,value=0,step=50000,format="%d")
        with c2: basic_salary=st.number_input("Basic (₹/yr)",0,value=0,step=25000,format="%d",help="~40% of gross if unsure")
        with c3: hra_received=st.number_input("HRA (₹/yr)",0,value=0,step=10000,format="%d")
        c1,c2=st.columns(2)
        with c1: rent_paid=st.number_input("Rent you pay (₹/yr)",0,value=0,step=10000,format="%d")
        with c2: employer_nps=st.number_input("Employer NPS (₹/yr)",0,value=0,step=5000,format="%d",help="Tax-free in both regimes!")
    elif tt in ("business","professional"):
        c1,c2=st.columns(2)
        with c1: biz_income=st.number_input("Business/Professional Income (₹/yr)",0,value=0,step=100000,format="%d")
        with c2: gross_salary=st.number_input("Salary if any (₹/yr)",0,value=0,step=50000,format="%d")
    elif tt=="trader":
        c1,c2=st.columns(2)
        with c1: trading_income=st.number_input("F&O Profit or (Loss) (₹)",value=0,step=50000,format="%d")
        with c2: gross_salary=st.number_input("Salary if any (₹/yr)",0,value=0,step=50000,format="%d")

    with st.expander("📈 Other income, capital gains, ESOPs"):
        c1,c2,c3=st.columns(3)
        with c1: interest_income=st.number_input("FD/Savings interest (₹/yr)",0,value=0,step=5000,format="%d")
        with c2: rental_income=st.number_input("Rental income (₹/yr)",0,value=0,step=10000,format="%d")
        with c3: dividend_income=st.number_input("Dividends (₹/yr)",0,value=0,step=5000,format="%d")
        c1,c2=st.columns(2)
        with c1: stcg_equity=st.number_input("Short-term gains on shares (₹)",0,value=0,step=10000,format="%d")
        with c2: ltcg_equity=st.number_input("Long-term gains on shares (₹)",0,value=0,step=10000,format="%d")
        esop_perquisite=st.number_input("ESOP perquisite value (₹)",0,value=0,step=50000,format="%d")
        foreign_esop=st.checkbox("These are from a foreign company")

    with st.expander("🏦 Investments & deductions (for Old Regime comparison)"):
        c1,c2,c3=st.columns(3)
        with c1: sec_80c=st.number_input("80C — EPF+PPF+ELSS+LIC (₹)",0,150000,0,step=10000,format="%d")
        with c2: sec_80d_self=st.number_input("80D — Health insurance (₹)",0,50000,0,step=5000,format="%d")
        with c3: sec_80ccd_1b=st.number_input("80CCD(1B) — Extra NPS (₹)",0,50000,0,step=10000,format="%d")
        c1,c2=st.columns(2)
        with c1: sec_80e=st.number_input("80E — Education loan interest (₹)",0,value=0,step=10000,format="%d")
        with c2: sec_24b=st.number_input("Home loan interest (₹)",0,200000,0,step=10000,format="%d")

    with st.expander("💳 Tax already paid"):
        c1,c2=st.columns(2)
        with c1: tds_deducted=st.number_input("TDS deducted by employer (₹)",0,value=0,step=10000,format="%d")
        with c2: advance_tax=st.number_input("Advance tax paid (₹)",0,value=0,step=10000,format="%d")

    if st.button("✅ Save & Show My Tax", type="primary", use_container_width=True):
        p=cp['profile']; p.taxpayer_type=tt; p.age=age; p.residency=rmap[res]; p.metro_city="Yes" in metro
        p.gross_salary=gross_salary; p.basic_salary=basic_salary if basic_salary else gross_salary*0.4
        p.hra_received=hra_received; p.rent_paid_annual=rent_paid; p.section_80ccd_2=employer_nps
        p.business_income=biz_income; p.trading_income=trading_income
        p.interest_income=interest_income; p.rental_income=rental_income; p.dividend_income=dividend_income
        p.stcg_equity=stcg_equity; p.ltcg_equity=ltcg_equity
        p.esop_perquisite=esop_perquisite; p.foreign_esop=foreign_esop
        p.section_80c=sec_80c; p.section_80d_self=sec_80d_self; p.section_80d_parents=0
        p.section_80ccd_1b=sec_80ccd_1b; p.section_80e=sec_80e; p.section_24b=sec_24b
        p.tds_deducted=tds_deducted; p.advance_tax_paid=advance_tax
        cp['complete']=True; st.session_state.page="Calculator"; st.rerun()


# ═══════════════════════════════════
# CALCULATOR
# ═══════════════════════════════════
elif page == "Calculator":
    st.markdown(f"## {st.session_state.active_profile}'s Tax Comparison")
    if not cp['complete']:
        st.warning("Set up your tax profile first — takes 2 minutes.")
        if st.button("→ Set Up Profile"): st.session_state.page="Tax Profile"; st.rerun()
        st.stop()
    p=cp['profile']; r=compare_regimes(p)
    old=r['old_regime']; new=r['new_regime']; rec=r['recommended']; sav=r['savings']
    st.success(f"🎯 **{'New' if rec=='new' else 'Old'} Regime saves you {format_currency(sav)} this year**")

    c1,c2=st.columns(2)
    with c1:
        st.markdown(f"### {'✅' if rec=='new' else ''} New Regime")
        st.markdown(f"**Taxable:** {format_currency(new['taxable_income'])}")
        st.markdown(f"Tax: {format_currency(new['slab_tax'])}")
        if new['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(new['rebate_87a'])}")
        st.markdown(f"Cess: {format_currency(new['cess'])}")
        st.markdown(f"### {format_currency(new['total_tax'])} ({new['effective_rate']}%)")
    with c2:
        st.markdown(f"### {'✅' if rec=='old' else ''} Old Regime")
        st.markdown(f"**Taxable:** {format_currency(old['taxable_income'])}")
        if old.get('hra_exemption',0)>0: st.caption(f"HRA exempt: {format_currency(old['hra_exemption'])}")
        if old['total_deductions']>0: st.caption(f"Deductions: {format_currency(old['total_deductions'])}")
        st.markdown(f"Tax: {format_currency(old['slab_tax'])}")
        if old['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(old['rebate_87a'])}")
        st.markdown(f"Cess: {format_currency(old['cess'])}")
        st.markdown(f"### {format_currency(old['total_tax'])} ({old['effective_rate']}%)")

    if old['total_deductions']>0:
        with st.expander("View deduction breakdown"):
            for s,a in old['deduction_breakdown'].items():
                if a>0: st.markdown(f"- **{s}:** {format_currency(a)}")

    # Net payable
    best = r[rec+'_regime']
    net = best['net_payable']
    if net > 0:
        st.info(f"💰 **Net tax to pay:** {format_currency(net)} (after TDS/advance tax already paid)")
    elif net < 0:
        st.info(f"🎉 **Refund expected:** {format_currency(abs(net))}")


# ═══════════════════════════════════
# PAYSLIP ANALYZER
# ═══════════════════════════════════
elif page == "Payslip Analyzer":
    st.markdown("## Read Your Payslip")
    st.caption("Upload and we extract the numbers. Or enter your monthly salary to see estimated annual tax.")
    up=st.file_uploader("Upload",type=['png','jpg','jpeg','pdf'],label_visibility="collapsed")
    if up and GEMINI_API_KEY:
        with st.spinner(f"🔍 {AGENT} is reading..."): doc=analyze_document(up.read(),GEMINI_API_KEY,up.type or "image/jpeg")
        if 'error' in doc: st.error(doc['error'])
        else: st.success("✅"); st.json(doc)
    elif up: st.error("AI not connected. Add API key in Settings → Secrets.")

    st.markdown("---")
    st.markdown("#### Quick estimate from monthly salary")
    c1,c2=st.columns(2)
    with c1: mg=st.number_input("Monthly gross (₹)",0,value=0,step=5000,format="%d")
    with c2: mb=st.number_input("Monthly basic (₹)",0,value=0,step=2500,format="%d",help="Leave 0 = auto 40%")
    if mg>0:
        pr=estimate_from_monthly_salary(mg,mb); comp=compare_regimes(pr); b=comp[comp['recommended']+'_regime']
        c1,c2,c3=st.columns(3)
        with c1: st.metric("Annual",format_lakhs(mg*12))
        with c2: st.metric("Tax",format_lakhs(b['total_tax']))
        with c3: st.metric("Take-home/mo",format_currency(mg-b['total_tax']/12))


# ═══════════════════════════════════
# OPTIMIZER
# ═══════════════════════════════════
elif page == "Optimizer":
    st.markdown("## Tax Savings Finder")
    if not cp['complete']:
        st.warning("Set up your tax profile first."); 
        if st.button("→ Set Up"): st.session_state.page="Tax Profile"; st.rerun()
        st.stop()
    p=cp['profile']; r=compare_regimes(p); rec=r['recommended']
    recs=[]
    if rec=='old' and p.section_80c<150000:
        g=150000-p.section_80c; s=g*0.30 if p.gross_salary>1000000 else g*0.20
        recs.append(('red','80C',f'You can save ~₹{s:,.0f} more',f'Invest ₹{g:,.0f} in ELSS/PPF/tax-saver FD before March 31.'))
    if p.section_80ccd_2==0:
        recs.append(('red','80CCD(2)','Ask your employer about NPS','This deduction works in BOTH regimes — it\'s the single best tax-saving move under new regime.'))
    if p.esop_perquisite>0:
        recs.append(('amber','ESOP',f'Your ESOP perquisite (₹{p.esop_perquisite:,.0f}) is taxed as salary','Consider timing of exercise. Startup employees may get a 4-year deferral.'))
    if p.foreign_esop:
        recs.append(('red','Foreign ESOP','You must disclose these in your ITR','Foreign shares must be reported in Schedule FA. Non-disclosure penalty: ₹10 lakh.'))
    if p.trading_income!=0:
        recs.append(('amber','F&O Trading','File ITR-3 — even if you had losses','F&O losses can be carried forward for 8 years, but only if you file on time.'))
    if rec=='old' and p.section_80d_self==0:
        recs.append(('green','80D','Get health insurance','Up to ₹25,000 deduction (₹50,000 if senior citizen). Parents add more.'))
    if not recs: st.success("🎉 Looks good! We couldn't find more savings based on your current profile.")
    for col,sec,t,d in recs:
        st.markdown(f'<div class="tc {col}"><b>{t}</b> <em>(Section {sec})</em><br>{d}</div>',unsafe_allow_html=True)


# ═══════════════════════════════════
# SCENARIOS
# ═══════════════════════════════════
elif page == "Scenarios":
    st.markdown("## What-If Scenarios")
    if not cp['complete']:
        st.warning("Set up your tax profile first.")
        if st.button("→ Set Up"): st.session_state.page="Tax Profile"; st.rerun()
        st.stop()
    p=cp['profile']; cur=compare_regimes(p); ct=cur[cur['recommended']+'_regime']['total_tax']
    sc=st.selectbox("What if...",["I switch tax regime?","I invest more in 80C?","I get a raise?","I sell shares?"])
    if sc=="I switch tax regime?":
        alt='old' if cur['recommended']=='new' else 'new'; at=cur[alt+'_regime']['total_tax']; d=at-ct
        st.metric(f"Tax under {'Old' if alt=='old' else 'New'} Regime",format_currency(at),
            delta=f"{'+'if d>0 else ''}{format_currency(d)}",delta_color="inverse")
        if d>0: st.warning(f"Switching would cost you ₹{d:,.0f} more.")
        else: st.success(f"You'd save ₹{abs(d):,.0f}!")
    elif sc=="I invest more in 80C?":
        ex=st.slider("Additional investment (₹)",0,150000,50000,10000)
        p2=copy.deepcopy(p); p2.section_80c=min(p.section_80c+ex,150000)
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        saved=ct-t2
        st.metric("Tax saving",format_currency(saved) if saved>0 else "No change")
    elif sc=="I get a raise?":
        pct=st.slider("Raise %",5,50,15,5)
        p2=copy.deepcopy(p); p2.gross_salary=int(p.gross_salary*(1+pct/100)); p2.basic_salary=int(p.basic_salary*(1+pct/100))
        r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
        c1,c2=st.columns(2)
        with c1: st.metric("New salary",format_lakhs(p2.gross_salary))
        with c2: st.metric("Extra tax",format_currency(t2-ct))
    elif sc=="I sell shares?":
        lg=st.number_input("Expected profit (₹)",0,value=200000,step=25000)
        p2=copy.deepcopy(p); p2.ltcg_equity+=lg; r2=compare_regimes(p2)
        t2=r2[r2['recommended']+'_regime']['total_tax']
        st.caption(f"First ₹1.25L is exempt. Taxable: ₹{max(0,lg-125000):,.0f}")
        st.metric("Tax on this sale",format_currency(t2-ct))


# ═══════════════════════════════════
# LAW UPDATES
# ═══════════════════════════════════
elif page == "Law Updates":
    st.markdown("## What's Changed in Tax Law")
    for dt,t,d,col in [
        ('Feb 2026','No changes for FY 2026-27','Tax slabs stay the same. New IT Act 2025 takes effect April 2026 — same rules, cleaner language.','blue'),
        ('Jul 2024','Share tax rates increased','Short-term: 15→20%. Long-term: 10→12.5%. But exemption up: ₹1L→₹1.25L. Indexation removed.','amber'),
        ('Feb 2025','Income up to ₹12.75L now tax-free','New regime: exemption ₹4L, rebate ₹60K. Salaried employees up to ₹12.75L pay zero.','green'),
    ]:
        ico={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
        st.markdown(f'<div class="tc {col}"><b>{ico} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)

    st.markdown("---")
    sq=st.text_input("🔍 Search any tax topic",placeholder="e.g. ESOP tax, HRA rules, F&O loss...")
    if sq:
        for r in st.session_state.vector_db.search_tax_law(sq)[:3]:
            st.markdown(f"**{r['metadata'].get('title','')}** ({r['metadata'].get('section','')})")
            st.markdown(r['content'][:300]+"..."); st.markdown("---")


# ═══════════════════════════════════
# ABOUT
# ═══════════════════════════════════
elif page == "About":
    st.markdown("## About TaxGuru")
    st.markdown(f"""**TaxGuru** helps Indian taxpayers plan and optimize their income tax. Built for FY 2025-26.

**How it works:** Your tax numbers are computed by a precise calculation engine (not generated by AI).
{AGENT}, your tax agent, answers questions using verified sections of the Income Tax Act — 47 provisions
covering salary, business income, capital gains, ESOPs, F&O trading, property, NRI rules, and more.

**Your privacy:** We never see or store your PAN, Aadhaar, address, date of birth, phone number,
email, bank account numbers, PF/UAN numbers, or employer name. These are automatically detected and
removed before anything reaches the AI. Everything clears when you close your browser.

**Built with:** Gemini AI + Google Search (for live law updates) • ChromaDB vector database • Streamlit •
UI designed in v0.dev • Vibe coded with Claude

*Always verify important tax decisions with a Chartered Accountant.*""")
    stats=st.session_state.vector_db.get_stats()
    c1,c2=st.columns(2)
    with c1: st.metric("Tax rules in AI",stats.get('tax_law_entries',len(TAX_KNOWLEDGE_BASE)))
    with c2: st.metric("AI Model","Gemini 2.5 Flash")
