"""SUAPS UPPA — couche design mobile V14.
Conserve toutes les fonctions de app.py et applique uniquement la nouvelle identité visuelle.
"""
from pathlib import Path
import streamlit as st

_original_markdown = st.markdown
_design_loaded = False

DESIGN_CSS = r"""
<style>
:root{
  --navy:#12365d; --blue:#1976d2; --cyan:#24b7c9; --ink:#17283a;
  --muted:#6f7f91; --surface:#ffffff; --line:#e8eef5; --bg:#f4f7fb;
}
html,body,[class*="css"]{font-family:Inter,ui-sans-serif,system-ui,-apple-system,"Segoe UI",sans-serif}
.stApp{background:linear-gradient(180deg,#f7f9fc 0%,#eef4f9 100%)!important;color:var(--ink)}
.block-container{max-width:1080px!important;padding-top:.8rem!important;padding-bottom:5rem!important}
header[data-testid="stHeader"]{background:rgba(247,249,252,.82);backdrop-filter:blur(12px)}
#MainMenu,footer{visibility:hidden}
h1,h2,h3{letter-spacing:-.025em;color:var(--ink)}
h1{font-weight:850!important} h2,h3{font-weight:780!important}
p{line-height:1.5}

/* Hero inspiré application sportive mobile */
.student-hero{
  background:linear-gradient(135deg,#143b68 0%,#176eaa 55%,#20b7c4 100%)!important;
  border:0!important;border-radius:28px!important;padding:28px 26px!important;color:white!important;
  box-shadow:0 18px 42px rgba(18,54,93,.22)!important;margin:8px 0 20px!important;
  position:relative;overflow:hidden
}
.student-hero:before{content:"";position:absolute;width:190px;height:190px;border-radius:50%;right:-70px;top:-90px;background:rgba(255,255,255,.11)}
.student-hero:after{content:"";position:absolute;width:110px;height:110px;border-radius:50%;right:75px;bottom:-80px;background:rgba(255,255,255,.08)}
.student-hero h1,.student-hero h2,.student-hero h3{color:white!important;margin:0 0 7px!important}
.student-hero p{color:rgba(255,255,255,.93)!important;margin:0!important;font-weight:520}

/* Cartes : familles, accès rapides, contenu */
.student-card{
  background:rgba(255,255,255,.96)!important;border:1px solid var(--line)!important;border-radius:22px!important;
  padding:18px!important;margin:9px 0 15px!important;box-shadow:0 8px 25px rgba(31,64,98,.075)!important;
  transition:transform .16s ease,box-shadow .16s ease!important
}
.student-card:hover{transform:translateY(-2px);box-shadow:0 13px 30px rgba(31,64,98,.13)!important}
.student-card h3{margin:0 0 8px!important;font-size:1.06rem!important}
.student-card p{color:var(--muted);margin:.25rem 0!important}
.student-pill{display:inline-block!important;background:#eef7ff!important;color:#1767a6!important;border:1px solid #dcecf8!important;border-radius:999px!important;padding:5px 10px!important;margin:3px 4px 3px 0!important;font-size:.79rem!important;font-weight:650!important}
.student-section-title{font-size:1.15rem!important;margin:24px 0 10px!important;color:var(--navy)!important}

/* Boutons type application */
div.stButton>button,div.stFormSubmitButton>button{
  width:100%;min-height:50px;border-radius:16px!important;font-weight:750!important;border:1px solid #dce7f1!important;
  box-shadow:0 5px 14px rgba(26,70,110,.08);transition:transform .14s ease,box-shadow .14s ease
}
div.stButton>button:hover,div.stFormSubmitButton>button:hover{transform:translateY(-1px);box-shadow:0 9px 18px rgba(26,70,110,.13);border-color:#a8cce8!important}
button[kind="primary"],div.stButton>button[kind="primary"]{background:linear-gradient(135deg,#1769aa,#22aebd)!important;color:white!important;border:0!important}

/* KPI, champs et onglets */
div[data-testid="stMetric"]{background:white;border:1px solid var(--line);border-radius:18px;padding:13px 15px;box-shadow:0 5px 16px rgba(31,64,98,.055)}
div[data-testid="stMetricValue"]{color:var(--navy);font-weight:800}
div[data-baseweb="select"]>div,input,textarea{border-radius:14px!important;background:white!important}
div[data-baseweb="tab-list"]{gap:7px;background:#eaf0f6;padding:5px;border-radius:15px}
button[data-baseweb="tab"]{border-radius:11px!important}
[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:16px;overflow:hidden}
[data-testid="stAlert"]{border-radius:16px}

/* Sidebar enseignant : sobre et lisible */
[data-testid="stSidebar"]{background:linear-gradient(180deg,#12365d,#174f78)!important}
[data-testid="stSidebar"] *{color:white!important}
[data-testid="stSidebar"] div[role="radiogroup"] label{padding:5px 3px;border-radius:10px}

/* Mobile : cartes en vraie pile, gros touch targets */
@media(max-width:768px){
  .block-container{padding:.55rem .72rem 5.5rem!important}
  .student-hero{border-radius:23px!important;padding:23px 19px!important;margin-top:4px!important}
  .student-hero h1{font-size:1.65rem!important;line-height:1.12!important}
  .student-card{border-radius:19px!important;padding:16px!important;margin-bottom:11px!important}
  .student-card h3{font-size:1rem!important}
  div.stButton>button,div.stFormSubmitButton>button{min-height:54px!important;font-size:.96rem!important}
  div[data-testid="stHorizontalBlock"]{gap:.55rem!important;flex-wrap:wrap!important}
  div[data-testid="column"]{min-width:calc(50% - .55rem)!important;flex:1 1 calc(50% - .55rem)!important}
  h1{font-size:1.65rem!important} h2{font-size:1.35rem!important} h3{font-size:1.08rem!important}
}
@media(max-width:430px){
  div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}
  .student-hero{padding:21px 17px!important}
}
</style>
"""

def _markdown_with_design(body, *args, **kwargs):
    global _design_loaded
    if not _design_loaded:
        _design_loaded = True
        _original_markdown(DESIGN_CSS, unsafe_allow_html=True)
    return _original_markdown(body, *args, **kwargs)

st.markdown = _markdown_with_design

source = Path(__file__).with_name("app.py").read_text(encoding="utf-8")
exec(compile(source, str(Path(__file__).with_name("app.py")), "exec"), globals(), globals())
