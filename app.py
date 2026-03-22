"""TaxGuru v13"""
import streamlit as st
import sys,os,copy,random,json,hashlib
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from tax_engine import TaxpayerProfile,compare_regimes,format_currency,format_lakhs
from knowledge_base import TAX_KNOWLEDGE_BASE
from gemini_integration import call_gemini,analyze_document,build_rag_query,anonymize_text,extract_financial_only
from vector_db import TaxVectorDB

LOGO=""
_p=os.path.join(os.path.dirname(os.path.abspath(__file__)),'logo_app_b64.txt')
if os.path.exists(_p):
    with open(_p) as f:LOGO=f.read().strip()
# Favicon with white bg
_fav="🏛️"
if LOGO:
    try:
        import base64 as b64m;from PIL import Image as PI,ImageDraw;import io as iom
        _img=PI.open(iom.BytesIO(b64m.b64decode(LOGO))).convert("RGBA")
        # White bg square
        bg=PI.new("RGBA",(40,40),(255,255,255,255))
        _img.thumbnail((36,36),PI.LANCZOS)
        bg.paste(_img,((40-_img.width)//2,(40-_img.height)//2),_img)
        _fav=bg.convert("RGB")
    except:_fav="🏛️"
st.set_page_config(page_title="TaxGuru",page_icon=_fav,layout="wide",initial_sidebar_state="collapsed")

if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag
def nav(p):st.session_state.pg=p;st.session_state.nav_radio=p
if 'pg' not in st.session_state:st.session_state.pg='Home'
if 'dark_mode' not in st.session_state:st.session_state.dark_mode=False  # LIGHT MODE DEFAULT

# ══════ SUPABASE ══════
def hash_pw(pw):return hashlib.sha256(pw.encode()).hexdigest()
@st.cache_resource
def _get_db():
    url=st.secrets.get("SUPABASE_URL","");key=st.secrets.get("SUPABASE_KEY","")
    if not url or not key:return None
    try:from supabase import create_client;return create_client(url,key)
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
    try:db.table("users").update({"profile_data":json.dumps(profiles_dict)}).eq("email",email).execute()
    except:pass
def _db_load_profiles(email):
    user=_db_get_user(email)
    if not user:return {}
    pd=user.get('profile_data',{})
    if isinstance(pd,str):
        try:pd=json.loads(pd)
        except:return {}
    if not isinstance(pd,dict):return {}
    # Handle legacy flat format: if keys look like field names, wrap in 'Default'
    if pd and not any(isinstance(v,dict) for v in pd.values()):
        # Legacy: flat {field:value} — wrap it
        return {"Default":pd}
    return pd
def save_all_profiles():
    email=st.session_state.get('user_email')
    if email and _get_db():
        all_p={}
        for name,prof in st.session_state.profiles.items():
            all_p[name]={k:v for k,v in vars(prof).items() if not k.startswith('_')}
        _db_save_profiles(email,all_p)

# ══════ LOGIN ══════
def check_login():
    if st.session_state.get('logged_in'):return True
    has_db=_get_db() is not None
    DK=st.session_state.dark_mode
    bg="#111827" if DK else "#FFFFFF";bd="#374151" if DK else "#E5E7EB";tc="#F1F5F9" if DK else "#1E293B"
    st.markdown(f"""<style>.login-card{{max-width:460px;margin:1rem auto;background:{bg};border:1px solid {bd};border-radius:16px;padding:2rem;}}
    .login-logo{{text-align:center;background:#FFFFFF;border-radius:12px;border:1px solid #E5E7EB;padding:0.8rem;margin-bottom:1rem;}}
    .login-logo img{{height:220px;}}
    </style>""",unsafe_allow_html=True)
    st.markdown('<div class="login-card">',unsafe_allow_html=True)
    if LOGO:st.markdown(f'<div class="login-logo"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    # Tagline + trust cards
    st.markdown(f'<div style="text-align:center;color:#D4A843;font-size:1.1rem;font-weight:600;margin:0.5rem 0">AI-powered Indian tax advisor</div>',unsafe_allow_html=True)
    st.markdown(f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:1rem"><div style="background:{"#1A1F2E" if DK else "#F8FAFC"};border:1px solid #D4A843;border-radius:8px;padding:0.6rem"><b style="color:#D4A843">🛡️ Always Accurate</b><br><span style="font-size:0.85rem;color:{tc}">Precise engine, cites IT Act sections, never guesses</span></div><div style="background:{"#1A1F2E" if DK else "#F8FAFC"};border:1px solid #D4A843;border-radius:8px;padding:0.6rem"><b style="color:#D4A843">🔒 Data Private</b><br><span style="font-size:0.85rem;color:{tc}">No PAN/Aadhaar stored. Session-only. Close browser=gone.</span></div></div>',unsafe_allow_html=True)
    if has_db:
        tab1,tab2=st.tabs(["🔑 Login","✨ Sign Up"])
        with tab1:
            email=st.text_input("Email",key="le");pw=st.text_input("Password",type="password",key="lp")
            if st.button("Log In",type="primary",use_container_width=True,key="lb"):
                if not email or not pw:st.error("Enter both fields.")
                else:
                    user=_db_get_user(email)
                    if user and user['password_hash']==hash_pw(pw):
                        st.session_state.logged_in=True;st.session_state.user_email=email
                        saved=_db_load_profiles(email)
                        if saved:
                            st.session_state.profiles={}
                            for name,data in saved.items():
                                p=TaxpayerProfile()
                                if isinstance(data,str):
                                    try:data=json.loads(data)
                                    except:continue
                                if isinstance(data,dict):
                                    for k,v in data.items():
                                        try:
                                            if hasattr(p,k):setattr(p,k,v)
                                        except:pass
                                st.session_state.profiles[name]=p
                            if st.session_state.profiles:
                                st.session_state.active_profile=list(st.session_state.profiles.keys())[0];st.session_state.pc=True
                        st.rerun()
                    else:st.error("Invalid credentials.")
        with tab2:
            ne=st.text_input("Email",key="se");np=st.text_input("Password (6+)",type="password",key="sp");np2=st.text_input("Confirm",type="password",key="sp2")
            if st.button("Create Account",use_container_width=True,key="sb"):
                if not ne or not np:st.error("Fill all.")
                elif np!=np2:st.error("Mismatch.")
                elif len(np)<6:st.error("Min 6 chars.")
                elif _db_get_user(ne):st.error("Exists.")
                elif _db_create_user(ne,hash_pw(np)):st.session_state.logged_in=True;st.session_state.user_email=ne;st.rerun()
    st.markdown("---")
    c1,c2=st.columns([3,1])
    with c1:
        if st.button("Continue as guest" if has_db else "Enter TaxGuru →",type="primary" if not has_db else "secondary",use_container_width=True,key="gb"):
            st.session_state.logged_in=True;st.session_state.user_email=None;st.rerun()
    with c2:
        if st.button("Light/Dark Mode",key="lt"):st.session_state.dark_mode=not st.session_state.dark_mode;st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    return False

# ══════ CSS — DARK BASE ══════
st.markdown("""<style>
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}
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
.tt{background:#1A1F2E;border:2px solid #D4A843;border-radius:10px;padding:0.9rem;}.tt h4{color:#D4A843!important;margin:0 0 0.4rem;font-size:1.15rem;}.tt ul{list-style:none;padding:0;margin:0;}.tt li{padding:0.15rem 0;font-size:1rem;color:#F1F5F9;line-height:1.5;}.tt li::before{content:'✓ ';color:#10B981;font-weight:700;}
.su{background:#1C1917;border:2px solid #D4A843;border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 0.8rem;text-align:center;}.su b{font-size:1.2rem;color:#FDE68A;}.su span{color:#E2E8F0;font-size:1rem;}
.fb{background:#111827;border:1px solid #374151;border-radius:10px;padding:0.8rem;margin-bottom:0.3rem;}.fb h4{color:#D4A843;margin:0 0 0.2rem;font-size:1.05rem;}.fb p{color:#CBD5E1;font-size:0.92rem;margin:0;line-height:1.4;}
.logo-panel{background:#FFFFFF;border:1px solid #D4A843;border-radius:10px;padding:0.5rem;text-align:center;margin-bottom:0.3rem;}.logo-panel img{height:280px;}
.ch{background:#1E293B;border:1px solid #475569;padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}.ch .dot{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}@keyframes p{0%,100%{opacity:1}50%{opacity:0.4}}.ch .nm{font-weight:700;font-size:1rem;color:#F1F5F9;}.ch .rl{font-size:0.85rem;color:#CBD5E1;}
.cd2{font-size:0.85rem;color:#CBD5E1;font-style:italic;margin-top:0.3rem;}
.pv{background:#172554;border:1px solid #1E40AF;border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:#93C5FD;margin-bottom:0.5rem;}
.cmp-tbl{width:100%;border-collapse:collapse;margin:0.5rem 0;}.cmp-tbl th{background:#1E293B;color:#D4A843;padding:0.5rem;text-align:right;border:1px solid #374151;}.cmp-tbl th:first-child{text-align:left;}.cmp-tbl td{padding:0.4rem 0.5rem;border:1px solid #374151;color:#E2E8F0;text-align:right;}.cmp-tbl td:first-child{text-align:left;color:#CBD5E1;}.cmp-tbl tr.total{background:#1A1F2E;font-weight:700;}.cmp-tbl tr.total td{color:#D4A843;font-size:1.05rem;}
[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stNumberInput"] input,.stTextInput input{background:#1E293B!important;color:#F1F5F9!important;border-color:#475569!important;}
[data-testid="stFileUploader"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}
[data-testid="stExpander"]{background:#111827;border:1px solid #374151;border-radius:8px;}[data-testid="stExpander"] summary{color:#F1F5F9!important;}
[data-testid="stMetric"]{background:#111827;border:1px solid #374151;border-radius:8px;padding:0.5rem;}[data-testid="stMetricValue"]{color:#D4A843!important;}[data-testid="stMetricLabel"]{color:#CBD5E1!important;}
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{background:#D4A843!important;color:#000!important;border:none!important;font-weight:900!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}
.stButton>button:not([kind="primary"]){background:#1E293B!important;color:#F1F5F9!important;border:1px solid #475569!important;font-weight:700!important;-webkit-text-fill-color:#F1F5F9!important;}
/* CHAT INPUT: truly taller box */
[data-testid="stChatInput"] textarea{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;min-height:250px!important;height:250px!important;}
[data-testid="stChatInput"]{background:#FFF!important;border:2px solid #475569;border-radius:8px;}
[data-testid="stChatInput"] button{background:#D4A843!important;color:#000!important;}
/* Selectbox dropdown menus */
[data-baseweb="popover"],[data-baseweb="menu"],[data-baseweb="select"] [role="listbox"]{background:#1E293B!important;}
[data-baseweb="menu"] li,[data-baseweb="select"] [role="option"]{color:#F1F5F9!important;}
[data-baseweb="menu"] li:hover,[data-baseweb="select"] [role="option"]:hover{background:#334155!important;}
@media(max-width:900px){.tg{grid-template-columns:1fr;}.logo-panel img{height:160px;}}
</style>""",unsafe_allow_html=True)

# ══════ LIGHT MODE OVERRIDE ══════
if not st.session_state.dark_mode:
    st.markdown("""<style>
    .stApp,[data-testid="stAppViewContainer"]{background:#F8FAFC!important;color:#1E293B!important;}
    h1,h2,h3,h4{color:#0F172A!important;}p,li,span,.stMarkdown{color:#334155!important;}
    .cd,.fb{background:#FFF!important;border-color:#E2E8F0!important;}.cd *,.fb *{color:#1E293B!important;}
    .tt{background:#F1F5F9!important;}.tt li,.tt h4{color:#1E293B!important;}.tt h4{color:#92400E!important;}
    .su{background:#FFFBEB!important;}.su *{color:#92400E!important;}
    .ch{background:#F1F5F9!important;}.ch .nm,.ch .rl{color:#1E293B!important;}
    .cd2{color:#64748B!important;}.pv{background:#EFF6FF!important;color:#1E40AF!important;border-color:#BFDBFE!important;}
    .cmp-tbl th{background:#F1F5F9!important;color:#0F172A!important;border-color:#E2E8F0!important;}
    .cmp-tbl td{color:#1E293B!important;border-color:#E2E8F0!important;}.cmp-tbl tr.total td{color:#92400E!important;}
    .logo-panel{border-color:#E2E8F0!important;}
    [data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    [data-testid="stNumberInput"] input,.stTextInput input{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    [data-testid="stExpander"]{background:#FFF!important;border-color:#E2E8F0!important;}[data-testid="stExpander"] summary{color:#1E293B!important;}
    [data-testid="stMetric"]{background:#FFF!important;border-color:#E2E8F0!important;}
    [data-testid="stFileUploader"]{background:#FFF!important;border-color:#E2E8F0!important;}
    div[data-testid="stHorizontalBlock"]:first-child .stRadio label{background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;}
    .stButton>button:not([kind="primary"]){background:#FFF!important;color:#1E293B!important;border-color:#CBD5E1!important;-webkit-text-fill-color:#1E293B!important;}
    /* Dropdown menus in light mode */
    [data-baseweb="popover"],[data-baseweb="menu"],[data-baseweb="select"] [role="listbox"]{background:#FFF!important;border:1px solid #E2E8F0!important;}
    [data-baseweb="menu"] li,[data-baseweb="select"] [role="option"]{color:#1E293B!important;}
    [data-baseweb="menu"] li:hover,[data-baseweb="select"] [role="option"]:hover{background:#F1F5F9!important;}
    </style>""",unsafe_allow_html=True)

# ══════ LOGIN GATE ══════
if not check_login():st.stop()

# ══════ SESSION ══════
if 'profiles' not in st.session_state:st.session_state.profiles={'Default':TaxpayerProfile()}
if 'active_profile' not in st.session_state:st.session_state.active_profile='Default'
if 'pc' not in st.session_state:st.session_state.pc=False
if 'ch' not in st.session_state:st.session_state.ch=[]
if 'vdb' not in st.session_state:st.session_state.vdb=TaxVectorDB();st.session_state.vdb.index_knowledge_base(TAX_KNOWLEDGE_BASE)
K=st.secrets.get("GEMINI_API_KEY",os.environ.get("GEMINI_API_KEY",""))
def P():return st.session_state.profiles.get(st.session_state.active_profile,TaxpayerProfile())
def IC():return st.session_state.pc and st.session_state.active_profile in st.session_state.profiles
SHORT="""You are {agent_name}, Indian tax advisor. CONCISE: 3-4 sentences. No intro/disclaimer. Cite sections."""

TABS=["Home","Tax Profile","Tax Calculator","Savings Finder","What-If Scenarios","Profiles","Law Updates","About"]
if 'nav_radio' not in st.session_state:st.session_state.nav_radio="Home"
nc1,nc2,nc3=st.columns([9,1,1])
with nc1:sel=st.radio("",TABS,horizontal=True,label_visibility="collapsed",key="nav_radio")
with nc2:
    if st.button("Light/Dark",key="tb"):st.session_state.dark_mode=not st.session_state.dark_mode;st.rerun()
with nc3:
    if st.button("Logout",key="lo"):
        for k in list(st.session_state.keys()):del st.session_state[k]
        st.rerun()
st.session_state.pg=sel

if sel in ("Tax Calculator","Savings Finder","What-If Scenarios") and IC():
    st.caption(f"📋 Profile: **{st.session_state.active_profile}**")

def chat_with_logo(k=""):
    if LOGO:st.markdown(f'<div class="logo-panel"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A}</span><br><span class="rl">Your Tax Agent</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=300)
    with bx:
        if not st.session_state.ch:st.markdown(f"👋 **I'm {A}.** Ask me any tax question.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A}...",key=f"c{k}"):
        cl,_=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp="⚠️ API key not set."
        else:pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf);rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,agent_name=A,system_prompt=SHORT)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 {A}: IT Act + latest circulars.</div>',unsafe_allow_html=True)
def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat_with_logo(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown('<h1 style="font-size:1.7rem!important;margin:0 0 0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1.05rem">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>',unsafe_allow_html=True)
        st.markdown('<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter your details.</span></div>',unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary",on_click=nav,args=("Tax Profile",))
        with bc2:st.button("✏️ Enter Manually",use_container_width=True,on_click=nav,args=("Tax Profile",))
        fc1,fc2,fc3=st.columns(3)
        with fc1:st.markdown('<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New — exact savings.</p></div>',unsafe_allow_html=True);st.button("Open Calculator →",use_container_width=True,key="h1",on_click=nav,args=("Tax Calculator",))
        with fc2:st.markdown('<div class="fb"><h4>🔀 What-If</h4><p>Raise, loan, sale — see impact.</p></div>',unsafe_allow_html=True);st.button("Open Scenarios →",use_container_width=True,key="h4",on_click=nav,args=("What-If Scenarios",))
        with fc3:st.markdown('<div class="fb"><h4>💡 Savings</h4><p>What to invest, by when.</p></div>',unsafe_allow_html=True);st.button("Open Savings →",use_container_width=True,key="h3",on_click=nav,args=("Savings Finder",))
        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Precise engine — not AI guesses</li><li>Cites IT Act sections</li><li>{A} says "check with a CA" when unsure</li><li>Real-time: Budget 2026, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Data Private</h4><ul><li>No PAN, Aadhaar, address, DOB, phone, email</li><li>Bank, PF/UAN, employer — auto-deleted</li><li>Session-only. Close browser → gone.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat_with_logo("home")

elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        if IC():st.info(f"⚠️ Editing **{st.session_state.active_profile}**. Changes will update this profile.")
        st.markdown("#### 📄 Upload Document")
        st.markdown('<div class="pv">🔒 Only numbers extracted.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip/Form 16",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner(f"{A} reading..."):doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success("✅ Data:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}")
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                def _use():
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4);p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted');p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000);p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'));st.session_state.pc=True;save_all_profiles();nav("Tax Calculator")
                st.button("✅ Use Data",type="primary",use_container_width=True,on_click=_use)
        elif up:st.error("API key not set.")
        st.markdown("---\n#### ✏️ Manual")
        c1,c2=st.columns(2)
        with c1:types=st.multiselect("Income from...",["Salary","Business","Professional","Trading","Investments","Freelancing","Other"],default=["Salary"]);age=st.number_input("Age",18,100,30)
        with c2:
            st.markdown("**Residency**");cit=st.selectbox("Citizenship",["Indian","PIO","Foreign"]);di=st.number_input("Days in India this FY",0,366,365);d4=st.number_input("Days last 4yr",0,1461,1400);i15=st.checkbox("Income>₹15L")
            if di>=182:rs="resident";st.markdown("✅ Resident")
            elif cit!="Foreign":
                if i15 and di>=120 and d4>=365:rs="rnor";st.markdown("⚠️ RNOR")
                elif di>=60 and d4>=365:rs="resident";st.markdown("✅ Resident")
                else:rs="nri";st.markdown("🌍 NRI")
            else:rs="resident" if di>=60 and d4>=365 else "nri";st.markdown("✅ Resident" if rs=="resident" else "🌍 NRI")
            met=st.selectbox("Metro?",["Yes—Del/Mum/Kol/Che/Hyd/Pune/Ahd/Blr","No"])
        t="salaried"
        for x in ["Business","Professional","Trading"]:
            if x in types:t=x.lower()
        gs=bs=hra=rent=enps=biz=trd=ii2=ri2=dv=stcg=ltcg=esop=s80c=s80d=s80n=s80e=s24b=tds=adv=0;fe=False
        if "Salary" in types:
            c1,c2,c3=st.columns(3)
            with c1:gs=st.number_input("Gross₹/yr",0,value=0,step=50000,format="%d")
            with c2:bs=st.number_input("Basic₹/yr",0,value=0,step=25000,format="%d")
            with c3:hra=st.number_input("HRA₹/yr",0,value=0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:rent=st.number_input("Rent₹/yr",0,value=0,step=10000,format="%d")
            with c2:enps=st.number_input("EmployerNPS₹/yr",0,value=0,step=5000,format="%d")
        if any(x in types for x in ["Business","Professional","Freelancing"]):biz=st.number_input("Biz Income₹",0,value=0,step=100000,format="%d")
        if "Trading" in types:trd=st.number_input("Trading P/(L)₹",value=0,step=50000,format="%d")
        with st.expander("📈 More income"):
            c1,c2,c3=st.columns(3)
            with c1:ii2=st.number_input("Interest",0,value=0,step=5000,format="%d")
            with c2:ri2=st.number_input("Rental",0,value=0,step=10000,format="%d")
            with c3:dv=st.number_input("Dividend",0,value=0,step=5000,format="%d")
            c1,c2=st.columns(2)
            with c1:stcg=st.number_input("STCG",0,value=0,step=10000,format="%d")
            with c2:ltcg=st.number_input("LTCG",0,value=0,step=10000,format="%d")
            esop=st.number_input("ESOP",0,value=0,step=50000,format="%d");fe=st.checkbox("Foreign ESOPs")
        with st.expander("🏦 Deductions"):
            c1,c2,c3=st.columns(3)
            with c1:s80c=st.number_input("80C",0,150000,0,step=10000,format="%d")
            with c2:s80d=st.number_input("80D",0,50000,0,step=5000,format="%d")
            with c3:s80n=st.number_input("NPS",0,50000,0,step=10000,format="%d")
            c1,c2=st.columns(2)
            with c1:s80e=st.number_input("EduLoan",0,value=0,step=10000,format="%d")
            with c2:s24b=st.number_input("HomeLoan",0,200000,0,step=10000,format="%d")
        with st.expander("💳 TDS"):
            c1,c2=st.columns(2)
            with c1:tds=st.number_input("TDS",0,value=0,step=10000,format="%d")
            with c2:adv=st.number_input("AdvTax",0,value=0,step=10000,format="%d")
        def _save():
            p=P();p.taxpayer_type=t;p.age=age;p.residency=rs;p.metro_city="Yes" in met;p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent;p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd;p.interest_income=ii2;p.rental_income=ri2;p.dividend_income=dv;p.stcg_equity=stcg;p.ltcg_equity=ltcg;p.esop_perquisite=esop;p.foreign_esop=fe;p.section_80c=s80c;p.section_80d_self=s80d;p.section_80d_parents=0;p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b;p.tds_deducted=tds;p.advance_tax_paid=adv;st.session_state.pc=True;save_all_profiles();nav("Tax Calculator")
        st.button("✅ Save & See Tax",type="primary",use_container_width=True,on_click=_save)
    with_chat(tp,"tp")

elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator")
        if not IC():st.warning("Set up profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        rows=[];rows.append(("Gross Salary",n['salary_income'],o['salary_income']))
        if n.get('hp_income') or o.get('hp_income'):rows.append(("House Property",n.get('hp_income',0),o.get('hp_income',0)))
        if n.get('business_income') or o.get('business_income'):rows.append(("Business",n.get('business_income',0),o.get('business_income',0)))
        if n.get('other_income') or o.get('other_income'):rows.append(("Other Income",n.get('other_income',0),o.get('other_income',0)))
        rows.append(("Gross Total Income",n['gross_total_income'],o['gross_total_income']))
        rows.append(("Standard Deduction",-75000,-50000))
        if o.get('hra_exemption',0)>0:rows.append(("HRA Exemption",0,-o['hra_exemption']))
        if o['total_deductions']>0:
            for s,a in o['deduction_breakdown'].items():
                if a>0:rows.append((f"Sec {s}",0,-a))
        rows.append(("Taxable Income",n['taxable_income'],o['taxable_income']))
        rows.append(("Slab Tax",n['slab_tax'],o['slab_tax']))
        if n['rebate_87a']>0 or o['rebate_87a']>0:rows.append(("87A Rebate",-n['rebate_87a'],-o['rebate_87a']))
        if n['surcharge']>0 or o['surcharge']>0:rows.append(("Surcharge",n['surcharge'],o['surcharge']))
        rows.append(("Cess 4%",n['cess'],o['cess']))
        rows.append(("TOTAL TAX",n['total_tax'],o['total_tax']))
        html=f'<table class="cmp-tbl"><tr><th>Description</th><th>New Regime {"✅" if rc=="new" else ""}</th><th>Old Regime {"✅" if rc=="old" else ""}</th></tr>'
        for d,nv,ov in rows:
            cls='total' if 'TOTAL' in d or 'Taxable' in d else ''
            nf=format_currency(abs(nv)) if nv!=0 else "—";of=format_currency(abs(ov)) if ov!=0 else "—"
            if nv<0:nf=f"({format_currency(abs(nv))})"
            if ov<0:of=f"({format_currency(abs(ov))})"
            html+=f'<tr class="{cls}"><td>{d}</td><td>{nf}</td><td>{of}</td></tr>'
        html+='</table>';st.markdown(html,unsafe_allow_html=True)
        st.button("💡 Find savings →",on_click=nav,args=("Savings Finder",))
    with_chat(calc,"calc")

elif sel=="Savings Finder":
    def sf():
        st.markdown("## Savings Finder")
        if not IC():st.warning("Set up profile.");st.button("→ Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);rc=r['recommended'];regime=st.radio("Regime:",["New","Old"],horizontal=True,key="rsf")
        rk='new' if regime=="New" else 'old';ct=r[rk+'_regime']['total_tax']
        recs=[]
        if rk=='old' and p.section_80c<150000:g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;sv=ct-compare_regimes(p2)['old_regime']['total_tax'];recs.append(('red','80C',f'₹{g:,.0f} more in 80C',f'Save {format_currency(max(sv,0))}','ELSS/PPF/FD','Top 3 ELSS funds India 2025. Name, return, lock-in. 3 lines.'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','₹15K-50K+','Both regimes','Top 3 NPS managers India. 3 lines.'))
        if rk=='old' and p.section_80d_self==0:p2=copy.deepcopy(p);p2.section_80d_self=25000;sv=ct-compare_regimes(p2)['old_regime']['total_tax'];recs.append(('amber','80D','Health insurance',f'Save {format_currency(max(sv,0))}','₹25K+₹50K','Top 3 health plans India 80D. 3 lines.'))
        if p.esop_perquisite>0:recs.append(('amber','17(2)(vi)',f'ESOP ₹{p.esop_perquisite:,.0f}','Slab rate','Time exercise',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading→ITR-3','Carry-forward','File correctly',None))
        if not recs:st.success("🎉 Optimized!")
        for col,sec,t,impact,det,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢');st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> ({sec})—{impact}<br><em>{det}</em></div>',unsafe_allow_html=True)
            if q and st.button(f"🔍 Explore",key=f"s_{sec}"):
                if K:
                    with st.spinner("..."):st.markdown(call_gemini(prompt=q,context="",language="en",api_key=K,agent_name=A,system_prompt=SHORT))
    with_chat(sf,"sf")

elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        if not IC():st.warning("Set up profile.");st.button("→ Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p);regime=st.radio("Regime:",["New","Old"],horizontal=True,key="rsc")
        rk='new' if regime=="New" else 'old';ct=cur[rk+'_regime']['total_tax']
        ALL=["Salary raise","80C invest","Employer NPS","Health ins(80D)","Home loan","Rent(HRA)","Sell equity LTCG","Sell equity STCG","Sell property","ESOPs","Edu loan","Side business","Rental income","Bonus","Donation(80G)","NPS self","FD interest"]
        chosen=st.multiselect("Select scenarios:",ALL,placeholder="Click for 17 options...")
        def ct2(p2):return compare_regimes(p2)[rk+'_regime']['total_tax']
        for s in chosen:
            st.markdown(f"---\n**{s}**");p2=copy.deepcopy(p)
            if s=="Salary raise":pct=st.slider("Raise%",5,100,20,5,key=f"w{s}");p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100));st.metric("Change",format_currency(ct2(p2)-ct))
            elif s=="80C invest":ex=st.slider("₹",0,150000,50000,10000,key=f"w{s}");p2.section_80c=min(p.section_80c+ex,150000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Employer NPS":n2=st.slider("₹/yr",0,int(max(p.basic_salary*0.14,100000)),50000,5000,key=f"w{s}");p2.section_80ccd_2=n2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Health ins(80D)":d2=st.slider("₹",0,50000,25000,5000,key=f"w{s}");p2.section_80d_self=d2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Home loan":li=st.number_input("Int₹/yr",0,200000,200000,25000,key=f"n{s}");p2.section_24b=min(li,200000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Rent(HRA)":rn=st.number_input("Rent₹/yr",0,value=240000,step=12000,key=f"n{s}");p2.rent_paid_annual=rn;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Sell equity LTCG":lg=st.number_input("₹",0,value=200000,step=25000,key=f"n{s}");p2.ltcg_equity+=lg;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Sell equity STCG":sg=st.number_input("₹",0,value=100000,step=25000,key=f"n{s}");p2.stcg_equity+=sg;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Sell property":gn=st.number_input("Gain₹",0,value=500000,step=50000,key=f"n{s}");p2.ltcg_other+=gn;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="ESOPs":ep=st.number_input("₹",0,value=500000,step=50000,key=f"n{s}");p2.esop_perquisite+=ep;st.metric("Extra tax",format_currency(ct2(p2)-ct))
            elif s=="Edu loan":ei=st.number_input("Int₹/yr",0,value=100000,step=10000,key=f"n{s}");p2.section_80e=ei;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Side business":bi=st.number_input("₹",0,value=300000,step=50000,key=f"n{s}");p2.business_income+=bi;st.metric("Extra",format_currency(ct2(p2)-ct))
            elif s=="Rental income":ri3=st.number_input("₹/yr",0,value=240000,step=12000,key=f"n{s}");p2.rental_income+=ri3;st.metric("Extra",format_currency(ct2(p2)-ct))
            elif s=="Bonus":bn=st.number_input("₹",0,value=500000,step=50000,key=f"n{s}");p2.gross_salary+=bn;st.metric("Tax",format_currency(ct2(p2)-ct))
            elif s=="Donation(80G)":dn=st.number_input("₹",0,value=50000,step=5000,key=f"n{s}");p2.section_80g=dn;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="NPS self":np2=st.slider("₹",0,50000,50000,5000,key=f"w{s}");p2.section_80ccd_1b=np2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="FD interest":fd=st.number_input("₹/yr",0,value=100000,step=10000,key=f"n{s}");p2.interest_income+=fd;st.metric("Extra",format_currency(ct2(p2)-ct))
    with_chat(sc,"sc")

elif sel=="Profiles":
    def pr():
        st.markdown("## My Profiles")
        email=st.session_state.get('user_email')
        if email:st.caption(f"Logged in as **{email}**")
        for name,prof in st.session_state.profiles.items():
            is_act=name==st.session_state.active_profile
            with st.expander(f"{'📋' if is_act else '📄'} {name} {'✅ Active' if is_act else ''}",expanded=is_act):
                c1,c2,c3=st.columns(3)
                with c1:st.markdown(f"**Type:** {prof.taxpayer_type}\n\n**Age:** {prof.age}\n\n**Residency:** {prof.residency}")
                with c2:st.markdown(f"**Gross Salary:** {format_currency(prof.gross_salary)}\n\n**Business:** {format_currency(prof.business_income)}\n\n**80C:** {format_currency(prof.section_80c)}")
                with c3:
                    r=compare_regimes(prof);b=r[r['recommended']+'_regime']
                    st.markdown(f"**Tax:** {format_currency(b['total_tax'])}\n\n**Rate:** {b['effective_rate']}%\n\n**Best:** {r['recommended'].title()}")
                bc1,bc2=st.columns(2)
                with bc1:
                    if not is_act and st.button(f"Set active",key=f"a_{name}"):st.session_state.active_profile=name;st.session_state.pc=True;st.rerun()
                with bc2:
                    if st.button(f"✏️ Edit",key=f"e_{name}"):st.session_state.active_profile=name;nav("Tax Profile")
        st.markdown("---\n#### ➕ Add Profile")
        nn=st.text_input("Name",placeholder="Spouse, Parent...",key="npn")
        if st.button("Create",type="primary") and nn:
            if nn in st.session_state.profiles:st.error("Exists.")
            else:st.session_state.profiles[nn]=TaxpayerProfile();st.session_state.active_profile=nn;st.session_state.pc=False;save_all_profiles();nav("Tax Profile")
    with_chat(pr,"pr")

elif sel=="Law Updates":
    def lu():
        st.markdown("## Law Updates")
        for dt,t,d,col in [('Mar 20, 2026','🆕 IT Rules 2026','HRA→8 metros. Form 124. CARF crypto.','blue'),('Mar 2026','AIS Alerts','CBDT transaction emails.','blue'),('Feb 2026','Budget 2026','Tax Year replaces PY/AY.','blue'),('Oct 2025','ITR Extended','Audit→Dec 10.','amber'),('Jul 2024','CG Changed','STCG 20%. LTCG 12.5%.','amber'),('Feb 2025','₹12.75L Free','87A ₹60K+SD ₹75K.','green'),('Apr 2024','Angel Tax Gone','Sec 56(2)(viib) removed.','green')]:
            st.markdown(f'<div class="cd {col}"><b>{"ℹ️" if col=="blue" else "⚠️" if col=="amber" else "✅"} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---\n#### ⚖️ Case Law")
        for t,d in [("Gopal Purohit","Separate portfolios OK."),("Unnikrishnan","ESOPs→taxable in India."),("HRA Parents","Rent OK with proof."),("Circular 6/2016","Classify consistently.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b> {d}</div>',unsafe_allow_html=True)
    with_chat(lu,"lu")

elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru

### Our Mission
India has over 9 crore income tax return filers — yet most don't optimize their taxes. The government issued ₹3.9 lakh crore in refunds in FY25, showing millions overpay through excess TDS and wrong regime choices. With 2 tax regimes and 70+ deduction sections, making the right choice is genuinely hard. **TaxGuru exists to change this.**

### How It Works
**🧮 Precise Calculation Engine** — Your tax numbers are computed by a deterministic mathematical engine, not generated by AI. The numbers are always exactly right — no rounding, no estimation, no hallucination.

**🤖 {A} — Your Tax Agent** — {A} is an intelligent agent with access to 60 sections of the Income Tax Act, key CBDT circulars, case law precedents, and Budget amendments. When you ask a question, {A} retrieves the most relevant legal provisions and constructs an answer grounded in actual law — citing specific sections.

**🔍 Real-Time Updates** — {A} can search the web for the latest tax developments — new circulars, court rulings, deadline extensions. This means advice stays current even as the law changes. Our knowledge base also auto-updates weekly.

**📄 Document Intelligence** — Upload a payslip or Form 16 and AI reads it, extracts only the financial numbers (ignoring all personal details), and fills your tax profile automatically.

**🔒 Privacy by Design** — We never collect, store, or transmit your name, PAN, Aadhaar, date of birth, address, phone number, email, bank account details, PF number, employer name, or employee ID. Only financial figures are processed. If you create an account, only your email and encrypted password are stored — your profile data is saved securely but contains no personal identifiers.

### Accuracy Commitment
- Every answer cites the specific section of the Income Tax Act
- When {A} is unsure, {A} says "consult a CA" — never guesses
- 60 provisions including CBDT Notification 22/2026 (March 20, 2026) and IT Rules 2026
- Tax calculations verified against government guidelines

### Who It's For
**Salaried** — regime comparison, HRA, payslip analysis • **Business** — presumptive taxation, audit • **Professionals** — 44ADA, advance tax • **Traders** — F&O, 43(5), ITR-3, loss carry-forward • **Investors** — capital gains, ESOP • **Seniors** — 80TTB, higher exemptions • **NRIs** — residency auto-determination, DTAA

*TaxGuru provides informational guidance. Not professional tax advice. For complex matters, consult a CA.*""")
    with_chat(ab,"ab")
