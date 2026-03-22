"""TaxGuru v12 — Multi-profile, logout, side-by-side calculator, profile management"""
import streamlit as st
import sys,os,copy,random,json,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB

# Load logo FIRST for favicon
LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()
_fav="🏛️"
if LOGO:
    try:
        import base64 as b64m;from PIL import Image as PI;import io as iom
        _fav=PI.open(iom.BytesIO(b64m.b64decode(LOGO)));_fav.thumbnail((32,32),PI.LANCZOS)
    except:_fav="🏛️"
st.set_page_config(page_title="TaxGuru",page_icon=_fav,layout="wide",initial_sidebar_state="collapsed")

if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag

def nav(p):st.session_state.pg=p;st.session_state.nav_radio=p
if 'pg' not in st.session_state:st.session_state.pg='Home'

# ══════ SUPABASE ══════
def hash_pw(pw):return hashlib.sha256(pw.encode()).hexdigest()

@st.cache_resource
def _get_db():
    url=st.secrets.get("SUPABASE_URL","");key=st.secrets.get("SUPABASE_KEY","")
    if not url or not key:return None
    try:
        from supabase import create_client;return create_client(url,key)
    except:return None

def _db_get_user(email):
    db=_get_db()
    if not db:return None
    try:r=db.table("users").select("*").eq("email",email).execute();return r.data[0] if r.data else None
    except:return None

def _db_create_user(email,pw_hash):
    db=_get_db()
    if not db:return False
    try:db.table("users").insert({"email":email,"password_hash":pw_hash,"profile_data":{}}).execute();return True
    except:return False

def _db_save_profiles(email,profiles_dict):
    db=_get_db()
    if not db:return
    try:db.table("users").update({"profile_data":profiles_dict}).eq("email",email).execute()
    except:pass

def _db_load_profiles(email):
    user=_db_get_user(email)
    if user and user.get('profile_data') and isinstance(user['profile_data'],dict):
        return user['profile_data']
    return {}

def save_all_profiles():
    email=st.session_state.get('user_email')
    if email and _get_db():
        all_p={}
        for name,prof in st.session_state.profiles.items():
            all_p[name]={k:v for k,v in vars(prof).items() if not k.startswith('_')}
        _db_save_profiles(email,all_p)

# ══════ LOGIN PAGE ══════
def check_login():
    if st.session_state.get('logged_in'):return True
    has_db=_get_db() is not None

    # Full-page dark login with centered card
    st.markdown("""<style>
    .login-wrap{max-width:440px;margin:1.5rem auto;padding:0;}
    .login-card{background:linear-gradient(135deg,#111827,#1E293B);border:1px solid #D4A843;border-radius:16px;padding:2rem;box-shadow:0 8px 32px rgba(0,0,0,0.3);}
    .login-logo{text-align:center;padding:1rem;margin-bottom:1rem;background:#FFFFFF;border-radius:12px;border:1px solid #E5E7EB;}
    .login-logo img{height:300px;}
    .login-tagline{text-align:center;color:#D4A843;font-size:1.1rem;margin:0.5rem 0 1rem;font-weight:600;}
    .login-features{display:grid;grid-template-columns:1fr 1fr;gap:0.4rem;margin:1rem 0;}
    .login-feat{background:#0B0F19;border:1px solid #374151;border-radius:8px;padding:0.5rem;text-align:center;font-size:0.8rem;color:#CBD5E1;}
    .login-feat b{color:#D4A843;display:block;font-size:0.85rem;}
    </style>""",unsafe_allow_html=True)

    st.markdown('<div class="login-wrap">',unsafe_allow_html=True)
    if LOGO:st.markdown(f'<div class="login-logo"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown('<div class="login-tagline">AI-powered Indian tax advisor • FY 2025-26</div>',unsafe_allow_html=True)

    if has_db:
        tab1,tab2=st.tabs(["🔑 Login","✨ Sign Up"])
        with tab1:
            email=st.text_input("Email",key="le",placeholder="you@email.com")
            pw=st.text_input("Password",type="password",key="lp")
            if st.button("Log In",type="primary",use_container_width=True,key="lb"):
                if not email or not pw:st.error("Enter email and password.")
                else:
                    user=_db_get_user(email)
                    if user and user['password_hash']==hash_pw(pw):
                        st.session_state.logged_in=True;st.session_state.user_email=email
                        saved=_db_load_profiles(email)
                        if saved and isinstance(saved,dict):
                            st.session_state.profiles={}
                            for name,data in saved.items():
                                p=TaxpayerProfile()
                                if isinstance(data,str):
                                    try:data=json.loads(data)
                                    except:continue
                                if isinstance(data,dict):
                                    for k,v in data.items():
                                        if hasattr(p,k):
                                            try:setattr(p,k,v)
                                            except:pass
                                st.session_state.profiles[name]=p
                            if st.session_state.profiles:
                                st.session_state.active_profile=list(st.session_state.profiles.keys())[0]
                                st.session_state.pc=True
                        st.rerun()
                    else:st.error("Invalid email or password.")
        with tab2:
            ne=st.text_input("Email",key="se",placeholder="you@email.com")
            np=st.text_input("Password (6+ characters)",type="password",key="sp")
            np2=st.text_input("Confirm Password",type="password",key="sp2")
            if st.button("Create Account",use_container_width=True,key="sb"):
                if not ne or not np:st.error("Fill all fields.")
                elif np!=np2:st.error("Passwords don't match.")
                elif len(np)<6:st.error("Min 6 characters.")
                elif _db_get_user(ne):st.error("Email already registered.")
                elif _db_create_user(ne,hash_pw(np)):
                    st.session_state.logged_in=True;st.session_state.user_email=ne;st.rerun()
                else:st.error("Signup failed.")

    st.markdown("---")
    tc1,tc2=st.columns([3,1])
    with tc2:
        if st.button("🌓 Dark/Light",key="login_theme"):
            if "dark_mode" not in st.session_state:st.session_state.dark_mode=True
            st.session_state.dark_mode=not st.session_state.dark_mode;st.rerun()
    with tc1:
        pass
    if st.button("Continue as guest" if has_db else "Enter TaxGuru →",
        type="primary" if not has_db else "secondary",use_container_width=True,key="gb"):
        st.session_state.logged_in=True;st.session_state.user_email=None;st.rerun()

    st.markdown("""<div class="login-features">
    <div class="login-feat"><b>⚖️ Tax Calculator</b>Old vs New regime</div>
    <div class="login-feat"><b>💡 Savings Finder</b>Personalized tips</div>
    <div class="login-feat"><b>🔀 19 Scenarios</b>What-if analysis</div>
    <div class="login-feat"><b>🔒 Privacy-First</b>No PAN/Aadhaar stored</div>
    </div>""",unsafe_allow_html=True)
    st.markdown('</div>',unsafe_allow_html=True)
    return False

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
.logo-panel{background:#FFFFFF;border:1px solid #D4A843;border-radius:10px;padding:0.5rem;text-align:center;margin-bottom:0.3rem;}
.logo-panel img{height:280px;}
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}
.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}
.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.85rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:#93C5FD;margin-bottom:0.5rem;}
/* Comparison table */
.cmp-tbl{width:100%;border-collapse:collapse;margin:0.5rem 0;}
.cmp-tbl th{background:#1E293B;color:#D4A843;padding:0.5rem;text-align:right;border:1px solid #374151;font-size:0.95rem;}
.cmp-tbl th:first-child{text-align:left;}
.cmp-tbl td{padding:0.4rem 0.5rem;border:1px solid #374151;color:#E2E8F0;text-align:right;font-size:0.95rem;}
.cmp-tbl td:first-child{text-align:left;color:#CBD5E1;}
.cmp-tbl tr.total{background:#1A1F2E;font-weight:700;}
.cmp-tbl tr.total td{color:#D4A843;font-size:1.05rem;}
.cmp-tbl .winner{color:#4ADE80!important;font-weight:700;}
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
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:#D4A843!important;color:#000!important;border:none!important;font-weight:900!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:700!important;font-size:0.95rem!important;-webkit-text-fill-color:#F1F5F9!important;}
[data-testid="stChatInput"]{background:#FFF!important;border:2px solid #475569;border-radius:8px;min-height:120px;}
[data-testid="stChatInput"] textarea{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000!important;}
@media(max-width:900px){.tg{grid-template-columns:1fr;}}
</style>""",unsafe_allow_html=True)

# ══════ THEME TOGGLE ══════
if 'dark_mode' not in st.session_state:st.session_state.dark_mode=True
if not st.session_state.dark_mode:
    st.markdown("""<style>
    .stApp,[data-testid="stAppViewContainer"]{background:#F8FAFC!important;color:#1E293B!important;}
    h1,h2,h3,h4{color:#0F172A!important;}p,li,span,.stMarkdown{color:#334155!important;}
    .cd,.fb{background:#FFFFFF!important;border-color:#E2E8F0!important;color:#1E293B!important;}
    .cd *,.fb *{color:#1E293B!important;}
    .tt{background:#F1F5F9!important;border-color:#D4A843!important;}.tt *{color:#1E293B!important;}
    .su{background:#FFFBEB!important;border-color:#D4A843!important;}.su *{color:#92400E!important;}
    .ch{background:#F1F5F9!important;border-color:#CBD5E1!important;}.ch *{color:#1E293B!important;}
    .cd2{color:#64748B!important;}
    .pv{background:#EFF6FF!important;color:#1E40AF!important;border-color:#BFDBFE!important;}
    .cmp-tbl th{background:#F1F5F9!important;color:#0F172A!important;border-color:#E2E8F0!important;}
    .cmp-tbl td{color:#1E293B!important;border-color:#E2E8F0!important;}
    .cmp-tbl tr.total td{color:#92400E!important;}
    .logo-panel{background:#FFFFFF!important;border-color:#E2E8F0!important;}
    [data-testid="stSelectbox"]>div>div{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    [data-testid="stNumberInput"] input{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    .stTextInput input{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    [data-testid="stExpander"]{background:#FFF!important;border-color:#E2E8F0!important;}
    [data-testid="stExpander"] summary{color:#1E293B!important;}
    [data-testid="stMultiSelect"]>div>div{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    [data-testid="stMetric"]{background:#FFF!important;border-color:#E2E8F0!important;}
    [data-testid="stFileUploader"]{background:#FFF!important;border-color:#E2E8F0!important;}
    div[data-testid="stHorizontalBlock"]:first-child .stRadio label{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{background:#F1F5F9!important;}
    .stButton>button:not([kind="primary"]){background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;-webkit-text-fill-color:#1E293B!important;}
    </style>""",unsafe_allow_html=True)

# ══════ LOGIN GATE ══════
if not check_login():st.stop()

# ══════ SESSION ══════
if 'profiles' not in st.session_state:st.session_state.profiles={'Default':TaxpayerProfile()}
if 'active_profile' not in st.session_state:st.session_state.active_profile='Default'
if 'pc' not in st.session_state:st.session_state.pc=False
if 'ch' not in st.session_state:st.session_state.ch=[]
if 'vdb' not in st.session_state:
    st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profiles.get(st.session_state.active_profile,TaxpayerProfile())
def IC():return st.session_state.pc and st.session_state.active_profile in st.session_state.profiles
SHORT="""You are {agent_name}, Indian tax advisor. Be CONCISE: 3-4 sentences max. No intro. No disclaimer. Cite sections."""

# ══════ NAV with Profiles + Logout ══════
TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Profiles","Law Updates","About"]
if 'nav_radio' not in st.session_state:st.session_state.nav_radio="Home"

nc1,nc2,nc3=st.columns([9,1,1])
with nc1:sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",key="nav_radio")
with nc2:
    if st.button("🌓" if st.session_state.dark_mode else "☀️",key="theme_btn",help="Toggle dark/light mode"):
        st.session_state.dark_mode=not st.session_state.dark_mode;st.rerun()
with nc3:
    if st.button("Logout",key="logout_btn"):
        for k in list(st.session_state.keys()):del st.session_state[k]
        st.rerun()
st.session_state.pg=sel

# Active profile indicator on tool pages
if sel in ("Tax Calculator","Savings Finder","What-If Scenarios") and IC():
    ap=st.session_state.active_profile
    st.markdown(f"📋 Active profile: **{ap}** | Tax: **{format_lakhs(compare_regimes(P())[compare_regimes(P())['recommended']+'_regime']['total_tax'])}**")

# ══════ Chat ══════
def chat_with_logo(k=""):
    if LOGO:st.markdown(f'<div class="logo-panel"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A}</span><br><span class="rl">Your Tax Agent</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=280)
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
    st.markdown(f'<div class="cd2">💡 {A} is grounded in the IT Act and latest circulars.</div>',unsafe_allow_html=True)

def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat_with_logo(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown('<h1 style="font-size:1.7rem!important;margin:0 0 0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1.05rem;color:#E2E8F0">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>',unsafe_allow_html=True)
        st.markdown('<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter your details.</span></div>',unsafe_allow_html=True)
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
        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Tax numbers from a precise engine — not AI guesses</li><li>Cites actual Income Tax Act sections</li><li>{A} says "check with a CA" when unsure</li><li>Real-time: Budget 2026, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Your Data Stays Private</h4><ul><li>No PAN, Aadhaar, address, DOB, phone, email collected</li><li>Bank, PF/UAN, employer — auto-deleted</li><li>Session-only. Close browser → gone.</li><li>Login saves profile securely — nothing else.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat_with_logo("home")

# ══════ TAX PROFILE ══════
elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        # Show if editing existing
        if IC():
            st.info(f"⚠️ You are editing profile **{st.session_state.active_profile}**. Any changes will update this profile when you click Save.")
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
                    p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'));st.session_state.pc=True;save_all_profiles();nav("Tax Calculator")
                st.button("✅ Use This Data",type="primary",use_container_width=True,on_click=_use)
        elif up:st.error("API key not configured.")
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
            d4=st.number_input("Days in India, last 4 yrs",0,1461,1400)
            i15=st.checkbox("Indian income > ₹15L")
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
            biz=st.number_input("Business/Prof Income ₹",0,value=0,step=100000,format="%d")
        if "Trading (stocks, F&O, crypto)" in types:
            trd=st.number_input("Trading P/(L) ₹",value=0,step=50000,format="%d")
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
            p.tds_deducted=tds;p.advance_tax_paid=adv;st.session_state.pc=True;save_all_profiles();nav("Tax Calculator")
        st.button("✅ Save & See My Tax",type="primary",use_container_width=True,on_click=_save)
    with_chat(tp,"tp")

# ══════ TAX CALCULATOR — side-by-side table ══════
elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator — Old vs New Regime")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        # Build comparison table rows
        rows=[]
        rows.append(("**Gross Salary**",n['salary_income'],o['salary_income']))
        if n.get('hp_income') or o.get('hp_income'):rows.append(("House Property",n.get('hp_income',0),o.get('hp_income',0)))
        if n.get('business_income') or o.get('business_income'):rows.append(("Business Income",n.get('business_income',0),o.get('business_income',0)))
        if n.get('other_income') or o.get('other_income'):rows.append(("Other Income",n.get('other_income',0),o.get('other_income',0)))
        if n.get('esop_perquisite') or o.get('esop_perquisite'):rows.append(("ESOP Perquisite",n.get('esop_perquisite',0),o.get('esop_perquisite',0)))
        rows.append(("**Gross Total Income**",n['gross_total_income'],o['gross_total_income']))
        if o.get('hra_exemption',0)>0:rows.append(("*Less: HRA Exemption*",0,-o['hra_exemption']))
        rows.append(("*Less: Standard Deduction*",-75000,-50000))
        if o['total_deductions']>0:
            for s,a in o['deduction_breakdown'].items():
                if a>0:rows.append((f"*Less: {s}*",0,-a))
        if n.get('section_80ccd_2',0) or (n['total_deductions']>0 and 'Section 80CCD(2)' in n.get('deduction_breakdown',{})):
            pass  # Already captured above
        rows.append(("**Taxable Income**",n['taxable_income'],o['taxable_income']))
        rows.append(("Tax on Slabs",n['slab_tax'],o['slab_tax']))
        if n.get('stcg_equity_tax') or o.get('stcg_equity_tax'):rows.append(("STCG Tax (20%)",n.get('stcg_equity_tax',0),o.get('stcg_equity_tax',0)))
        if n.get('ltcg_equity_tax') or o.get('ltcg_equity_tax'):rows.append(("LTCG Tax (12.5%)",n.get('ltcg_equity_tax',0),o.get('ltcg_equity_tax',0)))
        if n['rebate_87a']>0 or o['rebate_87a']>0:rows.append(("*87A Rebate*",-n['rebate_87a'],-o['rebate_87a']))
        if n['surcharge']>0 or o['surcharge']>0:rows.append(("Surcharge",n['surcharge'],o['surcharge']))
        rows.append(("Cess (4%)",n['cess'],o['cess']))
        rows.append(("**TOTAL TAX**",n['total_tax'],o['total_tax']))
        if n['tds_deducted']>0 or o['tds_deducted']>0:
            rows.append(("*Less: TDS*",-n['tds_deducted'],-o['tds_deducted']))
            rows.append(("*Less: Advance Tax*",-n['advance_tax_paid'],-o['advance_tax_paid']))
            rows.append(("**Net Payable/Refund**",n['net_payable'],o['net_payable']))
        # Render HTML table
        nw='winner' if rc=='new' else '';ow='winner' if rc=='old' else ''
        html=f'<table class="cmp-tbl"><tr><th>Description</th><th class="{nw}">New Regime {"✅" if rc=="new" else ""}</th><th class="{ow}">Old Regime {"✅" if rc=="old" else ""}</th></tr>'
        for desc,nv,ov in rows:
            is_total='total' if desc.startswith("**TOTAL") or desc.startswith("**Net") else ''
            d=desc.replace("**","").replace("*","")
            nf=format_currency(abs(nv)) if nv!=0 else "—"
            of=format_currency(abs(ov)) if ov!=0 else "—"
            if nv<0:nf=f"-{format_currency(abs(nv))}"
            if ov<0:of=f"-{format_currency(abs(ov))}"
            if nv==0 and ov==0:continue
            html+=f'<tr class="{is_total}"><td>{d}</td><td>{nf}</td><td>{of}</td></tr>'
        html+='</table>'
        st.markdown(html,unsafe_allow_html=True)
        st.button("💡 Find ways to save more →",on_click=nav,args=("Savings Finder",))
    with_chat(calc,"calc")

# ══════ SAVINGS FINDER ══════
elif sel=="Savings Finder":
    def sf():
        st.markdown("## Savings Finder")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);rc=r['recommended'];ct=r[rc+'_regime']['total_tax']
        regime=st.radio("Regime:",["New Regime","Old Regime"],horizontal=True,key="rp_sf")
        rk='new' if regime=="New Regime" else 'old';ct=r[rk+'_regime']['total_tax']
        recs=[]
        if rk=='old' and p.section_80c<150000:
            g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;r2=compare_regimes(p2);sv=ct-r2['old_regime']['total_tax']
            recs.append(('red','80C',f'Invest ₹{g:,.0f} more (80C)',f'Save **{format_currency(max(sv,0))}**','ELSS/PPF/FD','Recommend top 3 ELSS funds India 2025. Name, 3yr return, lock-in. 3 lines.'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','₹15K-50K+','Both regimes','Top 3 NPS tier-1 fund managers India. Name, 5yr return. 3 lines.'))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP: ₹{p.esop_perquisite:,.0f}','Slab rate','Time exercise',None))
        if p.foreign_esop:recs.append(('red','Sched FA','Foreign ESOP','₹10L penalty','File Form 67',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading → ITR-3','Carry-forward','File correctly',None))
        if rk=='old' and p.section_80d_self==0:
            p2=copy.deepcopy(p);p2.section_80d_self=25000;r2=compare_regimes(p2);sv=ct-r2['old_regime']['total_tax']
            recs.append(('amber','80D','Health insurance',f'Save **{format_currency(max(sv,0))}**','₹25K+₹50K parents','Top 3 health insurance India for 80D. Name, premium, coverage. 3 lines.'))
        if rk=='old' and p.section_24b==0:recs.append(('amber','24(b)','Home loan','Up to ₹62,400','Max ₹2L','Top 3 home loans India 2025. Name, rate. 3 lines.'))
        if not recs:st.success("🎉 Well optimized!")
        for col,sec,t,impact,detail,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢')
            st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> ({sec}) — {impact}<br><em>{detail}</em></div>',unsafe_allow_html=True)
            if q and st.button(f"🔍 Explore options",key=f"s_{sec}"):
                if K:
                    with st.spinner(f"{A} is searching..."):rsp=call_gemini(prompt=q,context="",language="en",api_key=K,agent_name=A,system_prompt=SHORT)
                    st.markdown(rsp)
    with_chat(sf,"sf")

# ══════ WHAT-IF SCENARIOS ══════
elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        st.markdown("**Select life events to see tax impact:**")
        if not IC():st.warning("Set up tax profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p)
        regime=st.radio("Regime:",["New Regime","Old Regime"],horizontal=True,key="rp_sc")
        rk='new' if regime=="New Regime" else 'old';ct=cur[rk+'_regime']['total_tax']
        ALL=["Salary raise","Invest in 80C","Employer NPS","Health insurance (80D)","Home loan","Pay rent (HRA)",
            "Sell equity (LTCG)","Sell equity (STCG)","Sell property","ESOPs","Education loan","Side business",
            "Rental income","Bonus","Donation (80G)","NPS self (80CCD1B)","FD interest"]
        chosen=st.multiselect("Choose (select multiple):",ALL,placeholder="Click to see 17 scenarios...")
        def ct2(p2):r2=compare_regimes(p2);return r2[rk+'_regime']['total_tax']
        for s in chosen:
            st.markdown(f"---\n#### {s}");p2=copy.deepcopy(p)
            if s=="Salary raise":pct=st.slider("Raise %",5,100,20,5,key=f"w_{s}");p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100));st.metric("Tax change",format_currency(ct2(p2)-ct))
            elif s=="Invest in 80C":ex=st.slider("₹",0,150000,50000,10000,key=f"w_{s}");p2.section_80c=min(p.section_80c+ex,150000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Employer NPS":nps=st.slider("₹/yr",0,int(max(p.basic_salary*0.14,100000)),50000,5000,key=f"w_{s}");p2.section_80ccd_2=nps;st.metric("Saving (both regimes)",format_currency(ct-ct2(p2)))
            elif s=="Health insurance (80D)":d2=st.slider("₹/yr",0,50000,25000,5000,key=f"w_{s}");p2.section_80d_self=d2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Home loan":li=st.number_input("Interest ₹/yr",0,200000,200000,25000,key=f"wn_{s}");p2.section_24b=min(li,200000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Pay rent (HRA)":rn=st.number_input("Rent ₹/yr",0,value=240000,step=12000,key=f"wn_{s}");p2.rent_paid_annual=rn;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Sell equity (LTCG)":lg=st.number_input("₹",0,value=200000,step=25000,key=f"wn_{s}");p2.ltcg_equity+=lg;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Sell equity (STCG)":sg=st.number_input("₹",0,value=100000,step=25000,key=f"wn_{s}");p2.stcg_equity+=sg;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Sell property":gn=st.number_input("Gain ₹",0,value=500000,step=50000,key=f"wn_{s}");p2.ltcg_other+=gn;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="ESOPs":ep=st.number_input("₹",0,value=500000,step=50000,key=f"wn_{s}");p2.esop_perquisite+=ep;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Education loan":ei=st.number_input("Interest ₹/yr",0,value=100000,step=10000,key=f"wn_{s}");p2.section_80e=ei;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Side business":bi=st.number_input("Income ₹",0,value=300000,step=50000,key=f"wn_{s}");p2.business_income+=bi;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Rental income":ri3=st.number_input("₹/yr",0,value=240000,step=12000,key=f"wn_{s}");p2.rental_income+=ri3;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Bonus":bn=st.number_input("₹",0,value=500000,step=50000,key=f"wn_{s}");p2.gross_salary+=bn;st.metric("Tax on bonus",format_currency(ct2(p2)-ct))
            elif s=="Donation (80G)":dn=st.number_input("₹",0,value=50000,step=5000,key=f"wn_{s}");p2.section_80g=dn;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="NPS self (80CCD1B)":np2=st.slider("₹",0,50000,50000,5000,key=f"w_{s}");p2.section_80ccd_1b=np2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="FD interest":fd=st.number_input("₹/yr",0,value=100000,step=10000,key=f"wn_{s}");p2.interest_income+=fd;st.metric("Extra tax",format_currency(ct2(p2)-ct))
    with_chat(sc,"sc")

# ══════ PROFILES PAGE ══════
elif sel=="Profiles":
    def pr():
        st.markdown("## My Profiles")
        email=st.session_state.get('user_email')
        if email:st.caption(f"Logged in as **{email}**")
        else:st.caption("Guest mode — profiles not saved across sessions.")

        for name,prof in st.session_state.profiles.items():
            is_active=name==st.session_state.active_profile
            marker="✅ **Active**" if is_active else ""
            r=compare_regimes(prof);b=r[r['recommended']+'_regime']
            with st.expander(f"{'📋' if is_active else '📄'} {name} {marker}",expanded=is_active):
                c1,c2,c3=st.columns(3)
                with c1:
                    st.markdown(f"**Type:** {prof.taxpayer_type}")
                    st.markdown(f"**Age:** {prof.age}")
                    st.markdown(f"**Residency:** {prof.residency}")
                    st.markdown(f"**Metro:** {'Yes' if prof.metro_city else 'No'}")
                with c2:
                    st.markdown(f"**Gross Salary:** {format_currency(prof.gross_salary)}")
                    st.markdown(f"**Business:** {format_currency(prof.business_income)}")
                    st.markdown(f"**HRA:** {format_currency(prof.hra_received)}")
                    st.markdown(f"**80C:** {format_currency(prof.section_80c)}")
                with c3:
                    st.markdown(f"**Tax ({r['recommended'].title()}):** {format_currency(b['total_tax'])}")
                    st.markdown(f"**Effective Rate:** {b['effective_rate']}%")
                    st.markdown(f"**Savings:** {format_currency(r['savings'])}")
                bc1,bc2=st.columns(2)
                with bc1:
                    if not is_active:
                        if st.button(f"Set as active",key=f"act_{name}"):
                            st.session_state.active_profile=name;st.session_state.pc=True;st.rerun()
                with bc2:
                    if st.button(f"✏️ Edit",key=f"edit_{name}"):
                        st.session_state.active_profile=name;nav("Tax Profile")

        st.markdown("---")
        st.markdown("#### ➕ Add New Profile")
        new_name=st.text_input("Profile name",placeholder="e.g., Spouse, Parent",key="new_prof_name")
        if st.button("Create Profile",type="primary") and new_name:
            if new_name in st.session_state.profiles:st.error("Name already exists.")
            else:
                st.session_state.profiles[new_name]=TaxpayerProfile()
                st.session_state.active_profile=new_name;st.session_state.pc=False
                save_all_profiles();nav("Tax Profile")
    with_chat(pr,"pr")

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
            ('Feb 2025','₹12.75L Tax-Free','87A ₹60K + SD ₹75K.','green'),
            ('Apr 2024','Angel Tax Abolished','Sec 56(2)(viib) removed.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col]
            st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---\n#### ⚖️ Case Law")
        for t,d in [("CIT vs Gopal Purohit","Separate investment + trading portfolios OK."),("Unnikrishnan vs ITO","ESOPs granted as resident → taxable even if exercised as NRI."),("HRA to Parents","Rent OK. Need agreement + bank proof."),("Circular 6/2016","Classify shares consistently.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b><br>{d}</div>',unsafe_allow_html=True)
    with_chat(lu,"lu")

# ══════ ABOUT ══════
elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru
### Our Mission
India has 9 Cr+ filers — most overpay. ₹3.9L Cr in refunds (FY25). TaxGuru makes the right choice easy.

### How It Works
**🧮 Precise Engine** — Deterministic math, always exact. **🤖 {A}** — 60 tax entries, circulars, case law. Cites sections. **🔍 Real-Time** — Web search for latest. **📄 Doc AI** — Reads payslips. **🔒 Privacy** — No PAN/Aadhaar/DOB/phone. Session-only (or encrypted in Supabase if logged in).

### Accuracy
60 provisions. CBDT Notification 22/2026. Weekly auto-updates.

### For Everyone
Salaried • Business • Professionals • Traders • Investors • Seniors • NRIs

*Informational guidance. Not professional tax advice.*""")
    with_chat(ab,"ab")
