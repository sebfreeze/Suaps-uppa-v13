
import streamlit as st
import sqlite3
from datetime import datetime, date
from pathlib import Path

DB = "suaps_v14.db"
ACTIVITES = ["Natation", "Sauvetage", "Surf", "Rugby", "Course à pied", "Pelote Basque"]
MODALITES = ["UET", "UECF", "Non noté", "Personnel"]

st.set_page_config(
    page_title="SUAPS UPPA - V14",
    page_icon="🏃",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------- STYLE MOBILE / APK ----------
st.markdown("""
<style>
:root{
  --primary:#0B5FFF;
  --secondary:#00A88F;
  --bg:#F5F8FD;
  --card:#FFFFFF;
  --text:#14213D;
}
html, body, [class*="css"]{
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp{
  background:linear-gradient(180deg,#F7FAFF 0%,#F4F7FB 100%);
}
.block-container{
  max-width:1180px;
  padding-top:1rem;
  padding-bottom:5rem;
}
.hero{
  border-radius:28px;
  padding:26px;
  color:white;
  background:linear-gradient(135deg,#0B5FFF 0%,#5B63FF 58%,#00A88F 100%);
  box-shadow:0 18px 42px rgba(24,64,140,.18);
  margin-bottom:18px;
}
.hero h1{margin:0;font-size:2.1rem;}
.hero p{font-size:1.05rem;opacity:.96;margin:.5rem 0 0;}
.card{
  background:white;
  border-radius:22px;
  padding:18px;
  box-shadow:0 8px 24px rgba(20,33,61,.08);
  border:1px solid rgba(20,33,61,.05);
  margin-bottom:14px;
}
.sport{
  background:white;
  border-radius:20px;
  padding:16px;
  min-height:118px;
  box-shadow:0 7px 20px rgba(20,33,61,.07);
  border:1px solid #E8EEF8;
}
.badge{
  display:inline-block;
  padding:6px 10px;
  border-radius:999px;
  background:#EAF2FF;
  color:#0B5FFF;
  font-weight:700;
  font-size:.8rem;
}
.small{color:#62708A;font-size:.92rem;}
div.stButton > button{
  width:100%;
  border-radius:15px;
  min-height:48px;
  font-weight:700;
}
div[data-testid="stMetric"]{
  background:white;
  border:1px solid #E7EDF7;
  border-radius:18px;
  padding:12px;
}
@media (max-width: 720px){
  .block-container{padding:.65rem .75rem 5rem;}
  .hero{padding:20px;border-radius:22px;}
  .hero h1{font-size:1.65rem;}
  .hero p{font-size:.95rem;}
}
</style>
""", unsafe_allow_html=True)

# ---------- BASE DE DONNEES ----------
def conn():
    c = sqlite3.connect(DB, check_same_thread=False)
    c.row_factory = sqlite3.Row
    return c

def init_db():
    c = conn()
    cur = c.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS utilisateurs(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        profil TEXT NOT NULL,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        identifiant TEXT,
        composante TEXT,
        actif INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS offres(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        jour_horaire TEXT,
        lieu TEXT,
        capacite INTEGER DEFAULT 20,
        public TEXT DEFAULT 'Tous',
        ouverte INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        offre_id INTEGER NOT NULL,
        modalite TEXT NOT NULL,
        statut TEXT DEFAULT 'Inscrit',
        date_inscription TEXT NOT NULL,
        UNIQUE(utilisateur_id, offre_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS seances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offre_id INTEGER NOT NULL,
        date_seance TEXT NOT NULL,
        theme TEXT,
        qr_token TEXT,
        qr_ouvert INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS presences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seance_id INTEGER NOT NULL,
        utilisateur_id INTEGER NOT NULL,
        statut TEXT DEFAULT 'Présent',
        mode_validation TEXT DEFAULT 'Manuel',
        commentaire TEXT,
        UNIQUE(seance_id, utilisateur_id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS evaluations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        note REAL,
        bareme REAL DEFAULT 20,
        coefficient REAL DEFAULT 1,
        commentaire TEXT,
        date_eval TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS performances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        valeur REAL,
        unite TEXT,
        commentaire TEXT,
        date_perf TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS competences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activite TEXT NOT NULL,
        code TEXT NOT NULL,
        libelle TEXT NOT NULL,
        UNIQUE(activite, code)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS acquisitions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        utilisateur_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        niveau TEXT DEFAULT 'Non évalué',
        commentaire TEXT,
        date_validation TEXT,
        UNIQUE(utilisateur_id, competence_id)
    )
    """)

    # Offres de démonstration
    n = cur.execute("SELECT COUNT(*) AS n FROM offres").fetchone()["n"]
    if n == 0:
        exemples = [
            ("Natation","Natation tous niveaux","Lundi 18h00","Piscine universitaire",24,"Tous"),
            ("Sauvetage","Préparation BNSSA / Sauvetage","Mardi 19h00","Piscine universitaire",20,"Étudiants"),
            ("Surf","Surf découverte & progression","Mercredi 14h00","Côte basque / Landes",18,"Tous"),
            ("Rugby","Rugby universitaire","Jeudi 18h30","Terrain universitaire",30,"Tous"),
            ("Course à pied","Running campus","Mardi 12h30","Campus de Pau",40,"Tous"),
            ("Pelote Basque","Pelote Basque","Jeudi 17h30","Fronton universitaire",20,"Tous"),
        ]
        cur.executemany("""
            INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public)
            VALUES(?,?,?,?,?,?)
        """, exemples)

    # Compétences
    defaults = {
        "Natation":["Respiration et aisance","Propulsion","Endurance","Virages"],
        "Sauvetage":["Sécurité","Approche victime","Remorquage","Conduite de secours"],
        "Surf":["Lecture du milieu","Rame","Take-off","Sécurité et priorités"],
        "Rugby":["Passe","Placement","Défense","Organisation collective"],
        "Course à pied":["Gestion d'allure","Endurance","Technique","Échauffement-récupération"],
        "Pelote Basque":["Frappe","Placement","Choix tactiques","Règles et sécurité"],
    }
    for act, items in defaults.items():
        for i, lib in enumerate(items, 1):
            cur.execute(
                "INSERT OR IGNORE INTO competences(activite,code,libelle) VALUES(?,?,?)",
                (act, f"{act[:3].upper()}{i}", lib)
            )

    c.commit()
    c.close()

def rows(sql, params=()):
    c = conn()
    data = c.execute(sql, params).fetchall()
    c.close()
    return data

def execute(sql, params=()):
    c = conn()
    cur = c.cursor()
    cur.execute(sql, params)
    c.commit()
    rid = cur.lastrowid
    c.close()
    return rid

init_db()

# ---------- SESSION ----------
defaults = {
    "page":"Accueil",
    "profil":None,
    "user_id":None,
    "user_name":None,
}
for k,v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def go(page):
    st.session_state.page = page
    st.rerun()

def hero(title, subtitle):
    st.markdown(f"""
    <div class="hero">
      <div class="badge">SUAPS • UPPA • V14</div>
      <h1>{title}</h1>
      <p>{subtitle}</p>
    </div>
    """, unsafe_allow_html=True)

def get_user():
    if not st.session_state.user_id:
        return None
    r = rows("SELECT * FROM utilisateurs WHERE id=?", (st.session_state.user_id,))
    return r[0] if r else None

# ---------- ACCUEIL ----------
def page_accueil():
    hero("Bouge. Progresse. Partage.", "Ton sport universitaire dans une application simple, mobile et motivante.")

    if Path("logo_uppa.png").exists():
        st.image("logo_uppa.png", width=210)

    st.subheader("Choisis ton espace")
    c1,c2,c3 = st.columns(3)
    with c1:
        st.markdown("""<div class="card"><h3>🎓 Étudiant</h3><p class="small">Inscriptions, planning, présence, résultats et compétences.</p></div>""", unsafe_allow_html=True)
        if st.button("Entrer comme étudiant", key="p_etudiant"):
            st.session_state.profil = "Étudiant"
            go("Connexion")
    with c2:
        st.markdown("""<div class="card"><h3>👥 Personnel UPPA</h3><p class="small">Activités sportives, créneaux, événements et suivi des inscriptions.</p></div>""", unsafe_allow_html=True)
        if st.button("Entrer comme personnel", key="p_personnel"):
            st.session_state.profil = "Personnel"
            go("Connexion")
    with c3:
        st.markdown("""<div class="card"><h3>🧑‍🏫 Enseignant / Admin</h3><p class="small">Présences, groupes, évaluations, performances et pilotage.</p></div>""", unsafe_allow_html=True)
        if st.button("Entrer comme enseignant", key="p_admin"):
            st.session_state.profil = "Enseignant/Admin"
            go("Administration")

    st.subheader("Activités")
    icons = {
        "Natation":"🏊","Sauvetage":"🛟","Surf":"🏄","Rugby":"🏉",
        "Course à pied":"🏃","Pelote Basque":"🟢"
    }
    cols = st.columns(3)
    for i, a in enumerate(ACTIVITES):
        with cols[i % 3]:
            st.markdown(f"""<div class="sport"><h3>{icons[a]} {a}</h3><p class="small">Découvre les créneaux et inscris-toi depuis ton téléphone.</p></div>""", unsafe_allow_html=True)

# ---------- CONNEXION / CREATION ----------
def page_connexion():
    hero(f"Espace {st.session_state.profil}", "Identifie-toi ou crée ton profil pour accéder à tes activités.")
    profil = st.session_state.profil

    tab1, tab2 = st.tabs(["Connexion", "Créer mon profil"])
    with tab1:
        email = st.text_input("Adresse e-mail", key="login_email")
        if st.button("Me connecter", type="primary"):
            r = rows("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=?", (email.strip(), profil))
            if r:
                st.session_state.user_id = r[0]["id"]
                st.session_state.user_name = f'{r[0]["prenom"]} {r[0]["nom"]}'
                go("Mon espace")
            else:
                st.error("Profil introuvable. Utilise l'onglet « Créer mon profil ».")

    with tab2:
        c1,c2 = st.columns(2)
        nom = c1.text_input("Nom")
        prenom = c2.text_input("Prénom")
        email2 = st.text_input("E-mail UPPA")
        if profil == "Étudiant":
            ident = st.text_input("Numéro étudiant")
            comp = st.text_input("Formation / composante")
        else:
            ident = st.text_input("Identifiant personnel (facultatif)")
            comp = st.text_input("Service / composante")
        if st.button("Créer mon profil", type="primary"):
            if not nom or not prenom or not email2:
                st.warning("Nom, prénom et e-mail sont obligatoires.")
            else:
                try:
                    uid = execute("""
                        INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,composante)
                        VALUES(?,?,?,?,?,?)
                    """,(profil,nom.strip(),prenom.strip(),email2.strip(),ident.strip(),comp.strip()))
                    st.session_state.user_id = uid
                    st.session_state.user_name = f"{prenom.strip()} {nom.strip()}"
                    go("Mon espace")
                except sqlite3.IntegrityError:
                    st.error("Cette adresse e-mail est déjà enregistrée.")

    if st.button("← Retour à l'accueil"):
        go("Accueil")

# ---------- ESPACE UTILISATEUR ----------
def page_mon_espace():
    u = get_user()
    if not u:
        go("Accueil")
    hero(f"Bonjour {u['prenom']} 👋", f"Espace {u['profil']} • retrouve tes inscriptions et tes prochaines activités.")

    c1,c2,c3,c4 = st.columns(4)
    ins = rows("SELECT COUNT(*) n FROM inscriptions WHERE utilisateur_id=? AND statut='Inscrit'", (u["id"],))[0]["n"]
    pres = rows("SELECT COUNT(*) n FROM presences WHERE utilisateur_id=? AND statut='Présent'", (u["id"],))[0]["n"]
    ev = rows("SELECT COUNT(*) n FROM evaluations WHERE utilisateur_id=?", (u["id"],))[0]["n"]
    acq = rows("SELECT COUNT(*) n FROM acquisitions WHERE utilisateur_id=? AND niveau IN ('Acquis','Maîtrisé')", (u["id"],))[0]["n"]
    c1.metric("Inscriptions", ins)
    c2.metric("Présences", pres)
    c3.metric("Évaluations", ev)
    c4.metric("Compétences", acq)

    b1,b2,b3,b4 = st.columns(4)
    if b1.button("➕ M'inscrire"): go("Inscriptions")
    if b2.button("📅 Mon planning"): go("Planning")
    if b3.button("✅ Présence QR"): go("Présence")
    if b4.button("📈 Mes résultats"): go("Résultats")

    st.markdown("### Mes activités")
    mine = rows("""
        SELECT o.*, i.modalite, i.statut
        FROM inscriptions i JOIN offres o ON o.id=i.offre_id
        WHERE i.utilisateur_id=? ORDER BY o.activite
    """,(u["id"],))
    if not mine:
        st.info("Tu n'as pas encore d'inscription.")
    else:
        for r in mine:
            st.markdown(f"""
            <div class="card">
              <b>{r['activite']} — {r['intitule']}</b><br>
              <span class="small">📅 {r['jour_horaire'] or 'À définir'} • 📍 {r['lieu'] or 'À définir'} • {r['modalite']}</span>
            </div>
            """, unsafe_allow_html=True)

    if st.button("Se déconnecter"):
        st.session_state.user_id = None
        st.session_state.user_name = None
        go("Accueil")

# ---------- INSCRIPTIONS ----------
def page_inscriptions():
    u = get_user()
    hero("Inscriptions sportives", "Choisis une activité et réserve ton créneau.")
    offres = rows("SELECT * FROM offres WHERE ouverte=1 ORDER BY activite,intitule")
    for o in offres:
        nb = rows("SELECT COUNT(*) n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'", (o["id"],))[0]["n"]
        dispo = max(0, o["capacite"]-nb)
        st.markdown(f"""
        <div class="card">
          <h3>{o['activite']} — {o['intitule']}</h3>
          <div class="small">📅 {o['jour_horaire']} &nbsp; • &nbsp; 📍 {o['lieu']} &nbsp; • &nbsp; Places : {dispo}/{o['capacite']} &nbsp; • &nbsp; Public : {o['public']}</div>
        </div>
        """, unsafe_allow_html=True)
        if u["profil"] == "Personnel":
            modalite = "Personnel"
        else:
            modalite = st.selectbox(
                "Modalité",
                ["UET","UECF","Non noté"],
                key=f"mod_{o['id']}"
            )
        if st.button(f"S'inscrire à {o['activite']}", key=f"ins_{o['id']}"):
            if dispo <= 0:
                st.error("Créneau complet.")
            elif o["public"] == "Étudiants" and u["profil"] != "Étudiant":
                st.warning("Ce créneau est réservé aux étudiants.")
            else:
                try:
                    execute("""
                        INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,date_inscription)
                        VALUES(?,?,?,?)
                    """,(u["id"],o["id"],modalite,datetime.now().isoformat(timespec="seconds")))
                    st.success("Inscription enregistrée.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.info("Tu es déjà inscrit à ce créneau.")
    if st.button("← Mon espace"): go("Mon espace")

# ---------- PLANNING ----------
def page_planning():
    u = get_user()
    hero("Mon planning", "Tes créneaux sportifs en un coup d'œil.")
    data = rows("""
        SELECT o.activite,o.intitule,o.jour_horaire,o.lieu,i.modalite
        FROM inscriptions i JOIN offres o ON o.id=i.offre_id
        WHERE i.utilisateur_id=? AND i.statut='Inscrit'
        ORDER BY o.jour_horaire
    """,(u["id"],))
    if data:
        for r in data:
            st.markdown(f"""<div class="card"><b>{r['activite']} — {r['intitule']}</b><br><span class="small">📅 {r['jour_horaire']} • 📍 {r['lieu']} • {r['modalite']}</span></div>""", unsafe_allow_html=True)
    else:
        st.info("Aucun créneau pour le moment.")
    if st.button("← Mon espace"): go("Mon espace")

# ---------- PRESENCE QR / MANUEL ----------
def page_presence():
    u = get_user()
    hero("Validation de présence", "Saisis le code affiché par l'enseignant pour valider ta présence.")
    token = st.text_input("Code de présence / QR")
    if st.button("Valider ma présence", type="primary"):
        r = rows("""
            SELECT s.id, o.activite, s.date_seance
            FROM seances s JOIN offres o ON o.id=s.offre_id
            WHERE s.qr_token=? AND s.qr_ouvert=1
        """,(token.strip(),))
        if not r:
            st.error("Code invalide ou validation fermée.")
        else:
            sid = r[0]["id"]
            try:
                execute("""
                    INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation)
                    VALUES(?,?,?,?)
                """,(sid,u["id"],"Présent","QR"))
            except sqlite3.IntegrityError:
                execute("""
                    UPDATE presences SET statut='Présent',mode_validation='QR'
                    WHERE seance_id=? AND utilisateur_id=?
                """,(sid,u["id"]))
            st.success(f"Présence validée : {r[0]['activite']}.")
    if st.button("← Mon espace"): go("Mon espace")

# ---------- RESULTATS ----------
def page_resultats():
    u = get_user()
    hero("Mes résultats", "Suis tes évaluations, performances et compétences.")
    t1,t2,t3 = st.tabs(["Notes","Performances","Compétences"])
    with t1:
        data = rows("SELECT * FROM evaluations WHERE utilisateur_id=? ORDER BY date_eval DESC",(u["id"],))
        if not data: st.info("Aucune évaluation enregistrée.")
        for r in data:
            st.markdown(f"""<div class="card"><b>{r['activite']} — {r['intitule']}</b><br><span class="small">Note : {r['note'] if r['note'] is not None else '-'} / {r['bareme']} • Coef. {r['coefficient']} • {r['date_eval']}</span></div>""", unsafe_allow_html=True)
    with t2:
        data = rows("SELECT * FROM performances WHERE utilisateur_id=? ORDER BY date_perf DESC",(u["id"],))
        if not data: st.info("Aucune performance enregistrée.")
        for r in data:
            st.markdown(f"""<div class="card"><b>{r['activite']} — {r['intitule']}</b><br><span class="small">{r['valeur']} {r['unite'] or ''} • {r['date_perf']}</span></div>""", unsafe_allow_html=True)
    with t3:
        data = rows("""
            SELECT c.activite,c.code,c.libelle,COALESCE(a.niveau,'Non évalué') niveau
            FROM competences c
            LEFT JOIN acquisitions a ON a.competence_id=c.id AND a.utilisateur_id=?
            ORDER BY c.activite,c.code
        """,(u["id"],))
        for r in data:
            st.markdown(f"""<div class="card"><b>{r['activite']} • {r['code']}</b><br>{r['libelle']}<br><span class="badge">{r['niveau']}</span></div>""", unsafe_allow_html=True)
    if st.button("← Mon espace"): go("Mon espace")

# ---------- ADMINISTRATION ----------
def page_admin():
    hero("Espace Enseignant / Administration", "Pilotage SUAPS : inscriptions, présences, évaluations, performances et compétences.")

    t1,t2,t3,t4,t5 = st.tabs(["Tableau de bord","Créneaux","Présences","Évaluations","Compétences"])

    with t1:
        a,b,c,d = st.columns(4)
        a.metric("Utilisateurs", rows("SELECT COUNT(*) n FROM utilisateurs")[0]["n"])
        b.metric("Inscriptions", rows("SELECT COUNT(*) n FROM inscriptions WHERE statut='Inscrit'")[0]["n"])
        c.metric("Séances", rows("SELECT COUNT(*) n FROM seances")[0]["n"])
        d.metric("Présences", rows("SELECT COUNT(*) n FROM presences WHERE statut='Présent'")[0]["n"])

        st.markdown("#### Dernières inscriptions")
        data = rows("""
            SELECT u.prenom,u.nom,u.profil,o.activite,o.intitule,i.modalite,i.date_inscription
            FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id
            JOIN offres o ON o.id=i.offre_id
            ORDER BY i.id DESC LIMIT 30
        """)
        if data:
            st.dataframe([dict(r) for r in data], use_container_width=True)

    with t2:
        st.markdown("#### Ajouter un créneau")
        c1,c2 = st.columns(2)
        act = c1.selectbox("Activité", ACTIVITES)
        intitule = c2.text_input("Intitulé", value=f"{act} - créneau")
        c3,c4 = st.columns(2)
        horaire = c3.text_input("Jour / horaire")
        lieu = c4.text_input("Lieu")
        c5,c6 = st.columns(2)
        capacite = c5.number_input("Capacité", 1, 200, 20)
        public = c6.selectbox("Public", ["Tous","Étudiants","Personnel"])
        if st.button("Créer le créneau"):
            execute("""
                INSERT INTO offres(activite,intitule,jour_horaire,lieu,capacite,public)
                VALUES(?,?,?,?,?,?)
            """,(act,intitule,horaire,lieu,capacite,public))
            st.success("Créneau créé.")
            st.rerun()

        st.markdown("#### Créneaux existants")
        st.dataframe([dict(r) for r in rows("SELECT * FROM offres ORDER BY activite")], use_container_width=True)

    with t3:
        offres = rows("SELECT * FROM offres ORDER BY activite,intitule")
        if offres:
            opts = {f"{o['activite']} — {o['intitule']}":o["id"] for o in offres}
            lib = st.selectbox("Créneau", list(opts.keys()), key="admin_offre_presence")
            offre_id = opts[lib]
            d = st.date_input("Date de séance", value=date.today())
            theme = st.text_input("Thème de séance")
            token = st.text_input("Code QR / présence", value=f"SUAPS-{datetime.now().strftime('%H%M%S')}")
            if st.button("Ouvrir une séance de présence"):
                sid = execute("""
                    INSERT INTO seances(offre_id,date_seance,theme,qr_token,qr_ouvert)
                    VALUES(?,?,?,?,1)
                """,(offre_id,str(d),theme,token))
                st.success(f"Séance ouverte. Code à afficher : {token}")

            st.markdown("#### Validation manuelle")
            users = rows("""
                SELECT u.id,u.prenom,u.nom,u.profil
                FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id
                WHERE i.offre_id=? AND i.statut='Inscrit'
                ORDER BY u.nom,u.prenom
            """,(offre_id,))
            sessions = rows("SELECT * FROM seances WHERE offre_id=? ORDER BY id DESC",(offre_id,))
            if sessions and users:
                sess = st.selectbox("Séance", sessions, format_func=lambda r:f"{r['date_seance']} — {r['theme'] or 'Séance'}", key="sess_manual")
                person = st.selectbox("Participant", users, format_func=lambda r:f"{r['nom']} {r['prenom']} ({r['profil']})", key="pers_manual")
                statut = st.selectbox("Statut", ["Présent","Absent","Excusé"])
                if st.button("Enregistrer la présence manuelle"):
                    try:
                        execute("""
                            INSERT INTO presences(seance_id,utilisateur_id,statut,mode_validation)
                            VALUES(?,?,?,?)
                        """,(sess["id"],person["id"],statut,"Manuel"))
                    except sqlite3.IntegrityError:
                        execute("""
                            UPDATE presences SET statut=?,mode_validation='Manuel'
                            WHERE seance_id=? AND utilisateur_id=?
                        """,(statut,sess["id"],person["id"]))
                    st.success("Présence enregistrée.")

    with t4:
        users = rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' ORDER BY nom,prenom")
        if users:
            person = st.selectbox("Étudiant", users, format_func=lambda r:f"{r['nom']} {r['prenom']}", key="eval_user")
            c1,c2 = st.columns(2)
            act = c1.selectbox("Activité", ACTIVITES, key="eval_act")
            titre = c2.text_input("Évaluation / test")
            c3,c4,c5 = st.columns(3)
            note = c3.number_input("Note", 0.0, 100.0, 10.0)
            bareme = c4.number_input("Barème", 1.0, 100.0, 20.0)
            coef = c5.number_input("Coefficient", 0.1, 20.0, 1.0)
            commentaire = st.text_area("Commentaire", key="eval_comment")
            if st.button("Enregistrer l'évaluation"):
                execute("""
                    INSERT INTO evaluations(utilisateur_id,activite,intitule,note,bareme,coefficient,commentaire,date_eval)
                    VALUES(?,?,?,?,?,?,?,?)
                """,(person["id"],act,titre,note,bareme,coef,commentaire,str(date.today())))
                st.success("Évaluation enregistrée.")

            st.markdown("#### Performance")
            p1,p2,p3 = st.columns(3)
            pact = p1.selectbox("Activité performance", ACTIVITES, key="perf_act")
            pint = p2.text_input("Test / performance")
            unite = p3.text_input("Unité", value="s")
            valeur = st.number_input("Valeur", value=0.0)
            if st.button("Enregistrer la performance"):
                execute("""
                    INSERT INTO performances(utilisateur_id,activite,intitule,valeur,unite,date_perf)
                    VALUES(?,?,?,?,?,?)
                """,(person["id"],pact,pint,valeur,unite,str(date.today())))
                st.success("Performance enregistrée.")

    with t5:
        users = rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' ORDER BY nom,prenom")
        if users:
            person = st.selectbox("Étudiant", users, format_func=lambda r:f"{r['nom']} {r['prenom']}", key="comp_user")
            act = st.selectbox("Activité", ACTIVITES, key="comp_act")
            comps = rows("SELECT * FROM competences WHERE activite=? ORDER BY code",(act,))
            if comps:
                comp = st.selectbox("Compétence", comps, format_func=lambda r:f"{r['code']} — {r['libelle']}")
                niveau = st.selectbox("Niveau", ["Non évalué","En cours","Acquis","Maîtrisé"])
                commentaire = st.text_area("Commentaire compétence")
                if st.button("Valider la compétence"):
                    old = rows("SELECT id FROM acquisitions WHERE utilisateur_id=? AND competence_id=?",(person["id"],comp["id"]))
                    if old:
                        execute("""
                            UPDATE acquisitions SET niveau=?,commentaire=?,date_validation=?
                            WHERE utilisateur_id=? AND competence_id=?
                        """,(niveau,commentaire,str(date.today()),person["id"],comp["id"]))
                    else:
                        execute("""
                            INSERT INTO acquisitions(utilisateur_id,competence_id,niveau,commentaire,date_validation)
                            VALUES(?,?,?,?,?)
                        """,(person["id"],comp["id"],niveau,commentaire,str(date.today())))
                    st.success("Compétence mise à jour.")

    if st.button("← Retour accueil"):
        go("Accueil")

# ---------- ROUTEUR ----------
page = st.session_state.page

if page == "Accueil":
    page_accueil()
elif page == "Connexion":
    page_connexion()
elif page == "Mon espace":
    page_mon_espace()
elif page == "Inscriptions":
    page_inscriptions()
elif page == "Planning":
    page_planning()
elif page == "Présence":
    page_presence()
elif page == "Résultats":
    page_resultats()
elif page == "Administration":
    page_admin()
else:
    st.session_state.page = "Accueil"
    st.rerun()
