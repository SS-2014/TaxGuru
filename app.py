"""TaxGuru v6 — White/navy theme, compact hero, large fonts, clickable features"""
import streamlit as st
import sys, os, copy, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from tax_engine import (TaxpayerProfile, compare_regimes, estimate_from_monthly_salary, format_currency, format_lakhs)
from knowledge_base import TAX_KNOWLEDGE_BASE, format_for_llm_context
from gemini_integration import (call_gemini, analyze_document, build_rag_query, anonymize_text, extract_financial_only)
from vector_db import TaxVectorDB

st.set_page_config(page_title="TaxGuru", page_icon="🏛️", layout="wide", initial_sidebar_state="collapsed")
LOGO_B64 = ""
_lp = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logo_app_b64.txt')
if os.path.exists(_lp):
    with open(_lp) as f: LOGO_B64 = f.read().strip()
if 'agent_name' not in st.session_state:
    st.session_state.agent_name = random.choice(["Karthik","Kavya"])
A = st.session_state.agent_name

st.markdown("""<style>
/* NUKE streamlit branding */
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],
button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],
div[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
footer:after{content:'';visibility:hidden;display:block;}
.stApp>header{display:none!important;}
.stApp{margin-top:-0.5rem;background:#FAFAFA;}

/* Base */
html,body,[data-testid="stAppViewContainer"]{font-size:16px;color:#1E293B;font-family:'Segoe UI',system-ui,sans-serif;}
h1,h2,h3,h4{color:#0F172A;}

/* Nav pills */
div[data-testid="stHorizontalBlock"]:first-child .stRadio>div{gap:0.3rem;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{
  background:#F1F5F9;border:1px solid #CBD5E1;border-radius:8px;padding:0.4rem 0.9rem;
  font-size:0.95rem;font-weight:500;color:#334155;cursor:pointer;transition:all 0.15s;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label[data-checked="true"],
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){
  background:#0F172A!important;color:#fff!important;border-color:#0F172A!important;}

/* Hero */
.hero-row{display:flex;gap:2rem;align-items:center;padding:1.5rem 0;border-bottom:1px solid #E2E8F0;margin-bottom:1.5rem;}
.hero-left{flex:1;}
.hero-left img{height:56px;margin-bottom:0.6rem;}
.hero-left h1{font-size:1.8rem;color:#0F172A;margin:0 0 0.4rem;}
.hero-left p{color:#64748B;font-size:1rem;line-height:1.5;margin:0 0 0.6rem;}
.hero-left .tags{display:flex;gap:0.3rem;flex-wrap:wrap;}
.hero-left .tag{padding:0.2rem 0.5rem;background:#F0FDF4;border:1px solid #86EFAC;border-radius:6px;
  font-size:0.72rem;color:#166534;font-weight:500;}
.hero-right{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;min-width:260px;}
.hero-stat{text-align:center;background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:0.7rem 0.5rem;}
.hero-stat .n{font-size:1.3rem;font-weight:700;color:#0F172A;}
.hero-stat .l{font-size:0.65rem;color:#64748B;text-transform:uppercase;letter-spacing:0.5px;}

/* Setup note */
.setup{background:#FFFBEB;border:1px solid #FDE68A;border-radius:10px;padding:0.8rem 1rem;margin:0.8rem 0;font-size:0.95rem;color:#92400E;}

/* Feature cards */
.fg{display:grid;grid-template-columns:repeat(3,1fr);gap:0.8rem;margin:1rem 0;}
.fc{background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:1rem;cursor:pointer;transition:all 0.15s;}
.fc:hover{border-color:#0F172A;box-shadow:0 2px 8px rgba(0,0,0,0.06);}
.fc h4{font-size:1rem;color:#0F172A;margin:0 0 0.3rem;} .fc p{font-size:0.88rem;color:#64748B;margin:0;line-height:1.4;}

/* Trust cards */
.tg{display:grid;grid-template-columns:1fr 1fr;gap:1rem;margin:1rem 0;}
.tt{background:#F8FAFC;border:1px solid #E2E8F0;border-radius:10px;padding:1.2rem;}
.tt h4{font-size:1.15rem;color:#0F172A;margin:0 0 0.6rem;}
.tt ul{list-style:none;padding:0;margin:0;}
.tt li{padding:0.2rem 0;font-size:0.95rem;color:#1E293B;line-height:1.5;}
.tt li::before{content:'✓ ';color:#059669;font-weight:700;}

/* Info cards */
.card{background:#fff;border:1px solid #E2E8F0;border-radius:10px;padding:1rem;margin:0.4rem 0;}
.card.green{border-left:4px solid #059669;} .card.amber{border-left:4px solid #D97706;}
.card.red{border-left:4px solid #DC2626;} .card.blue{border-left:4px solid #2563EB;}
.privacy{background:#EFF6FF;border:1px solid #BFDBFE;border-radius:8px;padding:0.5rem 0.8rem;font-size:0.85rem;color:#1E40AF;margin-bottom:0.8rem;}

/* Chat panel */
.chat-hdr{background:#0F172A;color:#fff;padding:0.7rem 1rem;border-radius:10px 10px 0 0;display:flex;align-items:center;gap:0.5rem;}
.chat-hdr .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:pulse 2s infinite;}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.chat-hdr .nm{font-weight:600;font-size:1rem;} .chat-hdr .rl{font-size:0.75rem;color:#94A3B8;}
.chat-disc{font-size:0.78rem;color:#64748B;font-style:italic;margin-top:0.5rem;line-height:1.4;}

@media(max-width:900px){.fg{grid-template-columns:1fr 1fr;}.tg,.hero-row{flex-direction:column;}}
@media(max-width:600px){.fg{grid-template-columns:1fr;}.hero-right{grid-template-columns:1fr 1fr;}}
</style>""", unsafe_allow_html=True)

# Session
for k,v in {'profiles':{'Me':TaxpayerProfile()},'active_profile':'Me','profile_complete':{},'chat_history':[],'page':'Home'}.items():
    if k not in st.session_state: st.session_state[k]=v
if 'vector_db' not in st.session_state:
    st.session_state.vector_db=TaxVectorDB(); st.session_state.vector_db.index_knowledge_base(TAX_KNOWLEDGE_BASE)
KEY=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P(): return st.session_state.profiles[st.session_state.active_profile]
def IC(): return st.session_state.profile_complete.get(st.session_state.active_profile,False)
def go(p): st.session_state.page=p

# NAV
tabs=["Home","Tax Profile","Calculator","Savings Finder","Scenarios","Law Updates","About"]
sel=st.radio("",tabs,horizontal=True,label_visibility="collapsed",
    index=tabs.index(st.session_state.page) if st.session_state.page in tabs else 0,key="nav")
st.session_state.page=sel

# Profile switcher
if sel not in ("Home","Law Updates","About"):
    pc1,pc2=st.columns([4,1])
    with pc2:
        names=list(st.session_state.profiles.keys())
        if len(names)<5: names.append("➕ Add")
        ch=st.selectbox("",names,index=names.index(st.session_state.active_profile) if st.session_state.active_profile in names else 0,label_visibility="collapsed")
        if ch=="➕ Add":
            nn=f"Profile {len(st.session_state.profiles)+1}"; st.session_state.profiles[nn]=TaxpayerProfile(); st.session_state.active_profile=nn; st.rerun()
        else: st.session_state.active_profile=ch
    with pc1:
        if IC():
            r=compare_regimes(P()); b=r[r['recommended']+'_regime']
            st.markdown(f"**{st.session_state.active_profile}** — Tax: **{format_lakhs(b['total_tax'])}** | Rate: {b['effective_rate']}% | {'New' if r['recommended']=='new' else 'Old'} Regime ✅")
        else: st.caption(f"**{st.session_state.active_profile}** — not set up yet")

# CHAT
def chat(k=""):
    st.markdown(f'<div class="chat-hdr"><div class="dot"></div><div><span class="nm">{A} — Your Tax Agent</span><br><span class="rl">Ask anything about Indian income tax</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("Language",[("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=320)
    with bx:
        if not st.session_state.chat_history:
            st.markdown(f"👋 **Hi, I'm {A}!** Ask me anything about Indian income tax — which regime to pick, how ESOPs are taxed, F&O rules, capital gains, deductions — I'll cite the exact law and never make things up.")
        for m in st.session_state.chat_history:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None): st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A} anything...",key=f"c{k}"):
        cl,n=anonymize_text(pr); st.session_state.chat_history.append({'role':'user','content':pr})
        if not KEY: rsp="⚠️ API key not set. Admin: add GEMINI_API_KEY in Settings → Secrets."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {}; rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=KEY)
        st.session_state.chat_history.append({'role':'assistant','content':rsp}); st.rerun()
    st.markdown(f'<div class="chat-disc">💡 {A} is grounded in the Income Tax Act, latest Budget circulars, and tax case law. For important decisions or complex cases, consult a professional tax advisor or Chartered Accountant.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1]); 
    with c1: fn()
    with c2: chat(k)

# ═══ HOME ═══
if sel=="Home":
    _l=f'<img src="data:image/png;base64,{LOGO_B64}">' if LOGO_B64 else ''
    st.markdown(f"""<div class="hero-row">
    <div class="hero-left">{_l}
    <h1>Stop overpaying your taxes.</h1>
    <p>AI that knows Indian tax law helps you pick the right regime, find every deduction, and plan ahead.</p>
    <div class="tags"><span class="tag">Always Accurate</span><span class="tag">Your Data Stays Private</span>
    <span class="tag">FY 2025-26 Updated</span><span class="tag">Works in Hindi</span></div></div>
    <div class="hero-right">
    <div class="hero-stat"><div class="n">9 Cr+</div><div class="l">ITR Filers in India</div></div>
    <div class="hero-stat"><div class="n">₹3.9L Cr</div><div class="l">Tax Refunds in FY25</div></div>
    <div class="hero-stat"><div class="n">2 Regimes</div><div class="l">70+ Sections</div></div>
    <div class="hero-stat"><div class="n">47</div><div class="l">Tax Rules in our AI</div></div>
    </div></div>""",unsafe_allow_html=True)

    st.markdown("""<div class="setup">📋 <b>Set up your tax profile (one-time, takes 2 minutes)</b><br>
    Upload a document or enter your details. You only need to do this once — then all tools work automatically.
    Create up to 5 profiles for family members.</div>""",unsafe_allow_html=True)
    c1,c2=st.columns(2)
    with c1:
        if st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary"): go("Tax Profile"); st.rerun()
    with c2:
        if st.button("✏️ Enter Details Manually",use_container_width=True): go("Tax Profile"); st.rerun()

    st.markdown(f"""<div class="fg">
    <div class="fc"><h4>⚖️ Regime Comparison</h4><p>See exactly how much you save under Old vs New — in rupees, not percentages.</p></div>
    <div class="fc"><h4>📄 Document Upload</h4><p>Drop your payslip or Form 16. We read it and fill in everything for you.</p></div>
    <div class="fc"><h4>💡 Savings Finder</h4><p>Specific recommendations: what to invest, how much, by when.</p></div>
    <div class="fc"><h4>🔀 What-If Scenarios</h4><p>Getting a raise? Selling shares? Buying a house? See the tax impact before you act.</p></div>
    <div class="fc"><h4>💬 {A} — Tax Agent</h4><p>Ask {A} anything in English, Hindi, Tamil, Telugu, or Kannada.</p></div>
    <div class="fc"><h4>👨‍👩‍👧‍👦 Family Profiles</h4><p>Create up to 5 profiles for spouse, parents — compare and plan together.</p></div>
    </div>""",unsafe_allow_html=True)

    st.markdown(f"""<div class="tg">
    <div class="tt"><h4>🛡️ Always Accurate</h4><ul>
    <li>Your tax numbers are calculated by a precise engine — not guessed by AI</li>
    <li>Every answer cites the actual section of the Income Tax Act</li>
    <li>When unsure, we tell you to check with a CA — we never make things up</li>
    <li>Updated with Budget 2025 and Budget 2026 changes</li></ul></div>
    <div class="tt"><h4>🔒 Your Data Stays Private</h4><ul>
    <li>We never see your PAN, Aadhaar, address, date of birth, phone, or email</li>
    <li>Bank account numbers and PF/UAN details are never stored</li>
    <li>Your employer name and employee ID are stripped automatically</li>
    <li>Everything clears when you close the browser — nothing is saved</li></ul></div>
    </div>""",unsafe_allow_html=True)

    st.markdown("---")
    chat("home")

# ═══ TAX PROFILE ═══
elif sel=="Tax Profile":
    def tp():
        st.markdown("## Set Up Your Tax Profile")
        st.caption(f"Profile: **{st.session_state.active_profile}** — create up to 5 for family members.")
        st.markdown("#### 📄 Quick: Upload a Document")
        st.markdown('<div class="privacy">🔒 We only read financial numbers. Your name, PAN, employer, and personal details are automatically ignored.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax computation sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and KEY:
            with st.spinner(f"🔍 {A} is reading your document..."):
                doc=analyze_document(up.read(),KEY,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual'; mul=1 if ann else 12
                st.success(f"✅ {'Annual' if ann else 'Monthly'} data found:")
                for k,v in doc.items():
                    if k not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{k.replace('_',' ').title()}:** ₹{v:,.0f}"+("" if ann else f" → ₹{v*mul:,.0f}/yr"))
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in ("NOT_FOUND",None): return d
                    try: return float(v)*mul
                    except: return d
                if st.button("✅ Use This Data",type="primary",use_container_width=True):
                    p=P(); p.taxpayer_type="salaried"; p.gross_salary=gv('gross_salary')
                    p.basic_salary=gv('basic_salary',p.gross_salary*0.4); p.hra_received=gv('hra')
                    p.tds_deducted=gv('tds_deducted'); p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    st.session_state.profile_complete[st.session_state.active_profile]=True; go("Calculator"); st.rerun()
            else: st.error("Couldn't read document. Try manual entry.")
        elif up: st.error("API key not configured.")
        st.markdown("---")
        st.markdown("#### ✏️ Or Enter Manually")
        c1,c2=st.columns(2)
        with c1:
            tt=st.selectbox("I am a...",["Salaried Employee","Business Owner","Professional","F&O Trader","Investor","Freelancer"])
            tm={"Salaried Employee":"salaried","Business Owner":"business","Professional":"professional","F&O Trader":"trader","Investor":"investor","Freelancer":"professional"}
            age=st.number_input("Age",18,100,30)
        with c2:
            res=st.selectbox("Residency",["Resident Indian","NRI","RNOR"])
            rm={"Resident Indian":"resident","NRI":"nri","RNOR":"rnor"}
            met=st.selectbox("Metro city?",["Yes (Delhi/Mumbai/Chennai/Kolkata)","No"])
        t=tm[tt]; gs=bs=hra=rent=enps=biz=trd=ii=ri=di=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0; fesop=False
        st.markdown("##### Income")
        if t=="salaried":
            c1,c2,c3=st.columns(3)
            with c1: gs=st.number_input("Gross Salary ₹/yr",0,value=0,step=50000,format="%d")
            with c2: bs=st.number_input("Basic ₹/yr",0,value=0,step=25000,format="%d",help="~40% of gross")
            with c3: hra=st.number_input("HRA ₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1: rent=st.number_input("Rent Paid ₹/yr",0,value=0,step=10000,format="%d")
            with c2: enps=st.number_input("Employer NPS ₹/yr",0,value=0,step=5000,format="%d",help="Saves tax in BOTH regimes")
        elif t in ("business","professional"):
            c1,c2=st.columns(2)
            with c1: biz=st.number_input("Business Income ₹",0,value=0,step=100000,format="%d")
            with c2: gs=st.number_input("Salary (if any) ₹",0,value=0,step=50000,format="%d")
        elif t=="trader":
            c1,c2=st.columns(2)
            with c1: trd=st.number_input("F&O Profit/(Loss) ₹",value=0,step=50000,format="%d")
            with c2: gs=st.number_input("Salary (if any) ₹",0,value=0,step=50000,format="%d")
        with st.expander("Other income, capital gains, ESOPs"):
            c1,c2,c3=st.columns(3)
            with c1: ii=st.number_input("Interest ₹/yr",0,value=0,step=5000,format="%d")
            with c2: ri=st.number_input("Rental ₹/yr",0,value=0,step=10000,format="%d")
            with c3: di=st.number_input("Dividend ₹/yr",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1: stcg=st.number_input("Short-term gains ₹",0,value=0,step=10000,format="%d")
            with c2: ltcg=st.number_input("Long-term gains ₹",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite ₹",0,value=0,step=50000,format="%d"); fesop=st.checkbox("Foreign company ESOPs")
        with st.expander("Deductions (for Old Regime comparison)"):
            c1,c2,c3=st.columns(3)
            with c1: s80c=st.number_input("80C ₹",0,150000,0,step=10000,format="%d")
            with c2: s80d=st.number_input("80D Health ₹",0,50000,0,step=5000,format="%d")
            with c3: s80n=st.number_input("NPS Extra ₹",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1: s80e=st.number_input("Edu Loan Int ₹",0,value=0,step=10000,format="%d")
            with c2: s24b=st.number_input("Home Loan Int ₹",0,200000,0,step=10000,format="%d")
        with st.expander("TDS & advance tax already paid"):
            c1,c2=st.columns(2)
            with c1: tds=st.number_input("TDS ₹",0,value=0,step=10000,format="%d")
            with c2: adv=st.number_input("Advance Tax ₹",0,value=0,step=10000,format="%d")
        if st.button("✅ Save & See My Tax",type="primary",use_container_width=True):
            p=P(); p.taxpayer_type=t; p.age=age; p.residency=rm[res]; p.metro_city="Yes" in met
            p.gross_salary=gs; p.basic_salary=bs if bs else gs*0.4; p.hra_received=hra; p.rent_paid_annual=rent
            p.section_80ccd_2=enps; p.business_income=biz; p.trading_income=trd
            p.interest_income=ii; p.rental_income=ri; p.dividend_income=di
            p.stcg_equity=stcg; p.ltcg_equity=ltcg; p.esop_perquisite=esop; p.foreign_esop=fesop
            p.section_80c=s80c; p.section_80d_self=s80d; p.section_80d_parents=0; p.section_80ccd_1b=s80n
            p.section_80e=s80e; p.section_24b=s24b; p.tds_deducted=tds; p.advance_tax_paid=adv
            st.session_state.profile_complete[st.session_state.active_profile]=True; go("Calculator"); st.rerun()
    with_chat(tp,"tp")

# ═══ CALCULATOR ═══
elif sel=="Calculator":
    def calc():
        st.markdown("## Which Regime Saves You More?")
        if not IC():
            st.warning("Set up your tax profile first."); 
            if st.button("→ Set Up Profile"): go("Tax Profile"); st.rerun()
            return
        p=P(); r=compare_regimes(p); o=r['old_regime']; n=r['new_regime']; rc=r['recommended']; sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"### {'✅ ' if rc=='new' else ''}New Regime"); st.markdown(f"Taxable: **{format_currency(n['taxable_income'])}**")
            st.markdown(f"Tax: {format_currency(n['slab_tax'])}"); 
            if n['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(n['rebate_87a'])}")
            st.markdown(f"Cess: {format_currency(n['cess'])}"); st.markdown(f"**Total: {format_currency(n['total_tax'])} ({n['effective_rate']}%)**")
        with c2:
            st.markdown(f"### {'✅ ' if rc=='old' else ''}Old Regime"); st.markdown(f"Taxable: **{format_currency(o['taxable_income'])}**")
            if o.get('hra_exemption',0)>0: st.caption(f"HRA exempt: {format_currency(o['hra_exemption'])}")
            if o['total_deductions']>0: st.caption(f"Deductions: {format_currency(o['total_deductions'])}")
            st.markdown(f"Tax: {format_currency(o['slab_tax'])}");
            if o['rebate_87a']>0: st.markdown(f"Rebate: -{format_currency(o['rebate_87a'])}")
            st.markdown(f"Cess: {format_currency(o['cess'])}"); st.markdown(f"**Total: {format_currency(o['total_tax'])} ({o['effective_rate']}%)**")
        if o['total_deductions']>0:
            with st.expander("Deduction details"):
                for s,a in o['deduction_breakdown'].items():
                    if a>0: st.markdown(f"- **{s}:** {format_currency(a)}")
    with_chat(calc,"calc")

# ═══ SAVINGS FINDER ═══
elif sel=="Savings Finder":
    def sf():
        st.markdown("## How to Save More Tax")
        if not IC():
            st.warning("Set up your tax profile first.");
            if st.button("→ Set Up Profile"): go("Tax Profile"); st.rerun()
            return
        p=P(); r=compare_regimes(p); rc=r['recommended']; recs=[]
        if rc=='old' and p.section_80c<150000:
            g=150000-p.section_80c; s=g*0.30 if p.gross_salary>1000000 else g*0.20
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more in 80C',f'ELSS, PPF, or tax-saver FD. Could save ~₹{s:,.0f}.','Before March 31'))
        if p.section_80ccd_2==0: recs.append(('red','80CCD(2)','Ask employer about NPS','Works in BOTH regimes — up to 14% of basic.','Ask HR'))
        if p.esop_perquisite>0: recs.append(('amber','17(2)(vi)',f'ESOP perquisite: ₹{p.esop_perquisite:,.0f}','Taxed as salary. Time exercise carefully.','Consult CA'))
        if p.foreign_esop: recs.append(('red','Schedule FA','Foreign ESOPs must be disclosed','Penalty for non-disclosure: ₹10L under Black Money Act.','File Schedule FA + Form 67'))
        if p.trading_income!=0: recs.append(('red','43(5)','F&O: must file ITR-3','Even losses must be reported for 8-year carry-forward.','Get a CA'))
        if rc=='old' and p.section_80d_self==0: recs.append(('amber','80D','Get health insurance','Up to ₹25K self + ₹50K parents = ₹1L deduction.','Buy policy'))
        if not recs: st.success("🎉 Well optimized!")
        for col,sec,t,d,a in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="card {col}"><b>{ic} {t}</b> <em>(Section {sec})</em><br>{d}<br><b>→ {a}</b></div>',unsafe_allow_html=True)
    with_chat(sf,"sf")

# ═══ SCENARIOS ═══
elif sel=="Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        if not IC():
            st.warning("Set up your tax profile first.");
            if st.button("→ Set Up Profile"): go("Tax Profile"); st.rerun()
            return
        p=P(); cur=compare_regimes(p); ct=cur[cur['recommended']+'_regime']['total_tax']
        s=st.selectbox("What do you want to explore?",["Switch regime","Invest more in 80C","Get a raise","Sell shares","Buy/rent a house","Take a loan"])
        if s=="Switch regime":
            alt='old' if cur['recommended']=='new' else 'new'; at=cur[alt+'_regime']['total_tax']; d=at-ct
            st.metric(f"Tax under {'Old' if alt=='old' else 'New'} Regime",format_currency(at),
                delta=f"+{format_currency(d)}" if d>0 else f"{format_currency(d)}",delta_color="inverse")
        elif s=="Invest more in 80C":
            ex=st.slider("Additional 80C ₹",0,150000,50000,10000)
            p2=copy.deepcopy(p); p2.section_80c=min(p.section_80c+ex,150000); r2=compare_regimes(p2)
            st.metric("Tax",format_currency(r2[r2['recommended']+'_regime']['total_tax']),
                delta=f"-{format_currency(ct-r2[r2['recommended']+'_regime']['total_tax'])}")
        elif s=="Get a raise":
            pct=st.slider("Raise %",5,50,15,5)
            p2=copy.deepcopy(p); p2.gross_salary=int(p.gross_salary*(1+pct/100)); p2.basic_salary=int(p.basic_salary*(1+pct/100))
            r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
            c1,c2=st.columns(2)
            with c1: st.metric("New salary",format_lakhs(p2.gross_salary))
            with c2: st.metric("Extra tax",format_currency(t2-ct))
        elif s=="Sell shares":
            lg=st.number_input("Expected LTCG ₹",0,value=200000,step=25000)
            p2=copy.deepcopy(p); p2.ltcg_equity+=lg; r2=compare_regimes(p2)
            st.metric("Additional tax",format_currency(r2[r2['recommended']+'_regime']['total_tax']-ct))
        elif s=="Buy/rent a house":
            st.markdown("##### If you take a home loan:")
            loan_int=st.number_input("Expected home loan interest ₹/yr",0,value=200000,step=25000)
            loan_pri=st.number_input("Home loan principal repayment ₹/yr",0,value=100000,step=25000)
            p2=copy.deepcopy(p); p2.section_24b=min(loan_int,200000); p2.section_80c=min(p.section_80c+loan_pri,150000)
            r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
            st.metric("Tax with home loan",format_currency(t2),delta=f"-{format_currency(ct-t2)} saved" if ct>t2 else "No change")
            st.caption("Home loan interest (Section 24b, max ₹2L) and principal (Section 80C) deductions apply under Old Regime only.")
            st.markdown("##### If you pay rent without owning a house:")
            rent_yr=st.number_input("Annual rent ₹",0,value=240000,step=12000)
            p3=copy.deepcopy(p); p3.rent_paid_annual=rent_yr
            r3=compare_regimes(p3); t3=r3[r3['recommended']+'_regime']['total_tax']
            st.metric("Tax with HRA claim",format_currency(t3),delta=f"-{format_currency(ct-t3)} saved" if ct>t3 else "No change")
            st.caption("HRA exemption (Section 10(13A)) applies under Old Regime if you receive HRA from employer.")
        elif s=="Take a loan":
            lt=st.selectbox("Loan type",["Education loan","Home loan (see 'Buy/rent a house')","Personal loan (no tax benefit)"])
            if lt=="Education loan":
                ei=st.number_input("Annual interest on education loan ₹",0,value=100000,step=10000)
                p2=copy.deepcopy(p); p2.section_80e=ei; r2=compare_regimes(p2); t2=r2[r2['recommended']+'_regime']['total_tax']
                st.metric("Tax with education loan",format_currency(t2),delta=f"-{format_currency(ct-t2)} saved")
                st.caption("Section 80E: Full interest deductible, no upper limit, for 8 years. Old Regime only.")
            elif lt=="Personal loan (no tax benefit)":
                st.info("Personal loans don't offer any income tax deduction. Only education and home loans have tax benefits.")
    with_chat(sc,"sc")

# ═══ LAW UPDATES ═══
elif sel=="Law Updates":
    def lu():
        st.markdown("## Recent Tax Law Changes")
        for dt,t,d,col in [
            ('Feb 2026','No slab changes for FY 2026-27','New Income Tax Act 2025 effective April 2026 — reorganizes the law, no rate changes.','blue'),
            ('Jul 2024','Capital gains rates changed','Short-term equity: 15%→20%. Long-term: 10%→12.5%. Indexation removed for all assets.','amber'),
            ('Feb 2025','Income up to ₹12.75L now tax-free','New regime exemption ₹4L, rebate ₹60K. Salaried up to ₹12.75L pay zero tax.','green'),
        ]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="card {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---")
        sq=st.text_input("🔍 Search any tax topic",placeholder="ESOP, HRA, F&O, capital gains, NRI...")
        if sq:
            for r in st.session_state.vector_db.search_tax_law(sq)[:3]:
                st.markdown(f"**{r['metadata'].get('title','')}** ({r['metadata'].get('section','')})")
                st.markdown(r['content'][:300]+"..."); st.markdown("---")
    with_chat(lu,"lu")

# ═══ ABOUT ═══
elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru
**TaxGuru** helps Indian taxpayers plan and optimize their taxes for FY 2025-26.

**Built with:** Gemini AI (Google) with search grounding for real-time law updates • ChromaDB vector database with 47 tax law entries • 3 AI agents (Tax Advisor, Document Reader, Law Updater) • UI designed in v0.dev (Vercel AI) • Deployed on Streamlit Cloud • Code written with Claude (Anthropic)

**Privacy:** We never collect your name, PAN, Aadhaar, date of birth, address, phone number, email, bank account, PF number, or employer details. Only financial figures are processed in your browser session. Close the tab and everything is gone.

**{A}** always cites the specific section of the Income Tax Act. When unsure, {A} tells you to consult a CA rather than guess.

*This is informational guidance, not professional tax advice.*""")
    with_chat(ab,"ab")
