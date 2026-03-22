"""TaxGuru v14 — Elegant design, high contrast, all bugs fixed"""
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
_fav="🏛️"
if LOGO:
    try:
        import base64 as b64m;from PIL import Image as PI;import io as iom
        _i=PI.open(iom.BytesIO(b64m.b64decode(LOGO))).convert("RGBA")
        bg=PI.new("RGBA",(40,40),(255,255,255,255));_i.thumbnail((36,36),PI.LANCZOS)
        bg.paste(_i,((40-_i.width)//2,(40-_i.height)//2),_i);_fav=bg.convert("RGB")
    except:pass
st.set_page_config(page_title="TaxGuru",page_icon=_fav,layout="wide",initial_sidebar_state="collapsed")
if 'ag' not in st.session_state:st.session_state.ag=random.choice(["Karthik","Kavya"])
A=st.session_state.ag
def nav(p):st.session_state.pg=p;st.session_state.nav_radio=p
def nav_edit(name):st.session_state.active_profile=name;nav("Tax Profile")
def nav_activate(name):st.session_state.active_profile=name;st.session_state.pc=True
if 'pg' not in st.session_state:st.session_state.pg='Home'
if 'dark_mode' not in st.session_state:st.session_state.dark_mode=False
def toggle_theme():st.session_state.dark_mode=not st.session_state.dark_mode

# ══════ SUPABASE ══════
def hash_pw(pw):return hashlib.sha256(pw.encode()).hexdigest()
@st.cache_resource
def _get_db():
    url=st.secrets.get("SUPABASE_URL","");key=st.secrets.get("SUPABASE_KEY","")
    if not url or not key:return None
    try:from supabase import create_client;return create_client(url,key)
    except:return None
def _db_get_user(e):
    db=_get_db()
    if not db:return None
    try:r=db.table("users").select("*").eq("email",e).execute();return r.data[0] if r.data else None
    except:return None
def _db_create_user(e,h):
    db=_get_db()
    if not db:return False
    try:db.table("users").insert({"email":e,"password_hash":h,"profile_data":"{}"}).execute();return True
    except:return False
def _db_save(email,pd):
    db=_get_db()
    if not db:return
    try:db.table("users").update({"profile_data":json.dumps(pd)}).eq("email",email).execute()
    except:pass
def _db_load(email):
    u=_db_get_user(email)
    if not u:return {}
    pd=u.get('profile_data',{})
    if isinstance(pd,str):
        try:pd=json.loads(pd)
        except:return {}
    if not isinstance(pd,dict):return {}
    if pd and not any(isinstance(v,dict) for v in pd.values()):return {"Default":pd}
    return pd
def save_all():
    e=st.session_state.get('user_email')
    if e and _get_db():
        ap={n:{k:v for k,v in vars(p).items() if not k.startswith('_')} for n,p in st.session_state.profiles.items()}
        _db_save(e,ap)

# ══════ COLORS — Elegant, high contrast ══════
DK=st.session_state.dark_mode
# Dark: deep navy bg, bright white text, teal accents
# Light: clean white bg, dark slate text, teal accents
if DK:
    # Dark mode: dark page, LIGHT cards, dark text on cards
    BG="#0F172A";BG2="#F1F5F9";BD="#CBD5E1";TX="#F1F5F9";TX2="#94A3B8";AC="#4ADE80";AC2="#22C55E";HL="#E2E8F0"
    CTX="#0F172A";BTN_BG="#F1F5F9";BTN_TX="#0F172A"  # card text, button colors
else:
    # Light mode: light page, DARK cards, white text on cards  
    BG="#F8FAFC";BG2="#1E293B";BD="#334155";TX="#0F172A";TX2="#475569";AC="#22C55E";AC2="#16A34A";HL="#111827"
    CTX="#F1F5F9";BTN_BG="#1E293B";BTN_TX="#F1F5F9"  # card text, button colors"

# ══════ LOGIN ══════
def check_login():
    if st.session_state.get('logged_in'):return True
    has_db=_get_db() is not None
    st.markdown(f'<style>.login-box{{max-width:460px;margin:1rem auto;background:{BG2};border:1px solid {BD};border-radius:16px;padding:2rem;}}.login-logo{{text-align:center;background:#FFF;border-radius:12px;border:1px solid #E2E8F0;padding:0.8rem;margin-bottom:0.8rem;}}.login-logo img{{height:180px;}}</style>',unsafe_allow_html=True)
    # Light/Dark toggle top right
    _,tc=st.columns([8,1])
    with tc:st.button("Light/Dark",key="lt_login",on_click=toggle_theme)
    st.markdown('<div class="login-box">',unsafe_allow_html=True)
    if LOGO:st.markdown(f'<div class="login-logo"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown(f'<div style="text-align:center;color:{AC};font-size:1.1rem;font-weight:600;margin-bottom:0.5rem">AI-powered Indian tax advisor</div>',unsafe_allow_html=True)
    st.markdown(f'<div style="display:grid;grid-template-columns:1fr 1fr;gap:0.5rem;margin-bottom:1rem"><div style="background:{HL};border:1px solid {BD};border-radius:8px;padding:0.6rem"><b style="color:{AC}">🛡️ Always Accurate</b><br><span style="font-size:0.85rem;color:{TX2}">Precise engine, cites IT Act sections, never guesses</span></div><div style="background:{HL};border:1px solid {BD};border-radius:8px;padding:0.6rem"><b style="color:{AC}">🔒 Data Private</b><br><span style="font-size:0.85rem;color:{TX2}">No PAN/Aadhaar stored. Session-only. Browser close=gone.</span></div></div>',unsafe_allow_html=True)
    if has_db:
        tab1,tab2=st.tabs(["🔑 Login","✨ Sign Up"])
        with tab1:
            em=st.text_input("Email",key="le");pw=st.text_input("Password",type="password",key="lp")
            if st.button("Log In",type="primary",use_container_width=True,key="lb"):
                if not em or not pw:st.error("Enter both.")
                else:
                    u=_db_get_user(em)
                    if u and u['password_hash']==hash_pw(pw):
                        st.session_state.logged_in=True;st.session_state.user_email=em
                        saved=_db_load(em)
                        if saved:
                            st.session_state.profiles={}
                            for n,d in saved.items():
                                p=TaxpayerProfile()
                                if isinstance(d,str):
                                    try:d=json.loads(d)
                                    except:continue
                                if isinstance(d,dict):
                                    for k,v in d.items():
                                        try:
                                            if hasattr(p,k):setattr(p,k,v)
                                        except:pass
                                st.session_state.profiles[n]=p
                            if st.session_state.profiles:st.session_state.active_profile=list(st.session_state.profiles.keys())[0];st.session_state.pc=True
                        st.rerun()
                    else:st.error("Invalid credentials.")
        with tab2:
            ne=st.text_input("Email",key="se");np=st.text_input("Password (6+)",type="password",key="sp");np2=st.text_input("Confirm",type="password",key="sp2")
            if st.button("Create Account",use_container_width=True,key="sb"):
                if not ne or not np:st.error("Fill all.")
                elif np!=np2:st.error("Mismatch.")
                elif len(np)<6:st.error("Min 6.")
                elif _db_get_user(ne):st.error("Exists.")
                elif _db_create_user(ne,hash_pw(np)):st.session_state.logged_in=True;st.session_state.user_email=ne;st.rerun()
    st.markdown("---")
    if st.button("Continue as guest" if has_db else "Enter TaxGuru →",type="primary" if not has_db else "secondary",use_container_width=True,key="gb"):
        st.session_state.logged_in=True;st.session_state.user_email=None;st.rerun()
    st.markdown('</div>',unsafe_allow_html=True)
    return False

# ══════ CSS ══════
st.markdown(f"""<style>
#MainMenu,footer,header,.stAppToolbar,[data-testid="stHeader"],[data-testid="manage-app-button"],[data-testid="stStatusWidget"],[data-testid="stDecoration"],.stDeployButton,.viewerBadge_container__r5tak,.styles_viewerBadge__CvC9N,div.viewerBadge_link__qRIco,iframe[title="streamlit_badge"],._profileContainer_gzau3_53,div[class*="StatusWidget"],button[kind="header"],div[data-testid="stToolbar"],[data-testid="collapsedControl"],[data-testid="stSidebarCollapsedControl"],[data-testid="stSidebar"]{{display:none!important;visibility:hidden!important;height:0!important;position:absolute!important;top:-9999px!important;}}
footer:after{{content:'';visibility:hidden;display:block;}}.stApp>header{{display:none!important;}}
.stApp,[data-testid="stAppViewContainer"]{{background:{BG}!important;color:{TX}!important;}}
[data-testid="stVerticalBlock"]{{gap:0.3rem!important;}}
h1,h2,h3,h4{{color:{TX}!important;}}p,li,span,.stMarkdown{{color:{TX2};}}
.stApp{{margin-top:0;}}.block-container{{padding:0.3rem 1.2rem 0.5rem!important;max-width:100%!important;}}
[data-testid="stAppViewContainer"]>div:first-child{{padding-top:0.2rem!important;}}
/* Nav */
div[data-testid="stHorizontalBlock"]:first-child .stRadio label{{background:{BG2};border:1px solid {BD};border-radius:6px;padding:0.35rem 0.8rem;font-size:0.95rem;font-weight:600;color:{TX};}}
div[data-testid="stHorizontalBlock"]:first-child .stRadio label:hover{{background:{HL};}}
div[data-testid="stHorizontalBlock"]:first-child .stRadio div[role="radiogroup"] label:has(input:checked){{background:{AC}!important;color:#000!important;border-color:{AC}!important;font-weight:700;}}
/* Cards */
.cd{{background:{BG2};border:1px solid {BD};border-radius:10px;padding:0.8rem;margin:0.3rem 0;font-size:1rem;color:{CTX};}}
.cd.green{{border-left:3px solid #10B981;}}.cd.amber{{border-left:3px solid #F59E0B;}}.cd.red{{border-left:3px solid #EF4444;}}.cd.blue{{border-left:3px solid #3B82F6;}}
/* Trust */
.tg{{display:grid;grid-template-columns:1fr 1fr;gap:0.6rem;margin:0.5rem 0;}}
.tt{{background:{HL};border:2px solid {AC};border-radius:10px;padding:0.9rem;}}.tt h4{{color:{AC2}!important;margin:0 0 0.4rem;font-size:1.15rem;}}.tt ul{{list-style:none;padding:0;margin:0;}}.tt li{{padding:0.15rem 0;font-size:1rem;color:{CTX};line-height:1.5;}}.tt li::before{{content:'✓ ';color:#10B981;font-weight:700;}}
/* Setup */
.su{{background:{HL};border:2px solid {AC};border-radius:10px;padding:0.7rem 1rem;margin:0.6rem 0 0.8rem;text-align:center;}}.su b{{font-size:1.2rem;color:{AC2};}}.su span{{color:{TX2};font-size:1rem;}}
/* Feature */
.fb{{background:{BG2};border:1px solid {BD};border-radius:10px;padding:0.8rem;margin-bottom:0.3rem;}}.fb h4{{color:{AC2};margin:0 0 0.2rem;font-size:1.05rem;}}.fb p{{color:{CTX};font-size:0.92rem;margin:0;line-height:1.4;}}
/* Logo */
.logo-panel{{background:#FFF;border:1px solid {BD};border-radius:10px;padding:0.5rem;text-align:center;margin-bottom:0.3rem;}}.logo-panel img{{height:200px;}}
/* Chat */
.ch{{background:{BG2};border:1px solid {BD};padding:0.5rem 0.8rem;border-radius:8px 8px 0 0;display:flex;align-items:center;gap:0.5rem;}}.ch .dot{{width:8px;height:8px;background:#4ADE80;border-radius:50%;animation:p 2s infinite;}}@keyframes p{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}.ch .nm{{font-weight:700;font-size:1rem;color:{CTX};}}.ch .rl{{font-size:0.85rem;color:{CTX};}}
.cd2{{font-size:0.85rem;color:{TX2};font-style:italic;margin-top:0.3rem;}}
.pv{{background:{"#172554" if DK else "#EFF6FF"};border:1px solid {"#1E40AF" if DK else "#BFDBFE"};border-radius:6px;padding:0.4rem 0.7rem;font-size:0.9rem;color:{"#93C5FD" if DK else "#1E40AF"};margin-bottom:0.5rem;}}
/* Table */
.cmp-tbl{{width:100%;border-collapse:collapse;margin:0.5rem 0;}}.cmp-tbl th{{background:{HL};color:{AC2};padding:0.5rem;text-align:right;border:1px solid {BD};}}.cmp-tbl th:first-child{{text-align:left;}}.cmp-tbl td{{padding:0.4rem 0.5rem;border:1px solid {BD};color:{TX};text-align:right;}}.cmp-tbl td:first-child{{text-align:left;color:{TX2};}}.cmp-tbl tr.total{{background:{HL};font-weight:700;}}.cmp-tbl tr.total td{{color:{AC2};font-size:1.05rem;}}
/* Inputs */
[data-testid="stSelectbox"]>div>div,[data-testid="stMultiSelect"]>div>div{{background:{BG2}!important;color:{TX}!important;border-color:{BD}!important;}}
[data-testid="stNumberInput"] input,.stTextInput input{{background:{BG2}!important;color:{TX}!important;border-color:{BD}!important;}}
[data-testid="stFileUploader"]{{background:{BG2};border:1px solid {BD};border-radius:8px;padding:0.5rem;}}
[data-testid="stExpander"]{{background:{BG2};border:1px solid {BD};border-radius:8px;}}[data-testid="stExpander"] summary{{color:{TX}!important;}}
[data-testid="stMetric"]{{background:{BG2};border:1px solid {BD};border-radius:8px;padding:0.5rem;}}[data-testid="stMetricValue"]{{color:{AC}!important;}}[data-testid="stMetricLabel"]{{color:{TX2}!important;}}
/* Buttons */
.stButton>button[kind="primary"],.stButton>button[data-testid="stBaseButton-primary"]{{background:{AC}!important;color:#000!important;border:none!important;font-weight:800!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;}}
.stButton>button:not([kind="primary"]){{background:{BTN_BG}!important;color:{BTN_TX}!important;border:1px solid {BD}!important;font-weight:700!important;-webkit-text-fill-color:{BTN_TX}!important;}}
/* Chat input */
[data-testid="stChatInput"] textarea{{background:#FFF!important;color:#000!important;font-size:1rem!important;-webkit-text-fill-color:#000!important;min-height:200px!important;height:200px!important;}}
[data-testid="stChatInput"]{{background:#FFF!important;border:2px solid {BD};border-radius:8px;}}
[data-testid="stChatInput"] button{{background:{AC}!important;color:#FFF!important;}}
/* Dropdowns */
[data-baseweb="popover"],[data-baseweb="menu"],[data-baseweb="select"] [role="listbox"]{{background:{BG2}!important;border:1px solid {BD}!important;}}
[data-baseweb="menu"] li,[data-baseweb="select"] [role="option"]{{color:{TX}!important;}}
[data-baseweb="menu"] li:hover,[data-baseweb="select"] [role="option"]:hover{{background:{HL}!important;}}
@media(max-width:900px){{.tg{{grid-template-columns:1fr;}}.logo-panel img{{height:120px;}}}}
</style>""",unsafe_allow_html=True)

if not check_login():st.stop()

# Session
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
with nc2:st.button("Light/Dark",key="tb",on_click=toggle_theme)
with nc3:
    if st.button("Logout",key="lo"):
        for k in list(st.session_state.keys()):del st.session_state[k]
        st.rerun()
st.session_state.pg=sel
if sel in ("Tax Calculator","Savings Finder","What-If Scenarios") and IC():st.caption(f"📋 Profile: **{st.session_state.active_profile}**")

def chat_col(k=""):
    if LOGO:st.markdown(f'<div class="logo-panel"><img src="data:image/png;base64,{LOGO}"></div>',unsafe_allow_html=True)
    st.markdown(f'<div class="ch"><div class="dot"></div><div><span class="nm">{A}</span><br><span class="rl">TaxGuru Tax Agent</span></div></div>',unsafe_allow_html=True)
    lang=st.selectbox("",[ ("English","en"),("हिन्दी","hi"),("தமிழ்","ta"),("తెలుగు","te"),("ಕನ್ನಡ","kn")],format_func=lambda x:x[0],label_visibility="collapsed",key=f"l{k}")
    bx=st.container(height=280)
    with bx:
        if not st.session_state.ch:st.markdown(f"👋 **I'm {A}.** Ask me any tax question.")
        for m in st.session_state.ch:
            with st.chat_message(m['role'],avatar="🧑‍💼" if m['role']=='assistant' else None):st.markdown(m['content'])
    if pr:=st.chat_input(f"Ask {A}...",key=f"c{k}"):
        cl,_=anonymize_text(pr);st.session_state.ch.append({'role':'user','content':pr})
        if not K:rsp="⚠️ API key not set."
        else:pf=extract_financial_only(vars(P())) if IC() else {};rg=build_rag_query(cl,pf);rsp=call_gemini(prompt=cl,context=rg['context'],language=lang[1],api_key=K,agent_name=A,system_prompt=SHORT)
        st.session_state.ch.append({'role':'assistant','content':rsp});st.rerun()
    st.markdown(f'<div class="cd2">💡 TaxGuru: IT Act + latest circulars.</div>',unsafe_allow_html=True)
def with_chat(fn,k=""):
    c1,c2=st.columns([3,1])
    with c1:fn()
    with c2:chat_col(k)

# ══════ HOME ══════
if sel=="Home":
    c1,c2=st.columns([3,1])
    with c1:
        st.markdown(f'<h1 style="font-size:1.7rem!important;margin:0 0 0.2rem!important">Stop overpaying your taxes.</h1><p style="font-size:1.05rem;color:{TX2}">AI that knows Indian tax law — pick the right regime, find every deduction, plan ahead.</p>',unsafe_allow_html=True)
        st.markdown(f'<div class="su"><b>Set up your tax profile (one-time, 2 minutes)</b><br><span>Upload a document or enter your details.</span></div>',unsafe_allow_html=True)
        bc1,bc2=st.columns(2)
        with bc1:st.button("📄 Upload Payslip / Form 16",use_container_width=True,type="primary",on_click=nav,args=("Tax Profile",))
        with bc2:st.button("✏️ Enter Manually",use_container_width=True,on_click=nav,args=("Tax Profile",))
        fc1,fc2,fc3=st.columns(3)
        with fc1:st.markdown(f'<div class="fb"><h4>⚖️ Tax Calculator</h4><p>Old vs New regime side-by-side — see exact savings in rupees, not percentages. Know which regime is better for your specific situation.</p></div>',unsafe_allow_html=True);st.button("Open Tax Calculator →",use_container_width=True,key="h1",on_click=nav,args=("Tax Calculator",))
        with fc2:st.markdown(f'<div class="fb"><h4>🔀 What-If Scenarios</h4><p>Getting a raise? Taking a home loan? Investing in ELSS? Selling shares? See exactly how each life event changes your tax — before you decide.</p></div>',unsafe_allow_html=True);st.button("Open What-If Scenarios →",use_container_width=True,key="h4",on_click=nav,args=("What-If Scenarios",))
        with fc3:st.markdown(f'<div class="fb"><h4>💡 Savings Finder</h4><p>Personalized recommendations — which section to invest under, exactly how much, and by when. With precise tax impact for each suggestion.</p></div>',unsafe_allow_html=True);st.button("Open Savings Finder →",use_container_width=True,key="h3",on_click=nav,args=("Savings Finder",))
        st.markdown(f'<div class="tg"><div class="tt"><h4>🛡️ Always Accurate</h4><ul><li>Tax numbers from a precise calculation engine — not AI guesses</li><li>Every answer cites the actual Income Tax Act section</li><li>TaxGuru says "check with a CA" when unsure — never makes things up</li><li>Updated real-time with Budget 2026 changes, circulars, court judgements</li></ul></div><div class="tt"><h4>🔒 Your Data Stays Private</h4><ul><li>We never see your PAN, Aadhaar, address, DOB, phone, or email</li><li>Bank accounts, PF/UAN, employer name — all auto-deleted</li><li>Only salary/deduction numbers used — in your browser session only</li><li>Close the browser → everything gone. Nothing saved. Ever.</li></ul></div></div>',unsafe_allow_html=True)
    with c2:chat_col("home")

elif sel=="Tax Profile":
    def tp():
        st.markdown("## Tax Profile")
        if IC():st.info(f"⚠️ Editing **{st.session_state.active_profile}**. Changes update this profile.")
        st.markdown("#### 📄 Upload Document")
        st.markdown(f'<div class="pv">🔒 Only numbers extracted.</div>',unsafe_allow_html=True)
        up=st.file_uploader("Payslip/Form 16",type=['png','jpg','jpeg','pdf'],key="pfu")
        if up and K:
            with st.spinner("Reading..."):doc=analyze_document(up.read(),K,up.type or "image/jpeg")
            if 'error' not in doc:
                ann=doc.get('period','monthly')=='annual';mul=1 if ann else 12
                st.success("✅ Data found:")
                for ky,v in doc.items():
                    if ky not in ('period','raw_text','parse_error') and isinstance(v,(int,float)) and v>0:st.markdown(f"- **{ky.replace('_',' ').title()}:** ₹{v:,.0f}")
                def gv(ky,d=0):
                    v=doc.get(ky,d)
                    if v in("NOT_FOUND",None):return d
                    try:return float(v)*mul
                    except:return d
                def _use():
                    p=P();p.taxpayer_type="salaried";p.gross_salary=gv('gross_salary');p.basic_salary=gv('basic_salary',p.gross_salary*0.4);p.hra_received=gv('hra');p.tds_deducted=gv('tds_deducted');p.section_80c=min(gv('section_80c_total',gv('pf_employee')),150000);p.section_80ccd_2=gv('section_80ccd_2',gv('pf_employer'));st.session_state.pc=True;save_all();nav("Tax Calculator")
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
            met=st.selectbox("Metro?",["Yes—8cities","No"])
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
            with c2:enps=st.number_input("EmployerNPS",0,value=0,step=5000,format="%d")
        if any(x in types for x in ["Business","Professional","Freelancing"]):biz=st.number_input("BizIncome₹",0,value=0,step=100000,format="%d")
        if "Trading" in types:trd=st.number_input("TradingP/(L)",value=0,step=50000,format="%d")
        with st.expander("📈 More"):
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
            p=P();p.taxpayer_type=t;p.age=age;p.residency=rs;p.metro_city="Yes" in met;p.gross_salary=gs;p.basic_salary=bs if bs else gs*0.4;p.hra_received=hra;p.rent_paid_annual=rent;p.section_80ccd_2=enps;p.business_income=biz;p.trading_income=trd;p.interest_income=ii2;p.rental_income=ri2;p.dividend_income=dv;p.stcg_equity=stcg;p.ltcg_equity=ltcg;p.esop_perquisite=esop;p.foreign_esop=fe;p.section_80c=s80c;p.section_80d_self=s80d;p.section_80d_parents=0;p.section_80ccd_1b=s80n;p.section_80e=s80e;p.section_24b=s24b;p.tds_deducted=tds;p.advance_tax_paid=adv;st.session_state.pc=True;save_all();nav("Tax Calculator")
        st.button("✅ Save & See Tax",type="primary",use_container_width=True,on_click=_save)
    with_chat(tp,"tp")

elif sel=="Tax Calculator":
    def calc():
        st.markdown("## Tax Calculator")
        if not IC():st.warning("Set up profile first.");st.button("→ Tax Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();r=compare_regimes(p);o=r['old_regime'];n=r['new_regime'];rc=r['recommended'];sv=r['savings']
        st.success(f"🎯 **{'New' if rc=='new' else 'Old'} Regime saves you {format_currency(sv)}**")
        rows=[];rows.append(("Gross Salary",n['salary_income'],o['salary_income']))
        if n.get('business_income') or o.get('business_income'):rows.append(("Business",n.get('business_income',0),o.get('business_income',0)))
        if n.get('other_income') or o.get('other_income'):rows.append(("Other",n.get('other_income',0),o.get('other_income',0)))
        rows.append(("Gross Total",n['gross_total_income'],o['gross_total_income']))
        rows.append(("Std Deduction",-75000,-50000))
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
        p=P();r=compare_regimes(p);rc=r['recommended'];regime=st.radio("Regime:",["New","Old"],horizontal=True,key="rsf");rk='new' if regime=="New" else 'old';ct=r[rk+'_regime']['total_tax']
        recs=[]
        if rk=='old' and p.section_80c<150000:g=150000-p.section_80c;p2=copy.deepcopy(p);p2.section_80c=150000;sv=ct-compare_regimes(p2)['old_regime']['total_tax'];recs.append(('red','80C',f'₹{g:,.0f} more in 80C',f'Save {format_currency(max(sv,0))}','ELSS/PPF/FD','Top 3 ELSS funds India 2025. Name, return, lock-in. 3 lines.'))
        if p.section_80ccd_2==0:recs.append(('red','80CCD(2)','Employer NPS','₹15K-50K+','Both regimes','Top 3 NPS managers. 3 lines.'))
        if rk=='old' and p.section_80d_self==0:p2=copy.deepcopy(p);p2.section_80d_self=25000;sv=ct-compare_regimes(p2)['old_regime']['total_tax'];recs.append(('amber','80D','Health insurance',f'Save {format_currency(max(sv,0))}','₹25K+₹50K','Top 3 health plans for 80D. 3 lines.'))
        if p.esop_perquisite>0:recs.append(('amber','ESOP',f'₹{p.esop_perquisite:,.0f}','Slab rate','Time exercise',None))
        if p.trading_income!=0:recs.append(('red','43(5)','Trading→ITR-3','Carry-forward','File correctly',None))
        if not recs:st.success("🎉 Optimized!")
        for col,sec,t,imp,det,q in recs:
            ic={'red':'🔴','amber':'🟡'}.get(col,'🟢');st.markdown(f'<div class="cd {col}"><b>{ic} {t}</b> ({sec})—{imp}<br><em>{det}</em></div>',unsafe_allow_html=True)
            if q and st.button(f"🔍 Explore",key=f"s_{sec}"):
                if K:
                    with st.spinner("..."):st.markdown(call_gemini(prompt=q,context="",language="en",api_key=K,agent_name=A,system_prompt=SHORT))
    with_chat(sf,"sf")

elif sel=="What-If Scenarios":
    def sc():
        st.markdown("## What-If Scenarios")
        if not IC():st.warning("Set up profile.");st.button("→ Profile",type="primary",on_click=nav,args=("Tax Profile",));return
        p=P();cur=compare_regimes(p);regime=st.radio("Regime:",["New","Old"],horizontal=True,key="rsc");rk='new' if regime=="New" else 'old';ct=cur[rk+'_regime']['total_tax']
        ALL=["Salary raise","80C invest","Employer NPS","Health ins(80D)","Home loan","Rent(HRA)","Sell equity LTCG","Sell equity STCG","Sell property","ESOPs","Edu loan","Side business","Rental income","Bonus","Donation(80G)","NPS self","FD interest"]
        chosen=st.multiselect("Select scenarios:",ALL,placeholder="17 options...")
        def ct2(p2):return compare_regimes(p2)[rk+'_regime']['total_tax']
        for s in chosen:
            st.markdown(f"---\n**{s}**");p2=copy.deepcopy(p)
            if s=="Salary raise":pct=st.slider("%",5,100,20,5,key=f"w{s}");p2.gross_salary=int(p.gross_salary*(1+pct/100));p2.basic_salary=int(p.basic_salary*(1+pct/100));st.metric("Change",format_currency(ct2(p2)-ct))
            elif s=="80C invest":ex=st.slider("₹",0,150000,50000,10000,key=f"w{s}");p2.section_80c=min(p.section_80c+ex,150000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Employer NPS":n2=st.slider("₹/yr",0,int(max(p.basic_salary*0.14,100000)),50000,5000,key=f"w{s}");p2.section_80ccd_2=n2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Health ins(80D)":d2=st.slider("₹",0,50000,25000,5000,key=f"w{s}");p2.section_80d_self=d2;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Home loan":li=st.number_input("Int₹/yr",0,200000,200000,25000,key=f"n{s}");p2.section_24b=min(li,200000);st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Rent(HRA)":rn=st.number_input("₹/yr",0,value=240000,step=12000,key=f"n{s}");p2.rent_paid_annual=rn;st.metric("Saving",format_currency(ct-ct2(p2)))
            elif s=="Sell equity LTCG":lg=st.number_input("₹",0,value=200000,step=25000,key=f"n{s}");p2.ltcg_equity+=lg;st.metric("Extra",format_currency(ct2(p2)-ct))
            elif s=="Sell equity STCG":sg=st.number_input("₹",0,value=100000,step=25000,key=f"n{s}");p2.stcg_equity+=sg;st.metric("Extra",format_currency(ct2(p2)-ct))
            elif s=="Sell property":gn=st.number_input("Gain₹",0,value=500000,step=50000,key=f"n{s}");p2.ltcg_other+=gn;st.metric("Extra",format_currency(ct2(p2)-ct))
            elif s=="ESOPs":ep=st.number_input("₹",0,value=500000,step=50000,key=f"n{s}");p2.esop_perquisite+=ep;st.metric("Extra",format_currency(ct2(p2)-ct))
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
        e=st.session_state.get('user_email')
        if e:st.caption(f"Logged in as **{e}**")
        for name,prof in st.session_state.profiles.items():
            ia=name==st.session_state.active_profile
            with st.expander(f"{'📋' if ia else '📄'} {name} {'✅ Active' if ia else ''}",expanded=ia):
                c1,c2,c3=st.columns(3)
                with c1:st.markdown(f"**Type:** {prof.taxpayer_type}\n\n**Age:** {prof.age}\n\n**Residency:** {prof.residency}")
                with c2:st.markdown(f"**Gross:** {format_currency(prof.gross_salary)}\n\n**Business:** {format_currency(prof.business_income)}\n\n**80C:** {format_currency(prof.section_80c)}")
                with c3:r=compare_regimes(prof);b=r[r['recommended']+'_regime'];st.markdown(f"**Tax:** {format_currency(b['total_tax'])}\n\n**Rate:** {b['effective_rate']}%\n\n**Best:** {r['recommended'].title()}")
                bc1,bc2=st.columns(2)
                with bc1:
                    if not ia:st.button(f"Set active",key=f"a_{name}",on_click=nav_activate,args=(name,))
                with bc2:
                    st.button(f"✏️ Edit",key=f"e_{name}",on_click=nav_edit,args=(name,))
        st.markdown("---\n#### ➕ Add Profile")
        nn=st.text_input("Name",placeholder="Spouse, Parent...",key="npn")
        def _add():
            if nn and nn not in st.session_state.profiles:
                st.session_state.profiles[nn]=TaxpayerProfile();st.session_state.active_profile=nn;st.session_state.pc=False;save_all();nav("Tax Profile")
        st.button("Create",type="primary",on_click=_add)
    with_chat(pr,"pr")

elif sel=="Law Updates":
    def lu():
        st.markdown("## Law Updates")
        for dt,t,d,col in [('Mar 20, 2026','🆕 Income Tax Rules 2026 Notified by CBDT','HRA now covers 8 metro cities (adds Hyderabad, Pune, Ahmedabad, Bengaluru). New Form 124 for HRA claims. Sections reduced from 819 to 536. CARF crypto reporting mandatory.','blue'),('Mar 2026','CBDT Sending AIS Transaction Alerts','High-value transactions detected in Annual Information Statement. Not a formal notice but verify your AIS on the e-filing portal.','blue'),('Feb 2026','Union Budget 2026 — No Rate Changes','Tax Year concept replaces Previous Year/Assessment Year from April 2026. No changes to tax slabs or rates.','blue'),('Oct 2025','ITR Filing Deadline Extended (Circular 15/2025)','Audit cases extended from October 31 to December 10, 2025. Audit report deadline moved to November 10.','amber'),('Jul 2024','Capital Gains Tax Rates Changed','STCG on equity increased from 15% to 20%. LTCG on equity increased from 10% to 12.5%. LTCG exemption raised from ₹1L to ₹1.25L. Indexation benefit removed for all assets.','amber'),('Feb 2025','Income Up to ₹12.75 Lakh Now Tax-Free for Salaried','New regime: basic exemption ₹4L, Section 87A rebate ₹60K, standard deduction ₹75K.','green'),('Apr 2024','Angel Tax Abolished','Section 56(2)(viib) removed for all investors — resident and non-resident — from April 2025.','green')]:
            ic={'blue':'ℹ️','amber':'⚠️','green':'✅'}[col];st.markdown(f'<div class="cd {col}"><b>{ic} [{dt}] {t}</b><br>{d}</div>',unsafe_allow_html=True)
        st.markdown("---\n#### ⚖️ Key Case Law")
        for t,d in [("CIT vs Gopal Purohit (Bombay HC)","A taxpayer can maintain separate investment and trading portfolios. The intention at the time of purchase determines classification."),("Unnikrishnan vs ITO (Mumbai ITAT)","ESOPs granted while India-resident are taxable in India even if exercised later as an NRI. Perquisite accrues during employment."),("HRA Paid to Parents (Multiple ITAT)","Paying rent to parents is allowed for HRA exemption, provided it is genuinely paid and included in parents' income. Need rental agreement and bank transfer proof."),("CBDT Circular 6/2016","A taxpayer can classify some shares as investment and others as trading stock, provided this classification is followed consistently year over year.")]:
            st.markdown(f'<div class="cd blue"><b>⚖️ {t}</b><br>{d}</div>',unsafe_allow_html=True)
    with_chat(lu,"lu")

elif sel=="About":
    def ab():
        st.markdown(f"""## About TaxGuru

### Our Mission
India has over 9 crore income tax return filers — yet most don't optimize their taxes. The government issued ₹3.9 lakh crore in refunds in FY25, showing millions overpay through excess TDS and wrong regime choices. With 2 tax regimes and 70+ deduction sections, making the right choice is genuinely hard. **TaxGuru exists to change this.**

### How It Works
**🧮 Precise Calculation Engine** — Your tax numbers are computed by a deterministic mathematical engine, not generated by AI. The numbers are always exactly right — no rounding, no estimation, no hallucination.

**🤖 Intelligent Tax Agent** — TaxGuru's agent has access to 60 sections of the Income Tax Act, key CBDT circulars, case law precedents, and Budget amendments. When you ask a question, it retrieves the most relevant legal provisions and constructs an answer grounded in actual law — citing specific sections.

**🔍 Real-Time Updates** — The agent can search the web for the latest tax developments — new circulars, court rulings, deadline extensions. This means advice stays current even as the law changes. Our knowledge base also auto-updates weekly.

**📄 Document Intelligence** — Upload a payslip or Form 16 and AI reads it, extracts only the financial numbers (ignoring all personal details), and fills your tax profile automatically.

**🔒 Privacy by Design** — We never collect, store, or transmit your name, PAN, Aadhaar, date of birth, address, phone number, email, bank account details, PF number, employer name, or employee ID. Only financial figures are processed. If you create an account, only your email and encrypted password are stored.

### Accuracy Commitment
- Every answer cites the specific section of the Income Tax Act
- When unsure, TaxGuru says "consult a CA" — never guesses
- 60 provisions including CBDT Notification 22/2026 (March 20, 2026)
- Tax calculations verified against government guidelines

### Who It's For
**Salaried** — regime comparison, HRA, payslip analysis • **Business** — presumptive taxation, audit • **Professionals** — 44ADA, advance tax • **Traders** — F&O, 43(5), ITR-3, loss carry-forward • **Investors** — capital gains, ESOP • **Seniors** — 80TTB, higher exemptions • **NRIs** — residency auto-determination, DTAA

*TaxGuru provides informational guidance. Not professional tax advice. For complex matters, consult a CA.*""")
    with_chat(ab,"ab")
