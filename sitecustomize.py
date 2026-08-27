"""Charge automatiquement l'identité visuelle SUAPS V14 au démarrage Python."""
try:
    import streamlit as st
    _md = st.markdown
    _done = False
    _css = r'''<style>
    :root{--navy:#12365d;--blue:#1976d2;--cyan:#24b7c9;--ink:#17283a;--muted:#6f7f91;--line:#e5edf5}
    html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
    .stApp{background:linear-gradient(180deg,#f8faff 0%,#eef4f9 100%)!important;color:var(--ink)}
    .block-container{max-width:1080px!important;padding-top:.8rem!important;padding-bottom:5rem!important}
    header[data-testid="stHeader"]{background:rgba(248,250,255,.84)!important;backdrop-filter:blur(12px)}
    h1,h2,h3{letter-spacing:-.025em!important;color:var(--ink);font-weight:780!important}
    .hero{background:linear-gradient(135deg,#123b68 0%,#176faa 55%,#20b8c5 100%)!important;border-radius:28px!important;padding:29px 26px!important;box-shadow:0 18px 42px rgba(18,54,93,.22)!important;position:relative;overflow:hidden}
    .hero:after{content:"";position:absolute;width:180px;height:180px;border-radius:50%;right:-60px;top:-80px;background:rgba(255,255,255,.11)}
    .hero h1,.hero p{color:white!important}.hero h1{font-size:2rem!important}.hero .badge{background:rgba(255,255,255,.18)!important;color:white!important;border:1px solid rgba(255,255,255,.24)!important}
    .card{background:rgba(255,255,255,.97)!important;border:1px solid var(--line)!important;border-radius:22px!important;padding:19px!important;margin-bottom:14px!important;box-shadow:0 8px 24px rgba(31,64,98,.075)!important;transition:.16s ease!important}
    .card:hover{transform:translateY(-2px);box-shadow:0 13px 30px rgba(31,64,98,.13)!important}
    .card b{color:#173e67;font-size:1.04rem}.small{color:var(--muted)!important;line-height:1.55!important}
    .badge{border-radius:999px!important;padding:6px 11px!important;font-weight:750!important}
    div.stButton>button,div.stFormSubmitButton>button{width:100%;min-height:50px;border-radius:16px!important;font-weight:750!important;border:1px solid #dce7f1!important;box-shadow:0 5px 14px rgba(26,70,110,.08)!important;transition:.14s ease!important}
    div.stButton>button:hover,div.stFormSubmitButton>button:hover{transform:translateY(-1px);border-color:#9fc9e7!important;box-shadow:0 9px 18px rgba(26,70,110,.13)!important}
    div[data-testid="stMetric"]{background:white!important;border:1px solid var(--line)!important;border-radius:18px!important;padding:13px 15px!important;box-shadow:0 5px 16px rgba(31,64,98,.055)!important}
    div[data-testid="stMetricValue"]{color:var(--navy)!important;font-weight:800!important}
    div[data-baseweb="select"]>div,input,textarea{border-radius:14px!important;background:white!important}
    [data-testid="stAlert"],[data-testid="stDataFrame"]{border-radius:16px!important;overflow:hidden}
    [data-testid="stSidebar"]{background:linear-gradient(180deg,#12365d,#17547f)!important}
    [data-testid="stSidebar"] *{color:white!important}
    @media(max-width:768px){
      .block-container{padding:.55rem .72rem 5.5rem!important}.hero{border-radius:23px!important;padding:23px 19px!important}.hero h1{font-size:1.6rem!important}
      .card{border-radius:19px!important;padding:17px!important}.stButton button{min-height:54px!important;font-size:.96rem!important}
      div[data-testid="stHorizontalBlock"]{gap:.55rem!important;flex-wrap:wrap!important}div[data-testid="column"]{min-width:calc(50% - .55rem)!important;flex:1 1 calc(50% - .55rem)!important}
    }
    @media(max-width:430px){div[data-testid="column"]{min-width:100%!important;flex:1 1 100%!important}}
    </style>'''
    def _styled_markdown(body,*args,**kwargs):
        global _done
        if not _done:
            _done=True
            _md(_css,unsafe_allow_html=True)
        return _md(body,*args,**kwargs)
    st.markdown=_styled_markdown
except Exception:
    pass
