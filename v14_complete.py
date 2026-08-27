import sqlite3
from datetime import date, datetime
from pathlib import Path
import streamlit as st

DB="suaps_v14.db"
ACTIVITES=["Natation","Sauvetage","Surf","Rugby","Course à pied","Pelote Basque"]
FAMILLES=[("🏊","Activités aquatiques","Natation • Sauvetage • Aquagym"),("🏉","Activités collectives et duelles","Sports collectifs • Raquettes • Combat"),("🌿","Activités physiques de pleine nature","Nature • Glisse • Aventure"),("💃","Activités dansées et artistiques","Danse • Expression • Créativité"),("🧘","Activités douces et remise en forme","Bien-être • Mobilité • Renforcement"),("🏃","Activités athlétiques","Course • Endurance • Performance")]

st.set_page_config(page_title="SUAPS UPPA",page_icon="🏃",layout="wide",initial_sidebar_state="collapsed")
st.markdown("""<style>
.stApp{background:#F5F8FD}.block-container{max-width:1150px;padding-top:1rem;padding-bottom:4rem}
.hero{padding:22px;border-radius:24px;color:white;background:linear-gradient(135deg,#0B5FFF,#5B63FF 58%,#00A88F);margin-bottom:16px}.hero h1{margin:0}.hero p{margin:.4rem 0 0}
.card{background:white;border:1px solid #E7EDF7;border-radius:18px;padding:15px;margin-bottom:12px;box-shadow:0 5px 16px rgba(20,33,61,.06)}
.small{color:#62708A;font-size:.92rem}.badge{display:inline-block;padding:5px 9px;border-radius:999px;background:#EAF2FF;color:#0B5FFF;font-weight:700;font-size:.8rem}
div.stButton>button{width:100%;min-height:44px;border-radius:13px;font-weight:700}div[data-testid="stMetric"]{background:white;border:1px solid #E7EDF7;border-radius:15px;padding:9px}
@media(max-width:720px){.block-container{padding:.6rem .7rem 4rem}.hero{padding:17px}.hero h1{font-size:1.5rem}}
</style>""",unsafe_allow_html=True)

def db():
    c=sqlite3.connect(DB,check_same_thread=False,timeout=10); c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=NORMAL"); return c

@st.cache_resource
def init_db():
    c=db(); q=c.cursor(); q.executescript("""
    CREATE TABLE IF NOT EXISTS utilisateurs(id INTEGER PRIMARY KEY AUTOINCREMENT,profil TEXT NOT NULL,nom TEXT NOT NULL,prenom TEXT NOT NULL,email TEXT NOT NULL UNIQUE,identifiant TEXT,composante TEXT,actif INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS offres(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,intitule TEXT NOT NULL,jour_horaire TEXT,lieu TEXT,capacite INTEGER DEFAULT 20,public TEXT DEFAULT 'Tous',ouverte INTEGER DEFAULT 1);
    CREATE TABLE IF NOT EXISTS inscriptions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,offre_id INTEGER NOT NULL,modalite TEXT NOT NULL,statut TEXT DEFAULT 'Inscrit',date_inscription TEXT NOT NULL,UNIQUE(utilisateur_id,offre_id));
    CREATE TABLE IF NOT EXISTS seances(id INTEGER PRIMARY KEY AUTOINCREMENT,offre_id INTEGER NOT NULL,date_seance TEXT NOT NULL,theme TEXT,qr_token TEXT,qr_ouvert INTEGER DEFAULT 0);
    CREATE TABLE IF NOT EXISTS presences(id INTEGER PRIMARY KEY AUTOINCREMENT,seance_id INTEGER NOT NULL,utilisateur_id INTEGER NOT NULL,statut TEXT DEFAULT 'Présent',mode_validation TEXT DEFAULT 'Manuel',commentaire TEXT,UNIQUE(seance_id,utilisateur_id));
    CREATE TABLE IF NOT EXISTS evaluations(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,intitule TEXT NOT NULL,note REAL,bareme REAL DEFAULT 20,coefficient REAL DEFAULT 1,commentaire TEXT,date_eval TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS performances(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,activite TEXT NOT NULL,intitule TEXT NOT NULL,valeur REAL,unite TEXT,commentaire TEXT,date_perf TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS competences(id INTEGER PRIMARY KEY AUTOINCREMENT,activite TEXT NOT NULL,code TEXT NOT NULL,libelle TEXT NOT NULL,UNIQUE(activite,code));
    CREATE TABLE IF NOT EXISTS acquisitions(id INTEGER PRIMARY KEY AUTOINCREMENT,utilisateur_id INTEGER NOT NULL,competence_id INTEGER NOT NULL,niveau TEXT DEFAULT 'Non évalué',commentaire TEXT,date_validation TEXT,UNIQUE(utilisateur_id,competence_id));
    CREATE INDEX IF NOT EXISTS ix_ins_u ON inscriptions(utilisateur_id,statut);CREATE INDEX IF NOT EXISTS ix_ins_o ON inscriptions(offre_id,statut);CREATE INDEX IF NOT EXISTS ix_pre_u ON presences(utilisateur_id,statut);CREATE INDEX IF NOT EXISTS ix_sea_o ON seances(offre_id,id);CREATE INDEX IF NOT EXISTS ix_ev_u ON evaluations(utilisateur_id,date_eval);CREATE INDEX IF NOT EXISTS ix_pf_u ON performances(utilisateur_id,date_perf);CREATE INDEX IF NOT EXISTS ix_ac_u ON acquisitions(utilisateur_id,competence_id);
    """)
    if q.execute("SELECT COUNT(*) n FROM offres").fetchone()["n"]==0:
        q.executemany("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",[("Natation","Natation tous niveaux","Lundi 18h00","Piscine universitaire",24,"Tous"),("Sauvetage","Préparation BNSSA / Sauvetage","Mardi 19h00","Piscine universitaire",20,"Étudiants"),("Surf","Surf découverte & progression","Mercredi 14h00","Côte basque / Landes",18,"Tous"),("Rugby","Rugby universitaire","Jeudi 18h30","Terrain universitaire",30,"Tous"),("Course à pied","Running campus","Mardi 12h30","Campus de Pau",40,"Tous"),("Pelote Basque","Pelote Basque","Jeudi 17h30","Fronton universitaire",20,"Tous")])
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
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); i=q.lastrowid; c.close(); return i

def hero(t,s): st.markdown(f'<div class="hero"><span class="badge">SUAPS • UPPA</span><h1>{t}</h1><p>{s}</p></div>',unsafe_allow_html=True)
def card(title,text=""): st.markdown(f'<div class="card"><b>{title}</b><br><span class="small">{text}</span></div>',unsafe_allow_html=True)
for k,v in {"page":"Accueil","profil":None,"user_id":None,"admin_section":"Tableau de bord"}.items(): st.session_state.setdefault(k,v)
def go(p): st.session_state.page=p; st.rerun()
def user(): return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,)) if st.session_state.user_id else None

def accueil():
    hero("Bouge. Progresse. Partage.","Le sport universitaire dans une application simple, mobile et motivante.")
    if Path("logo_uppa.png").exists(): st.image("logo_uppa.png",width=190)
    st.subheader("Choisis ton espace"); a,b,c=st.columns(3)
    for col,title,txt,prof in [(a,"🎓 Étudiant","Inscriptions, planning, présence, résultats et compétences.","Étudiant"),(b,"👥 Personnel UPPA","Activités, créneaux et inscriptions.","Personnel"),(c,"🧑‍🏫 Enseignant / Admin","Présences, évaluations et pilotage.","Enseignant/Admin")]:
        with col:
            card(title,txt)
            if st.button("Entrer",key=f"enter_{prof}"): st.session_state.profil=prof; go("Administration" if prof=="Enseignant/Admin" else "Connexion")
    st.subheader("6 familles d’activités"); cols=st.columns(3)
    for i,(ico,t,d) in enumerate(FAMILLES):
        with cols[i%3]: card(f"{ico} {t}",d)

def connexion():
    hero(f"Espace {st.session_state.profil}","Connecte-toi ou crée ton profil."); prof=st.session_state.profil; t1,t2=st.tabs(["Connexion","Créer mon profil"])
    with t1:
        with st.form("login"):
            email=st.text_input("Adresse e-mail"); ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
            if r: st.session_state.user_id=r["id"]; go("Mon espace")
            st.error("Profil introuvable.")
    with t2:
        with st.form("signup"):
            a,b=st.columns(2); nom=a.text_input("Nom"); pre=b.text_input("Prénom"); mail=st.text_input("E-mail UPPA"); ident=st.text_input("Numéro étudiant / identifiant"); comp=st.text_input("Formation / service"); ok=st.form_submit_button("Créer mon profil",type="primary")
        if ok:
            if not nom or not pre or not mail: st.warning("Nom, prénom et e-mail sont obligatoires.")
            else:
                try: st.session_state.user_id=exe("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante) VALUES(?,?,?,?,?,?)",(prof,nom.strip(),pre.strip(),mail.strip(),ident.strip(),comp.strip())); go("Mon espace")
                except sqlite3.IntegrityError: st.error("Cette adresse e-mail est déjà enregistrée.")
    if st.button("← Accueil"): go("Accueil")

def espace():
    u=user()
    if not u: go("Accueil")
    hero(f"Bonjour {u['prenom']} 👋",f"Espace {u['profil']} • activités et progression.")
    s=one("SELECT (SELECT COUNT(*) FROM inscriptions WHERE utilisateur_id=? AND statut='Inscrit') i,(SELECT COUNT(*) FROM presences WHERE utilisateur_id=? AND statut='Présent') p,(SELECT COUNT(*) FROM evaluations WHERE utilisateur_id=?) e,(SELECT COUNT(*) FROM acquisitions WHERE utilisateur_id=? AND niveau IN ('Acquis','Maîtrisé')) c",(u["id"],u["id"],u["id"],u["id"]))
    for col,label,val in zip(st.columns(4),["Inscriptions","Présences","Évaluations","Compétences"],[s["i"],s["p"],s["e"],s["c"]]): col.metric(label,val)
    for col,label,p in zip(st.columns(4),["➕ M'inscrire","📅 Planning","✅ Présence QR","📈 Résultats"],["Inscriptions","Planning","Présence","Résultats"]):
        if col.button(label): go(p)
    st.markdown("### Mes activités"); mine=rows("SELECT o.activite,o.intitule,o.jour_horaire,o.lieu,i.modalite FROM inscriptions i JOIN offres o ON o.id=i.offre_id WHERE i.utilisateur_id=? AND i.statut='Inscrit' ORDER BY o.activite",(u["id"],))
    if not mine: st.info("Aucune inscription.")
    for r in mine: card(f"{r['activite']} — {r['intitule']}",f"📅 {r['jour_horaire'] or 'À définir'} • 📍 {r['lieu'] or 'À définir'} • {r['modalite']}")
    if st.button("Se déconnecter"): st.session_state.user_id=None; go("Accueil")

def inscriptions():
    u=user(); hero("Inscriptions sportives","Choisis une activité et réserve ton créneau.")
    data=rows("SELECT o.*,COUNT(CASE WHEN i.statut='Inscrit' THEN 1 END) n FROM offres o LEFT JOIN inscriptions i ON i.offre_id=o.id WHERE o.ouverte=1 GROUP BY o.id ORDER BY o.activite,o.intitule")
    for o in data:
        dispo=max(0,o["capacite"]-o["n"]); card(f"{o['activite']} — {o['intitule']}",f"📅 {o['jour_horaire'] or 'À définir'} • 📍 {o['lieu'] or 'À définir'} • Places {dispo}/{o['capacite']} • {o['public']}")
        mod="Personnel" if u["profil"]=="Personnel" else st.selectbox("Modalité",["UET","UECF","Non noté"],key=f"m{o['id']}")
        if st.button(f"S'inscrire à {o['activite']}",key=f"i{o['id']}"):
            if dispo<=0: st.error("Créneau complet.")
            elif o["public"]=="Étudiants" and u["profil"]!="Étudiant": st.warning("Créneau réservé aux étudiants.")
            else:
                try: exe("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,date_inscription) VALUES(?,?,?,?)",(u["id"],o["id"],mod,datetime.now().isoformat(timespec="seconds"))); st.success("Inscription enregistrée."); st.rerun()
                except sqlite3.IntegrityError: st.info("Tu es déjà inscrit.")
    if st.button("← Mon espace"): go("Mon espace")

def planning():
    u=user(); hero("Mon planning","Tes créneaux en un coup d'œil."); data=rows("SELECT o.activite,o.intitule,o.jour_horaire,o.lieu,i.modalite FROM inscriptions i JOIN offres o ON o.id=i.offre_id WHERE i.utilisateur_id=? AND i.statut='Inscrit' ORDER BY o.jour_horaire",(u["id"],))
    if not data: st.info("Aucun créneau.")
    for r in data: card(f"{r['activite']} — {r['intitule']}",f"📅 {r['jour_horaire'] or 'À définir'} • 📍 {r['lieu'] or 'À définir'} • {r['modalite']}")
    if st.button("← Mon espace"): go("Mon espace")

def presence():
    u=user(); hero("Validation de présence","Saisis le code affiché par l'enseignant.")
    with st.form("pres"):
        tok=st.text_input("Code de présence / QR"); ok=st.form_submit_button("Valider",type="primary")
    if ok:
        s=one("SELECT s.id,o.activite FROM seances s JOIN offres o ON o.id=s.offre_id WHERE s.qr_token=? AND s.qr_ouvert=1 ORDER BY s.id DESC LIMIT 1",(tok.strip(),))
        if not s: st.error("Code invalide ou fermé.")
        else:
            try: exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,?)",(s["id"],u["id"],"Présent","QR"))
            except sqlite3.IntegrityError: exe("UPDATE presences SET statut='Présent',mode_validation='QR' WHERE seance_id=? AND utilisateur_id=?",(s["id"],u["id"]))
            st.success(f"Présence validée : {s['activite']}.")
    if st.button("← Mon espace"): go("Mon espace")

def resultats():
    u=user(); hero("Mes résultats","Notes, performances et compétences."); typ=st.radio("Afficher",["Notes","Performances","Compétences"],horizontal=True)
    if typ=="Notes": data=rows("SELECT * FROM evaluations WHERE utilisateur_id=? ORDER BY date_eval DESC,id DESC",(u["id"],)); [card(f"{r['activite']} — {r['intitule']}",f"{r['note'] if r['note'] is not None else '-'} / {r['bareme']} • Coef. {r['coefficient']} • {r['date_eval']}") for r in data]
    elif typ=="Performances": data=rows("SELECT * FROM performances WHERE utilisateur_id=? ORDER BY date_perf DESC,id DESC",(u["id"],)); [card(f"{r['activite']} — {r['intitule']}",f"{r['valeur']} {r['unite'] or ''} • {r['date_perf']}") for r in data]
    else: data=rows("SELECT c.activite,c.code,c.libelle,COALESCE(a.niveau,'Non évalué') niveau FROM competences c LEFT JOIN acquisitions a ON a.competence_id=c.id AND a.utilisateur_id=? ORDER BY c.activite,c.code",(u["id"],)); [card(f"{r['activite']} • {r['code']}",f"{r['libelle']} • {r['niveau']}") for r in data]
    if not data: st.info("Aucune donnée.")
    if st.button("← Mon espace"): go("Mon espace")

def admin():
    hero("Espace Enseignant / Administration","Une seule rubrique est calculée à la fois pour gagner en rapidité."); sec=st.radio("Rubrique",["Tableau de bord","Créneaux","Présences","Évaluations","Compétences"],horizontal=True,key="admin_section")
    if sec=="Tableau de bord":
        s=one("SELECT (SELECT COUNT(*) FROM utilisateurs WHERE actif=1) u,(SELECT COUNT(*) FROM inscriptions WHERE statut='Inscrit') i,(SELECT COUNT(*) FROM seances) s,(SELECT COUNT(*) FROM presences WHERE statut='Présent') p")
        for col,l,v in zip(st.columns(4),["Utilisateurs","Inscriptions","Séances","Présences"],[s["u"],s["i"],s["s"],s["p"]]): col.metric(l,v)
        d=rows("SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id ORDER BY i.id DESC LIMIT 30"); st.dataframe([dict(x) for x in d],use_container_width=True,hide_index=True) if d else st.info("Aucune inscription.")
    elif sec=="Créneaux":
        with st.form("newslot"):
            a,b=st.columns(2); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Intitulé",value=f"{act} - créneau"); c,d=st.columns(2); hor=c.text_input("Jour / horaire"); lieu=d.text_input("Lieu"); e,f=st.columns(2); cap=e.number_input("Capacité",1,200,20); pub=f.selectbox("Public",["Tous","Étudiants","Personnel"]); ok=st.form_submit_button("Créer le créneau",type="primary")
        if ok: exe("INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public) VALUES(?,?,?,?,?,?)",(act,title,hor,lieu,cap,pub)); st.success("Créneau créé."); st.rerun()
        offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offs:
            mp={f"{o['activite']} — {o['intitule']} ({'ouvert' if o['ouverte'] else 'fermé'})":o for o in offs}; o=mp[st.selectbox("Modifier un créneau",list(mp))]
            with st.form("editslot"):
                a,b=st.columns(2); ea=a.selectbox("Activité",ACTIVITES,index=ACTIVITES.index(o["activite"]) if o["activite"] in ACTIVITES else 0); et=b.text_input("Intitulé",o["intitule"]); c,d=st.columns(2); eh=c.text_input("Jour / horaire",o["jour_horaire"] or ""); el=d.text_input("Lieu",o["lieu"] or ""); e,f=st.columns(2); ec=e.number_input("Capacité",1,200,int(o["capacite"])); ep=f.selectbox("Public",["Tous","Étudiants","Personnel"],index=["Tous","Étudiants","Personnel"].index(o["public"]) if o["public"] in ["Tous","Étudiants","Personnel"] else 0); opened=st.checkbox("Ouvert aux inscriptions",bool(o["ouverte"])); save=st.form_submit_button("Enregistrer",type="primary")
            if save: exe("UPDATE offres SET activite=?,intitule=?,jour_horaire=?,lieu=?,capacite=?,public=?,ouverte=? WHERE id=?",(ea,et,eh,el,ec,ep,int(opened),o["id"])); st.success("Créneau mis à jour."); st.rerun()
            dep=one("SELECT (SELECT COUNT(*) FROM inscriptions WHERE offre_id=?) i,(SELECT COUNT(*) FROM seances WHERE offre_id=?) s",(o["id"],o["id"]))
            if dep["i"]==0 and dep["s"]==0 and st.button("🗑️ Supprimer définitivement"): exe("DELETE FROM offres WHERE id=?",(o["id"],)); st.rerun()
            elif dep["i"] or dep["s"]: st.caption("Ce créneau a un historique : ferme-le plutôt que le supprimer.")
    elif sec=="Présences":
        offs=rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offs:
            mp={f"{o['activite']} — {o['intitule']}":o["id"] for o in offs}; oid=mp[st.selectbox("Créneau",list(mp))]
            with st.form("newsess"):
                d=st.date_input("Date",date.today()); theme=st.text_input("Thème"); tok=st.text_input("Code QR / présence",value=f"SUAPS-{datetime.now().strftime('%H%M%S')}"); ok=st.form_submit_button("Ouvrir une séance",type="primary")
            if ok: exe("UPDATE seances SET qr_ouvert=0 WHERE offre_id=?",(oid,)); exe("INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert) VALUES(?,?,?,?,1)",(oid,str(d),theme,tok)); st.success(f"Code : {tok}"); st.rerun()
            ss=rows("SELECT * FROM seances WHERE offre_id=? ORDER BY id DESC LIMIT 20",(oid,)); us=rows("SELECT u.id,u.nom,u.prenom,u.profil FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id WHERE i.offre_id=? AND i.statut='Inscrit' ORDER BY u.nom,u.prenom",(oid,))
            if ss:
                s=st.selectbox("Séance",ss,format_func=lambda r:f"{r['date_seance']} — {r['theme'] or 'Séance'}")
                if s["qr_ouvert"] and st.button("Fermer le QR"): exe("UPDATE seances SET qr_ouvert=0 WHERE id=?",(s["id"],)); st.rerun()
                if us:
                    with st.form("manual"):
                        p=st.selectbox("Participant",us,format_func=lambda r:f"{r['nom']} {r['prenom']} ({r['profil']})"); stat=st.selectbox("Statut",["Présent","Absent","Excusé"]); ok=st.form_submit_button("Enregistrer")
                    if ok:
                        try: exe("INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation) VALUES(?,?,?,?)",(s["id"],p["id"],stat,"Manuel"))
                        except sqlite3.IntegrityError: exe("UPDATE presences SET statut=?,mode_validation='Manuel' WHERE seance_id=? AND utilisateur_id=?",(stat,s["id"],p["id"]))
                        st.success("Présence enregistrée.")
    elif sec=="Évaluations":
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if us:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}"); mode=st.radio("Saisie",["Évaluation","Performance"],horizontal=True)
            if mode=="Évaluation":
                with st.form("eval"):
                    a,b=st.columns(2); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Évaluation / test"); c,d,e=st.columns(3); note=c.number_input("Note",0.,100.,10.); bar=d.number_input("Barème",1.,100.,20.); coef=e.number_input("Coefficient",.1,20.,1.); com=st.text_area("Commentaire"); ok=st.form_submit_button("Enregistrer",type="primary")
                if ok: exe("INSERT INTO evaluations(utilisateur_id,activite,intitule,note,bareme,coefficient,commentaire,date_eval) VALUES(?,?,?,?,?,?,?,?)",(p["id"],act,title,note,bar,coef,com,str(date.today()))); st.success("Évaluation enregistrée.")
            else:
                with st.form("perf"):
                    a,b,c=st.columns(3); act=a.selectbox("Activité",ACTIVITES); title=b.text_input("Test / performance"); unit=c.text_input("Unité","s"); val=st.number_input("Valeur",value=0.); com=st.text_area("Commentaire"); ok=st.form_submit_button("Enregistrer",type="primary")
                if ok: exe("INSERT INTO performances(utilisateur_id,activite,intitule,valeur,unite,commentaire,date_perf) VALUES(?,?,?,?,?,?,?)",(p["id"],act,title,val,unit,com,str(date.today()))); st.success("Performance enregistrée.")
    else:
        us=rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
        if us:
            p=st.selectbox("Étudiant",us,format_func=lambda r:f"{r['nom']} {r['prenom']}"); act=st.selectbox("Activité",ACTIVITES); cs=rows("SELECT * FROM competences WHERE activite=? ORDER BY code",(act,))
            if cs:
                with st.form("comp"):
                    co=st.selectbox("Compétence",cs,format_func=lambda r:f"{r['code']} — {r['libelle']}"); niv=st.selectbox("Niveau",["Non évalué","En cours","Acquis","Maîtrisé"]); com=st.text_area("Commentaire"); ok=st.form_submit_button("Valider",type="primary")
                if ok:
                    old=one("SELECT id FROM acquisitions WHERE utilisateur_id=? AND competence_id=?",(p["id"],co["id"]))
                    if old: exe("UPDATE acquisitions SET niveau=?,commentaire=?,date_validation=? WHERE utilisateur_id=? AND competence_id=?",(niv,com,str(date.today()),p["id"],co["id"]))
                    else: exe("INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,commentaire,date_validation) VALUES(?,?,?,?,?)",(p["id"],co["id"],niv,com,str(date.today())))
                    st.success("Compétence mise à jour.")
    if st.button("← Accueil"): go("Accueil")

P={"Accueil":accueil,"Connexion":connexion,"Mon espace":espace,"Inscriptions":inscriptions,"Planning":planning,"Présence":presence,"Résultats":resultats,"Administration":admin}
P.get(st.session_state.page,accueil)()
