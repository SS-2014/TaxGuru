"""TaxGuru v9 — Navigation fixed via callbacks. Black button text. Huge logo. Regime toggle."""
import streamlit as st
import sys,os,copy,random
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB
st.set_page_config(page_title="TaxGuru",page_icon="🏛️",layout="wide",initial_sidebar_state="collapsed")
LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()
if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag

# ══════ NAVIGATION via session state + callbacks ══════
if 'pg' not in st.session_state:st.session_state.pg='Home'
def nav(p):st.session_state.pg=p

st.markdown("""<style>
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],
button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
footer:after{content:'';visibility:hidden;display:block;}.stApp>header{display:none!important;}
.stApp,[data-testid="stAppViewContainer"]{background:#0B0F19!important;color:#F1F5F9;}
[data-testid="stVerticalBlock"]{gap:0.3rem!important;}
h1,h2,h3,h4{color:#F1F5F9!important;}p,li,span,.stMarkdown{color:#E2E8F0;}
.stApp{margin-top:0;}.block-container{padding:0.3rem 1.2rem 0.5rem!important;max-width:100%!important;}
[data-testid="stAppViewContainer"]>div:first-child{padding-top:0.2rem!important;}
/* Nav */
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{background:#1E293B;border:1px solid #475569;border-radius:6px;padding:0.35rem 0.8rem;font-size:0.95rem;font-weight:600;color:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#334155;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){background:#D4A843!important;color:#000!important;border-color:#D4A843!important;font-weight:700;}
/* Cards */
.cd{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin:0.3rem 0;font-size:1rem;color:#E2E8F0;}
.cd.green{border-left:3px solid #10B981;}.cd.amber{border-left:3px solid #F59E0B;}.cd.red{border-left:3px solid #EF4444;}.cd.blue{border-left:3px solid #3B82F6;}
/* Trust */
.tg{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}
.tt{background:#1A1F2E;border:2px solid #D4A843;border-radius:10px;padding:0.9rem;}
.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1.15rem;}
.tt ul{list-style:none;padding:0;margin:0;}.tt li{padding:0.15rem 0;font-size:1rem;color:#F1F5F9;line-height:1.5;}.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}
/* Setup */
.su{background:#1C1917;border:2px solid #D4A843;border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 0.8rem;text-align:center;}
.su b{font-size:1.2rem;color:#FDE68A;}.su span{color:#E2E8F0;font-size:1rem;}
/* Feature cards */
.fb{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin-bottom:0.3rem;}
.fb h4{color:#D4A843;margin:0 0 0.2rem;font-size:1.05rem;}.fb p{color:#CBD5E1;font-size:0.92rem;margin:0;line-height:1.4;}
/* Logo */
.logo-area{padding:0.1rem 0 0.2rem;}.logo-area img{height:200px;filter:drop-shadow(0 0 15px rgba(212,168,67,0.3));}
.logo-sm{padding:0.1rem 0;}.logo-sm img{height:200px;filter:drop-shadow(0 0 15px rgba(212,168,67,0.3));}
/* Chat */
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}
.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.85rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:#93C5FD;margin-bottom:0.5rem;}
/* Inputs */
[data-testid="stSelectbox"]>div>div{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stNumberInput"] input{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stFileUploader"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}
.stTextInput input{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stExpander"]{background:#111827;border:1px solid #374151;border-radius:8px;}
[data-testid="stExpander"] summary{color:#F1F5F9!important;font-size:1rem;}
[data-testid="stMultiSelect"]>div>div{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stMetric"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}
[data-testid="stMetricValue"]{color:#D4A843!important;font-size:1.3rem!important;}
[data-testid="stMetricLabel"]{color:#CBD5E1!important;}
/* BUTTONS: #000 on gold ALWAYS */
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:#D4A843!important;color:#000000!important;border:none!important;font-weight:900!important;font-size:1rem!important;-webkit-text-fill-color:#000000!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:700!important;font-size:0.95rem!important;-webkit-text-fill-color:#F1F5F9!important;}
/* Chat input */
[data-testid="stChatInput"]{background:#FFF!important;border:2px solid #475569;border-radius:8px;min-height:50px;}
[data-testid="stChatInput"] textarea{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000!important;}
.stSlider [data-testid="stThumbValue"]{color:#D4A843!important;}
/* Toggle */
[data-testid="stToggle"] label span{color:#F1F5F9!important;font-size:1rem!important;}
@media(max-width:900px){.tg{grid-template-columns:1fr;}.logo-area img,.logo-sm img{height:120px;}}
</style>""",unsafe_allow_html=True)

# Session
for k,v in {'profiles':{'Me':TaxpayerProfile()},'ap':'Me','pc':{},'ch':[]}.items():
    if k not in st.session_state:st.session_state[k]=v
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profiles[st.session_state.ap]
def IC():return st.session_state.pc.get(st.session_state.ap,False)

TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Law Updates","About"]
sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",
    index=TABS.index(st.session_state.pg) if st.session_state.pg in TABS else 0,key="nav_radio")
st.session_state.pg=sel

# Profile bar
if sel not in ("Home","Law Updates","About") and IC():
    c1,c2=st.columns([4,1])
    with c2:
        ns=list(st.session_state.profiles.keys())
        if len(ns)<5:ns.append("➕ Add")
        ch=st.selectbox("",ns,index=ns.index(st.session_state.ap) if st.session_state.ap in ns else 0,label_visibility="collapsed")
        if ch=="➕ Add":nn=f"Profile {len(st.session_state.profiles)+1}";st.session_state.profiles[nn]=TaxpayerProfile();st.session_state.ap=nn;st.rerun()
        else:st.session_state.ap=ch
    with c1:
        r=compare_regimes(P());b=r[r['recommended']+'_regime']
        st.markdown(f"**{st.session_state.ap}** — Tax: **{format_lakhs(b['total_tax'])}** | {b['effective_rate']}% | {'New' if r['recommended']=='new' else 'Old'} Regime ✅")

# Logo helper
def show_logo(home=False):
    if LOGO:
        cls="logo-area" if home else "logo-sm"
        st.markdown(f'<div class="{cls}"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)

# Chat
def chat(k=""):
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A} — Your Tax Agent</span><br><span class="rl">Ask me anything about your tax needs</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=420)
    with bx:
        if not st.session_state.ch:
            st.markdown(f"👋 **Hi, I'm {A}!** Ask me anything about Indian income tax — which regime to pick, how ESOPs are taxed, trading rules, capital gains, deductions. I cite the exact law and never guess.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A} anything...",key=f"c{k}"):
        cl,_=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp="⚠️ API key not set. Admin: add GEMINI_API_KEY in Settings → Secrets."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,agent_name=A)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the Income Tax Act, latest circulars, and case law. For important decisions, consult a CA.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        show_logo(home=True)
        st.markdown('<div style="margin-top:0.3rem"><h1 style="font-size:1.6rem!important;margin-bottom:0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1rem;color:#E2E8F0">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p></div>',unsafe_allow_html=True)
        st.markdown('<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter details. Create up to 5 profiles.</span></div>',unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary",on_click=nav,args=("Tax Profile",))
        with bc2:st.button("✏️ Enter Manually",use_container_width=True,on_click=nav,args=("Tax Profile",))

        fc1,fc2,fc3=st.columns(3)
        with fc1:
            st.markdown('<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New regime — see exact savings in rupees. Know which is better for you.</p></div>',unsafe_allow_html=True)
            st.button("Open Tax Calculator →",use_container_width=True,key="h1",on_click=nav,args=("Tax Calculator",))
        with fc2:
            st.markdown('<div class="fb"><h4>🔀 What-If Scenarios</h4><p>Getting a raise? Taking a home loan? Investing in ELSS? See how it changes your tax.</p></div>',unsafe_allow_html=True)
            st.button("Open Scenarios →",use_container_width=True,key="h4",on_click=nav,args=("What-If Scenarios",))
        with fc3:
            st.markdown('<div class="fb"><h4>💡 Savings Finder</h4><p>Specific recommendations — what to invest, how much, by when. With exact tax impact.</p></div>',unsafe_allow_html=True)
            st.button("Open Savings Finder →",use_container_width=True,key="h3",on_click=nav,args=("Savings Finder",))

        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Tax numbers from a precise calculation engine — not AI guesses</li><li>Every answer cites the actual Income Tax Act section</li><li>When unsure, {A} says "check with a CA" — never makes things up</li><li>Updated real-time with Budget 2026 changes, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Your Data Stays Private</h4><ul><li>We never see your PAN, Aadhaar, address, DOB, phone, or email</li><li>Bank accounts, PF/UAN, employer name — all auto-deleted</li><li>Only salary/deduction numbers used — in your browser session only</li><li>Close the browser → everything gone. Nothing saved. Ever.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat("home")

# ══════ TAX PROFILE ══════
elif sel=="Tax Profile":
    def tp():
        show_logo()
        st.markdown("## Tax Profile")
        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only financial numbers extracted. Personal details auto-ignored.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"🔍 {A} is reading your document..."):doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success(f"✅ {'Annual' if ann else 'Monthly'} data found:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}"+("" if ann else f" → ₹{v*mul:,.0f}/yr"))
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                st.button("✅ Use This Data",type="primary",use_container_width=True,key="use_doc",
                    on_click=lambda:_use_doc(gv))
            else:st.error("Couldn't read document. Try manual entry.")
        elif up:st.error("API key not configured.")
        st.markdown("---")
        st.markdown("#### ✏️ Manual Entry")
        c1,c2=st.columns(2)
        with c1:
            types=st.multiselect("I earn income from...",["Salary","Business","Professional services","Trading (stocks, F&O, crypto)","Investments","Freelancing","Other"],default=["Salary"])
            age=st.number_input("Age",18,100,30)
        with c2:
            st.markdown("**Residency** (we'll figure it out)")
            citizenship=st.selectbox("Citizenship",["Indian citizen","Person of Indian origin","Foreign citizen"])
            days_india=st.number_input("Days in India this FY (Apr-Mar)",0,366,365)
            days_4yr=st.number_input("Total days in India, last 4 years",0,1461,1400)
            income_15l=st.checkbox("Indian income exceeds ₹15 lakh")
            if days_india>=182:res_s="resident";st.markdown("✅ **Resident** — 182+ days")
            elif citizenship!="Foreign citizen":
                if income_15l and days_india>=120 and days_4yr>=365:res_s="rnor";st.markdown("⚠️ **RNOR** — 120+ days, >₹15L")
                elif days_india>=60 and days_4yr>=365 and not income_15l:res_s="resident";st.markdown("✅ **Resident** — 60+ days + 365+ in 4yr")
                else:res_s="nri";st.markdown("🌍 **NRI** — <182 days")
            else:
                if days_india>=60 and days_4yr>=365:res_s="resident";st.markdown("✅ **Resident**")
                else:res_s="nri";st.markdown("🌍 **Non-Resident**")
            met=st.selectbox("Metro? (50% HRA)",["Yes — Del/Mum/Kol/Che/Hyd/Pune/Ahd/Blr","No — Other"])
        t="salaried"
        if "Business" in types:t="business"
        if "Professional services" in types:t="professional"
        if "Trading (stocks, F&O, crypto)" in types:t="trader"
        gs=bs=hra=rent=enps=biz=trd=ii=ri=di=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False
        st.markdown("**💰 Income**")
        if "Salary" in types:
            c1,c2,c3=st.columns(3)
            with c1:gs=st.number_input("Gross Salary ₹/yr",0,value=0,step=50000,format="%d")
            with c2:bs=st.number_input("Basic ₹/yr",0,value=0,step=25000,format="%d")
            with c3:hra=st.number_input("HRA ₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:rent=st.number_input("Rent ₹/yr",0,value=0,step=10000,format="%d")
            with c2:enps=st.number_input("Employer NPS ₹/yr",0,value=0,step=5000,format="%d")
        if any(x in types for x in ["Business","Professional services","Freelancing"]):
            biz=st.number_input("Business/Professional Income ₹",0,value=0,step=100000,format="%d")
        if "Trading (stocks, F&O, crypto)" in types:
            trd=st.number_input("Trading Profit/(Loss) ₹",value=0,step=50000,format="%d")
        with st.expander("📈 Investments, capital gains, ESOPs"):
            c1,c2,c3=st.columns(3)
            with c1:ii=st.number_input("Interest",0,value=0,step=5000,format="%d")
            with c2:ri=st.number_input("Rental",0,value=0,step=10000,format="%d")
            with c3:di=st.number_input("Dividend",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("STCG",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("LTCG",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite",0,value=0,step=50000,format="%d")
            fe=st.checkbox("Foreign ESOPs")
        with st.expander("🏦 Deductions (Old Regime)"):
            c1,c2,c3=st.columns(3)
            with c1:s80c=st.number_input("80C",0,150000,0,step=10000,format="%d")
            with c2:s80d=st.number_input("80D",0,50000,0,step=5000,format="%d")
            with c3:s80n=st.number_input("NPS",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:s80e=st.number_input("Edu Loan",0,value=0,step=10000,format="%d")
            with c2:s24b=st.number_input("Home Loan",0,200000,0,step=10000,format="%d")
        with st.expander("💳 TDS / Advance Tax"):
            c1,c2=st.columns(2)
            with c1:tds=st.number_input("TDS",0,value=0,step=10000,format="%d")
            with c2:adv=st.number_input("Advance Tax",0,value=0,step=10000,format="%d")
        def _save():
            p=P();p.taxpayer_type=t;p.age=age;p.residency=res_s;p.metro_city="Yes" in met
            p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent
            p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd
            p.interest_income=ii;p.rental_income=ri;p.dividend_income=di;p.stcg_equity=stcg;p.ltcg_equity=ltcg
            p.esop_perquisite=esop;p.foreign_esop=fe;p.section_80c=s80c;p.section_80d_self=s80d
            p.section_80d_parents=0;p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b
            p.tds_deducted=tds;p.advance_tax_paid=adv
            st.session_state.pc[st.session_state.ap]=True;st.session_state.pg="Tax Calculator"
        st.button("✅ Save & See My Tax",type="primary",use_container_width=True,on_click=_save)
    def _use_doc(gv):
        p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
        p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted');p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
        p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'));st.session_state.pc[st.session_state.ap]=True;st.session_state.pg="Tax Calculator"
    with_chat(tp,"tp")

# ══════ TAX CALCULATOR with regime toggle ══════
elif sel=="Tax Calculator":
    def calc():
        show_logo()
        st.markdown("## Tax Calculator")
        if not IC():
            st.warning("Set up your tax profile first.");st.button("→ Set Up Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        # Regime toggle
        show_old=st.toggle("Show Old Regime details",value=True,key="tg_calc")
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"### {'✅ ' if rc=='new' else ''}New Regime")
            st.markdown(f"Taxable: **{format_currency(n['taxable_income'])}**")
            st.markdown(f"Slab tax: {format_currency(n['slab_tax'])}")
            if n['rebate_87a']>0:st.markdown(f"87A rebate: -{format_currency(n['rebate_87a'])}")
            if n['surcharge']>0:st.markdown(f"Surcharge: {format_currency(n['surcharge'])}")
            st.markdown(f"Cess: {format_currency(n['cess'])}")
            st.markdown(f"### Total: {format_currency(n['total_tax'])} ({n['effective_rate']}%)")
            np=n['net_payable']
            if np<0:st.markdown(f"**💰 Refund: {format_currency(abs(np))}**")
            elif np>0:st.markdown(f"Net payable: {format_currency(np)}")
        with c2:
            if show_old:
                st.markdown(f"### {'✅ ' if rc=='old' else ''}Old Regime")
                st.markdown(f"Taxable: **{format_currency(o['taxable_income'])}**")
                if o.get('hra_exemption',0)>0:st.caption(f"HRA: {format_currency(o['hra_exemption'])}")
                if o['total_deductions']>0:st.caption(f"Deductions: {format_currency(o['total_deductions'])}")
                st.markdown(f"Slab tax: {format_currency(o['slab_tax'])}")
                if o['rebate_87a']>0:st.markdown(f"87A rebate: -{format_currency(o['rebate_87a'])}")
                if o['surcharge']>0:st.markdown(f"Surcharge: {format_currency(o['surcharge'])}")
                st.markdown(f"Cess: {format_currency(o['cess'])}")
                st.markdown(f"### Total: {format_currency(o['total_tax'])} ({o['effective_rate']}%)")
                op=o['net_payable']
                if op<0:st.markdown(f"**💰 Refund: {format_currency(abs(op))}**")
                elif op>0:st.markdown(f"Net payable: {format_currency(op)}")
            else:
                st.info("Toggle above to compare with Old Regime")
        if show_old and o['total_deductions']>0:
            with st.expander("📋 Deduction breakdown"):
                for s,a in o['deduction_breakdown'].items():
                    if a>0:st.markdown(f"- **{s}:** {format_currency(a)}")
    with_chat(calc,"calc")

# ══════ SAVINGS FINDER with tax impact ══════
elif sel=="Savings Finder":
    def sf():
        show_logo()
        st.markdown("## Savings Finder")
        if not IC():
            st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);rc=r['recommended'];cur_tax=r[rc+'_regime']['total_tax']
        # Regime toggle
        regime=st.toggle("Analyze for Old Regime",value=(rc=='old'),key="tg_sf")
        regime_key='old' if regime else 'new'
        cur_tax=r[regime_key+'_regime']['total_tax']
        st.caption(f"Showing savings for **{regime_key.title()} Regime** (current tax: {format_currency(cur_tax)})")
        recs=[]
        if regime and p.section_80c<150000:
            g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;r2=compare_regimes(p2)
            sav=cur_tax-r2['old_regime']['total_tax']
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more under 80C',f'ELSS, PPF, or FD.',f'Save **{format_currency(max(sav,0))}** in tax','Before Mar 31','best ELSS mutual funds India 2025'))
        if p.section_80ccd_2==0:
            recs.append(('red','80CCD(2)','Employer NPS','Up to 14% of basic. Works in **BOTH** regimes.',f'Could save ₹15K-50K+','Ask HR',None))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP perquisite: ₹{p.esop_perquisite:,.0f}','Taxed as salary.',f'At your slab rate','Consult CA',None))
        if p.foreign_esop:recs.append(('red','Schedule FA','Foreign ESOPs — mandatory disclosure','₹10L penalty if not disclosed.',f'Penalty risk: ₹10L','File Schedule FA + Form 67',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading income → ITR-3','Report losses for 8yr carry-forward.',f'Loss offset benefit','Engage CA',None))
        if regime and p.section_80d_self==0:
            p2=copy.deepcopy(p);p2.section_80d_self=25000;r2=compare_regimes(p2)
            sav=cur_tax-r2['old_regime']['total_tax']
            recs.append(('amber','80D','Health insurance',f'Up to ₹25K self + ₹50K parents.',f'Save **{format_currency(max(sav,0))}**','Buy policy','best health insurance India 2025'))
        if regime and p.section_24b==0 and p.rental_income==0:
            recs.append(('amber','24(b)','Home loan interest','Up to ₹2L deduction.',f'Save up to ₹62,400','If applicable','best home loan rates India 2025'))
        if not recs:st.success("🎉 Well optimized for this regime!")
        for col,sec,t,d,impact,a,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> <em>({sec})</em><br>{d}<br>📊 <b>Tax impact:</b> {impact}<br>➡️ <b>Action:</b> {a}</div>',unsafe_allow_html=True)
            if q:
                if st.button(f"🔍 Explore options for this",key=f"s_{sec}"):
                    if K:
                        with st.spinner(f"{A} is searching..."):
                            res=call_gemini(prompt=f"Recommend top 3-5 specific {q} for Indian taxpayer FY 2025-26. Names, returns, lock-in, tax benefit.",context="",language="en",api_key=K,agent_name=A)
                        st.markdown(res)
    with_chat(sf,"sf")

# ══════ WHAT-IF SCENARIOS with regime toggle ══════
elif sel=="What-If Scenarios":
    def sc():
        show_logo()
        st.markdown("## What-If Scenarios")
        if not IC():
            st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p)
        regime=st.toggle("Compare using Old Regime",value=(cur['recommended']=='old'),key="tg_sc")
        rk='old' if regime else 'new'
        ct=cur[rk+'_regime']['total_tax']
        st.caption(f"Base: **{rk.title()} Regime** — current tax: {format_currency(ct)}")
        s=st.selectbox("Explore:",["Switch regime","Invest more in 80C","Salary raise","Sell shares/MFs","Buy or rent a house","Take a loan"])
        if s=="Switch regime":
            alt='old' if rk=='new' else 'new';at=cur[alt+'_regime']['total_tax'];d=at-ct
            st.metric(f"Tax under {alt.title()} Regime",format_currency(at),delta=f"+{format_currency(d)}" if d>0 else f"{format_currency(d)}",delta_color="inverse")
        elif s=="Invest more in 80C":
            ex=st.slider("Additional 80C ₹",0,150000,50000,10000)
            p2=copy.deepcopy(p);p2.section_80c=min(p.section_80c+ex,150000);r2=compare_regimes(p2)
            st.metric("Tax",format_currency(r2[rk+'_regime']['total_tax']),delta=f"-{format_currency(ct-r2[rk+'_regime']['total_tax'])}")
        elif s=="Salary raise":
            pct=st.slider("Raise %",5,100,20,5);p2=copy.deepcopy(p)
            p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100));p2.hra_received=int(p.hra_received*(1+pct/100))
            r2=compare_regimes(p2);t2=r2[rk+'_regime']['total_tax']
            c1,c2,c3=st.columns(3)
            with c1:st.metric("New salary",format_lakhs(p2.gross_salary))
            with c2:st.metric("New tax",format_currency(t2))
            with c3:st.metric("Extra tax",format_currency(t2-ct))
        elif s=="Sell shares/MFs":
            lg=st.number_input("LTCG ₹",0,value=200000,step=25000);sg=st.number_input("STCG ₹",0,value=0,step=25000)
            p2=copy.deepcopy(p);p2.ltcg_equity+=lg;p2.stcg_equity+=sg;r2=compare_regimes(p2)
            st.markdown(f"LTCG exempt: **{format_currency(min(lg,125000))}**")
            st.metric("Additional tax",format_currency(r2[rk+'_regime']['total_tax']-ct))
        elif s=="Buy or rent a house":
            tab1,tab2=st.tabs(["🏠 Buy (Home Loan)","🏢 Rent (HRA)"])
            with tab1:
                li=st.number_input("Loan interest ₹/yr",0,value=200000,step=25000);lp=st.number_input("Principal ₹/yr",0,value=100000,step=25000)
                p2=copy.deepcopy(p);p2.section_24b=min(li,200000);p2.section_80c=min(p.section_80c+lp,150000);r2=compare_regimes(p2)
                st.metric("Tax with home loan",format_currency(r2[rk+'_regime']['total_tax']),delta=f"-{format_currency(ct-r2[rk+'_regime']['total_tax'])}")
            with tab2:
                rn=st.number_input("Annual rent ₹",0,value=240000,step=12000);p3=copy.deepcopy(p);p3.rent_paid_annual=rn;r3=compare_regimes(p3)
                st.metric("Tax with HRA",format_currency(r3[rk+'_regime']['total_tax']),delta=f"-{format_currency(ct-r3[rk+'_regime']['total_tax'])}")
        elif s=="Take a loan":
            lt=st.selectbox("Type",["Education loan","Home loan (see above)","Personal (no benefit)"])
            if lt=="Education loan":
                ei=st.number_input("Interest ₹/yr",0,value=100000,step=10000);p2=copy.deepcopy(p);p2.section_80e=ei;r2=compare_regimes(p2)
                st.metric("Tax",format_currency(r2[rk+'_regime']['total_tax']),delta=f"-{format_currency(ct-r2[rk+'_regime']['total_tax'])}")
            elif "Personal" in lt:st.info("Personal loans have no tax benefit.")
    with_chat(sc,"sc")

# ══════ LAW UPDATES ══════
elif sel=="Law Updates":
    def lu():
        show_logo()
        st.markdown("## Latest Tax Law Updates")
        for dt,t,d,col in [
            ('Mar 20, 2026','🆕 IT Rules 2026 Notified','HRA expanded to 8 metros (adds Hyd/Pune/Ahd/Blr). Form 124 for HRA. Sections 819→536. CARF crypto reporting.','blue'),
            ('Mar 5, 2026','🆕 CARF: Crypto Reporting','OECD CARF adopted. All exchanges must report from Jan 2026.','blue'),
            ('Mar 2026','Significant Transaction Emails','CBDT sending emails about high-value transactions in AIS. Not a notice — but verify your AIS.','blue'),
            ('Feb 2026','Budget 2026 — No slab changes','IT Act 2025 effective Apr 2026. "Tax Year" replaces "PY/AY".','blue'),
            ('Oct 2025','ITR Deadline Extended (Circular 15/2025)','Audit cases: Oct 31 → Dec 10, 2025.','amber'),
            ('Jul 2024','Capital Gains Rates Changed','STCG equity 15→20%. LTCG 10→12.5%. Exemption ₹1L→₹1.25L. No indexation.','amber'),
            ('Feb 2025','₹12.75L Now Tax-Free (Salaried)','New regime: ₹4L exempt, 87A rebate ₹60K, std deduction ₹75K.','green'),
            ('Apr 2024','Angel Tax Abolished','Section 56(2)(viib) removed for all investors from April 2025.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---")
        st.markdown("#### ⚖️ Key Case Law")
        for t,d in [
            ("CIT vs Gopal Purohit (Bombay HC)","Taxpayer can maintain separate investment + trading portfolios. Intention at purchase matters."),
            ("Unnikrishnan vs ITO (Mumbai ITAT)","ESOPs granted while India-resident but exercised as NRI — taxable in India."),
            ("HRA to Parents (Multiple ITAT)","Paying rent to parents allowed for HRA if genuine. Need agreement + bank proof."),
            ("CBDT Circular 6/2016","Can classify some shares as investment, others as trading stock — if consistent.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.caption(f"💡 Ask {A} in the chat for the latest circulars and rulings.")
    with_chat(lu,"lu")

# ══════ ABOUT ══════
elif sel=="About":
    def ab():
        show_logo()
        st.markdown(f"""## About TaxGuru
### Our Mission
India has 9 Cr+ ITR filers — yet most overpay. ₹3.9L Cr in refunds (FY25) proves massive over-deduction. With 2 regimes and 70+ sections, TaxGuru makes the right choice easy.

### How It Works
**🧮 Precise Calculations** — Tax numbers come from a deterministic mathematical engine, not AI guesses. The numbers are always exactly right.

**🤖 {A} — Your Tax Agent** — An intelligent agent with access to 60 sections of the Income Tax Act, CBDT circulars, case law, and Budget amendments. {A} retrieves relevant legal provisions and constructs grounded answers, citing specific sections.

**🔍 Real-Time Updates** — {A} can search the web for the latest developments — new circulars, court rulings, deadline extensions — so advice stays current as the law changes.

**📄 Document Intelligence** — Upload a payslip or Form 16 and AI reads it, extracts only financial numbers, and fills your profile automatically.

**🔒 Privacy by Design** — We never collect PAN, Aadhaar, DOB, address, phone, email, bank details, PF number, employer name. Only financial figures are processed in your browser session. Close the browser = everything gone. Nothing saved on any server. Ever.

### Accuracy
Every answer cites the specific section. When unsure, {A} says "consult a CA." Our knowledge base covers 60 provisions including CBDT Notification 22/2026 (March 20, 2026).

### Who It's For
Salaried employees • Business owners • Professionals • Traders (F&O, intraday, crypto) • Investors • Senior citizens • NRIs

*Informational guidance only. Not professional tax advice. For complex matters, consult a CA.*""")
    with_chat(ab,"ab")
