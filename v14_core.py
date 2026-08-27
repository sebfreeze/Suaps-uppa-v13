import sqlite3
from datetime import date, datetime
from pathlib import Path
import streamlit as st

DB="suaps_v14.db"
ACTIVITES=["Natation","Sauvetage","Surf","Rugby","Course à pied","Pelote Basque"]
FAMILY_MAP={
    "Activités aquatiques":["Natation","Sauvetage"],
    "Activités collectives et duelles":["Rugby","Pelote Basque"],
    "Activités physiques de pleine nature":["Surf"],
    "Activités dansées et artistiques":[],
    "Activités douces et remise en forme":[],
    "Activités athlétiques":["Course à pied"],
}
FAMILLES=[
    ("🌊","Activités aquatiques","Nager • Sauver • Se dépasser","aqua"),
    ("🏉","Activités collectives et duelles","Coopérer • S’opposer • Jouer","team"),
    ("⛰️","Activités physiques de pleine nature","Explorer • Glisser • Respirer","nature"),
    ("💃","Activités dansées et artistiques","Créer • S’exprimer • Partager","dance"),
    ("🧘","Activités douces et remise en forme","Bien-être • Mobilité • Renforcement","well"),
    ("🏃","Activités athlétiques","Courir • Progresser • Performer","run"),
]

st.set_page_config(page_title="SUAPS UPPA", page_icon="🏃", layout="wide", initial_sidebar_state="collapsed")
st.markdown(r"""
<style>
:root{
 --navy:#062b62;--blue:#0757b7;--cyan:#0c91b7;--lime:#b5cb19;--teal:#0a8f8c;
 --orange:#ef7a09;--purple:#6840a6;--bg:#f4f7fb;--text:#10213b;--muted:#66758a;
}
html,body,[class*="css"]{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif}
.stApp{background:linear-gradient(180deg,#f8fbff 0%,#f2f6fb 100%);color:var(--text)}
.block-container{max-width:1080px;padding-top:.55rem;padding-bottom:6.5rem}
header[data-testid="stHeader"]{background:transparent}
[data-testid="stSidebar"]{display:none}
.suaps-top{display:flex;align-items:center;justify-content:space-between;gap:14px;margin:0 0 12px}
.suaps-brand{font-weight:900;color:var(--navy);font-size:2rem;letter-spacing:.06em}
.suaps-tag{font-weight:800;color:var(--blue);font-style:italic}
.phone-hero{border-radius:27px;padding:25px 23px;color:white;background:
 radial-gradient(circle at 90% 10%,rgba(255,255,255,.17),transparent 26%),
 linear-gradient(150deg,#041f49 0%,#073873 58%,#0757b7 100%);
 box-shadow:0 18px 45px rgba(5,43,98,.22);margin-bottom:15px}
.phone-hero .eyebrow{font-size:.8rem;font-weight:800;color:#c9df3c;letter-spacing:.08em;text-transform:uppercase}
.phone-hero h1{font-size:2.05rem;margin:.25rem 0 .15rem;line-height:1.08}
.phone-hero p{margin:0;color:#e9f3ff}
.quote{margin-top:15px;padding:14px 16px;border-radius:18px;background:linear-gradient(135deg,rgba(255,166,0,.30),rgba(255,255,255,.10));font-weight:800}
.section-title{font-size:1.05rem;font-weight:900;margin:20px 0 9px;color:#10213b}
.family{border-radius:22px;padding:18px;color:white;min-height:155px;box-shadow:0 10px 25px rgba(15,40,75,.14);position:relative;overflow:hidden}
.family:after{content:"";position:absolute;width:100px;height:100px;border-radius:50%;right:-20px;top:-25px;background:rgba(255,255,255,.12)}
.family .ico{font-size:2.1rem}.family h3{font-size:1.05rem;margin:.45rem 0 .3rem;color:white}.family p{font-size:.86rem;margin:0;color:rgba(255,255,255,.92)}
.aqua{background:linear-gradient(145deg,#0073c8,#00a6c8)}.team{background:linear-gradient(145deg,#9c1f2a,#d64b33)}
.nature{background:linear-gradient(145deg,#397a36,#79a532)}.dance{background:linear-gradient(145deg,#56328d,#8e53b1)}
.well{background:linear-gradient(145deg,#087d82,#13a4a0)}.run{background:linear-gradient(145deg,#d85e00,#f29208)}
.card{background:white;border:1px solid #e5ebf3;border-radius:20px;padding:16px;margin-bottom:10px;box-shadow:0 7px 20px rgba(15,40,75,.07)}
.card strong{color:var(--navy)}.muted{font-size:.9rem;color:var(--muted)}
.badge{display:inline-block;padding:4px 9px;border-radius:999px;font-size:.76rem;font-weight:800;background:#eaf2ff;color:#0757b7;margin-right:5px}
.kpi{background:white;border-radius:17px;padding:14px;border:1px solid #e5ebf3;text-align:center;box-shadow:0 5px 16px rgba(15,40,75,.06)}
.kpi b{font-size:1.45rem;color:var(--navy);display:block}.kpi span{font-size:.77rem;color:var(--muted);font-weight:700}
.progress-box{background:#eef8e8;border:1px solid #d8edca;border-radius:18px;padding:15px}
.bottom-nav{position:fixed;left:50%;bottom:10px;transform:translateX(-50%);width:min(96%,760px);z-index:999;
 display:flex;justify-content:space-around;background:rgba(255,255,255,.96);border:1px solid #e1e7ef;border-radius:21px;
 padding:9px 8px;box-shadow:0 12px 35px rgba(7,43,98,.18);backdrop-filter:blur(12px)}
.bottom-nav span{font-size:.72rem;color:#3e4f65;text-align:center;line-height:1.15}.bottom-nav b{display:block;font-size:1.1rem;color:#0757b7;margin-bottom:2px}
div.stButton>button,div.stFormSubmitButton>button{width:100%;border-radius:14px;min-height:47px;font-weight:800;border:none}
div.stButton>button[kind="primary"],div.stFormSubmitButton>button[kind="primary"]{background:#078b91;color:white}
div[data-testid="stMetric"]{background:white;border:1px solid #e5ebf3;border-radius:17px;padding:10px}
div[data-baseweb="select"]>div,input,textarea{border-radius:13px!important}
hr{border-color:#e5ebf3}
@media(max-width:720px){
 .block-container{padding:.35rem .62rem 6.2rem}
 .suaps-brand{font-size:1.6rem}.suaps-tag{font-size:.82rem}
 .phone-hero{padding:21px 17px;border-radius:23px}.phone-hero h1{font-size:1.7rem}
 div[data-testid="stHorizontalBlock"]{gap:.55rem}
 .family{min-height:140px;padding:15px}
}
</style>
""", unsafe_allow_html=True)

def db():
    c=sqlite3.connect(DB,check_same_thread=False,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=NORMAL")
    return c

@st.cache_resource
def init_db():
    c=db(); q=c.cursor()
    q.executescript("""
    CREATE TABLE IF NOT EXISTS utilisateurs(id INTEGER PRIMARY KEY AUTOINCREMENT,profil TEXT NOT NULL,nom TEXT NOT NULL,prenom TEXT NOT NULL,email TEXT NOT NULL UNIQUE,identifiant TEXT,composante TEXT,actif INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS offres(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,intitule TEXT NOT NULL,jour_horaire TEXT,lieu TEXT,capacite INTEGER DEFAULT 20,public TEXT DEFAULT 'Tous',ouverte INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS inscriptions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,offre_id INTEGER NOT NULL,modalite TEXT NOT NULL,statut TEXT DEFAULT 'Inscrit',date_inscription TEXT NOT NULL,UNIQUE(utilisateur_id,offre_id));
    CREATE TABLE IF NOT EXISTS seances(id INTEGER PRIMARY KEY AUTOINCREMENT,offre_id INTEGER NOT NULL,date_seance TEXT NOT NULL,theme TEXT,qr_token TEXT,qr_ouvert INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS presences(id INTEGER PRIMARY KEY AUTOINCREMENT,seance_id INTEGER NOT NULL,utilisateur_id INTEGER NOT NULL,statut TEXT DEFAULT 'Présent',mode_validation TEXT DEFAULT 'Manuel',commentaire TEXT,UNIQUE(seance_id,utilisateur_id));
    CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,intitule TEXT NOT NULL,note REAL,bareme REAL DEFAULT 20,coefficient REAL DEFAULT 1,commentaire TEXT,date_eval TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS performances(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,intitule TEXT NOT NULL,valeur REAL,unite TEXT,commentaire TEXT,date_perf TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS competences(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,code TEXT NOT NULL,libelle TEXT NOT NULL,UNIQUE(activite,code));
    CREATE TABLE IF NOT EXISTS acquisitions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,competence_id INTEGER NOT NULL,niveau TEXT DEFAULT 'Non évalué',commentaire TEXT,date_validation TEXT,UNIQUE(utilisateur_id,competence_id));
    CREATE INDEX IF NOT EXISTS ix_ins_u ON inscriptions(utilisateur_id,statut);
    CREATE INDEX IF NOT EXISTS ix_ins_o ON inscriptions(offre_id,statut);
    CREATE INDEX IF NOT EXISTS ix_pre_u ON presences(utilisateur_id,statut);
    CREATE INDEX IF NOT EXISTS ix_sea_o ON seances(offre_id,id);
    """)
    if q.execute("SELECT COUNT(*) n FROM offres").fetchone()["n"]==0:
        q.executemany("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",[
            ("Natation","Natation tous niveaux","Lundi 18h00","Piscine universitaire",24,"Tous"),
            ("Sauvetage","Préparation BNSSA / Sauvetage","Mardi 19h00","Piscine universitaire",20,"Étudiants"),
            ("Surf","Surf découverte & progression","Mercredi 14h00","Côte basque / Landes",18,"Tous"),
            ("Rugby","Rugby universitaire","Jeudi 18h30","Terrain universitaire",30,"Tous"),
            ("Course à pied","Running campus","Mardi 12h30","Campus de Pau",40,"Tous"),
            ("Pelote Basque","Pelote Basque","Jeudi 17h30","Fronton universitaire",20,"Tous")])
    defs={"Natation":["Respiration et aisance","Propulsion","Endurance","Virages"],"Sauvetage":["Sécurité","Approche victime","Remorquage","Conduite de secours"],"Surf":["Lecture du milieu","Rame","Take-off","Sécurité et priorités"],"Rugby":["Passe","Placement","Défense","Organisation collective"],"Course à pied":["Gestion d'allure","Endurance","Technique","Échauffement-récupération"],"Pelote Basque":["Frappe","Placement","Choix tactiques","Règles et sécurité"]}
    for a,items in defs.items():
        for i,x in enumerate(items,1): q.execute("INSERT OR IGNORE INTO competences(activite,code,libelle) VALUES(?,?,?)",(a,f"{a[:3].upper()}{i}",x))
    c.commit(); c.close()
init_db()

def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return r
def one(sql,p=()):
    r=rows(sql,p); return r[0] if r else None
def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x

for k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord","family":None}.items():
    st.session_state.setdefault(k,v)
def go(p): st.session_state.page=p; st.rerun()
def user(): return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,)) if st.session_state.user_id else None
def topbar():
    st.markdown('<div class="suaps-top"><div class="suaps-brand">SUAPS</div><div class="suaps-tag">Bouge ton campus,<br>révèle ton potentiel !</div></div>',unsafe_allow_html=True)
def hero(title,sub,eyebrow="SUAPS • UPPA"):
    st.markdown(f'<div class="phone-hero"><div class="eyebrow">{eyebrow}</div><h1>{title}</h1><p>{sub}</p><div class="quote">Le sport aujourd’hui, la réussite demain !</div></div>',unsafe_allow_html=True)
def card(title,text="",badges=None):
    badges=badges or []
    b="".join(f'<span class="badge">{x}</span>' for x in badges)
    st.markdown(f'<div class="card"><strong>{title}</strong><div class="muted">{text}</div><div style="margin-top:8px">{b}</div></div>',unsafe_allow_html=True)
def nav():
    st.markdown('<div class="bottom-nav"><span><b>⌂</b>Accueil</span><span><b>⚡</b>Activités</span><span><b>▣</b>Inscription</span><span><b>↗</b>Résultats</span><span><b>●</b>Profil</span></div>',unsafe_allow_html=True)

def accueil():
    topbar(); hero("Bouge. Progresse. Partage.","Le sport universitaire dans une application simple, mobile et motivante.")
    st.markdown('<div class="section-title">Choisis ton espace</div>',unsafe_allow_html=True)
    cols=st.columns(3)
    data=[("🎓","Étudiant","Inscriptions, présence, résultats et compétences.","Étudiant"),("👥","Personnel UPPA","Activités, créneaux et inscriptions.","Personnel"),("🧑‍🏫","Enseignant / Admin","Présences, évaluations et pilotage.","Enseignant/Admin")]
    for col,(ico,t,txt,prof) in zip(cols,data):
        with col:
            card(f"{ico} {t}",txt)
            if st.button("Entrer",key=f"enter_{prof}",type="primary"):
                st.session_state.profil=prof; go("Administration" if prof=="Enseignant/Admin" else "Connexion")
    st.markdown('<div class="section-title">6 familles d’activités</div>',unsafe_allow_html=True)
    for row in range(2):
        cols=st.columns(3)
        for j,col in enumerate(cols):
            i=row*3+j
            ico,t,d,cls=FAMILLES[i]
            with col:
                st.markdown(f'<div class="family {cls}"><div class="ico">{ico}</div><h3>{t}</h3><p>{d}</p></div>',unsafe_allow_html=True)
                if st.button("Découvrir",key=f"fam_{i}"):
                    st.session_state.family=t; go("Famille")
    nav()

def famille():
    topbar()
    fam=st.session_state.family or FAMILLES[0][1]
    item=next(x for x in FAMILLES if x[1]==fam)
    hero(f"{item[0]} {fam}",item[2],"ACTIVITÉS")
    acts=FAMILY_MAP.get(fam,[])
    if not acts: st.info("Les activités de cette famille seront ajoutées prochainement.")
    else:
        offs=rows("SELECT * FROM offres WHERE ouverte=1 ORDER BY activite,intitule")
        found=[o for o in offs if o["activite"] in acts]
        for o in found: card(f"{o['activite']} — {o['intitule']}",f"🕒 {o['jour_horaire'] or 'À définir'}  •  📍 {o['lieu'] or 'À définir'}",[o["public"]])
    if st.button("← Retour aux familles"): go("Accueil")
    nav()

def connexion():
    topbar(); hero(f"Espace {st.session_state.profil}","Connecte-toi ou crée ton profil.","MON PROFIL")
    prof=st.session_state.profil
    t1,t2=st.tabs(["Connexion","Créer mon profil"])
    with t1:
        with st.form("login"):
            email=st.text_input("Adresse e-mail")
            ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
            if r: st.session_state.user_id=r["id"]; go("Mon espace")
            else: st.error("Profil introuvable.")
    with t2:
        with st.form("signup"):
            a,b=st.columns(2); nom=a.text_input("Nom"); pre=b.text_input("Prénom")
            mail=st.text_input("E-mail UPPA"); ident=st.text_input("Numéro étudiant / identifiant"); comp=st.text_input("Formation / service")
            ok=st.form_submit_button("Créer mon profil",type="primary")
        if ok:
            if not nom or not pre or not mail: st.warning("Nom, prénom et e-mail sont obligatoires.")
            else:
                try:
                    st.session_state.user_id=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante) VALUES(?,?,?,?,?,?)",(prof,nom.strip(),pre.strip(),mail.strip(),ident.strip(),comp.strip())); go("Mon espace")
                except sqlite3.IntegrityError: st.error("Cette adresse e-mail est déjà enregistrée.")
    if st.button("← Accueil"): go("Accueil")

def espace():
    u=user()
    if not u: go("Accueil")
    topbar(); hero(f"Bonjour {u['prenom']} 👋",f"{u['profil']} • Prêt(e) pour ta prochaine séance ?","MON TABLEAU DE BORD")
    s=one("SELECT (SELECT COUNT(*) FROM inscriptions WHERE utilisateur_id=? AND statut='Inscrit') i,(SELECT COUNT(*) FROM presences WHERE utilisateur_id=? AND statut='Présent') p,(SELECT COUNT(*) FROM evaluations WHERE utilisateur_id=?) e,(SELECT COUNT(*) FROM acquisitions WHERE utilisateur_id=? AND niveau IN ('Acquis','Maîtrisé')) c",(u["id"],u["id"],u["id"],u["id"]))
    cols=st.columns(4)
    for col,l,v in zip(cols,["Présences","Inscriptions","Évaluations","Compétences"],[s["p"],s["i"],s["e"],s["c"]]):
        with col: st.markdown(f'<div class="kpi"><b>{v}</b><span>{l}</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Accès rapide</div>',unsafe_allow_html=True)
    for col,label,p in zip(st.columns(4),["📝 M'inscrire","📅 Planning","✅ Présence QR","📈 Résultats"],["Inscriptions","Planning","Présence","Résultats"]):
        if col.button(label): go(p)
    st.markdown('<div class="section-title">Mes activités</div>',unsafe_allow_html=True)
    mine=rows("SELECT o.activite,o.intitule,o.jour_horaire,o.lieu,i.modalite FROM inscriptions i JOIN offres o ON o.id=i.offre_id WHERE i.utilisateur_id=? AND i.statut='Inscrit' ORDER BY o.activite",(u["id"],))
    if not mine: st.info("Aucune inscription pour le moment.")
    for r in mine: card(f"{r['activite']} — {r['intitule']}",f"🕒 {r['jour_horaire'] or 'À définir'} • 📍 {r['lieu'] or 'À définir'}",[r["modalite"]])
    if st.button("Se déconnecter"): st.session_state.user_id=None; go("Accueil")
    nav()

def inscriptions():
    u=user(); topbar(); hero("Inscription","Choisis d’abord une famille, puis ton activité et ton créneau.","INSCRIPTION EN LIGNE")
    fam=st.selectbox("Famille d’activités",[x[1] for x in FAMILLES])
    acts=FAMILY_MAP.get(fam,[])
    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule")
    data=[o for o in data if o["activite"] in acts]
    if not data: st.info("Aucun créneau ouvert dans cette famille.")
    for o in data:
        dispo=max(0,o["capacite"]-o["n"])
        card(f"{o['activite']} — {o['intitule']}",f"🕒 {o['jour_horaire'] or 'À définir'} • 📍 {o['lieu'] or 'À définir'} • {dispo}/{o['capacite']} places",[o["public"]])
        mod="Personnel" if u["profil"]=="Personnel" else st.selectbox("Modalité",["UET","UECF","Non noté"],key=f"m{o['id']}")
        if st.button("S'inscrire",key=f"i{o['id']}",type="primary"):
            if dispo<=0: st.error("Créneau complet.")
            elif o["public"]=="Étudiants" and u["profil"]!="Étudiant": st.warning("Créneau réservé aux étudiants.")
            else:
                try:
                    exe("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,date_inscription) VALUES(?,?,?,?)",(u["id"],o["id"],mod,datetime.now().isoformat(timespec="seconds"))); st.success("Inscription enregistrée."); st.rerun()
                except sqlite3.IntegrityError: st.info("Tu es déjà inscrit.")
    if st.button("← Mon espace"): go("Mon espace")
    nav()

def planning():
    u=user(); topbar(); hero("Mon planning","Tes prochains créneaux en un coup d’œil.","AGENDA")
    data=rows("SELECT o.activite,o.intitule,o.jour_horaire,o.lieu,i.modalite FROM inscriptions i JOIN offres o ON o.id=i.offre_id WHERE i.utilisateur_id=? AND i.statut='Inscrit' ORDER BY o.jour_horaire",(u["id"],))
    if not data: st.info("Aucun créneau.")
    for r in data: card(f"{r['activite']} — {r['intitule']}",f"🕒 {r['jour_horaire'] or 'À définir'} • 📍 {r['lieu'] or 'À définir'}",[r["modalite"]])
    if st.button("← Mon espace"): go("Mon espace")
    nav()

def presence():
    u=user(); topbar(); hero("Présence","Scanne le QR Code ou saisis le code de la séance.","PRÉSENCE PAR QR CODE")
    st.markdown('<div class="card" style="text-align:center;padding:28px"><div style="font-size:4rem">▦</div><strong>QR SUAPS</strong><div class="muted">Le code est affiché par l’enseignant pendant la séance.</div></div>',unsafe_allow_html=True)
    with st.form("pres"):
        tok=st.text_input("Code de présence / QR")
        ok=st.form_submit_button("Valider ma présence",type="primary")
    if ok:
        s=one("SELECT s.id,o.activite FROM seances s JOIN offres o ON o.id=s.offre_id WHERE s.qr_token=? AND s.qr_ouvert=1 ORDER BY s.id DESC LIMIT 1",(tok.strip(),))
        if not s: st.error("Code invalide ou fermé.")
        else:
            try: exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,?)",(s["id"],u["id"],"Présent","QR"))
            except sqlite3.IntegrityError: exe("UPDATE presences SET statut='Présent',mode_validation='QR' WHERE seance_id=? AND utilisateur_id=?",(s["id"],u["id"]))
            st.success(f"Présence validée : {s['activite']} ✅")
    if st.button("← Mon espace"): go("Mon espace")
    nav()

def resultats():
    u=user(); topbar(); hero("Mes résultats","Notes, performances et compétences au même endroit.","PROGRESSION")
    typ=st.radio("Afficher",["Notes","Performances","Compétences"],horizontal=True)
    if typ=="Notes":
        data=rows("SELECT * FROM evaluations WHERE utilisateur_id=? ORDER BY date_eval DESC,id DESC",(u["id"],))
        for r in data: card(f"{r['activite']} — {r['intitule']}",f"{r['note'] if r['note'] is not None else '-'} / {r['bareme']} • Coef. {r['coefficient']} • {r['date_eval']}")
    elif typ=="Performances":
        data=rows("SELECT * FROM performances WHERE utilisateur_id=? ORDER BY date_perf DESC,id DESC",(u["id"],))
        for r in data: card(f"{r['activite']} — {r['intitule']}",f"{r['valeur']} {r['unite'] or ''} • {r['date_perf']}")
    else:
        data=rows("SELECT c.activite,c.code,c.libelle,COALESCE(a.niveau,'Non évalué') niveau FROM competences c LEFT JOIN acquisitions a ON a.competence_id=c.id AND a.utilisateur_id=? ORDER BY c.activite,c.code",(u["id"],))
        for r in data:
            badge="✅ "+r["niveau"] if r["niveau"] in ("Acquis","Maîtrisé") else r["niveau"]
            card(f"{r['activite']} • {r['code']}",r["libelle"],[badge])
    if not data: st.info("Aucune donnée.")
    if st.button("← Mon espace"): go("Mon espace")
    nav()

def admin():
    topbar(); hero("Enseignant / Administration","Pilotage rapide des créneaux, présences et évaluations.","ESPACE ENSEIGNANT")
    sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences"],horizontal=True,key="admin_section")
    if sec=="Tableau de bord":
        s=one("SELECT (SELECT COUNT(*) FROM utilisateurs WHERE actif=1) u,(SELECT COUNT(*) FROM inscriptions WHERE statut='Inscrit') i,(SELECT COUNT(*) FROM seances) s,(SELECT COUNT(*) FROM presences WHERE statut='Présent') p")
        for col,l,v in zip(st.columns(4),["Utilisateurs","Inscriptions","Séances","Présences"],[s["u"],s["i"],s["s"],s["p"]]): col.metric(l,v)
        d=rows("SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id ORDER BY i.id DESC LIMIT 30")
        if d: st.dataframe([dict(x) for x in d],use_container_width=True,hide_index=True)
    elif sec=="Créneaux":
        with st.form("newslot"):
            a,b=st.columns(2); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Intitulé",value=f"{act} - créneau")
            c,d=st.columns(2); hor=c.text_input("Jour / horaire"); lieu=d.text_input("Lieu")
            e,f=st.columns(2); cap=e.number_input("Capacité",1,200,20); pub=f.selectbox("Public",["Tous","Étudiants","Personnel"])
            ok=st.form_submit_button("Créer le créneau",type="primary")
        if ok: exe("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",(act,title,hor,lieu,cap,pub)); st.success("Créneau créé."); st.rerun()
        offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offs:
            mp={f"{o['activite']} — {o['intitule']} ({'ouvert' if o['ouverte'] else 'fermé'})":o for o in offs}
            o=mp[st.selectbox("Modifier un créneau",list(mp))]
            with st.form("editslot"):
                a,b=st.columns(2); ea=a.selectbox("Activité",ACTIVITES,index=ACTIVITES.index(o["activite"]) if o["activite"] in ACTIVITES else 0); et=b.text_input("Intitulé",o["intitule"])
                c,d=st.columns(2); eh=c.text_input("Jour / horaire",o["jour_horaire"] or ""); el=d.text_input("Lieu",o["lieu"] or "")
                e,f=st.columns(2); ec=e.number_input("Capacité",1,200,int(o["capacite"])); ep=f.selectbox("Public",["Tous","Étudiants","Personnel"],index=["Tous","Étudiants","Personnel"].index(o["public"]) if o["public"] in ["Tous","Étudiants","Personnel"] else 0)
                opened=st.checkbox("Ouvert aux inscriptions",bool(o["ouverte"])); save=st.form_submit_button("Enregistrer",type="primary")
            if save: exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"])); st.success("Créneau mis à jour."); st.rerun()
    elif sec=="Présences":
        offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offs:
            mp={f"{o['activite']} — {o['intitule']}":o["id"] for o in offs}; oid=mp[st.selectbox("Créneau",list(mp))]
            with st.form("newsess"):
                d=st.date_input("Date",date.today()); theme=st.text_input("Thème"); tok=st.text_input("Code QR / présence",value=f"SUAPS-{datetime.now().strftime('%H%M%S')}")
                ok=st.form_submit_button("Ouvrir une séance",type="primary")
            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
    elif sec=="Évaluations":
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if us:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}")
            mode=st.radio("Saisie",["Évaluation","Performance"],horizontal=True)
            if mode=="Évaluation":
                with st.form("eval"):
                    act=st.selectbox("Activité",ACTIVITES); title=st.text_input("Évaluation / test"); note=st.number_input("Note",0.,100.,10.); bar=st.number_input("Barème",1.,100.,20.); coef=st.number_input("Coefficient",0.1,20.,1.0); ok=st.form_submit_button("Enregistrer",type="primary")
                if ok: exe("INSERT INTO evaluations(utilisateur_id,activite,intitule,note,bareme,coefficient,date_eval) VALUES(?,?,?,?,?,?,?)",(p["id"],act,title,note,bar,coef,str(date.today()))); st.success("Évaluation enregistrée.")
            else:
                with st.form("perf"):
                    act=st.selectbox("Activité",ACTIVITES); title=st.text_input("Performance / test"); val=st.number_input("Valeur",value=0.0); unit=st.text_input("Unité"); ok=st.form_submit_button("Enregistrer",type="primary")
                if ok: exe("INSERT INTO performances(utilisateur_id,activite,intitule,valeur,unite,date_perf) VALUES(?,?,?,?,?,?)",(p["id"],act,title,val,unit,str(date.today()))); st.success("Performance enregistrée.")
    else:
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if us:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}")
            comps=rows("SELECT * FROM competences ORDER BY activite,code")
            if comps:
                c=st.selectbox("Compétence",comps,format_func=lambda r:f"{r['activite']} • {r['code']} — {r['libelle']}")
                niv=st.selectbox("Niveau",["Non évalué","En cours","Acquis","Maîtrisé"])
                if st.button("Valider la compétence",type="primary"):
                    try: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,date_validation) VALUES(?,?,?,?)",(p["id"],c["id"],niv,str(date.today())))
                    except sqlite3.IntegrityError: exe("UPDATE acquisitions SET niveau=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,str(date.today()),p["id"],c["id"]))
                    st.success("Compétence mise à jour.")
    if st.button("← Accueil"): go("Accueil")

pages={"Accueil":accueil,"Famille":famille,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}
pages.get(st.session_state.page,accueil)()
