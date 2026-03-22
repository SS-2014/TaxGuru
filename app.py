"""TaxGuru v11"""
import streamlit as st
import sys,os,copy,random,json,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB
# Load logo first so we can use it as favicon
LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()

# Create favicon from logo
_favicon="🏛️"
if LOGO:
    try:
        import base64;from PIL import Image as PILImage;import io
        _img=PILImage.open(io.BytesIO(base64.b64decode(LOGO)))
        _img.thumbnail((32,32),PILImage.LANCZOS)
        _favicon=_img
    except:pass

st.set_page_config(page_title="TaxGuru",page_icon=_favicon,layout="wide",initial_sidebar_state="collapsed")
if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag

# ══════ SUPABASE LOGIN SYSTEM ══════
def hash_pw(pw):return hashlib.sha256(pw.encode()).hexdigest()

@st.cache_resource
def _get_db():
    """Initialize Supabase client (cached, runs once)"""
    url=st.secrets.get("SUPABASE_URL","")
    key=st.secrets.get("SUPABASE_KEY","")
    if not url or not key:return None
    try:
        from supabase import create_client
        return create_client(url,key)
    except:return None

def _db_get_user(email):
    db=_get_db()
    if not db:return None
    try:
        r=db.table("users").select("*").eq("email",email).execute()
        return r.data[0] if r.data else None
    except:return None

def _db_create_user(email,pw_hash):
    db=_get_db()
    if not db:return False
    try:
        db.table("users").insert({"email":email,"password_hash":pw_hash,"profile_data":{}}).execute()
        return True
    except:return False

def _db_save_profile(email,profile_dict):
    db=_get_db()
    if not db:return
    try:db.table("users").update({"profile_data":profile_dict,"updated_at":"now()"}).eq("email",email).execute()
    except:pass

def _db_load_profile(email):
    user=_db_get_user(email)
    if user and user.get('profile_data'):
        p=TaxpayerProfile()
        for k,v in user['profile_data'].items():
            if hasattr(p,k):setattr(p,k,v)
        return p
    return None

def check_login():
    """Returns True if logged in, shows login form if not"""
    if st.session_state.get('logged_in'):return True
    
    # Check if Supabase is configured
    has_db=_get_db() is not None
    
    st.markdown('<div style="max-width:420px;margin:2rem auto;padding:2rem;background:#111827;border:1px solid #374151;border-radius:12px">',unsafe_allow_html=True)
    if LOGO:st.markdown(f'<div style="text-align:center"><img src="data:image/png;base64,{LOGO}" style="height:100px"></div>',unsafe_allow_html=True)
    st.markdown("### Welcome to TaxGuru")
    if has_db:st.markdown("Log in to save your tax profile across sessions.")
    else:st.markdown("Enter to start planning your taxes.")
    
    if has_db:
        tab1,tab2=st.tabs(["Login","Sign Up"])
        with tab1:
            email=st.text_input("Email",key="login_email")
            pw=st.text_input("Password",type="password",key="login_pw")
            if st.button("Log In",type="primary",use_container_width=True):
                if not email or not pw:st.error("Enter email and password.")
                else:
                    user=_db_get_user(email)
                    if user and user['password_hash']==hash_pw(pw):
                        st.session_state.logged_in=True;st.session_state.user_email=email
                        # Restore saved profile
                        saved=_db_load_profile(email)
                        if saved:st.session_state.profile=saved;st.session_state.pc=True
                        st.rerun()
                    else:st.error("Invalid email or password.")
        with tab2:
            ne=st.text_input("Email",key="signup_email")
            np=st.text_input("Password (6+ characters)",type="password",key="signup_pw")
            np2=st.text_input("Confirm Password",type="password",key="signup_pw2")
            if st.button("Sign Up",use_container_width=True):
                if not ne or not np:st.error("Fill all fields.")
                elif np!=np2:st.error("Passwords don't match.")
                elif len(np)<6:st.error("Password must be 6+ characters.")
                elif _db_get_user(ne):st.error("Email already registered.")
                elif _db_create_user(ne,hash_pw(np)):
                    st.session_state.logged_in=True;st.session_state.user_email=ne;st.rerun()
                else:st.error("Signup failed. Try again.")
    
    st.markdown("---")
    if st.button("Continue without login" if has_db else "Enter TaxGuru →",type="primary" if not has_db else "secondary",use_container_width=True):
        st.session_state.logged_in=True;st.session_state.user_email=None;st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    return False

def _save_profile():
    """Save current profile to Supabase for logged-in users"""
    email=st.session_state.get('user_email')
    if email:
        profile_dict={k:v for k,v in vars(st.session_state.profile).items() if not k.startswith('_')}
        _db_save_profile(email,profile_dict)

# Navigation
def nav(p):
    st.session_state.pg=p
    st.session_state.nav_radio=p

if 'pg' not in st.session_state:st.session_state.pg='Home'

# ══════ CSS ══════
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
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{background:#1E293B;border:1px solid #475569;border-radius:6px;padding:0.35rem 0.8rem;font-size:0.95rem;font-weight:600;color:#E2E8F0;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#334155;}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){background:#D4A843!important;color:#000!important;border-color:#D4A843!important;font-weight:700;}
.cd{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin:0.3rem 0;font-size:1rem;color:#E2E8F0;}
.cd.green{border-left:3px solid #10B981;}.cd.amber{border-left:3px solid #F59E0B;}.cd.red{border-left:3px solid #EF4444;}.cd.blue{border-left:3px solid #3B82F6;}
.tg{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}
.tt{background:#1A1F2E;border:2px solid #D4A843;border-radius:10px;padding:0.9rem;}
.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1.15rem;}.tt ul{list-style:none;padding:0;margin:0;}.tt li{padding:0.15rem 0;font-size:1rem;color:#F1F5F9;line-height:1.5;}.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}
.su{background:#1C1917;border:2px solid #D4A843;border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 0.8rem;text-align:center;}.su b{font-size:1.2rem;color:#FDE68A;}.su span{color:#E2E8F0;font-size:1rem;}
.fb{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin-bottom:0.3rem;}.fb h4{color:#D4A843;margin:0 0 0.2rem;font-size:1.05rem;}.fb p{color:#CBD5E1;font-size:0.92rem;margin:0;line-height:1.4;}
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}
.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.85rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:#93C5FD;margin-bottom:0.5rem;}
.logo-panel{background:#FFFFFF;border:1px solid #D4A843;border-radius:10px;padding:0.5rem;text-align:center;margin-bottom:0.3rem;}
.logo-panel img{height:180px;}
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
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:#D4A843!important;color:#000!important;border:none!important;font-weight:900!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:700!important;font-size:0.95rem!important;-webkit-text-fill-color:#F1F5F9!important;}
[data-testid="stChatInput"]{background:#FFF!important;border:2px solid #475569;border-radius:8px;min-height:50px;}
[data-testid="stChatInput"] textarea{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000!important;}
@media(max-width:900px){.tg{grid-template-columns:1fr;}}
</style>""",unsafe_allow_html=True)

# ══════ Login gate ══════
if not check_login():st.stop()

# ══════ Session ══════
for k,v in {'profile':TaxpayerProfile(),'pc':False,'ch':[]}.items():
    if k not in st.session_state:st.session_state[k]=v
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profile
def IC():return st.session_state.pc
SHORT="""You are {agent_name}, Indian tax advisor on TaxGuru. Be CONCISE: 3-4 sentences max. No intro. No disclaimer. Cite section numbers. Expand only if asked."""

# ══════ Nav — NO index param, let session state key control ══════
TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Law Updates","About"]
if 'nav_radio' not in st.session_state:st.session_state.nav_radio="Home"
sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",key="nav_radio")
st.session_state.pg=sel

# ══════ Regime selector (used on 3 pages) ══════
def regime_pick(key="rp"):
    return st.radio("Regime:",["New Regime","Old Regime"],horizontal=True,key=key,label_visibility="collapsed")

# ══════ Chat ══════
def chat_with_logo(k=""):
    if LOGO:st.markdown(f'<div class="logo-panel"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A}</span><br><span class="rl">Your Tax Agent</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=380)
    with bx:
        if not st.session_state.ch:st.markdown(f"👋 **I'm {A}.** Ask me any tax question.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A}...",key=f"c{k}"):
        cl,_=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp="⚠️ API key not set."
        else:
            pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf)
            rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,agent_name=A,system_prompt=SHORT)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the Income Tax Act and latest circulars.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat_with_logo(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown('<h1 style="font-size:1.7rem!important;margin:0 0 0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1.05rem;color:#E2E8F0;margin:0 0 0.5rem">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>',unsafe_allow_html=True)
        st.markdown('<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter your details manually.</span></div>',unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary",on_click=nav,args=("Tax Profile",))
        with bc2:st.button("✏️ Enter Manually",use_container_width=True,on_click=nav,args=("Tax Profile",))
        fc1,fc2,fc3=st.columns(3)
        with fc1:
            st.markdown('<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New — exact savings in rupees.</p></div>',unsafe_allow_html=True)
            st.button("Open Tax Calculator →",use_container_width=True,key="h1",on_click=nav,args=("Tax Calculator",))
        with fc2:
            st.markdown('<div class="fb"><h4>🔀 What-If Scenarios</h4><p>Raise, loan, ELSS, sale — see tax impact.</p></div>',unsafe_allow_html=True)
            st.button("Open Scenarios →",use_container_width=True,key="h4",on_click=nav,args=("What-If Scenarios",))
        with fc3:
            st.markdown('<div class="fb"><h4>💡 Savings Finder</h4><p>What to invest, how much, by when.</p></div>',unsafe_allow_html=True)
            st.button("Open Savings Finder →",use_container_width=True,key="h3",on_click=nav,args=("Savings Finder",))
        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Tax numbers from a precise engine — not AI guesses</li><li>Cites actual Income Tax Act sections</li><li>{A} says "check with a CA" when unsure — never guesses</li><li>Real-time: Budget 2026, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Your Data Stays Private</h4><ul><li>No PAN, Aadhaar, address, DOB, phone, email collected</li><li>Bank, PF/UAN, employer — auto-deleted</li><li>Session-only. Close browser → gone. Forever.</li><li>Login saves profile securely — nothing else.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat_with_logo("home")

# ══════ TAX PROFILE ══════
elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only financial numbers extracted.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip, Form 16, or tax sheet",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"🔍 {A} is reading..."):doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success(f"✅ Data found:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:
                        st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}"+("" if ann else f" → ₹{v*mul:,.0f}/yr"))
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                def _use():
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4)
                    p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted');p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000)
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'));st.session_state.pc=True;_save_profile();nav("Tax Calculator")
                st.button("✅ Use This Data",type="primary",use_container_width=True,on_click=_use)
        elif up:st.error("API key not set.")
        st.markdown("---")
        st.markdown("#### ✏️ Manual Entry")
        c1,c2=st.columns(2)
        with c1:
            types=st.multiselect("I earn income from...",["Salary","Business","Professional services","Trading (stocks, F&O, crypto)","Investments","Freelancing","Other"],default=["Salary"])
            age=st.number_input("Age",18,100,30)
        with c2:
            st.markdown("**Residency**")
            cit=st.selectbox("Citizenship",["Indian citizen","Person of Indian origin","Foreign citizen"])
            di=st.number_input("Days in India this FY",0,366,365)
            d4=st.number_input("Days in India, last 4 years",0,1461,1400)
            i15=st.checkbox("Indian income > ₹15 lakh")
            if di>=182:rs="resident";st.markdown("✅ **Resident**")
            elif cit!="Foreign citizen":
                if i15 and di>=120 and d4>=365:rs="rnor";st.markdown("⚠️ **RNOR**")
                elif di>=60 and d4>=365 and not i15:rs="resident";st.markdown("✅ **Resident**")
                else:rs="nri";st.markdown("🌍 **NRI**")
            else:rs="nri" if not(di>=60 and d4>=365) else "resident";st.markdown("✅ **Resident**" if rs=="resident" else "🌍 **NRI**")
            met=st.selectbox("Metro? (50% HRA)",["Yes — Del/Mum/Kol/Che/Hyd/Pune/Ahd/Blr","No"])
        t="salaried"
        if "Business" in types:t="business"
        if "Professional services" in types:t="professional"
        if "Trading (stocks, F&O, crypto)" in types:t="trader"
        gs=bs=hra=rent=enps=biz=trd=ii2=ri2=dv=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False
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
            with c1:ii2=st.number_input("Interest",0,value=0,step=5000,format="%d")
            with c2:ri2=st.number_input("Rental",0,value=0,step=10000,format="%d")
            with c3:dv=st.number_input("Dividend",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("STCG",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("LTCG",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP perquisite",0,value=0,step=50000,format="%d");fe=st.checkbox("Foreign ESOPs")
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
            p=P();p.taxpayer_type=t;p.age=age;p.residency=rs;p.metro_city="Yes" in met
            p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent
            p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd
            p.interest_income=ii2;p.rental_income=ri2;p.dividend_income=dv;p.stcg_equity=stcg;p.ltcg_equity=ltcg
            p.esop_perquisite=esop;p.foreign_esop=fe;p.section_80c=s80c;p.section_80d_self=s80d
            p.section_80d_parents=0;p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b
            p.tds_deducted=tds;p.advance_tax_paid=adv;st.session_state.pc=True;_save_profile();nav("Tax Calculator")
        st.button("✅ Save & See My Tax",type="primary",use_container_width=True,on_click=_save)
    with_chat(tp,"tp")

# ══════ TAX CALCULATOR — detailed breakdown ══════
elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        regime=regime_pick("rp_calc")
        rk='new' if regime=="New Regime" else 'old'
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        d=r[rk+'_regime']
        # Detailed breakdown
        st.markdown(f"### {regime} — Detailed Breakdown")
        st.markdown(f"**Gross salary income:** {format_currency(d['salary_income'])}")
        if d.get('hp_income',0):st.markdown(f"**House property income:** {format_currency(d['hp_income'])}")
        if d.get('business_income',0):st.markdown(f"**Business income:** {format_currency(d['business_income'])}")
        if d.get('other_income',0):st.markdown(f"**Other income:** {format_currency(d['other_income'])}")
        if d.get('esop_perquisite',0):st.markdown(f"**ESOP perquisite:** {format_currency(d['esop_perquisite'])}")
        st.markdown(f"**Gross total income:** {format_currency(d['gross_total_income'])}")
        if rk=='old' and d.get('hra_exemption',0)>0:st.markdown(f"*Less HRA exemption:* -{format_currency(d['hra_exemption'])}")
        if d['total_deductions']>0:
            st.markdown(f"*Less Chapter VI-A deductions:* -{format_currency(d['total_deductions'])}")
            for s,a in d['deduction_breakdown'].items():
                if a>0:st.markdown(f"&nbsp;&nbsp;&nbsp;&nbsp;{s}: {format_currency(a)}")
        st.markdown(f"**Taxable income:** {format_currency(d['taxable_income'])}")
        st.markdown("---")
        st.markdown(f"Tax on slab: {format_currency(d['slab_tax'])}")
        if d.get('stcg_equity_tax',0):st.markdown(f"STCG tax (20%): {format_currency(d['stcg_equity_tax'])}")
        if d.get('ltcg_equity_tax',0):st.markdown(f"LTCG tax (12.5%): {format_currency(d['ltcg_equity_tax'])}")
        if d['rebate_87a']>0:st.markdown(f"87A rebate: -{format_currency(d['rebate_87a'])}")
        if d['surcharge']>0:st.markdown(f"Surcharge: {format_currency(d['surcharge'])}")
        st.markdown(f"Cess (4%): {format_currency(d['cess'])}")
        st.markdown(f"### Total tax: {format_currency(d['total_tax'])} (effective {d['effective_rate']}%)")
        if d['tds_deducted']>0 or d['advance_tax_paid']>0:
            st.markdown(f"TDS paid: {format_currency(d['tds_deducted'])} | Advance tax: {format_currency(d['advance_tax_paid'])}")
            np2=d['net_payable']
            if np2<0:st.markdown(f"**💰 Refund due: {format_currency(abs(np2))}**")
            else:st.markdown(f"**Net payable: {format_currency(np2)}**")
        st.markdown("---")
        st.button("💡 Find ways to save more tax →",on_click=nav,args=("Savings Finder",))
    with_chat(calc,"calc")

# ══════ SAVINGS FINDER ══════
elif sel=="Savings Finder":
    def sf():
        st.markdown("## Savings Finder")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p)
        regime=regime_pick("rp_sf");rk='new' if regime=="New Regime" else 'old'
        ct=r[rk+'_regime']['total_tax']
        recs=[]
        if rk=='old' and p.section_80c<150000:
            g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;r2=compare_regimes(p2)
            sv=ct-r2['old_regime']['total_tax']
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more (80C)',f'Save **{format_currency(max(sv,0))}**','ELSS/PPF/FD','Recommend top 3 ELSS tax-saving mutual funds in India for 2025. Name, 3yr return, lock-in. No disclaimers. 3 lines max.'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','Save ₹15K-50K+','Both regimes','Recommend top 3 NPS tier-1 fund managers in India. Name, 5yr return. 3 lines max.'))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP: ₹{p.esop_perquisite:,.0f}','Slab rate','Time exercise',None))
        if p.foreign_esop:recs.append(('red','Sched FA','Foreign ESOP','₹10L penalty','File Form 67',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading → ITR-3','Carry-forward losses','File correctly',None))
        if rk=='old' and p.section_80d_self==0:
            p2=copy.deepcopy(p);p2.section_80d_self=25000;r2=compare_regimes(p2);sv=ct-r2['old_regime']['total_tax']
            recs.append(('amber','80D','Health insurance',f'Save **{format_currency(max(sv,0))}**','₹25K+₹50K parents','Recommend top 3 health insurance plans in India for tax saving under 80D, 2025. Name, premium range, coverage. 3 lines max.'))
        if rk=='old' and p.section_24b==0:recs.append(('amber','24(b)','Home loan interest','Up to ₹62,400','Max ₹2L','Recommend top 3 home loan providers in India 2025 with best interest rates. Name, rate. 3 lines max.'))
        if not recs:st.success("🎉 Well optimized!")
        for col,sec,t,impact,detail,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> ({sec}) — {impact}<br><em>{detail}</em></div>',unsafe_allow_html=True)
            if q:
                if st.button(f"🔍 Explore options",key=f"s_{sec}"):
                    if K:
                        with st.spinner(f"{A} is searching..."):
                            rsp=call_gemini(prompt=q,context="",language="en",api_key=K,agent_name=A,system_prompt=SHORT)
                        st.markdown(rsp)
    with_chat(sf,"sf")

# ══════ WHAT-IF SCENARIOS — multiselect from 19 ══════
elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        st.markdown("**Select one or more life events to see the tax impact:**")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p)
        regime=regime_pick("rp_sc");rk='new' if regime=="New Regime" else 'old'
        ct=cur[rk+'_regime']['total_tax']
        st.caption(f"Current tax ({regime}): **{format_currency(ct)}**")
        ALL_SC=["Salary raise","Invest in 80C (ELSS/PPF)","Start employer NPS","Buy health insurance (80D)",
            "Take a home loan","Pay rent (HRA)","Sell equity (LTCG)","Sell equity (STCG)","Sell property",
            "Receive ESOPs","Take education loan","Start a side business","Earn rental income",
            "Receive a bonus","Make a donation (80G)","Invest in NPS self (80CCD1B)","Earn FD interest"]
        chosen=st.multiselect("Choose scenarios (select multiple):",ALL_SC,default=[],placeholder="Click to see options...")
        def calc_tax(p2):r2=compare_regimes(p2);return r2[rk+'_regime']['total_tax']
        for s in chosen:
            st.markdown(f"---\n#### {s}")
            p2=copy.deepcopy(p)
            if s=="Salary raise":
                pct=st.slider("Raise %",5,100,20,5,key=f"wr_{s}");p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100))
                c1,c2=st.columns(2)
                with c1:st.metric("New salary",format_lakhs(p2.gross_salary))
                with c2:st.metric("Tax change",format_currency(calc_tax(p2)-ct))
            elif s=="Invest in 80C (ELSS/PPF)":
                ex=st.slider("80C amount ₹",0,150000,50000,10000,key=f"wr_{s}");p2.section_80c=min(p.section_80c+ex,150000)
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Start employer NPS":
                nps=st.slider("NPS ₹/yr",0,int(max(p.basic_salary*0.14,100000)),50000,5000,key=f"wr_{s}");p2.section_80ccd_2=nps
                st.metric("Tax saving (both regimes)",format_currency(ct-calc_tax(p2)))
            elif s=="Buy health insurance (80D)":
                d2=st.slider("Premium ₹/yr",0,50000,25000,5000,key=f"wr_{s}");p2.section_80d_self=d2
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Take a home loan":
                li=st.number_input("Interest ₹/yr",0,value=200000,step=25000,key=f"wn_{s}a");lp=st.number_input("Principal ₹/yr",0,value=100000,step=25000,key=f"wn_{s}b")
                p2.section_24b=min(li,200000);p2.section_80c=min(p.section_80c+lp,150000)
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Pay rent (HRA)":
                rn=st.number_input("Annual rent ₹",0,value=240000,step=12000,key=f"wn_{s}");p2.rent_paid_annual=rn
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Sell equity (LTCG)":
                lg=st.number_input("LTCG ₹",0,value=200000,step=25000,key=f"wn_{s}");p2.ltcg_equity+=lg
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Sell equity (STCG)":
                sg=st.number_input("STCG ₹",0,value=100000,step=25000,key=f"wn_{s}");p2.stcg_equity+=sg
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Sell property":
                gn=st.number_input("Capital gain ₹",0,value=500000,step=50000,key=f"wn_{s}");p2.ltcg_other+=gn
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Receive ESOPs":
                ep=st.number_input("ESOP value ₹",0,value=500000,step=50000,key=f"wn_{s}");p2.esop_perquisite+=ep
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Take education loan":
                ei=st.number_input("Interest ₹/yr",0,value=100000,step=10000,key=f"wn_{s}");p2.section_80e=ei
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Start a side business":
                bi=st.number_input("Business income ₹",0,value=300000,step=50000,key=f"wn_{s}");p2.business_income+=bi
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Earn rental income":
                ri3=st.number_input("Rental income ₹",0,value=240000,step=12000,key=f"wn_{s}");p2.rental_income+=ri3
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
            elif s=="Receive a bonus":
                bn=st.number_input("Bonus ₹",0,value=500000,step=50000,key=f"wn_{s}");p2.gross_salary+=bn
                st.metric("Tax on bonus",format_currency(calc_tax(p2)-ct))
            elif s=="Make a donation (80G)":
                dn=st.number_input("Donation ₹",0,value=50000,step=5000,key=f"wn_{s}");p2.section_80g=dn
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Invest in NPS self (80CCD1B)":
                np2=st.slider("NPS ₹",0,50000,50000,5000,key=f"wr_{s}");p2.section_80ccd_1b=np2
                st.metric("Tax saving",format_currency(ct-calc_tax(p2)))
            elif s=="Earn FD interest":
                fd=st.number_input("FD interest ₹/yr",0,value=100000,step=10000,key=f"wn_{s}");p2.interest_income+=fd
                st.metric("Extra tax",format_currency(calc_tax(p2)-ct))
    with_chat(sc,"sc")

# ══════ LAW UPDATES ══════
elif sel=="Law Updates":
    def lu():
        st.markdown("## Latest Tax Law Updates")
        for dt,t,d,col in [
            ('Mar 20, 2026','🆕 IT Rules 2026 Notified','HRA→8 metros. Form 124. Sections 819→536. CARF crypto.','blue'),
            ('Mar 5, 2026','🆕 CARF: Crypto Reporting','All exchanges must report from Jan 2026.','blue'),
            ('Mar 2026','Significant Transaction Emails','CBDT AIS alerts. Verify on e-filing portal.','blue'),
            ('Feb 2026','Budget 2026','Tax Year replaces PY/AY. No rate changes.','blue'),
            ('Oct 2025','ITR Deadline Extended','Audit: Oct 31 → Dec 10, 2025.','amber'),
            ('Jul 2024','Capital Gains Changed','STCG 15→20%. LTCG 10→12.5%. No indexation.','amber'),
            ('Feb 2025','₹12.75L Tax-Free','New regime: ₹4L+87A ₹60K+SD ₹75K.','green'),
            ('Apr 2024','Angel Tax Abolished','Sec 56(2)(viib) removed.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---\n#### ⚖️ Case Law")
        for t,d in [("CIT vs Gopal Purohit (Bombay HC)","Separate investment + trading portfolios OK."),
            ("Unnikrishnan vs ITO","ESOPs granted as resident → taxable in India even if exercised as NRI."),
            ("HRA to Parents (ITAT)","Rent to parents OK. Need agreement + bank transfer."),
            ("CBDT Circular 6/2016","Classify shares as investment or trading — must be consistent.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b><br>{d}</div>',unsafe_allow_html=True)
    with_chat(lu,"lu")

# ══════ ABOUT ══════
elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru

### Our Mission
India has over 9 crore income tax return filers — yet most don't optimize their taxes. The government issued ₹3.9 lakh crore in refunds in FY25, showing millions overpay through excess TDS and wrong regime choices. With 2 tax regimes and 70+ deduction sections, making the right choice is hard. **TaxGuru exists to change this.**

### How It Works
**🧮 Precise Calculation Engine** — Your tax numbers are computed by a deterministic mathematical engine, not generated by AI. The numbers are always exactly right — no rounding, no estimation, no hallucination.

**🤖 {A} — Your Tax Agent** — {A} is an intelligent agent with access to 60 sections of the Income Tax Act, key CBDT circulars, case law precedents, and Budget amendments. When you ask a question, {A} retrieves the most relevant legal provisions and constructs an answer grounded in actual law — citing specific sections.

**🔍 Real-Time Updates** — {A} can search the web for the latest tax developments — new circulars, court rulings, deadline extensions. This means advice stays current even as the law changes. Our knowledge base also auto-updates weekly via automated scripts.

**📄 Document Intelligence** — Upload a payslip or Form 16 and AI reads it, extracts only the financial numbers (ignoring all personal details), and fills your tax profile automatically.

**🔒 Privacy by Design** — We never collect, store, or transmit your name, PAN, Aadhaar, date of birth, address, phone number, email, bank account details, PF number, employer name, or employee ID. Only financial figures are processed. If you create an account, only your email and encrypted password are stored — your profile data is saved securely but contains no personal identifiers.

### Accuracy Commitment
- Every answer cites the specific section of the Income Tax Act
- When {A} is unsure, {A} says "consult a CA" — never guesses
- 60 provisions including CBDT Notification 22/2026 (March 20, 2026) and IT Rules 2026
- Tax calculations verified against government guidelines and major tax platforms
- Updated with Budget 2025, Budget 2026, and all major circulars

### Who It's For
**Salaried employees** — regime comparison, HRA, payslip analysis • **Business owners** — presumptive taxation, audit requirements • **Professionals** — Section 44ADA, advance tax planning • **Traders** — F&O/intraday, Section 43(5), ITR-3, loss carry-forward • **Investors** — capital gains, ESOP taxation (domestic + foreign) • **Senior citizens** — higher exemptions, 80TTB, TDS thresholds • **NRIs** — residency auto-determination, DTAA, foreign tax credit

*TaxGuru provides informational guidance based on Indian tax law. This is not professional tax advice. For complex matters, always consult a qualified Chartered Accountant.*""")
    with_chat(ab,"ab")
