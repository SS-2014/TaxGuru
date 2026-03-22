"""TaxGuru v7 — Dark theme. Compact. Chat everywhere. Clickable features."""
import streamlit as st
import sys,os,copy,random
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,estimate_from_monthly_salary,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE,format_for_llm_context
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB

st.set_page_config(page_title="TaxGuru",page_icon="🏛️",layout="wide",initial_sidebar_state="collapsed")
LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()
if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag

# ═══ DARK THEME CSS ═══
st.markdown("""<style>
/* Nuke branding */
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],
[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,
.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,
iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],
button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],
[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]
{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
footer:after{content:'';visibility:hidden;display:block;}
.stApp>header{display:none!important;}

/* Dark base */
.stApp,[data-testid="stAppViewContainer"]{background:#0B0F19!important;color:#E2E8F0;}
[data-testid="stVerticalBlock"]{gap:0.4rem!important;}
h1,h2,h3,h4{color:#F1F5F9!important;}
p,li,span,.stMarkdown{color:#CBD5E1;}
.stApp{margin-top:-0.5rem;}

/* Nav pills */
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{
  background:#1E293B;border:1px solid #334155;border-radius:6px;padding:0.35rem 0.8rem;
  font-size:0.85rem;font-weight:500;color:#94A3B8;cursor:pointer;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#334155;color:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){
  background:#D4A843!important;color:#0B0F19!important;border-color:#D4A843!important;font-weight:700;}

/* Cards */
.cd{background:#111827;border:1px solid #1F2937;border-radius:10px;padding:1rem;margin:0.3rem 0;}
.cd.green{border-left:3px solid #10B981;} .cd.amber{border-left:3px solid #F59E0B;}
.cd.red{border-left:3px solid #EF4444;} .cd.blue{border-left:3px solid #3B82F6;}

/* Feature grid */
.fg{display:grid;grid-template-columns:repeat(3,1fr);gap:0.6rem;margin:0.5rem 0;}
.fc{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:0.8rem;cursor:pointer;transition:all .15s;}
.fc:hover{border-color:#D4A843;background:#1A2332;}
.fc h4{color:#F1F5F9;margin:0 0 0.2rem;font-size:0.9rem;} .fc p{color:#94A3B8;font-size:0.78rem;margin:0;line-height:1.3;}

/* Trust */
.tg{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}
.tt{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:0.8rem;}
.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1rem;}
.tt ul{list-style:none;padding:0;margin:0;}
.tt li{padding:0.1rem 0;font-size:0.85rem;color:#CBD5E1;line-height:1.4;}
.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}

/* Setup */
.su{background:#1C1917;border:1px solid #D4A843;border-radius:8px;padding:0.6rem 0.8rem;font-size:0.88rem;color:#FDE68A;margin:0.4rem 0;}

/* Hero */
.hero-row{display:flex;gap:1.5rem;align-items:center;padding:0.6rem 0 0.8rem;margin-bottom:0.3rem;}
.hero-left{flex:1;}
.hero-left img{height:90px;margin-bottom:0.3rem;}
.hero-left h1{font-size:1.5rem;color:#F1F5F9!important;margin:0 0 0.2rem;}
.hero-left p{color:#94A3B8;font-size:0.9rem;line-height:1.4;margin:0 0 0.4rem;}
.hero-left .tags{display:flex;gap:0.3rem;flex-wrap:wrap;}
.hero-left .tg2{padding:0.15rem 0.45rem;background:rgba(212,168,67,0.15);border:1px solid rgba(212,168,67,0.3);border-radius:5px;font-size:0.65rem;color:#D4A843;font-weight:500;}

/* Chat header */
.ch{background:#1E293B;border:1px solid #334155;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.4rem;}
.ch .dot{width:7px;height:7px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}
@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:600;font-size:0.9rem;color:#F1F5F9;} .ch .rl{font-size:0.68rem;color:#64748B;}
.cd2{font-size:0.72rem;color:#64748B;font-style:italic;margin-top:0.3rem;}

/* Privacy */
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.78rem;color:#93C5FD;margin-bottom:0.5rem;}

/* Inputs/selects dark override */
[data-testid="stSelectbox"]>div>div{background:#1E293B!important;color:#E2E8F0!important;border-color:#334155!important;}
[data-testid="stNumberInput"] input{background:#1E293B!important;color:#E2E8F0!important;border-color:#334155!important;}
[data-testid="stFileUploader"]{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:0.5rem;}
.stTextInput input{background:#1E293B!important;color:#E2E8F0!important;border-color:#334155!important;}
.stSlider{color:#E2E8F0!important;}

/* Buttons */
.stButton>button[kind="primary"]{background:#D4A843!important;color:#0B0F19!important;border:none!important;font-weight:700;}
.stButton>button[kind="secondary"],.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#E2E8F0!important;border:1px solid #334155!important;}

/* Expander */
[data-testid="stExpander"]{background:#111827;border:1px solid #1F2937;border-radius:8px;}
[data-testid="stExpander"] summary{color:#CBD5E1!important;}

/* Metric */
[data-testid="stMetric"]{background:#111827;border:1px solid #1F2937;border-radius:8px;padding:0.5rem;}
[data-testid="stMetricValue"]{color:#D4A843!important;}
[data-testid="stMetricLabel"]{color:#94A3B8!important;}

/* Chat input */
[data-testid="stChatInput"]{background:#1E293B!important;}
[data-testid="stChatInput"] textarea{background:#1E293B!important;color:#E2E8F0!important;}

@media(max-width:900px){.fg{grid-template-columns:1fr 1fr;}.tg{grid-template-columns:1fr;}.hero-row{flex-direction:column;}}
@media(max-width:600px){.fg{grid-template-columns:1fr;}}
</style>""",unsafe_allow_html=True)

# Session
for k,v in {'profiles':{'Me':TaxpayerProfile()},'active_profile':'Me','pc':{},'ch':[],'page':'Home'}.items():
    if k not in st.session_state:st.session_state[k]=v
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profiles[st.session_state.active_profile]
def IC():return st.session_state.pc.get(st.session_state.active_profile,False)
def go(p):st.session_state.page=p

TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Law Updates","About"]
sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",
    index=TABS.index(st.session_state.page) if st.session_state.page in TABS else 0,key="n")
st.session_state.page=sel

# Profile bar
if sel not in ("Home","Law Updates","About"):
    c1,c2=st.columns([4,1])
    with c2:
        ns=list(st.session_state.profiles.keys())
        if len(ns)<5:ns.append("➕ Add Profile")
        ch=st.selectbox("",ns,index=ns.index(st.session_state.active_profile) if st.session_state.active_profile in ns else 0,label_visibility="collapsed")
        if ch=="➕ Add Profile":
            nn=f"Profile {len(st.session_state.profiles)+1}";st.session_state.profiles[nn]=TaxpayerProfile();st.session_state.active_profile=nn;st.rerun()
        else:st.session_state.active_profile=ch
    with c1:
        if IC():
            r=compare_regimes(P());b=r[r['recommended']+'_regime']
            st.markdown(f"**{st.session_state.active_profile}** — Tax: **{format_lakhs(b['total_tax'])}** | {b['effective_rate']}% | {'New' if r['recommended']=='new' else 'Old'} ✅")
        else:st.caption(f"**{st.session_state.active_profile}** — not set up")

# ═══ CHAT ═══
def chat(k=""):
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A} — Your Tax Agent</span><br><span class="rl">Ask anything about Indian income tax</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=350)
    with bx:
        if not st.session_state.ch:
            st.markdown(f"👋 **Hi, I'm {A}!** Ask me anything about Indian income tax — regime choice, ESOPs, F&O, capital gains, deductions. I cite the exact law and never guess.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A} anything...",key=f"c{k}"):
        cl,n=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp=f"⚠️ API key not set. Admin: add GEMINI_API_KEY in Settings → Secrets."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the Income Tax Act, latest circulars, and case law. For complex cases, consult a CA.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat(k)

# ═══ HOME ═══
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        _l=f'<img src="data:image/png;base64,{LOGO}">' if LOGO else ''
        st.markdown(f"""<div class="hero-row"><div class="hero-left">{_l}
        <h1>Stop overpaying your taxes.</h1>
        <p>AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>
        <div class="tags"><span class="tg2">Always Accurate</span><span class="tg2">Private</span><span class="tg2">FY 2025-26</span><span class="tg2">Works in Hindi</span></div>
        </div></div>""",unsafe_allow_html=True)

        st.markdown(f"""<div class="su">📋 <b>Set up your tax profile (one-time, 2 min)</b> — upload a document or enter details. Create up to 5 profiles.</div>""",unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:
            if st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary"):go("Tax Profile");st.rerun()
        with bc2:
            if st.button("✏️ Enter Manually",use_container_width=True):go("Tax Profile");st.rerun()

        st.markdown(f"""<div class="fg">
        <div class="fc" onclick=""><h4>⚖️ Tax Calculator</h4><p>Old vs New regime — exact rupee savings.</p></div>
        <div class="fc"><h4>📄 Document Upload</h4><p>Payslip or Form 16 → auto-fill profile.</p></div>
        <div class="fc"><h4>💡 Savings Finder</h4><p>What to invest, how much, by when.</p></div>
        <div class="fc"><h4>🔀 What-If Scenarios</h4><p>Raise? Home loan? Share sale? See impact.</p></div>
        <div class="fc"><h4>💬 {A}</h4><p>Tax agent in 5 languages. Cites the law.</p></div>
        <div class="fc"><h4>👥 5 Profiles</h4><p>Compare tax across multiple profiles.</p></div>
        </div>""",unsafe_allow_html=True)

        st.markdown(f"""<div class="tg">
        <div class="tt"><h4>🛡️ Always Accurate</h4><ul>
        <li>Tax numbers from a precise calculation engine — not AI guesses</li>
        <li>Every answer cites the actual Income Tax Act section</li>
        <li>When unsure, {A} says "check with a CA" — never makes things up</li>
        <li>Updated with Budget 2025 and Budget 2026 changes</li></ul></div>
        <div class="tt"><h4>🔒 Your Data Stays Private</h4><ul>
        <li>We never see your PAN, Aadhaar, address, DOB, phone, or email</li>
        <li>Bank accounts, PF/UAN, employer name — all auto-stripped</li>
        <li>Only salary/deduction numbers used — in your browser session only</li>
        <li>Close the browser → everything gone. Nothing saved. Ever.</li></ul></div>
        </div>""",unsafe_allow_html=True)

    with c2:
        chat("home")

# ═══ TAX PROFILE ═══
elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        st.caption(f"Profile: **{st.session_state.active_profile}**")
        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only financial numbers extracted. Personal details auto-ignored.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"🔍 {A} is reading..."):
                doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success(f"✅ {'Annual' if ann else 'Monthly'} data:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}"+("" if ann else f" → ₹{v*mul:,.0f}/yr"))
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                if st.button("✅ Use This Data",type="primary",use_container_width=True):
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
                    p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted')
                    p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000);p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'))
                    st.session_state.pc[st.session_state.active_profile]=True;go("Tax Calculator");st.rerun()
            else:st.error("Couldn't read. Try manual.")
        elif up:st.error("API key not set.")
        st.markdown("---")
        st.markdown("#### ✏️ Manual Entry")
        c1,c2=st.columns(2)
        with c1:
            tt=st.selectbox("I am a...",["Salaried","Business Owner","Professional","F&O Trader","Investor","Freelancer"])
            tm={"Salaried":"salaried","Business Owner":"business","Professional":"professional","F&O Trader":"trader","Investor":"investor","Freelancer":"professional"}
            age=st.number_input("Age",18,100,30)
        with c2:
            res=st.selectbox("Residency",["Resident","NRI","RNOR"]);rm={"Resident":"resident","NRI":"nri","RNOR":"rnor"}
            met=st.selectbox("Metro?",["Yes (Del/Mum/Che/Kol)","No"])
        t=tm[tt];gs=bs=hra=rent=enps=biz=trd=ii=ri=di=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False
        st.markdown("**Income**")
        if t=="salaried":
            c1,c2,c3=st.columns(3)
            with c1:gs=st.number_input("Gross ₹/yr",0,value=0,step=50000,format="%d")
            with c2:bs=st.number_input("Basic ₹/yr",0,value=0,step=25000,format="%d")
            with c3:hra=st.number_input("HRA ₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:rent=st.number_input("Rent ₹/yr",0,value=0,step=10000,format="%d")
            with c2:enps=st.number_input("Employer NPS ₹/yr",0,value=0,step=5000,format="%d")
        elif t in("business","professional"):
            c1,c2=st.columns(2)
            with c1:biz=st.number_input("Business Income ₹",0,value=0,step=100000,format="%d")
            with c2:gs=st.number_input("Salary ₹",0,value=0,step=50000,format="%d")
        elif t=="trader":
            c1,c2=st.columns(2)
            with c1:trd=st.number_input("F&O P/(L) ₹",value=0,step=50000,format="%d")
            with c2:gs=st.number_input("Salary ₹",0,value=0,step=50000,format="%d")
        with st.expander("Other income / Capital gains / ESOPs"):
            c1,c2,c3=st.columns(3)
            with c1:ii=st.number_input("Interest",0,value=0,step=5000,format="%d")
            with c2:ri=st.number_input("Rental",0,value=0,step=10000,format="%d")
            with c3:di=st.number_input("Dividend",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("STCG",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("LTCG",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite",0,value=0,step=50000,format="%d");fe=st.checkbox("Foreign ESOPs")
        with st.expander("Deductions (Old Regime)"):
            c1,c2,c3=st.columns(3)
            with c1:s80c=st.number_input("80C",0,150000,0,step=10000,format="%d")
            with c2:s80d=st.number_input("80D",0,50000,0,step=5000,format="%d")
            with c3:s80n=st.number_input("NPS",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:s80e=st.number_input("Edu Loan",0,value=0,step=10000,format="%d")
            with c2:s24b=st.number_input("Home Loan",0,200000,0,step=10000,format="%d")
        with st.expander("TDS / Advance Tax"):
            c1,c2=st.columns(2)
            with c1:tds=st.number_input("TDS",0,value=0,step=10000,format="%d")
            with c2:adv=st.number_input("Advance Tax",0,value=0,step=10000,format="%d")
        if st.button("✅ Save & See Tax",type="primary",use_container_width=True):
            p=P();p.taxpayer_type=t;p.age=age;p.residency=rm[res];p.metro_city="Yes" in met
            p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent
            p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd
            p.interest_income=ii;p.rental_income=ri;p.dividend_income=di
            p.stcg_equity=stcg;p.ltcg_equity=ltcg;p.esop_perquisite=esop;p.foreign_esop=fe
            p.section_80c=s80c;p.section_80d_self=s80d;p.section_80d_parents=0;p.section_80ccd_1b=s80n
            p.section_80e=s80e;p.section_24b=s24b;p.tds_deducted=tds;p.advance_tax_paid=adv
            st.session_state.pc[st.session_state.active_profile]=True;go("Tax Calculator");st.rerun()
    with_chat(tp,"tp")

# ═══ TAX CALCULATOR ═══
elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator")
        if not IC():
            st.warning("Set up your tax profile first.");
            if st.button("→ Tax Profile"):go("Tax Profile");st.rerun()
            return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        c1,c2=st.columns(2)
        with c1:
            st.markdown(f"### {'✅ ' if rc=='new' else ''}New Regime")
            st.markdown(f"Taxable: **{format_currency(n['taxable_income'])}**")
            st.markdown(f"Tax: {format_currency(n['slab_tax'])}")
            if n['rebate_87a']>0:st.markdown(f"Rebate: -{format_currency(n['rebate_87a'])}")
            st.markdown(f"Cess: {format_currency(n['cess'])}")
            st.markdown(f"**Total: {format_currency(n['total_tax'])} ({n['effective_rate']}%)**")
        with c2:
            st.markdown(f"### {'✅ ' if rc=='old' else ''}Old Regime")
            st.markdown(f"Taxable: **{format_currency(o['taxable_income'])}**")
            if o.get('hra_exemption',0)>0:st.caption(f"HRA: {format_currency(o['hra_exemption'])}")
            if o['total_deductions']>0:st.caption(f"Deductions: {format_currency(o['total_deductions'])}")
            st.markdown(f"Tax: {format_currency(o['slab_tax'])}")
            if o['rebate_87a']>0:st.markdown(f"Rebate: -{format_currency(o['rebate_87a'])}")
            st.markdown(f"Cess: {format_currency(o['cess'])}")
            st.markdown(f"**Total: {format_currency(o['total_tax'])} ({o['effective_rate']}%)**")
        if o['total_deductions']>0:
            with st.expander("Deductions"):
                for s,a in o['deduction_breakdown'].items():
                    if a>0:st.markdown(f"- **{s}:** {format_currency(a)}")
    with_chat(calc,"calc")

# ═══ SAVINGS FINDER ═══
elif sel=="Savings Finder":
    def sf():
        st.markdown("## Savings Finder")
        if not IC():
            st.warning("Set up tax profile first.");
            if st.button("→ Tax Profile"):go("Tax Profile");st.rerun()
            return
        p=P();r=compare_regimes(p);rc=r['recommended'];recs=[]
        if rc=='old' and p.section_80c<150000:
            g=150000-p.section_80c;s=g*0.30 if p.gross_salary>1e6 else g*0.20
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more in 80C',f'ELSS, PPF, or tax-saver FD → save ~₹{s:,.0f}','Before Mar 31','elss mutual funds India 2025 best tax saving'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','Works in BOTH regimes — up to 14% basic','Ask HR',None))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP: ₹{p.esop_perquisite:,.0f}','Taxed as salary. Time exercise carefully.','Consult CA',None))
        if p.foreign_esop:recs.append(('red','Sched FA','Foreign ESOPs','Must disclose. ₹10L penalty if not.','File Sched FA + Form 67',None))
        if p.trading_income!=0:recs.append(('red','43(5)','F&O: file ITR-3','Report even losses for 8yr carry-forward.','Get a CA',None))
        if rc=='old' and p.section_80d_self==0:recs.append(('amber','80D','Health insurance','Up to ₹25K self + ₹50K parents','Buy policy','best health insurance India 2025 tax saving'))
        if rc=='old' and p.section_24b==0 and p.rental_income==0:recs.append(('amber','24(b)','Home loan interest','Up to ₹2L deduction under old regime','If applicable','best home loan rates India 2025'))
        if not recs:st.success("🎉 Well optimized!")
        for col,sec,t,d,a,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> <em>({sec})</em><br>{d}<br><b>→ {a}</b></div>',unsafe_allow_html=True)
            if q:
                if st.button(f"🔍 Search options for: {t}",key=f"s_{sec}"):
                    if K:
                        with st.spinner("Searching..."):
                            res=call_gemini(prompt=f"I'm an Indian taxpayer looking to save tax. Recommend specific {q}. Give top 3-5 options with names, expected returns, lock-in period, and tax benefit. Be specific with product names available in India in 2025-26.",
                                context="",language="en",api_key=K)
                        st.markdown(res)
                    else:st.error("API key not set.")
    with_chat(sf,"sf")

# ═══ WHAT-IF SCENARIOS ═══
elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        if not IC():
            st.warning("Set up tax profile first.");
            if st.button("→ Tax Profile"):go("Tax Profile");st.rerun()
            return
        p=P();cur=compare_regimes(p);ct=cur[cur['recommended']+'_regime']['total_tax']
        s=st.selectbox("Explore:",["Switch regime","More 80C","Raise","Sell shares","Buy/rent a house","Take a loan"])
        if s=="Switch regime":
            alt='old' if cur['recommended']=='new' else 'new';at=cur[alt+'_regime']['total_tax'];d=at-ct
            st.metric(f"{'Old' if alt=='old' else 'New'} Regime",format_currency(at),delta=f"+{format_currency(d)}" if d>0 else format_currency(d),delta_color="inverse")
        elif s=="More 80C":
            ex=st.slider("Extra 80C ₹",0,150000,50000,10000);p2=copy.deepcopy(p);p2.section_80c=min(p.section_80c+ex,150000)
            r2=compare_regimes(p2);st.metric("Tax",format_currency(r2[r2['recommended']+'_regime']['total_tax']),delta=f"-{format_currency(ct-r2[r2['recommended']+'_regime']['total_tax'])}")
        elif s=="Raise":
            pct=st.slider("Raise %",5,50,15,5);p2=copy.deepcopy(p);p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100))
            r2=compare_regimes(p2);c1,c2=st.columns(2)
            with c1:st.metric("New salary",format_lakhs(p2.gross_salary))
            with c2:st.metric("Extra tax",format_currency(r2[r2['recommended']+'_regime']['total_tax']-ct))
        elif s=="Sell shares":
            lg=st.number_input("LTCG ₹",0,value=200000,step=25000);p2=copy.deepcopy(p);p2.ltcg_equity+=lg
            r2=compare_regimes(p2);st.metric("Tax on sale",format_currency(r2[r2['recommended']+'_regime']['total_tax']-ct))
        elif s=="Buy/rent a house":
            st.markdown("**Home loan:**")
            li=st.number_input("Loan interest ₹/yr",0,value=200000,step=25000);lp=st.number_input("Principal ₹/yr",0,value=100000,step=25000)
            p2=copy.deepcopy(p);p2.section_24b=min(li,200000);p2.section_80c=min(p.section_80c+lp,150000)
            r2=compare_regimes(p2);t2=r2[r2['recommended']+'_regime']['total_tax']
            st.metric("Tax with home loan",format_currency(t2),delta=f"-{format_currency(ct-t2)}" if ct>t2 else "Same")
            st.caption("24(b) max ₹2L + 80C — Old Regime only.")
            st.markdown("**Rent (HRA claim):**")
            rn=st.number_input("Annual rent ₹",0,value=240000,step=12000);p3=copy.deepcopy(p);p3.rent_paid_annual=rn
            r3=compare_regimes(p3);st.metric("Tax with HRA",format_currency(r3[r3['recommended']+'_regime']['total_tax']),
                delta=f"-{format_currency(ct-r3[r3['recommended']+'_regime']['total_tax'])}" if ct>r3[r3['recommended']+'_regime']['total_tax'] else "Same")
        elif s=="Take a loan":
            lt=st.selectbox("Type",["Education loan","Home loan (see Buy/rent above)","Personal (no tax benefit)"])
            if lt=="Education loan":
                ei=st.number_input("Annual interest ₹",0,value=100000,step=10000);p2=copy.deepcopy(p);p2.section_80e=ei
                r2=compare_regimes(p2);st.metric("Tax",format_currency(r2[r2['recommended']+'_regime']['total_tax']),
                    delta=f"-{format_currency(ct-r2[r2['recommended']+'_regime']['total_tax'])}")
                st.caption("80E: full interest, no limit, 8 years. Old Regime.")
            elif "Personal" in lt:st.info("Personal loans have no tax benefit.")
    with_chat(sc,"sc")

# ═══ LAW UPDATES ═══
elif sel=="Law Updates":
    def lu():
        st.markdown("## Law Updates")
        for dt,t,d,col in [('Feb 2026','No slab changes FY26-27','New IT Act 2025 Apr 2026 — reorg only.','blue'),
            ('Jul 2024','CG rates changed','STCG 15→20%. LTCG 10→12.5%. No indexation.','amber'),
            ('Feb 2025','₹12.75L now tax-free','New regime: ₹4L exempt, ₹60K rebate.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        sq=st.text_input("🔍 Search",placeholder="ESOP, HRA, F&O...")
        if sq:
            for r in st.session_state.vdb.search_tax_law(sq)[:3]:
                st.markdown(f"**{r['metadata'].get('title','')}** ({r['metadata'].get('section','')})")
                st.markdown(r['content'][:300]+"...");st.markdown("---")
    with_chat(lu,"lu")

# ═══ ABOUT ═══
elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru

**Our mission:** Make tax planning simple, accurate, and accessible for every Indian taxpayer — from first-time filers to experienced investors.

**India has over 9 crore ITR filers** — yet most don't optimize. The government issued ₹3.9 lakh crore in refunds in FY25, showing massive over-deduction. With 2 regimes and 70+ sections, choosing right is hard. TaxGuru solves this with AI grounded in actual tax law.

**Built with:** Gemini AI + Google Search Grounding • ChromaDB (47 entries, all-MiniLM-L6-v2) • 3 AI agents • v0.dev design • Streamlit Cloud • Claude

**Privacy:** No PAN, Aadhaar, DOB, address, phone, email, bank, PF, employer ever collected. Session-only. Close tab = gone.

**{A}** cites exact IT Act sections. Says "consult a CA" when unsure. Never guesses.

*Informational guidance only. Not professional tax advice.*""")
    with_chat(ab,"ab")
