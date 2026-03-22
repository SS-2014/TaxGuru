"""TaxGuru v8"""
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

# ══════ CSS: Dark theme, high contrast, bigger fonts ══════
st.markdown("""<style>
/* Hide Streamlit */
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],
button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
footer:after{content:'';visibility:hidden;display:block;}
.stApp>header{display:none!important;}

/* Dark base - HIGH CONTRAST */
.stApp,[data-testid="stAppViewContainer"]{background:#0B0F19!important;color:#F1F5F9;}
[data-testid="stVerticalBlock"]{gap:0.3rem!important;}
h1,h2,h3,h4{color:#F1F5F9!important;}
p,li,span,.stMarkdown{color:#E2E8F0;}
.stApp{margin-top:0;padding-top:0;}
[data-testid="stAppViewContainer"]>div:first-child{padding-top:0.2rem!important;}
.block-container{padding:0.3rem 1.2rem 0.5rem!important;max-width:100%!important;}

/* Nav pills */
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{
  background:#1E293B;border:1px solid #475569;border-radius:6px;padding:0.35rem 0.8rem;
  font-size:0.95rem;font-weight:600;color:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#334155;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){
  background:#D4A843!important;color:#000000!important;border-color:#D4A843!important;font-weight:700;}

/* Cards */
.cd{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin:0.3rem 0;font-size:1rem;color:#E2E8F0;}
.cd.green{border-left:3px solid #10B981;}.cd.amber{border-left:3px solid #F59E0B;}.cd.red{border-left:3px solid #EF4444;}.cd.blue{border-left:3px solid #3B82F6;}

/* Trust boxes - gold border, prominent */
.tg{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}
.tt{background:#1A1F2E;border:2px solid #D4A843;border-radius:10px;padding:0.9rem;}
.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1.15rem;}
.tt ul{list-style:none;padding:0;margin:0;}
.tt li{padding:0.15rem 0;font-size:1rem;color:#F1F5F9;line-height:1.5;}
.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}

/* Setup banner */
.su{background:#1C1917;border:2px solid #D4A843;border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 1rem;text-align:center;}
.su b{font-size:1.2rem;color:#FDE68A;}.su span{color:#E2E8F0;font-size:1rem;}

/* Logo */
.logo-area{padding:0.2rem 0 0.3rem;}
.logo-area img{height:140px;}

/* Hero text */
.ht h1{font-size:1.6rem!important;margin:0 0 0.2rem!important;line-height:1.3;}
.ht p{color:#E2E8F0;font-size:1rem;margin:0 0 0.3rem;}
.tags{display:flex;gap:0.3rem;flex-wrap:wrap;}
.tg2{padding:0.15rem 0.5rem;background:rgba(212,168,67,0.15);border:1px solid rgba(212,168,67,0.3);
  border-radius:4px;font-size:0.75rem;color:#D4A843;font-weight:600;}

/* Feature buttons with descriptions */
.fb{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin:0.2rem 0;}
.fb h4{color:#D4A843;margin:0 0 0.2rem;font-size:1.05rem;}
.fb p{color:#CBD5E1;font-size:0.9rem;margin:0;line-height:1.4;}

/* Chat */
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}
.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.82rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}

.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.88rem;color:#93C5FD;margin-bottom:0.5rem;}

/* ALL inputs dark */
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

/* BUTTONS: BLACK text on gold, always readable */
.stButton>button[kind="primary"]{background:#D4A843!important;color:#000000!important;border:none!important;font-weight:800!important;font-size:1rem!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:600!important;font-size:0.95rem!important;}

/* CHAT INPUT: white bg, black text, tall */
[data-testid="stChatInput"]{background:#FFFFFF!important;border:2px solid #475569;border-radius:8px;min-height:50px;}
[data-testid="stChatInput"] textarea{background:#FFFFFF!important;color:#000000!important;font-size:1rem!important;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000000!important;}

/* Slider */
.stSlider [data-testid="stThumbValue"]{color:#D4A843!important;}

@media(max-width:900px){.tg{grid-template-columns:1fr;}}
</style>""",unsafe_allow_html=True)

# ══════ Session State ══════
for k,v in {'profiles':{'Me':TaxpayerProfile()},'ap':'Me','pc':{},'ch':[],'pg':'Home'}.items():
    if k not in st.session_state:st.session_state[k]=v
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profiles[st.session_state.ap]
def IC():return st.session_state.pc.get(st.session_state.ap,False)
def go(p):st.session_state.pg=p

# ══════ Nav ══════
TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Law Updates","About"]
sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",
    index=TABS.index(st.session_state.pg) if st.session_state.pg in TABS else 0,key="nav")
st.session_state.pg=sel

# Profile bar (only when complete)
if sel not in ("Home","Law Updates","About") and IC():
    c1,c2=st.columns([4,1])
    with c2:
        ns=list(st.session_state.profiles.keys())
        if len(ns)<5:ns.append("➕ Add")
        ch=st.selectbox("",ns,index=ns.index(st.session_state.ap) if st.session_state.ap in ns else 0,label_visibility="collapsed")
        if ch=="➕ Add":
            nn=f"Profile {len(st.session_state.profiles)+1}"
            st.session_state.profiles[nn]=TaxpayerProfile()
            st.session_state.ap=nn
            st.rerun()
        else:st.session_state.ap=ch
    with c1:
        r=compare_regimes(P());b=r[r['recommended']+'_regime']
        st.markdown(f"**{st.session_state.ap}** — Tax: **{format_lakhs(b['total_tax'])}** | {b['effective_rate']}% | {'New' if r['recommended']=='new' else 'Old'} Regime ✅")

# ══════ Chat widget ══════
def chat(k=""):
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A} — Your Tax Agent</span><br><span class="rl">Ask me anything about your tax needs</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=400)
    with bx:
        if not st.session_state.ch:
            st.markdown(f"👋 **Hi, I'm {A}!** Ask me anything about Indian income tax — which regime to pick, how ESOPs are taxed, trading rules, capital gains, deductions. I cite the exact law and never guess.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):
                st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A} anything...",key=f"c{k}"):
        cl,n=anonymize_text(pr)
        st.session_state.ch.append({'role':'user','content':pr})
        if not K:
            rsp=f"⚠️ API key not set. Admin: add GEMINI_API_KEY in Settings → Secrets."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {}
            rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,agent_name=A)
        st.session_state.ch.append({'role':'assistant','content':rsp})
        st.rerun()
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the Income Tax Act, latest circulars, and case law. For important decisions or complex cases, consult a professional tax advisor or CA.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat(k)

# ══════════════════════════════════
# HOME
# ══════════════════════════════════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        if LOGO:
            st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
        st.markdown(f'<div class="ht"><h1>Stop overpaying your taxes.</h1><p>AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p><div class="tags"><span class="tg2">Always Accurate</span><span class="tg2">Private</span><span class="tg2">Latest Updates</span><span class="tg2">Chat in Indian Languages</span></div></div>',unsafe_allow_html=True)

        st.markdown(f'<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter details. Create up to 5 profiles.</span></div>',unsafe_allow_html=True)

        bc1,bc2=st.columns(2)
        with bc1:
            if st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary"):
                go("Tax Profile")
                st.rerun()
        with bc2:
            if st.button("✏️ Enter Manually",use_container_width=True):
                go("Tax Profile")
                st.rerun()

        # 3 feature buttons with descriptions
        fc1,fc2,fc3=st.columns(3)
        with fc1:
            st.markdown('<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New regime — see exact savings in rupees. Know which regime is better for you.</p></div>',unsafe_allow_html=True)
            if st.button("Open Tax Calculator →",use_container_width=True,key="h1"):
                go("Tax Calculator")
                st.rerun()
        with fc2:
            st.markdown('<div class="fb"><h4>🔀 What-If Scenarios</h4><p>Getting a raise? Taking a home loan? Selling shares? See how it changes your tax.</p></div>',unsafe_allow_html=True)
            if st.button("Open Scenarios →",use_container_width=True,key="h4"):
                go("What-If Scenarios")
                st.rerun()
        with fc3:
            st.markdown('<div class="fb"><h4>💡 Savings Finder</h4><p>Specific recommendations — what to invest, how much, by when. With tax impact.</p></div>',unsafe_allow_html=True)
            if st.button("Open Savings Finder →",use_container_width=True,key="h3"):
                go("Savings Finder")
                st.rerun()

        st.markdown(f"""<div class="tg">
<div class="tt"><h4>🛡️ Always Accurate</h4><ul>
<li>Tax numbers from a precise calculation engine — not AI guesses</li>
<li>Every answer cites the actual Income Tax Act section</li>
<li>When unsure, {A} says "check with a CA" — never makes things up</li>
<li>Updated real-time with Budget 2026 changes, circulars, court judgements</li></ul></div>
<div class="tt"><h4>🔒 Your Data Stays Private</h4><ul>
<li>We never see your PAN, Aadhaar, address, DOB, phone, or email</li>
<li>Bank accounts, PF/UAN, employer name — all auto-deleted</li>
<li>Only salary/deduction numbers used — in your browser session only</li>
<li>Close the browser → everything gone. Nothing saved. Ever.</li></ul></div>
</div>""",unsafe_allow_html=True)
    with c2:
        chat("home")

# ══════════════════════════════════
# TAX PROFILE
# ══════════════════════════════════
elif sel=="Tax Profile":
    def tp():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown("## Tax Profile")

        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only financial numbers extracted. Personal details auto-ignored.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"🔍 {A} is reading your document..."):
                doc=analyze_document(up.read(),K,up.type or "image/jpeg")
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
                if st.button("✅ Use This Data",type="primary",use_container_width=True):
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary')
                    p.basic_salary=gv('basic_salary',p.gross_salary*0.4);p.hra_received=gv('hra')
                    p.tds_deducted=gv('tds_deducted')
                    p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    st.session_state.pc[st.session_state.ap]=True
                    go("Tax Calculator")
                    st.rerun()
            else:st.error("Couldn't read document. Try manual entry.")
        elif up:st.error("API key not configured.")

        st.markdown("---")
        st.markdown("#### ✏️ Manual Entry")

        c1,c2=st.columns(2)
        with c1:
            # MULTISELECT: can be salaried + trader etc.
            types=st.multiselect("I earn income from... (select all that apply)",
                ["Salary","Business","Professional services","Trading (stocks, F&O, crypto)","Investments","Freelancing","Other"],
                default=["Salary"],help="You can select multiple. For example: Salary + Trading.")
            other_type=""
            if "Other" in types:
                other_type=st.text_input("Specify other income type")
            age=st.number_input("Age",18,100,30)

        with c2:
            # RESIDENCY AUTO-CALC
            st.markdown("**Residency status** (we'll figure this out for you)")
            citizenship=st.selectbox("Citizenship",["Indian citizen","Person of Indian origin","Foreign citizen"])
            days_india=st.number_input("Days spent in India this financial year",0,366,365,help="Count from April 1 to March 31")
            days_4yr=st.number_input("Total days in India in the last 4 years",0,1461,1400,help="Approximate is fine")
            india_income_over_15l=st.checkbox("My Indian income exceeds ₹15 lakh",help="Income from Indian sources (excluding foreign income)")

            # Auto-calculate residency
            if days_india>=182:
                res_status="resident"
                res_display="✅ **Resident** — You were in India for 182+ days"
            elif citizenship in ["Indian citizen","Person of Indian origin"]:
                if india_income_over_15l and days_india>=120 and days_4yr>=365:
                    res_status="rnor"
                    res_display="⚠️ **RNOR** — 120+ days with >₹15L Indian income"
                elif days_india>=60 and days_4yr>=365 and not india_income_over_15l:
                    res_status="resident"
                    res_display="✅ **Resident** — 60+ days this year + 365+ in last 4 years"
                else:
                    res_status="nri"
                    res_display="🌍 **Non-Resident (NRI)** — Less than 182 days in India"
            else:
                if days_india>=60 and days_4yr>=365:
                    res_status="resident"
                    res_display="✅ **Resident**"
                else:
                    res_status="nri"
                    res_display="🌍 **Non-Resident**"
            st.markdown(res_display)

            met=st.selectbox("Metro city? (50% HRA)",["Yes — Del/Mum/Kol/Che/Hyd/Pune/Ahd/Blr","No — Other cities"],
                help="From April 2026: 8 cities qualify for 50% HRA.")

        # Map types to primary type
        t="salaried"
        if "Business" in types:t="business"
        if "Professional services" in types:t="professional"
        if "Trading (stocks, F&O, crypto)" in types:t="trader"
        if "Salary" in types:t="salaried"  # Default if salary selected

        gs=bs=hra=rent=enps=biz=trd=ii=ri=di=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False

        st.markdown("**💰 Income Details**")
        if "Salary" in types:
            c1,c2,c3=st.columns(3)
            with c1:gs=st.number_input("Gross Salary ₹/yr",0,value=0,step=50000,format="%d")
            with c2:bs=st.number_input("Basic ₹/yr",0,value=0,step=25000,format="%d",help="~40% of gross")
            with c3:hra=st.number_input("HRA ₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:rent=st.number_input("Rent Paid ₹/yr",0,value=0,step=10000,format="%d")
            with c2:enps=st.number_input("Employer NPS ₹/yr",0,value=0,step=5000,format="%d",help="Saves tax in BOTH regimes")

        if any(x in types for x in ["Business","Professional services","Freelancing"]):
            c1,c2=st.columns(2)
            with c1:biz=st.number_input("Business/Professional Income ₹/yr",0,value=0,step=100000,format="%d")
            with c2:
                if "Salary" not in types:
                    gs=st.number_input("Any salary income ₹/yr",0,value=0,step=50000,format="%d")

        if "Trading (stocks, F&O, crypto)" in types:
            c1,c2=st.columns(2)
            with c1:trd=st.number_input("Trading Profit/(Loss) ₹",value=0,step=50000,format="%d",help="F&O, intraday, crypto. Negative for losses.")
            with c2:
                if "Salary" not in types and biz==0:
                    gs=st.number_input("Any salary income ₹/yr",0,value=0,step=50000,format="%d",key="gs2")

        with st.expander("📈 Investment income, capital gains, ESOPs"):
            c1,c2,c3=st.columns(3)
            with c1:ii=st.number_input("Interest ₹/yr",0,value=0,step=5000,format="%d")
            with c2:ri=st.number_input("Rental ₹/yr",0,value=0,step=10000,format="%d")
            with c3:di=st.number_input("Dividend ₹/yr",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("Short-term capital gains ₹",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("Long-term capital gains ₹",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite value ₹",0,value=0,step=50000,format="%d")
            fe=st.checkbox("Foreign company ESOPs (requires Schedule FA disclosure)")

        with st.expander("🏦 Deductions — for Old Regime comparison"):
            c1,c2,c3=st.columns(3)
            with c1:s80c=st.number_input("80C (EPF/PPF/ELSS/LIC) ₹",0,150000,0,step=10000,format="%d")
            with c2:s80d=st.number_input("80D Health Insurance ₹",0,50000,0,step=5000,format="%d")
            with c3:s80n=st.number_input("80CCD(1B) NPS Extra ₹",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:s80e=st.number_input("80E Education Loan Interest ₹",0,value=0,step=10000,format="%d")
            with c2:s24b=st.number_input("24(b) Home Loan Interest ₹",0,200000,0,step=10000,format="%d")

        with st.expander("💳 TDS and advance tax already paid"):
            c1,c2=st.columns(2)
            with c1:tds=st.number_input("TDS deducted ₹",0,value=0,step=10000,format="%d")
            with c2:adv=st.number_input("Advance tax paid ₹",0,value=0,step=10000,format="%d")

        if st.button("✅ Save & See My Tax",type="primary",use_container_width=True):
            p=P();p.taxpayer_type=t;p.age=age;p.residency=res_status;p.metro_city="Yes" in met
            p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent
            p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd
            p.interest_income=ii;p.rental_income=ri;p.dividend_income=di
            p.stcg_equity=stcg;p.ltcg_equity=ltcg;p.esop_perquisite=esop;p.foreign_esop=fe
            p.section_80c=s80c;p.section_80d_self=s80d;p.section_80d_parents=0
            p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b
            p.tds_deducted=tds;p.advance_tax_paid=adv
            st.session_state.pc[st.session_state.ap]=True
            go("Tax Calculator")
            st.rerun()
    with_chat(tp,"tp")

# ══════════════════════════════════
# TAX CALCULATOR
# ══════════════════════════════════
elif sel=="Tax Calculator":
    def calc():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown("## Tax Calculator — Old vs New Regime")
        if not IC():
            st.warning("Set up your tax profile first to see calculations.")
            if st.button("→ Set Up Tax Profile",type="primary"):
                go("Tax Profile")
                st.rerun()
            return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"### {'✅ ' if rc=='new' else ''}New Regime")
            st.markdown(f"Taxable income: **{format_currency(n['taxable_income'])}**")
            st.markdown(f"Tax on slabs: {format_currency(n['slab_tax'])}")
            if n['rebate_87a']>0:st.markdown(f"Section 87A rebate: -{format_currency(n['rebate_87a'])}")
            st.markdown(f"Health & education cess (4%): {format_currency(n['cess'])}")
            st.markdown(f"### Total tax: {format_currency(n['total_tax'])}")
            st.markdown(f"Effective rate: **{n['effective_rate']}%**")
            if n['net_payable']>=0:st.markdown(f"Net payable: {format_currency(n['net_payable'])}")
            else:st.markdown(f"**Refund due: {format_currency(abs(n['net_payable']))}**")
        with c2:
            st.markdown(f"### {'✅ ' if rc=='old' else ''}Old Regime")
            st.markdown(f"Taxable income: **{format_currency(o['taxable_income'])}**")
            if o.get('hra_exemption',0)>0:st.caption(f"HRA exemption: {format_currency(o['hra_exemption'])}")
            if o['total_deductions']>0:st.caption(f"Chapter VI-A deductions: {format_currency(o['total_deductions'])}")
            st.markdown(f"Tax on slabs: {format_currency(o['slab_tax'])}")
            if o['rebate_87a']>0:st.markdown(f"Section 87A rebate: -{format_currency(o['rebate_87a'])}")
            st.markdown(f"Health & education cess (4%): {format_currency(o['cess'])}")
            st.markdown(f"### Total tax: {format_currency(o['total_tax'])}")
            st.markdown(f"Effective rate: **{o['effective_rate']}%**")
            if o['net_payable']>=0:st.markdown(f"Net payable: {format_currency(o['net_payable'])}")
            else:st.markdown(f"**Refund due: {format_currency(abs(o['net_payable']))}**")
        if o['total_deductions']>0:
            with st.expander("📋 Deduction breakdown (Old Regime)"):
                for s,a in o['deduction_breakdown'].items():
                    if a>0:st.markdown(f"- **Section {s}:** {format_currency(a)}")
    with_chat(calc,"calc")

# ══════════════════════════════════
# SAVINGS FINDER
# ══════════════════════════════════
elif sel=="Savings Finder":
    def sf():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown("## Savings Finder")
        if not IC():
            st.warning("Set up your tax profile first.")
            if st.button("→ Set Up Tax Profile",type="primary"):go("Tax Profile");st.rerun()
            return
        p=P();r=compare_regimes(p);rc=r['recommended'];cur_tax=r[rc+'_regime']['total_tax']
        recs=[]
        if rc=='old' and p.section_80c<150000:
            g=150000-p.section_80c;s=g*0.30 if p.gross_salary>1e6 else g*0.20
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more under Section 80C',f'ELSS mutual funds, PPF, or tax-saver FDs. Potential saving: **~₹{s:,.0f}**',f'Effective rate drops to ~{max(0,cur_tax-s)/max(p.gross_salary,1)*100:.1f}%','Before March 31','best ELSS mutual funds India 2025 tax saving'))
        if p.section_80ccd_2==0:
            recs.append(('red','80CCD(2)','Ask your employer about NPS contribution','Employer NPS (up to 14% of basic salary) is deductible in **BOTH** old and new regimes. This is the single most powerful tax-saving tool under the new regime.','Could save ₹15,000-50,000+',
                'Ask your HR/payroll team',None))
        if p.esop_perquisite>0:
            recs.append(('amber','17(2)(vi)',f'ESOP perquisite: ₹{p.esop_perquisite:,.0f}','This is taxed as salary income. Consider timing your exercise carefully — if at a DPIIT startup, you may defer tax up to 48 months.','Taxed at your slab rate','Consult a CA before exercising',None))
        if p.foreign_esop:
            recs.append(('red','Schedule FA','Foreign ESOP disclosure is **mandatory**','Must report in Schedule FA of your ITR. Non-disclosure penalty: ₹10 lakh under Black Money Act. Also need Form 67 for Foreign Tax Credit.','Penalty risk: ₹10L','File immediately',None))
        if p.trading_income!=0:
            recs.append(('red','43(5)','Trading income must be reported in ITR-3','Even losses must be filed — they can be carried forward for 8 years against future business income (not salary). Audit required if turnover exceeds ₹10 Cr.','Loss carry-forward benefit','Engage a CA for ITR-3',None))
        if rc=='old' and p.section_80d_self==0:
            recs.append(('amber','80D','Get health insurance for tax benefit','Self/family: up to ₹25K (₹50K if senior). Parents: additional ₹25-50K. Maximum: ₹1 lakh total deduction.','Save ₹5,200 to ₹31,200 in tax','Buy a health policy','best health insurance India 2025 tax saving'))
        if rc=='old' and p.section_24b==0 and p.rental_income==0:
            recs.append(('amber','24(b)','Home loan interest deduction','Up to ₹2 lakh deduction on self-occupied property under Old Regime.','Save up to ₹62,400 in tax','If applicable','best home loan rates India 2025'))
        if not recs:
            st.success("🎉 Your tax is well-optimized! We couldn't find additional savings based on your current profile.")
        for col,sec,t,d,impact,a,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> <em>(Section {sec})</em><br>{d}<br>📊 <b>Impact:</b> {impact}<br>➡️ <b>Action:</b> {a}</div>',unsafe_allow_html=True)
            if q:
                if st.button(f"🔍 Want to explore specific options for this?",key=f"s_{sec}"):
                    if K:
                        with st.spinner(f"{A} is searching for options..."):
                            res=call_gemini(prompt=f"I'm an Indian taxpayer for FY 2025-26. Recommend top 3-5 specific {q}. Include: product name, expected return, lock-in period, tax benefit amount. Only products available in India.",
                                context="",language="en",api_key=K,agent_name=A)
                        st.markdown(res)
    with_chat(sf,"sf")

# ══════════════════════════════════
# WHAT-IF SCENARIOS
# ══════════════════════════════════
elif sel=="What-If Scenarios":
    def sc():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown("## What-If Scenarios")
        if not IC():
            st.warning("Set up your tax profile first.")
            if st.button("→ Set Up Tax Profile",type="primary"):go("Tax Profile");st.rerun()
            return
        p=P();cur=compare_regimes(p);ct=cur[cur['recommended']+'_regime']['total_tax']

        s=st.selectbox("What do you want to explore?",
            ["Switch tax regime","Invest more in 80C","Get a salary raise","Sell shares or mutual funds",
             "Buy or rent a house","Take a loan"])

        if s=="Switch tax regime":
            alt='old' if cur['recommended']=='new' else 'new'
            at=cur[alt+'_regime']['total_tax'];d=at-ct
            st.metric(f"Tax under {'Old' if alt=='old' else 'New'} Regime",format_currency(at),
                delta=f"+{format_currency(d)} more" if d>0 else f"{format_currency(d)} saved",delta_color="inverse")
            if d>0:st.info(f"Stick with **{cur['recommended'].title()} Regime** — switching would cost you more.")
            else:st.success(f"Consider switching to **{alt.title()} Regime** to save {format_currency(abs(d))}.")

        elif s=="Invest more in 80C":
            ex=st.slider("Additional 80C investment ₹",0,150000,50000,step=10000)
            p2=copy.deepcopy(p);p2.section_80c=min(p.section_80c+ex,150000)
            r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
            st.metric("Your tax with extra 80C",format_currency(t2),
                delta=f"-{format_currency(ct-t2)} saved" if ct>t2 else "No change")
            if ct>t2:st.info(f"Options: ELSS (3yr lock-in, equity), PPF (15yr, guaranteed), Tax Saver FD (5yr).")

        elif s=="Get a salary raise":
            pct=st.slider("Expected raise %",5,100,20,step=5)
            p2=copy.deepcopy(p);p2.gross_salary=int(p.gross_salary*(1+pct/100))
            p2.basic_salary=int(p.basic_salary*(1+pct/100));p2.hra_received=int(p.hra_received*(1+pct/100))
            r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
            c1,c2,c3=st.columns(3)
            with c1:st.metric("New salary",format_lakhs(p2.gross_salary))
            with c2:st.metric("New tax",format_currency(t2))
            with c3:st.metric("Extra tax",format_currency(t2-ct))

        elif s=="Sell shares or mutual funds":
            lg=st.number_input("Expected long-term capital gain ₹",0,value=200000,step=25000)
            sg=st.number_input("Expected short-term capital gain ₹",0,value=0,step=25000)
            p2=copy.deepcopy(p);p2.ltcg_equity+=lg;p2.stcg_equity+=sg
            r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
            st.markdown(f"LTCG exempt (first ₹1.25L): **{format_currency(min(lg,125000))}**")
            st.metric("Additional tax from sale",format_currency(t2-ct))

        elif s=="Buy or rent a house":
            tab1,tab2=st.tabs(["🏠 Buy (Home Loan)","🏢 Rent (HRA Claim)"])
            with tab1:
                li=st.number_input("Home loan interest ₹/yr",0,value=200000,step=25000)
                lp=st.number_input("Principal repayment ₹/yr",0,value=100000,step=25000)
                p2=copy.deepcopy(p);p2.section_24b=min(li,200000);p2.section_80c=min(p.section_80c+lp,150000)
                r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
                st.metric("Tax with home loan",format_currency(t2),
                    delta=f"-{format_currency(ct-t2)} saved" if ct>t2 else "No change")
                st.caption("Section 24(b): interest up to ₹2L. Section 80C: principal. Old Regime only.")
            with tab2:
                rn=st.number_input("Annual rent you'd pay ₹",0,value=240000,step=12000)
                p3=copy.deepcopy(p);p3.rent_paid_annual=rn
                r3=compare_regimes(p3);t3=r3[r3['recommended']+'_regime']['total_tax']
                st.metric("Tax with HRA claim",format_currency(t3),
                    delta=f"-{format_currency(ct-t3)} saved" if ct>t3 else "No change")
                st.caption("HRA exemption under Section 10(13A). Old Regime only. Requires rent receipts.")

        elif s=="Take a loan":
            lt=st.selectbox("Loan type",["Education loan","Home loan (see Buy a House above)","Personal loan (no tax benefit)"])
            if lt=="Education loan":
                ei=st.number_input("Annual education loan interest ₹",0,value=100000,step=10000)
                p2=copy.deepcopy(p);p2.section_80e=ei
                r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
                st.metric("Tax with education loan",format_currency(t2),
                    delta=f"-{format_currency(ct-t2)} saved" if ct>t2 else "No change")
                st.caption("Section 80E: **full interest deductible** (no upper limit) for 8 years. Old Regime only.")
            elif "Personal" in lt:
                st.info("Personal loans do not offer any income tax deduction in India.")
    with_chat(sc,"sc")

# ══════════════════════════════════
# LAW UPDATES (no search box, more content)
# ══════════════════════════════════
elif sel=="Law Updates":
    def lu():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown("## Latest Tax Law Updates")
        updates=[
            ('Mar 20, 2026','🆕 Income Tax Rules 2026 Notified by CBDT','HRA expanded to 8 metro cities (adding Hyderabad, Pune, Ahmedabad, Bengaluru). New Form 124 for HRA claims — must disclose landlord relationship if rent > ₹1L. Sections reduced from 819 to 536. CARF for crypto reporting now mandatory.','blue'),
            ('Mar 5, 2026','🆕 Crypto Asset Reporting Framework (CARF)','India adopts OECD CARF. All crypto exchanges and custodians must report transactions to tax authorities from January 2026. Self-certification required from account holders.','blue'),
            ('Mar 2026','Significant Transaction Emails from IT Department','CBDT sending emails about high-value transactions detected in AIS. Not a notice — but ignoring may trigger scrutiny. Verify your AIS on the e-filing portal.','blue'),
            ('Feb 2026','Union Budget 2026 — No slab changes','Income Tax Act 2025 effective April 2026. New terminology: "Tax Year" replaces "Previous Year/Assessment Year". No rate changes.','blue'),
            ('Oct 2025','ITR Filing Deadline Extended (CBDT Circular 15/2025)','Audit cases: deadline extended from Oct 31 to Dec 10, 2025. Audit report deadline: Nov 10, 2025.','amber'),
            ('Jul 2024','Capital Gains Tax Rates Changed','STCG on equity: 15% → 20%. LTCG on equity: 10% → 12.5%. LTCG exemption: ₹1L → ₹1.25L. Indexation benefit removed for all asset classes.','amber'),
            ('Feb 2025','Income Up to ₹12.75L Now Tax-Free (Salaried)','New regime: basic exemption ₹4L, Section 87A rebate ₹60K. With standard deduction of ₹75K, salaried individuals earning up to ₹12.75L pay zero tax.','green'),
            ('Apr 2024','Angel Tax Abolished','Section 56(2)(viib) — angel tax removed for ALL investors (resident and non-resident) from April 2025. Companies can raise capital at any premium.','green'),
        ]
        for dt,t,d,col in updates:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### Key Case Law & Rulings")
        cases=[
            ("CIT vs Gopal Purohit (Bombay HC)","A taxpayer can maintain two portfolios — one for investment (capital gains) and one for trading (business income). Taxpayer's intention at time of purchase matters."),
            ("Unnikrishnan vs ITO (Mumbai ITAT)","ESOPs granted while India resident but exercised as NRI — held taxable in India. Perquisite accrues during employment period, not exercise date."),
            ("HRA to Parents (Multiple ITAT)","Paying rent to parents is allowed for HRA exemption if genuinely paid and included in parents' income. Rent agreement + bank transfer proof required."),
            ("CBDT Circular 6/2016","Taxpayer can classify some shares as investment and others as trading stock — provided this is followed consistently year over year."),
        ]
        for title,desc in cases:
            st.markdown(f'<div class="cd blue"><b>⚖️ {title}</b><br>{desc}</div>',unsafe_allow_html=True)

        st.caption(f"💡 For the latest updates, ask {A} in the chat — {A} can search for recent circulars and rulings.")
    with_chat(lu,"lu")

# ══════════════════════════════════
# ABOUT
# ══════════════════════════════════
elif sel=="About":
    def ab():
        if LOGO:st.markdown(f'<div class="logo-area"><img src="data:image/png;base64,{LOGO}" style="height:60px"></div>',unsafe_allow_html=True)
        st.markdown(f"""## About TaxGuru

### Our Mission
India has over 9 crore income tax return filers — yet most don't optimize their taxes. The government issued ₹3.9 lakh crore in refunds in FY25 alone, showing that millions of taxpayers overpay through excess TDS and wrong regime choices. With 2 tax regimes and 70+ deduction sections, making the right choice is genuinely hard.

**TaxGuru exists to change this.** We believe every Indian taxpayer — whether a salaried employee, a small business owner, a freelancer, or an investor — deserves access to accurate, personalized tax advice without paying thousands for a CA consultation.

### How It Works
TaxGuru combines several AI and technology approaches to deliver accurate, real-time tax advice:

**🧮 Precise Calculation Engine** — Your tax numbers are computed by a deterministic mathematical engine, not generated by AI. This means the numbers are always exactly right — no rounding, no estimation, no hallucination.

**🤖 Intelligent Tax Agent ({A})** — {A} is an AI agent trained specifically on Indian income tax law. {A} has access to 60 sections of the Income Tax Act, key CBDT circulars, case law precedents, and Budget amendments. When you ask a question, {A} retrieves the most relevant legal provisions and constructs an answer grounded in actual law — citing specific sections.

**🔍 Real-Time Updates** — {A} can search the web for the latest tax developments — new circulars, court rulings, deadline extensions. This means the advice stays current even as the law changes.

**📄 Document Intelligence** — Upload a payslip or Form 16 and our AI reads it, extracts the financial numbers (ignoring all personal information), and fills in your tax profile automatically.

**🔒 Privacy by Design** — We never collect, store, or transmit your name, PAN, Aadhaar, date of birth, address, phone number, email, bank account details, PF number, employer name, or employee ID. Only financial figures (salary, deductions, investments) are processed — and only within your browser session. Close the browser and everything is gone. Nothing is saved on any server. Ever.

### Accuracy Commitment
- Every answer cites the specific section of the Income Tax Act
- When {A} is not sure about something, {A} tells you to consult a Chartered Accountant — rather than guess
- Our knowledge base covers 60 provisions including the latest CBDT Notification 22/2026 (March 20, 2026) and IT Rules 2026
- Tax calculations are verified against government guidelines and major tax platforms

### Who It's For
TaxGuru serves all types of Indian taxpayers:
- **Salaried employees** — regime comparison, HRA optimization, payslip analysis
- **Business owners** — presumptive taxation, audit requirements, expense deductions
- **Professionals** — Section 44ADA, professional tax, advance tax planning
- **Traders** — F&O/intraday classification, Section 43(5), ITR-3 requirements, loss carry-forward
- **Investors** — capital gains (equity, debt, property), ESOP taxation (domestic and foreign)
- **Senior citizens** — higher exemptions, 80TTB, TDS thresholds, pension taxation
- **NRIs** — residency determination, DTAA, foreign tax credit, Schedule FA

*TaxGuru provides informational guidance based on Indian tax law. This is not professional tax advice. For complex matters, always consult a qualified Chartered Accountant.*""")
    with_chat(ab,"ab")
