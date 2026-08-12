
import streamlit as st
import sqlite3
import secrets
import socket
import os
import re
from pathlib import Path
import pandas as pd
import qrcode
try:
    import psycopg
except Exception:
    psycopg = None
from datetime import date, datetime, timedelta
from io import BytesIO

DB = "suaps_presence.db"

ACTIVITES = ["Natation", "Sauvetage", "Surf", "Rugby", "Course à pied", "Pelote Basque"]

def secret_value(name, default=""):
    env = os.getenv(name, "")
    if env:
        return env
    try:
        if name in st.secrets:
            return str(st.secrets[name])
    except Exception:
        pass
    return default

DATABASE_URL = secret_value("DATABASE_URL", "").strip()
USE_POSTGRES = bool(DATABASE_URL)

def sql_compat(sql):
    if not USE_POSTGRES:
        return sql
    q = sql.replace("?", "%s")
    q = q.replace("INTEGER PRIMARY KEY AUTOINCREMENT", "SERIAL PRIMARY KEY")
    if re.match(r"^\s*INSERT\s+OR\s+IGNORE\s+INTO", q, flags=re.I):
        q = re.sub(r"INSERT\s+OR\s+IGNORE\s+INTO", "INSERT INTO", q, count=1, flags=re.I)
        q = q.rstrip().rstrip(";") + " ON CONFLICT DO NOTHING"
    return q

class CompatCursor:
    def __init__(self, cursor):
        self._cursor = cursor

    def execute(self, sql, params=()):
        self._cursor.execute(sql_compat(sql), params)
        return self

    def fetchone(self):
        return self._cursor.fetchone()

    def fetchall(self):
        return self._cursor.fetchall()

    @property
    def lastrowid(self):
        return getattr(self._cursor, "lastrowid", None)

class CompatConnection:
    def __init__(self, raw, is_pg=False):
        self.raw = raw
        self.is_pg = is_pg

    def cursor(self):
        return CompatCursor(self.raw.cursor())

    def execute(self, sql, params=()):
        if self.is_pg:
            cur = self.raw.cursor()
            cur.execute(sql_compat(sql), params)
            return CompatCursor(cur)
        return self.raw.execute(sql, params)

    def commit(self):
        self.raw.commit()

    def close(self):
        self.raw.close()

def get_conn():
    if USE_POSTGRES:
        if psycopg is None:
            raise RuntimeError("Le paquet psycopg n'est pas installé.")
        raw = psycopg.connect(DATABASE_URL, autocommit=False)
        return CompatConnection(raw, is_pg=True)
    raw = sqlite3.connect(DB, check_same_thread=False)
    raw.execute("PRAGMA foreign_keys = ON")
    return CompatConnection(raw, is_pg=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS etudiants(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nom TEXT NOT NULL,
        prenom TEXT NOT NULL,
        email TEXT,
        numero_etudiant TEXT UNIQUE,
        groupe TEXT,
        actif INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS seances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activite TEXT NOT NULL,
        date_seance TEXT NOT NULL,
        groupe TEXT,
        theme TEXT,
        checkin_token TEXT,
        checkin_expires TEXT,
        checkin_open INTEGER DEFAULT 0
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS presences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        seance_id INTEGER NOT NULL,
        etudiant_id INTEGER NOT NULL,
        statut TEXT NOT NULL DEFAULT 'Présent',
        commentaire TEXT,
        UNIQUE(seance_id, etudiant_id),
        FOREIGN KEY(seance_id) REFERENCES seances(id) ON DELETE CASCADE,
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS evaluations(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        date_eval TEXT NOT NULL,
        note REAL,
        bareme REAL DEFAULT 20,
        coefficient REAL DEFAULT 1,
        commentaire TEXT,
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS performances(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        date_perf TEXT NOT NULL,
        valeur REAL,
        unite TEXT,
        bareme_min REAL,
        bareme_max REAL,
        note_calculee REAL,
        commentaire TEXT,
        bareme_id INTEGER,
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE
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
    CREATE TABLE IF NOT EXISTS offres_inscription(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activite TEXT NOT NULL,
        intitule TEXT NOT NULL,
        groupe TEXT,
        jour_horaire TEXT,
        lieu TEXT,
        capacite INTEGER DEFAULT 0,
        ouverte INTEGER DEFAULT 1,
        date_debut TEXT,
        date_fin TEXT,
        token TEXT UNIQUE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS inscriptions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        offre_id INTEGER NOT NULL,
        etudiant_id INTEGER NOT NULL,
        modalite TEXT NOT NULL,
        date_inscription TEXT NOT NULL,
        statut TEXT NOT NULL DEFAULT 'Inscrit',
        commentaire TEXT,
        UNIQUE(offre_id, etudiant_id),
        FOREIGN KEY(offre_id) REFERENCES offres_inscription(id) ON DELETE CASCADE,
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS baremes(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        activite TEXT NOT NULL,
        niveau_groupe TEXT,
        nom TEXT NOT NULL,
        unite TEXT NOT NULL,
        sens TEXT NOT NULL DEFAULT 'Plus élevé = meilleur',
        valeur_0 REAL,
        valeur_20 REAL,
        actif INTEGER DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS bareme_competences(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bareme_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        seuil_note REAL DEFAULT 10,
        niveau_attribue TEXT NOT NULL DEFAULT 'Acquis',
        UNIQUE(bareme_id, competence_id),
        FOREIGN KEY(bareme_id) REFERENCES baremes(id) ON DELETE CASCADE,
        FOREIGN KEY(competence_id) REFERENCES competences(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS acquisitions(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        niveau TEXT NOT NULL DEFAULT 'Non évalué',
        date_validation TEXT,
        commentaire TEXT,
        UNIQUE(etudiant_id, competence_id),
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE,
        FOREIGN KEY(competence_id) REFERENCES competences(id) ON DELETE CASCADE
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS validations_semestre(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        etudiant_id INTEGER NOT NULL,
        activite TEXT NOT NULL,
        statut TEXT NOT NULL DEFAULT 'À valider',
        date_validation TEXT,
        commentaire TEXT,
        UNIQUE(etudiant_id, activite),
        FOREIGN KEY(etudiant_id) REFERENCES etudiants(id) ON DELETE CASCADE
    )
    """)

    conn.commit()

    defaults = {
        "Natation": [
            ("NAT1", "Adopter une respiration adaptée et efficace"),
            ("NAT2", "Maîtriser l’alignement et la propulsion"),
            ("NAT3", "Nager de façon continue sur la distance demandée"),
            ("NAT4", "Maîtriser les virages et reprises de nage"),
        ],
        "Sauvetage": [
            ("SAU1", "Identifier une situation à risque"),
            ("SAU2", "Réaliser une entrée dans l’eau adaptée"),
            ("SAU3", "Approcher et remorquer une victime"),
            ("SAU4", "Mettre en œuvre une conduite de secours adaptée"),
        ],
        "Surf": [
            ("SUR1", "Lire les conditions et identifier les dangers"),
            ("SUR2", "Maîtriser la rame et le passage de barre"),
            ("SUR3", "Réaliser un take-off maîtrisé"),
            ("SUR4", "Respecter les règles de priorité et de sécurité"),
        ],
        "Rugby": [
            ("RUG1", "Maîtriser les passes et la continuité du jeu"),
            ("RUG2", "Se démarquer et occuper efficacement l’espace"),
            ("RUG3", "Respecter les règles de sécurité et de contact"),
            ("RUG4", "Participer à l’organisation collective offensive et défensive"),
        ],
        "Course à pied": [
            ("CAP1", "Adopter une allure adaptée à l’objectif"),
            ("CAP2", "Gérer son effort sur la durée"),
            ("CAP3", "Améliorer son efficacité de course"),
            ("CAP4", "S’échauffer, récupérer et courir en sécurité"),
        ],"Pelote Basque": [
    ("PEL1", "Maîtriser les gestes techniques fondamentaux : frappe, contrôle et précision"),
    ("PEL2", "Se placer et se déplacer efficacement en fonction de la trajectoire de la balle"),
    ("PEL3", "Construire le point en utilisant les espaces et en adaptant ses choix tactiques"),
    ("PEL4", "Respecter les règles, son partenaire/adversaire et les consignes de sécurité"),
],
    }
    for act, comps in defaults.items():
        for code, libelle in comps:
            cur.execute(
                "INSERT OR IGNORE INTO competences(activite, code, libelle) VALUES(?,?,?)",
                (act, code, libelle)
            )
    conn.commit()
    conn.close()

def qdf(sql, params=()):
    conn = get_conn()
    try:
        if USE_POSTGRES:
            with conn.raw.cursor() as cur:
                cur.execute(sql_compat(sql), params)
                cols = [d.name for d in cur.description] if cur.description else []
                rows = cur.fetchall()
            return pd.DataFrame(rows, columns=cols)
        return pd.read_sql_query(sql, conn.raw, params=params)
    finally:
        conn.close()

def exec_sql(sql, params=()):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(sql, params)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def upsert_presence(seance_id, etudiant_id, statut, commentaire):
    conn = get_conn()
    conn.execute("""
        INSERT INTO presences(seance_id, etudiant_id, statut, commentaire)
        VALUES(?,?,?,?)
        ON CONFLICT(seance_id, etudiant_id)
        DO UPDATE SET statut=excluded.statut, commentaire=excluded.commentaire
    """, (seance_id, etudiant_id, statut, commentaire))
    conn.commit()
    conn.close()

def upsert_acquisition(etudiant_id, competence_id, niveau, date_validation, commentaire):
    conn = get_conn()
    conn.execute("""
        INSERT INTO acquisitions(etudiant_id, competence_id, niveau, date_validation, commentaire)
        VALUES(?,?,?,?,?)
        ON CONFLICT(etudiant_id, competence_id)
        DO UPDATE SET niveau=excluded.niveau,
                      date_validation=excluded.date_validation,
                      commentaire=excluded.commentaire
    """, (etudiant_id, competence_id, niveau, date_validation, commentaire))
    conn.commit()
    conn.close()

def upsert_validation_semestre(etudiant_id, activite, statut, date_validation, commentaire):
    conn = get_conn()
    conn.execute("""
        INSERT INTO validations_semestre(etudiant_id, activite, statut, date_validation, commentaire)
        VALUES(?,?,?,?,?)
        ON CONFLICT(etudiant_id, activite)
        DO UPDATE SET statut=excluded.statut,
                      date_validation=excluded.date_validation,
                      commentaire=excluded.commentaire
    """, (etudiant_id, activite, statut, date_validation, commentaire))
    conn.commit()
    conn.close()


def public_base_url():
    configured = secret_value("APP_BASE_URL", "").strip().rstrip("/")
    if configured:
        return configured
    render_host = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
    if render_host:
        return f"https://{render_host}"
    return f"http://{local_ip()}:8501"

def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "localhost"

def open_checkin(seance_id, minutes=10):
    token = secrets.token_urlsafe(24)
    expiry = datetime.now() + timedelta(minutes=minutes)
    exec_sql(
        "UPDATE seances SET checkin_token=?, checkin_expires=?, checkin_open=1 WHERE id=?",
        (token, expiry.isoformat(timespec="seconds"), seance_id)
    )
    return token, expiry

def close_checkin(seance_id):
    exec_sql("UPDATE seances SET checkin_open=0 WHERE id=?", (seance_id,))


def calc_note_from_bareme(valeur, valeur_0, valeur_20, sens):
    if valeur_0 is None or valeur_20 is None or valeur_0 == valeur_20:
        return None
    if sens == "Plus élevé = meilleur":
        note = (valeur - valeur_0) / (valeur_20 - valeur_0) * 20
    else:
        note = (valeur_0 - valeur) / (valeur_0 - valeur_20) * 20
    return max(0, min(20, note))

def apply_bareme_competences(etudiant_id, bareme_id, note):
    if note is None:
        return 0
    links = qdf("""
        SELECT bc.competence_id, bc.seuil_note, bc.niveau_attribue
        FROM bareme_competences bc
        WHERE bc.bareme_id=?
    """, (bareme_id,))
    count = 0
    for _, r in links.iterrows():
        if note >= r["seuil_note"]:
            niv = r["niveau_attribue"]
            dval = str(date.today()) if niv in ["Acquis", "Maîtrisé"] else None
            upsert_acquisition(int(etudiant_id), int(r["competence_id"]), niv, dval, "Validation automatique via barème")
            count += 1
    return count

def make_qr_png(data):
    img = qrcode.make(data)
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def show_uppa_logo(width=420):
    logo_path = Path(__file__).parent  / "logo_uppa.png"
    if logo_path.exists():
        st.image(str(logo_path), width=width)

st.set_page_config(page_title="SUAPS - Présences & Compétences", page_icon="🏊", layout="wide")

st.markdown("""
<style>
:root{
  --uppa-blue:#0c3c78;
  --uppa-cyan:#18a9c9;
  --uppa-sand:#f5f1e8;
  --uppa-dark:#14202b;
}
.block-container{
  padding-top:1rem;
  padding-bottom:2rem;
}
.student-hero{
  border-radius:22px;
  padding:22px;
  background:linear-gradient(135deg, var(--uppa-blue), var(--uppa-cyan));
  color:white;
  margin-bottom:18px;
}
.student-hero h1{
  margin:0 0 6px 0;
  font-size:1.85rem;
}
.student-hero p{
  margin:0;
  opacity:.95;
}
.student-card{
  border-radius:18px;
  padding:16px;
  background:white;
  box-shadow:0 4px 18px rgba(0,0,0,.08);
  margin:8px 0 14px 0;
  border:1px solid rgba(12,60,120,.08);
}
.student-card h3{
  margin-top:0;
}
.student-pill{
  display:inline-block;
  padding:5px 10px;
  border-radius:999px;
  background:#eef7fb;
  color:#0c3c78;
  font-size:.85rem;
  margin-right:6px;
  margin-bottom:5px;
}
.student-kpi{
  border-radius:16px;
  padding:14px;
  background:#f7fbfd;
  border:1px solid #dbeef4;
  text-align:center;
}
.student-kpi .big{
  font-size:1.5rem;
  font-weight:700;
  color:#0c3c78;
}
.student-section-title{
  margin-top:20px;
  margin-bottom:6px;
  color:#14202b;
  font-weight:700;
}
@media (max-width: 768px){
  .block-container{
    padding-left:.8rem;
    padding-right:.8rem;
  }
  .student-hero{
    padding:18px;
  }
  .student-hero h1{
    font-size:1.55rem;
  }
  div[data-testid="stHorizontalBlock"]{
    gap:.5rem;
  }
  .stButton button{
    min-height:48px;
    border-radius:14px;
    font-weight:600;
  }
}
</style>
""", unsafe_allow_html=True)
init_db()

show_uppa_logo(width=330)
st.title("SUAPS — Présences, évaluations et compétences")
st.caption("Université de Pau et des Pays de l’Adour • Natation • Sauvetage • Surf • Rugby • Course à pied")
if secret_value("APP_BASE_URL") or os.getenv("RENDER_EXTERNAL_HOSTNAME"):
    backend_label = "PostgreSQL persistant" if USE_POSTGRES else "SQLite local"
    st.success(f"🌐 Version V13 en ligne — {backend_label}", icon="✅")




# Page publique d'inscription étudiant, accessible via ?inscription=TOKEN
registration_token = st.query_params.get("inscription")
if registration_token:
    offre = qdf(
        "SELECT * FROM offres_inscription WHERE token=? AND ouverte=1",
        (registration_token,)
    )
    if offre.empty:
        st.error("Cette inscription n’est pas disponible ou est fermée.")
        st.stop()

    o = offre.iloc[0]
    today = date.today()

    if o["date_debut"]:
        try:
            if today < date.fromisoformat(o["date_debut"]):
                st.warning("Les inscriptions ne sont pas encore ouvertes.")
                st.stop()
        except Exception:
            pass

    if o["date_fin"]:
        try:
            if today > date.fromisoformat(o["date_fin"]):
                st.warning("La période d’inscription est terminée.")
                st.stop()
        except Exception:
            pass

    show_uppa_logo(width=360)
    st.markdown("""
    <div class="student-hero">
      <h1>Inscription SUAPS</h1>
      <p>Choisis ton activité, ta modalité et rejoins ton créneau sportif.</p>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"### {o['activite']} — {o['intitule']}")
    if o["jour_horaire"]:
        st.write(f"**Créneau :** {o['jour_horaire']}")
    if o["lieu"]:
        st.write(f"**Lieu :** {o['lieu']}")
    if o["groupe"]:
        st.write(f"**Groupe / niveau :** {o['groupe']}")

    current_count = qdf(
        "SELECT COUNT(*) AS n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'",
        (int(o["id"]),)
    ).iloc[0]["n"]

    if int(o["capacite"] or 0) > 0:
        st.caption(f"Places : {current_count}/{int(o['capacite'])}")
        if current_count >= int(o["capacite"]):
            st.error("Ce créneau est complet.")
            st.stop()

    numero = st.text_input("Numéro étudiant")
    modalite = st.radio(
        "Modalité d’inscription",
        ["UET", "UECF", "Non noté"],
        horizontal=True
    )
    st.caption("Choisissez la modalité correspondant à votre inscription pédagogique.")

    if st.button("Valider mon inscription", type="primary", use_container_width=True):
        student = qdf(
            "SELECT * FROM etudiants WHERE numero_etudiant=? AND actif=1",
            (numero.strip(),)
        )
        if student.empty:
            st.error("Numéro étudiant non reconnu.")
        else:
            e = student.iloc[0]
            conn = get_conn()
            conn.execute("""
                INSERT INTO inscriptions(offre_id, etudiant_id, modalite, date_inscription, statut, commentaire)
                VALUES(?,?,?,?,?,?)
                ON CONFLICT(offre_id, etudiant_id)
                DO UPDATE SET modalite=excluded.modalite,
                              date_inscription=excluded.date_inscription,
                              statut='Inscrit'
            """, (int(o["id"]), int(e["id"]), modalite, datetime.now().isoformat(timespec="seconds"), "Inscrit", "Inscription en ligne"))
            conn.commit()
            conn.close()
            st.success(f"Inscription enregistrée pour {e['prenom']} {e['nom']} — {modalite}.")
    st.stop()

# Page publique d'émargement étudiant, accessible via ?checkin=TOKEN
params = st.query_params
checkin_token = params.get("checkin")
if checkin_token:
    session = qdf(
        "SELECT * FROM seances WHERE checkin_token=? AND checkin_open=1",
        (checkin_token,)
    )
    if session.empty:
        st.error("Ce lien d’émargement n’est pas valide ou la séance est fermée.")
        st.stop()

    ss = session.iloc[0]
    try:
        expiry = datetime.fromisoformat(ss["checkin_expires"]) if ss["checkin_expires"] else None
    except Exception:
        expiry = None
    if expiry and datetime.now() > expiry:
        st.error("La période d’émargement est terminée.")
        st.stop()

    show_uppa_logo(width=360)
    st.markdown("""
    <div class="student-hero">
      <h1>Présence SUAPS</h1>
      <p>Scanne, valide, c’est fait ✅</p>
    </div>
    """, unsafe_allow_html=True)
    st.write(f"**{ss['activite']}** — {ss['date_seance']}")
    if ss["theme"]:
        st.caption(ss["theme"])
    if ss["groupe"]:
        st.caption(f"Groupe : {ss['groupe']}")

    numero = st.text_input("Votre numéro étudiant")
    if st.button("Je valide ma présence", type="primary", use_container_width=True):
        student = qdf(
            "SELECT * FROM etudiants WHERE numero_etudiant=? AND actif=1",
            (numero.strip(),)
        )
        if student.empty:
            st.error("Numéro étudiant non reconnu.")
        else:
            e = student.iloc[0]
            if ss["groupe"] and e["groupe"] != ss["groupe"]:
                st.error("Vous n’appartenez pas au groupe de cette séance.")
            else:
                upsert_presence(int(ss["id"]), int(e["id"]), "Présent", "Auto-validation QR/NFC")
                st.success(f"Présence validée pour {e['prenom']} {e['nom']}.")
                st.balloons()
    st.stop()


# Accès V13 de test
TEST_ACCESS_CODE = secret_value("TEST_ACCESS_CODE", "").strip()
TEACHER_ACCESS_CODE = secret_value("TEACHER_ACCESS_CODE", "").strip()

if "test_access_ok" not in st.session_state:
    st.session_state.test_access_ok = not bool(TEST_ACCESS_CODE)
if "role" not in st.session_state:
    st.session_state.role = "Étudiant"

if not st.session_state.test_access_ok:
    show_uppa_logo(width=340)
    st.markdown("""
    <div class="student-hero">
      <h1>SUAPS UPPA • Test V13</h1>
      <p>Accès réservé au groupe de test.</p>
    </div>
    """, unsafe_allow_html=True)
    access_code = st.text_input("Code d’accès test", type="password")
    if st.button("Entrer", type="primary", use_container_width=True):
        if secrets.compare_digest(access_code, TEST_ACCESS_CODE):
            st.session_state.test_access_ok = True
            st.rerun()
        else:
            st.error("Code incorrect.")
    st.stop()

role_choice = st.sidebar.radio("Mode", ["Étudiant", "Enseignant"], index=0 if st.session_state.role == "Étudiant" else 1)
if role_choice == "Enseignant" and st.session_state.role != "Enseignant":
    if TEACHER_ACCESS_CODE:
        teacher_code = st.sidebar.text_input("Code enseignant", type="password", key="teacher_gate")
        if st.sidebar.button("Déverrouiller le mode enseignant"):
            if secrets.compare_digest(teacher_code, TEACHER_ACCESS_CODE):
                st.session_state.role = "Enseignant"
                st.rerun()
            else:
                st.sidebar.error("Code enseignant incorrect.")
        st.session_state.role = "Étudiant"
    else:
        st.session_state.role = "Enseignant"
elif role_choice == "Étudiant":
    st.session_state.role = "Étudiant"

if st.sidebar.button("Se déconnecter"):
    st.session_state.test_access_ok = not bool(TEST_ACCESS_CODE)
    st.session_state.role = "Étudiant"
    st.rerun()

if st.session_state.role == "Étudiant":
    menu = st.sidebar.radio("Navigation", ["Accueil", "Portail étudiant"])
else:
    menu = st.sidebar.radio(
        "Navigation",
        ["Accueil", "Tableau de bord", "Portail étudiant", "Étudiants", "Inscriptions en ligne",
         "Présences", "Émargement QR / NFC", "Cahier de notes", "Performances", "Barèmes",
         "Compétences", "Fiche étudiant", "Exports"]
    )

if menu == "Accueil":
    show_uppa_logo(width=360)
    st.markdown("""
    <div class="student-hero">
      <h1>SUAPS UPPA</h1>
      <p>Bouge ton campus, révèle ton potentiel !</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### Le sport, une force pour réussir")
    st.write(
        "Une seule application pour découvrir les activités, s’inscrire, valider sa présence, "
        "suivre ses performances, ses notes et l’acquisition de ses compétences."
    )

    promo_path = Path(__file__).parent / "assets" / "accueil_suaps_v12.png"
    if promo_path.exists():
        st.image(str(promo_path), use_container_width=True)

    st.markdown("### 6 activités, 6 ambiances")
    cols = st.columns(6)
    cards = [
        ("🏊", "Natation", "Technique • Endurance • Performance"),
        ("🛟", "Sauvetage", "Prévenir • Intervenir • Se dépasser"),
        ("🏄", "Surf", "Glisse • Équilibre • Sensations"),
        ("🏉", "Rugby", "Équipe • Engagement • Respect"),
        ("🏃", "Course à pied", "Endurance • Liberté • Progression"),("🥎", "Pelote Basque", "Adresse • Vitesse • Tradition"),
    ]
    for col, (ico, title, desc) in zip(cols, cards):
        col.markdown(
            f'<div class="student-card" style="min-height:150px;text-align:center;">'
            f'<div style="font-size:2.2rem;">{ico}</div>'
            f'<h3>{title}</h3><p>{desc}</p></div>',
            unsafe_allow_html=True
        )

    st.markdown("### Accès rapide")
st.markdown("### 📱 V14 Mobile — Accueil étudiant")
st.success("Bienvenue sur l'application mobile SUAPS UPPA 🎓")
    c1, c2 = st.columns(2)
    with c1:
        st.info("🎓 **Étudiants**\n\nOuvrez « Portail étudiant » pour retrouver vos inscriptions, présences, résultats et compétences.")
    with c2:
        st.info("🧑‍🏫 **Enseignants**\n\nUtilisez le tableau de bord pour gérer les groupes, appels, évaluations, performances et validations.")

elif menu == "Tableau de bord":
    etuds = qdf("SELECT * FROM etudiants WHERE actif=1")
    seances = qdf("SELECT * FROM seances")
    evals = qdf("SELECT * FROM evaluations")
    pres = qdf("SELECT * FROM presences")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Étudiants actifs", len(etuds))
    c2.metric("Séances enregistrées", len(seances))
    c3.metric("Évaluations", len(evals))
    if len(pres):
        taux = (pres["statut"].eq("Présent").sum() / len(pres)) * 100
        c4.metric("Taux de présence", f"{taux:.1f}%")
    else:
        c4.metric("Taux de présence", "—")

    st.subheader("Dernières séances")
    if len(seances):
        st.dataframe(seances.sort_values("date_seance", ascending=False).head(10), use_container_width=True)
    else:
        st.info("Aucune séance enregistrée pour le moment.")

elif menu == "Portail étudiant":
    show_uppa_logo(width=390)
    st.markdown("""
    <div class="student-hero">
      <h1>SUAPS • Université de Pau et des Pays de l’Adour</h1>
      <p>Bouge, progresse, valide tes compétences et suis ton parcours sportif.</p>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Version smartphone étudiant — accès rapide à l’inscription, la présence, les résultats et la progression.")

    numero_portail = st.text_input("🎓 Mon numéro étudiant", placeholder="Saisir votre numéro étudiant", key="student_portal_num")

    if numero_portail:
        student = qdf(
            "SELECT * FROM etudiants WHERE numero_etudiant=? AND actif=1",
            (numero_portail.strip(),)
        )
        if student.empty:
            st.warning("Numéro étudiant non reconnu.")
        else:
            e = student.iloc[0]
            st.markdown(f"""
            <div class="student-card">
              <h3>Bonjour {e['prenom']} 👋</h3>
              <span class="student-pill">Groupe : {e['groupe'] or '—'}</span>
              <span class="student-pill">N° étudiant : {e['numero_etudiant']}</span>
            </div>
            """, unsafe_allow_html=True)

            # KPIs
            pres = qdf("""
                SELECT s.activite, p.statut
                FROM presences p
                JOIN seances s ON s.id=p.seance_id
                WHERE p.etudiant_id=?
            """, (int(e["id"]),))

            evals = qdf("""
                SELECT activite, note, bareme, coefficient
                FROM evaluations
                WHERE etudiant_id=?
            """, (int(e["id"]),))

            acq = qdf("""
                SELECT c.activite, c.code, c.libelle,
                       COALESCE(a.niveau,'Non évalué') AS niveau
                FROM competences c
                LEFT JOIN acquisitions a
                  ON a.competence_id=c.id AND a.etudiant_id=?
                ORDER BY c.activite, c.code
            """, (int(e["id"]),))

            regs = qdf("""
                SELECT o.activite, o.intitule, o.jour_horaire, o.lieu,
                       i.modalite, i.statut
                FROM inscriptions i
                JOIN offres_inscription o ON o.id=i.offre_id
                WHERE i.etudiant_id=?
                ORDER BY i.date_inscription DESC
            """, (int(e["id"]),))

            if len(pres):
                taux = 100 * pres["statut"].eq("Présent").sum() / len(pres)
            else:
                taux = None

            if len(evals):
                tmp = evals.copy()
                tmp["n20"] = (tmp["note"] / tmp["bareme"]) * 20
                moyenne = (tmp["n20"] * tmp["coefficient"]).sum() / tmp["coefficient"].sum()
            else:
                moyenne = None

            if len(acq):
                acquired = acq["niveau"].isin(["Acquis", "Maîtrisé"]).sum()
                total_comp = len(acq)
            else:
                acquired = total_comp = 0

            c1, c2, c3 = st.columns(3)
            c1.markdown(
                f'<div class="student-kpi"><div class="big">{f"{taux:.0f}%" if taux is not None else "—"}</div><div>Présence</div></div>',
                unsafe_allow_html=True
            )
            c2.markdown(
                f'<div class="student-kpi"><div class="big">{f"{moyenne:.1f}/20" if moyenne is not None else "—"}</div><div>Moyenne</div></div>',
                unsafe_allow_html=True
            )
            c3.markdown(
                f'<div class="student-kpi"><div class="big">{acquired}/{total_comp}</div><div>Compétences</div></div>',
                unsafe_allow_html=True
            )

            st.markdown('<div class="student-section-title">📌 Mes inscriptions</div>', unsafe_allow_html=True)
            if len(regs):
                for _, r in regs.iterrows():
                    st.markdown(f"""
                    <div class="student-card">
                      <h3>{r['activite']} — {r['intitule']}</h3>
                      <span class="student-pill">{r['modalite']}</span>
                      <span class="student-pill">{r['statut']}</span>
                      <p>{r['jour_horaire'] or ''}<br>{r['lieu'] or ''}</p>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune inscription enregistrée.")

            st.markdown('<div class="student-section-title">🏅 Ma progression</div>', unsafe_allow_html=True)
            activity = st.selectbox("Choisir une activité", ACTIVITES, key="student_portal_activity")
            ca = acq[acq.activite == activity] if len(acq) else acq
            if len(ca):
                for _, r in ca.iterrows():
                    icon = "✅" if r["niveau"] in ["Acquis", "Maîtrisé"] else ("🟠" if r["niveau"] == "En cours d’acquisition" else "⚪")
                    st.markdown(f"""
                    <div class="student-card">
                      <strong>{icon} {r['code']} — {r['libelle']}</strong><br>
                      <span class="student-pill">{r['niveau']}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Aucune compétence renseignée pour cette activité.")

            st.markdown('<div class="student-section-title">📈 Mes performances</div>', unsafe_allow_html=True)
            perfs = qdf("""
                SELECT activite, intitule, date_perf, valeur, unite, note_calculee
                FROM performances
                WHERE etudiant_id=?
                ORDER BY date_perf DESC
                LIMIT 10
            """, (int(e["id"]),))
            if len(perfs):
                st.dataframe(perfs, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune performance enregistrée.")

            st.markdown('<div class="student-section-title">📅 Mes présences récentes</div>', unsafe_allow_html=True)
            recent = qdf("""
                SELECT s.date_seance, s.activite, s.theme, p.statut
                FROM presences p
                JOIN seances s ON s.id=p.seance_id
                WHERE p.etudiant_id=?
                ORDER BY s.date_seance DESC
                LIMIT 8
            """, (int(e["id"]),))
            if len(recent):
                st.dataframe(recent, use_container_width=True, hide_index=True)
            else:
                st.info("Aucune présence enregistrée.")

elif menu == "Étudiants":
    st.subheader("Gestion des étudiants")

    with st.expander("Importer une liste Excel / CSV", expanded=False):
        st.caption("Colonnes reconnues : nom, prenom, email, numero_etudiant, groupe.")
        uploaded = st.file_uploader("Fichier étudiants", type=["xlsx", "csv"], key="student_import")
        if uploaded is not None:
            try:
                imported = pd.read_csv(uploaded) if uploaded.name.lower().endswith(".csv") else pd.read_excel(uploaded)
                aliases = {}
                for c in imported.columns:
                    k = str(c).strip().lower().replace("é","e").replace("è","e").replace("ê","e").replace("à","a")
                    k = k.replace(" ","_").replace("-","_").replace("°","")
                    amap = {
                        "nom":"nom", "prenom":"prenom", "mail":"email", "e_mail":"email", "email":"email",
                        "numero_etudiant":"numero_etudiant", "numero":"numero_etudiant",
                        "n_etudiant":"numero_etudiant", "num_etudiant":"numero_etudiant",
                        "ine":"numero_etudiant", "groupe":"groupe", "group":"groupe"
                    }
                    if k in amap:
                        aliases[c] = amap[k]
                imported = imported.rename(columns=aliases)
                st.dataframe(imported.head(20), use_container_width=True, hide_index=True)

                if "nom" not in imported.columns or "prenom" not in imported.columns:
                    st.error("Le fichier doit contenir au minimum les colonnes Nom et Prénom.")
                elif st.button("Importer ces étudiants", type="primary"):
                    added, updated, errors = 0, 0, 0
                    conn = get_conn()
                    cur = conn.cursor()
                    for _, row in imported.iterrows():
                        def clean(v):
                            return "" if pd.isna(v) else str(v).strip()
                        nom_i, prenom_i = clean(row.get("nom","")), clean(row.get("prenom",""))
                        if not nom_i or not prenom_i:
                            errors += 1
                            continue
                        email_i = clean(row.get("email",""))
                        numero_i = clean(row.get("numero_etudiant",""))
                        groupe_i = clean(row.get("groupe",""))
                        existing = None
                        if numero_i:
                            existing = cur.execute("SELECT id FROM etudiants WHERE numero_etudiant=?", (numero_i,)).fetchone()
                        if not existing:
                            existing = cur.execute(
                                "SELECT id FROM etudiants WHERE lower(nom)=lower(?) AND lower(prenom)=lower(?)",
                                (nom_i, prenom_i)
                            ).fetchone()
                        if existing:
                            cur.execute(
                                "UPDATE etudiants SET nom=?, prenom=?, email=?, groupe=?, actif=1 WHERE id=?",
                                (nom_i, prenom_i, email_i, groupe_i, existing[0])
                            )
                            updated += 1
                        else:
                            cur.execute(
                                "INSERT INTO etudiants(nom,prenom,email,numero_etudiant,groupe) VALUES(?,?,?,?,?)",
                                (nom_i, prenom_i, email_i, numero_i or None, groupe_i)
                            )
                            added += 1
                    conn.commit()
                    conn.close()
                    st.success(f"Import terminé : {added} ajouté(s), {updated} mis à jour, {errors} ignoré(s).")
                    st.rerun()
            except Exception as e:
                st.error(f"Erreur de lecture : {e}")

        template = pd.DataFrame([
            {"nom":"DUPONT","prenom":"Emma","email":"emma.dupont@exemple.fr","numero_etudiant":"20260001","groupe":"NAT-A"},
            {"nom":"MARTIN","prenom":"Lucas","email":"lucas.martin@exemple.fr","numero_etudiant":"20260002","groupe":"RUG-B"}
        ])
        bio = BytesIO()
        with pd.ExcelWriter(bio, engine="openpyxl") as writer:
            template.to_excel(writer, index=False, sheet_name="Etudiants")
        st.download_button(
            "Télécharger un modèle Excel",
            data=bio.getvalue(),
            file_name="modele_import_etudiants_SUAPS.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    with st.expander("Ajouter un étudiant", expanded=True):
        with st.form("add_student"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom")
            prenom = c2.text_input("Prénom")
            c3, c4 = st.columns(2)
            numero = c3.text_input("N° étudiant")
            email = c4.text_input("Email")
            groupe = st.text_input("Groupe")
            ok = st.form_submit_button("Ajouter")
            if ok:
                try:
                    exec_sql(
                        "INSERT INTO etudiants(nom,prenom,email,numero_etudiant,groupe) VALUES(?,?,?,?,?)",
                        (nom.strip(), prenom.strip(), email.strip(), numero.strip() or None, groupe.strip())
                    )
                    st.success("Étudiant ajouté.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Impossible d’ajouter l’étudiant : {e}")

    df = qdf("SELECT id, nom, prenom, numero_etudiant, email, groupe, actif FROM etudiants ORDER BY nom, prenom")
    st.dataframe(df, use_container_width=True, hide_index=True)

elif menu == "Inscriptions en ligne":
    st.subheader("Inscriptions en ligne")
    st.caption("Création de créneaux et inscription étudiante selon trois modalités : UET, UECF ou Non noté.")

    tab1, tab2, tab3 = st.tabs(["Créer une offre", "Lien étudiant", "Suivi des inscrits"])

    with tab1:
        with st.form("create_offer"):
            c1, c2 = st.columns(2)
            activite = c1.selectbox("Activité", ACTIVITES, key="reg_activity")
            intitule = c2.text_input("Intitulé", placeholder="Ex. Natation perfectionnement")
            c3, c4 = st.columns(2)
            groupe = c3.text_input("Groupe / niveau", placeholder="Ex. NAT-A, débutant...")
            capacite = c4.number_input("Capacité (0 = illimitée)", min_value=0, value=24, step=1)
            jour_horaire = st.text_input("Jour / horaire", placeholder="Ex. Mardi 18h00–19h30")
            lieu = st.text_input("Lieu", placeholder="Ex. Piscine universitaire")
            c5, c6 = st.columns(2)
            ddeb = c5.date_input("Ouverture des inscriptions", value=date.today())
            dfin = c6.date_input("Fermeture des inscriptions", value=date.today() + timedelta(days=30))
            save = st.form_submit_button("Créer l’offre d’inscription", use_container_width=True)
            if save:
                token = secrets.token_urlsafe(20)
                exec_sql("""
                    INSERT INTO offres_inscription(
                        activite,intitule,groupe,jour_horaire,lieu,capacite,ouverte,date_debut,date_fin,token
                    ) VALUES(?,?,?,?,?,?,?,?,?,?)
                """, (activite, intitule.strip(), groupe.strip(), jour_horaire.strip(), lieu.strip(),
                      int(capacite), 1, str(ddeb), str(dfin), token))
                st.success("Offre créée.")
                st.rerun()

        offres = qdf("""
            SELECT id, activite, intitule, groupe, jour_horaire, lieu, capacite, ouverte, date_debut, date_fin
            FROM offres_inscription
            ORDER BY id DESC
        """)
        st.dataframe(offres, use_container_width=True, hide_index=True)

    with tab2:
        offres = qdf("SELECT * FROM offres_inscription ORDER BY id DESC")
        if offres.empty:
            st.info("Crée d’abord une offre.")
        else:
            labels = {
                r["id"]: f'{r["activite"]} — {r["intitule"]} — {r["jour_horaire"] or ""}'
                for _, r in offres.iterrows()
            }
            oid = st.selectbox("Offre", offres["id"].tolist(), format_func=lambda x: labels[x], key="reg_link_offer")
            o = offres[offres.id == oid].iloc[0]
            base_default = public_base_url()
            base = st.text_input(
                "Adresse de l’application",
                value=base_default,
                key="reg_base_url",
                help="Une fois l’application hébergée, remplace cette adresse par son URL publique."
            ).rstrip("/")
            url = f"{base}/?inscription={o['token']}"
            st.code(url)

            qr = make_qr_png(url)
            st.image(qr, caption="QR code d’inscription", width=320)
            st.download_button(
                "Télécharger le QR code d’inscription",
                data=qr,
                file_name=f"QR_inscription_{o['activite']}_{o['id']}.png",
                mime="image/png"
            )

            c1, c2 = st.columns(2)
            if c1.button("Ouvrir l’offre", use_container_width=True):
                exec_sql("UPDATE offres_inscription SET ouverte=1 WHERE id=?", (oid,))
                st.rerun()
            if c2.button("Fermer l’offre", use_container_width=True):
                exec_sql("UPDATE offres_inscription SET ouverte=0 WHERE id=?", (oid,))
                st.rerun()

    with tab3:
        offres = qdf("SELECT * FROM offres_inscription ORDER BY id DESC")
        if offres.empty:
            st.info("Aucune offre.")
        else:
            labels = {
                r["id"]: f'{r["activite"]} — {r["intitule"]}'
                for _, r in offres.iterrows()
            }
            oid = st.selectbox("Offre à suivre", offres["id"].tolist(), format_func=lambda x: labels[x], key="reg_follow_offer")
            inscrits = qdf("""
                SELECT e.nom, e.prenom, e.numero_etudiant, e.email, e.groupe,
                       i.modalite, i.date_inscription, i.statut
                FROM inscriptions i
                JOIN etudiants e ON e.id=i.etudiant_id
                WHERE i.offre_id=?
                ORDER BY i.date_inscription, e.nom, e.prenom
            """, (oid,))
            if inscrits.empty:
                st.info("Aucun inscrit pour le moment.")
            else:
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total", len(inscrits))
                c2.metric("UET", int((inscrits["modalite"]=="UET").sum()))
                c3.metric("UECF", int((inscrits["modalite"]=="UECF").sum()))
                c4.metric("Non noté", int((inscrits["modalite"]=="Non noté").sum()))
                st.dataframe(inscrits, use_container_width=True, hide_index=True)

                st.download_button(
                    "Exporter les inscrits en CSV",
                    data=inscrits.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"inscriptions_SUAPS_offre_{oid}.csv",
                    mime="text/csv"
                )

elif menu == "Présences":
    st.subheader("Feuille de présence")

    tab1, tab2, tab3 = st.tabs(["Créer une séance", "Faire l'appel", "Appel express mobile"])

    with tab1:
        with st.form("create_session"):
            c1, c2 = st.columns(2)
            activite = c1.selectbox("Activité", ACTIVITES)
            d = c2.date_input("Date", value=date.today())
            groupe = st.text_input("Groupe")
            theme = st.text_input("Thème / contenu de séance")
            submit = st.form_submit_button("Créer la séance")
            if submit:
                exec_sql(
                    "INSERT INTO seances(activite,date_seance,groupe,theme) VALUES(?,?,?,?)",
                    (activite, str(d), groupe.strip(), theme.strip())
                )
                st.success("Séance créée.")
                st.rerun()

    with tab2:
        seances = qdf("SELECT * FROM seances ORDER BY date_seance DESC, id DESC")
        if seances.empty:
            st.info("Crée d’abord une séance.")
        else:
            labels = {
                row["id"]: f'{row["date_seance"]} — {row["activite"]} — {row["groupe"] or "Tous"} — {row["theme"] or ""}'
                for _, row in seances.iterrows()
            }
            sid = st.selectbox("Séance", list(labels.keys()), format_func=lambda x: labels[x])
            séance = seances[seances.id == sid].iloc[0]
            groupe = séance["groupe"]

            if groupe:
                etuds = qdf(
                    "SELECT * FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom",
                    (groupe,)
                )
            else:
                etuds = qdf("SELECT * FROM etudiants WHERE actif=1 ORDER BY nom, prenom")

            existing = qdf("SELECT * FROM presences WHERE seance_id=?", (sid,))
            existing_map = {r["etudiant_id"]: r for _, r in existing.iterrows()}

            if etuds.empty:
                st.warning("Aucun étudiant dans ce groupe.")
            else:
                with st.form("attendance_form"):
                    rows = []
                    for _, e in etuds.iterrows():
                        old = existing_map.get(e["id"])
                        default_status = old["statut"] if old is not None else "Présent"
                        default_comment = old["commentaire"] if old is not None and old["commentaire"] else ""
                        c1, c2, c3 = st.columns([2, 1.4, 3])
                        c1.write(f'**{e["nom"]} {e["prenom"]}**')
                        statut = c2.selectbox(
                            "Statut",
                            ["Présent", "Absent", "Justifié", "Dispensé"],
                            index=["Présent", "Absent", "Justifié", "Dispensé"].index(default_status),
                            key=f"stat_{e['id']}"
                        )
                        com = c3.text_input("Commentaire", value=default_comment, key=f"com_{e['id']}")
                        rows.append((e["id"], statut, com))
                    save = st.form_submit_button("Enregistrer l'appel")
                    if save:
                        for eid, statut, com in rows:
                            upsert_presence(sid, eid, statut, com)
                        st.success("Présences enregistrées.")
                        st.rerun()



    with tab3:
        st.caption("Mode enseignant optimisé smartphone : appel rapide, recherche et corrections instantanées.")

        seances_m = qdf("SELECT * FROM seances ORDER BY date_seance DESC, id DESC")
        if seances_m.empty:
            st.info("Crée d’abord une séance.")
        else:
            labels_m = {
                row["id"]: f'{row["date_seance"]} — {row["activite"]} — {row["groupe"] or "Tous"}'
                for _, row in seances_m.iterrows()
            }

            sid_m = st.selectbox(
                "Séance",
                list(labels_m.keys()),
                format_func=lambda x: labels_m[x],
                key="mobile_sid"
            )

            sm = seances_m[seances_m.id == sid_m].iloc[0]
            gm = sm["groupe"]

            if gm:
                em = qdf(
                    "SELECT * FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom",
                    (gm,)
                )
            else:
                em = qdf("SELECT * FROM etudiants WHERE actif=1 ORDER BY nom, prenom")

            ex = qdf("SELECT * FROM presences WHERE seance_id=?", (sid_m,))
            exmap = {r["etudiant_id"]: r["statut"] for _, r in ex.iterrows()}

            if em.empty:
                st.warning("Aucun étudiant pour cette séance.")
            else:
                st.markdown("### Appel rapide")

                c1, c2 = st.columns(2)
                if c1.button("✅ Tous présents", use_container_width=True, type="primary", key=f"allpresent_{sid_m}"):
                    for _, e in em.iterrows():
                        upsert_presence(sid_m, int(e["id"]), "Présent", "Appel manuel smartphone")
                    st.success("Tous les étudiants ont été marqués présents.")
                    st.rerun()

                if c2.button("↩️ Réinitialiser", use_container_width=True, key=f"reset_{sid_m}"):
                    conn = get_conn()
                    conn.execute("DELETE FROM presences WHERE seance_id=?", (sid_m,))
                    conn.commit()
                    conn.close()
                    st.success("Appel réinitialisé.")
                    st.rerun()

                search = st.text_input(
                    "🔎 Rechercher un étudiant",
                    placeholder="Nom ou prénom",
                    key=f"search_mobile_{sid_m}"
                ).strip().lower()

                filtre = st.radio(
                    "Afficher",
                    ["Tous", "Non renseignés", "Présents", "Absents"],
                    horizontal=True,
                    key=f"filter_mobile_{sid_m}"
                )

                shown = em.copy()
                if search:
                    mask = (
                        shown["nom"].str.lower().str.contains(search, na=False) |
                        shown["prenom"].str.lower().str.contains(search, na=False)
                    )
                    shown = shown[mask]

                def current_status(student_id):
                    return exmap.get(student_id, "Non renseigné")

                if filtre != "Tous":
                    wanted = {
                        "Non renseignés": "Non renseigné",
                        "Présents": "Présent",
                        "Absents": "Absent"
                    }[filtre]
                    shown = shown[shown["id"].apply(lambda x: current_status(x) == wanted)]

                total = len(em)
                present = sum(1 for _, e in em.iterrows() if exmap.get(e["id"]) == "Présent")
                absent = sum(1 for _, e in em.iterrows() if exmap.get(e["id"]) == "Absent")
                justified = sum(1 for _, e in em.iterrows() if exmap.get(e["id"]) == "Justifié")
                dispensed = sum(1 for _, e in em.iterrows() if exmap.get(e["id"]) == "Dispensé")
                missing = total - present - absent - justified - dispensed

                m1, m2, m3 = st.columns(3)
                m1.metric("Présents", present)
                m2.metric("Absents", absent)
                m3.metric("À renseigner", missing)

                st.divider()

                if shown.empty:
                    st.info("Aucun étudiant ne correspond au filtre.")
                else:
                    statuses = ["Présent", "Absent", "Justifié", "Dispensé"]

                    for _, e in shown.iterrows():
                        eid = int(e["id"])
                        cur = exmap.get(eid, "Non renseigné")

                        st.markdown(f"#### {e['nom']} {e['prenom']}")
                        if e["numero_etudiant"]:
                            st.caption(f"N° {e['numero_etudiant']}")

                        c1, c2 = st.columns(2)
                        if c1.button(
                            "✅ Présent",
                            key=f"p_{sid_m}_{eid}",
                            use_container_width=True,
                            type="primary" if cur == "Présent" else "secondary"
                        ):
                            upsert_presence(sid_m, eid, "Présent", "Appel manuel smartphone")
                            st.rerun()

                        if c2.button(
                            "❌ Absent",
                            key=f"a_{sid_m}_{eid}",
                            use_container_width=True,
                            type="primary" if cur == "Absent" else "secondary"
                        ):
                            upsert_presence(sid_m, eid, "Absent", "Appel manuel smartphone")
                            st.rerun()

                        c3, c4 = st.columns(2)
                        if c3.button(
                            "🟠 Justifié",
                            key=f"j_{sid_m}_{eid}",
                            use_container_width=True,
                            type="primary" if cur == "Justifié" else "secondary"
                        ):
                            upsert_presence(sid_m, eid, "Justifié", "Appel manuel smartphone")
                            st.rerun()

                        if c4.button(
                            "🔵 Dispensé",
                            key=f"d_{sid_m}_{eid}",
                            use_container_width=True,
                            type="primary" if cur == "Dispensé" else "secondary"
                        ):
                            upsert_presence(sid_m, eid, "Dispensé", "Appel manuel smartphone")
                            st.rerun()

                        if cur != "Non renseigné":
                            st.caption(f"Statut actuel : **{cur}**")
                        else:
                            st.caption("Statut actuel : **non renseigné**")
                        st.divider()

elif menu == "Émargement QR / NFC":
    st.subheader("Émargement étudiant par QR code / NFC")
    st.caption("Le QR code et une puce NFC peuvent pointer vers la même adresse d’émargement.")

    sessions = qdf("SELECT * FROM seances ORDER BY date_seance DESC, id DESC")
    if sessions.empty:
        st.info("Crée d’abord une séance.")
    else:
        labels = {
            r["id"]: f'{r["date_seance"]} — {r["activite"]} — {r["groupe"] or "Tous"} — {r["theme"] or ""}'
            for _, r in sessions.iterrows()
        }
        sid = st.selectbox("Séance", list(labels.keys()), format_func=lambda x: labels[x])
        row = sessions[sessions.id == sid].iloc[0]

        duration = st.slider("Durée d’ouverture de l’émargement", 2, 30, 10, 1, format="%d min")
        c1, c2 = st.columns(2)
        if c1.button("Ouvrir / renouveler l’émargement", type="primary", use_container_width=True):
            token, expiry = open_checkin(sid, duration)
            st.success(f"Émargement ouvert jusqu’à {expiry.strftime('%H:%M:%S')}.")
            st.rerun()
        if c2.button("Fermer l’émargement", use_container_width=True):
            close_checkin(sid)
            st.success("Émargement fermé.")
            st.rerun()

        fresh = qdf("SELECT * FROM seances WHERE id=?", (sid,)).iloc[0]
        if fresh["checkin_open"] and fresh["checkin_token"]:
            base_default = public_base_url()
            base = st.text_input(
                "Adresse de l’application",
                value=base_default,
                help="En local, le téléphone de l’étudiant doit être sur le même réseau Wi-Fi. Une fois l’application hébergée, remplace cette adresse par son URL publique."
            ).rstrip("/")
            url = f"{base}/?checkin={fresh['checkin_token']}"
            qr_bytes = make_qr_png(url)
            st.image(qr_bytes, caption="QR code à scanner par les étudiants", width=320)
            st.code(url)
            st.download_button(
                "Télécharger le QR code",
                data=qr_bytes,
                file_name=f"QR_SUAPS_{fresh['activite']}_{fresh['date_seance']}.png",
                mime="image/png"
            )
            st.info("Pour le NFC : programme une étiquette NFC avec l’adresse affichée ci-dessus. Le téléphone ouvrira la même page que le QR code.")

            live = qdf("""
                SELECT e.nom, e.prenom, e.numero_etudiant, p.statut
                FROM presences p
                JOIN etudiants e ON e.id=p.etudiant_id
                WHERE p.seance_id=?
                ORDER BY e.nom, e.prenom
            """, (sid,))
            st.markdown("#### Présences enregistrées")
            st.dataframe(live, use_container_width=True, hide_index=True)
        else:
            st.warning("L’émargement de cette séance est actuellement fermé.")

elif menu == "Cahier de notes":
    st.subheader("Cahier de notes")
    st.caption("Saisie individuelle ou rapide par groupe, avec calcul automatique des moyennes pondérées.")

    tab_ind, tab_grp = st.tabs(["Saisie individuelle", "Saisie rapide par groupe"])

    etuds = qdf("SELECT id, nom, prenom, groupe FROM etudiants WHERE actif=1 ORDER BY nom, prenom")

    with tab_ind:
        if etuds.empty:
            st.info("Ajoute d’abord des étudiants.")
        else:
            labels = {r["id"]: f'{r["nom"]} {r["prenom"]} ({r["groupe"] or "sans groupe"})' for _, r in etuds.iterrows()}
            with st.form("add_eval"):
                c1, c2 = st.columns(2)
                eid = c1.selectbox("Étudiant", list(labels.keys()), format_func=lambda x: labels[x])
                activite = c2.selectbox("Activité", ACTIVITES)
                intitule = st.text_input("Intitulé de l'évaluation")
                c3, c4, c5 = st.columns(3)
                note = c3.number_input("Note", min_value=0.0, step=0.25)
                bareme = c4.number_input("Barème", min_value=1.0, value=20.0, step=1.0)
                coeff = c5.number_input("Coefficient", min_value=0.1, value=1.0, step=0.1)
                d = st.date_input("Date", value=date.today())
                commentaire = st.text_area("Commentaire")
                save = st.form_submit_button("Enregistrer la note", use_container_width=True)
                if save:
                    exec_sql(
                        """INSERT INTO evaluations(etudiant_id,activite,intitule,date_eval,note,bareme,coefficient,commentaire)
                           VALUES(?,?,?,?,?,?,?,?)""",
                        (eid, activite, intitule.strip(), str(d), note, bareme, coeff, commentaire.strip())
                    )
                    st.success("Évaluation enregistrée.")
                    st.rerun()

    with tab_grp:
        groupes_df = qdf("SELECT DISTINCT groupe FROM etudiants WHERE actif=1 AND groupe IS NOT NULL AND groupe<>'' ORDER BY groupe")
        groupes = groupes_df["groupe"].tolist() if not groupes_df.empty else []
        if not groupes:
            st.info("Aucun groupe défini.")
        else:
            c1, c2 = st.columns(2)
            groupe = c1.selectbox("Groupe", groupes)
            activite_g = c2.selectbox("Activité", ACTIVITES, key="grade_group_activity")
            intitule_g = st.text_input("Évaluation commune", placeholder="Ex. 100 m nage libre, parcours sauvetage...")
            c3, c4, c5 = st.columns(3)
            bareme_g = c3.number_input("Barème commun", min_value=1.0, value=20.0, step=1.0, key="grade_group_bareme")
            coeff_g = c4.number_input("Coefficient commun", min_value=0.1, value=1.0, step=0.1, key="grade_group_coeff")
            date_g = c5.date_input("Date", value=date.today(), key="grade_group_date")

            ge = qdf("SELECT id, nom, prenom FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom", (groupe,))
            if not ge.empty:
                with st.form("group_grades"):
                    rows = []
                    for _, e in ge.iterrows():
                        st.markdown(f"**{e['nom']} {e['prenom']}**")
                        n = st.number_input("Note", min_value=0.0, max_value=float(bareme_g), step=0.25, key=f"gn_{e['id']}")
                        com = st.text_input("Commentaire", key=f"gc_{e['id']}")
                        rows.append((int(e["id"]), n, com))
                    saveg = st.form_submit_button("Enregistrer toutes les notes", use_container_width=True)
                    if saveg:
                        for eid, n, com in rows:
                            exec_sql(
                                """INSERT INTO evaluations(etudiant_id,activite,intitule,date_eval,note,bareme,coefficient,commentaire)
                                   VALUES(?,?,?,?,?,?,?,?)""",
                                (eid, activite_g, intitule_g.strip(), str(date_g), n, bareme_g, coeff_g, com.strip())
                            )
                        st.success("Notes du groupe enregistrées.")
                        st.rerun()

    df = qdf("""
        SELECT e.nom, e.prenom, e.groupe, v.activite, v.intitule, v.date_eval,
               v.note, v.bareme, v.coefficient, v.commentaire
        FROM evaluations v
        JOIN etudiants e ON e.id=v.etudiant_id
        ORDER BY v.date_eval DESC, e.nom, e.prenom
    """)
    st.markdown("### Historique des notes")
    st.dataframe(df, use_container_width=True, hide_index=True)

    if not df.empty:
        calc = df.copy()
        calc["note_sur_20"] = (calc["note"] / calc["bareme"]) * 20
        synth = (
            calc.assign(pond=lambda x: x["note_sur_20"] * x["coefficient"])
                .groupby(["nom", "prenom", "activite"], as_index=False)
                .agg(total_pond=("pond","sum"), total_coeff=("coefficient","sum"))
        )
        synth["moyenne_sur_20"] = synth["total_pond"] / synth["total_coeff"]
        st.markdown("### Moyennes par activité")
        st.dataframe(
            synth[["nom","prenom","activite","moyenne_sur_20"]].round({"moyenne_sur_20":2}),
            use_container_width=True,
            hide_index=True
        )

elif menu == "Performances":
    st.subheader("Résultats de performance")
    st.caption("Saisie de résultats bruts avec conversion automatique en note si un barème est sélectionné.")

    etuds = qdf("SELECT id, nom, prenom, groupe FROM etudiants WHERE actif=1 ORDER BY nom, prenom")
    if etuds.empty:
        st.info("Ajoute d’abord des étudiants.")
    else:
        labels = {r["id"]: f'{r["nom"]} {r["prenom"]} ({r["groupe"] or "sans groupe"})' for _, r in etuds.iterrows()}
        with st.form("perf_form"):
            c1, c2 = st.columns(2)
            eid = c1.selectbox("Étudiant", list(labels.keys()), format_func=lambda x: labels[x])
            activite = c2.selectbox("Activité", ACTIVITES, key="perf_activity")

            student_group = etuds[etuds.id == eid].iloc[0]["groupe"] or ""
            baremes_df = qdf("""
                SELECT * FROM baremes
                WHERE actif=1 AND activite=?
                ORDER BY CASE WHEN niveau_groupe=? THEN 0 WHEN niveau_groupe IS NULL OR niveau_groupe='' THEN 1 ELSE 2 END, nom
            """, (activite, student_group))

            bareme_options = [0] + baremes_df["id"].tolist()
            def bareme_label(x):
                if x == 0:
                    return "Aucun barème automatique"
                r = baremes_df[baremes_df.id == x].iloc[0]
                niv = r["niveau_groupe"] or "tous niveaux"
                return f'{r["nom"]} — {niv}'

            bareme_id = st.selectbox("Barème", bareme_options, format_func=bareme_label)

            intitule = st.text_input("Épreuve / performance", placeholder="Ex. 50 m nage libre, Cooper 12 min, parcours sauvetage...")
            c3, c4, c5 = st.columns(3)
            valeur = c3.number_input("Résultat", step=0.01, format="%.2f")

            if bareme_id:
                br = baremes_df[baremes_df.id == bareme_id].iloc[0]
                unite = br["unite"]
                c4.text_input("Unité", value=unite, disabled=True)
            else:
                unite = c4.selectbox("Unité", ["s", "min", "m", "km", "répétitions", "points", "autre"])
            d = c5.date_input("Date", value=date.today(), key="perf_date")
            commentaire = st.text_area("Commentaire")

            if bareme_id:
                note_preview = calc_note_from_bareme(
                    valeur,
                    br["valeur_0"],
                    br["valeur_20"],
                    br["sens"]
                )
                if note_preview is not None:
                    st.info(f"Note calculée : {note_preview:.2f}/20")

            savep = st.form_submit_button("Enregistrer la performance", use_container_width=True)
            if savep:
                note_calc = None
                bmin = bmax = None
                if bareme_id:
                    bmin = br["valeur_0"]
                    bmax = br["valeur_20"]
                    note_calc = calc_note_from_bareme(valeur, bmin, bmax, br["sens"])

                exec_sql(
                    """INSERT INTO performances(etudiant_id,activite,intitule,date_perf,valeur,unite,bareme_min,bareme_max,note_calculee,commentaire,bareme_id)
                       VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                    (eid, activite, intitule.strip(), str(d), valeur, unite, bmin, bmax, note_calc, commentaire.strip(), bareme_id or None)
                )

                auto_count = 0
                if bareme_id and note_calc is not None:
                    auto_count = apply_bareme_competences(eid, bareme_id, note_calc)

                if auto_count:
                    st.success(f"Performance enregistrée. {auto_count} compétence(s) mise(s) à jour automatiquement.")
                else:
                    st.success("Performance enregistrée.")
                st.rerun()

        perf = qdf("""
            SELECT e.nom, e.prenom, e.groupe, p.activite, p.intitule, p.date_perf,
                   p.valeur, p.unite, p.note_calculee, b.nom AS bareme, p.commentaire
            FROM performances p
            JOIN etudiants e ON e.id=p.etudiant_id
            LEFT JOIN baremes b ON b.id=p.bareme_id
            ORDER BY p.date_perf DESC, e.nom, e.prenom
        """)
        st.markdown("### Historique des performances")
        st.dataframe(perf, use_container_width=True, hide_index=True)

elif menu == "Barèmes":
    st.subheader("Barèmes personnalisés")
    st.caption("Crée des barèmes par activité et niveau de groupe, puis relie-les aux compétences à valider automatiquement.")

    tab_b1, tab_b2 = st.tabs(["Créer / modifier", "Lier aux compétences"])

    with tab_b1:
        with st.form("create_bareme"):
            c1, c2 = st.columns(2)
            activite_b = c1.selectbox("Activité", ACTIVITES, key="bareme_act")
            niveau_b = c2.text_input("Niveau / groupe", placeholder="Ex. Débutant, Avancé, NAT-A, L1...")
            nom_b = st.text_input("Nom du barème", placeholder="Ex. 100 m nage libre")
            c3, c4 = st.columns(2)
            unite_b = c3.selectbox("Unité", ["s", "min", "m", "km", "répétitions", "points", "autre"])
            sens_b = c4.selectbox("Sens", ["Plus élevé = meilleur", "Plus faible = meilleur"])
            c5, c6 = st.columns(2)
            v0 = c5.number_input("Performance correspondant à 0/20", value=0.0, step=0.1)
            v20 = c6.number_input("Performance correspondant à 20/20", value=20.0, step=0.1)
            save_b = st.form_submit_button("Créer le barème", use_container_width=True)
            if save_b:
                exec_sql(
                    """INSERT INTO baremes(activite,niveau_groupe,nom,unite,sens,valeur_0,valeur_20,actif)
                       VALUES(?,?,?,?,?,?,?,1)""",
                    (activite_b, niveau_b.strip(), nom_b.strip(), unite_b, sens_b, v0, v20)
                )
                st.success("Barème créé.")
                st.rerun()

        st.markdown("### Barèmes existants")
        bdf = qdf("""
            SELECT id, activite, niveau_groupe, nom, unite, sens, valeur_0, valeur_20, actif
            FROM baremes
            ORDER BY activite, niveau_groupe, nom
        """)
        st.dataframe(bdf, use_container_width=True, hide_index=True)

        if not bdf.empty:
            bid = st.selectbox(
                "Barème à activer/désactiver",
                bdf["id"].tolist(),
                format_func=lambda x: f'{bdf[bdf.id==x].iloc[0]["activite"]} — {bdf[bdf.id==x].iloc[0]["nom"]}'
            )
            active_now = int(bdf[bdf.id == bid].iloc[0]["actif"]) == 1
            if st.button("Désactiver" if active_now else "Réactiver", use_container_width=True):
                exec_sql("UPDATE baremes SET actif=? WHERE id=?", (0 if active_now else 1, bid))
                st.rerun()

    with tab_b2:
        bdf = qdf("SELECT * FROM baremes WHERE actif=1 ORDER BY activite, nom")
        if bdf.empty:
            st.info("Crée d’abord un barème.")
        else:
            bid = st.selectbox(
                "Barème",
                bdf["id"].tolist(),
                format_func=lambda x: f'{bdf[bdf.id==x].iloc[0]["activite"]} — {bdf[bdf.id==x].iloc[0]["nom"]}',
                key="link_bareme"
            )
            br = bdf[bdf.id == bid].iloc[0]
            comps = qdf("SELECT * FROM competences WHERE activite=? ORDER BY code", (br["activite"],))
            if comps.empty:
                st.info("Aucune compétence disponible pour cette activité.")
            else:
                comp_labels = {r["id"]: f'{r["code"]} — {r["libelle"]}' for _, r in comps.iterrows()}
                cid = st.selectbox("Compétence", comps["id"].tolist(), format_func=lambda x: comp_labels[x])
                c1, c2 = st.columns(2)
                seuil = c1.number_input("Seuil de note pour validation", min_value=0.0, max_value=20.0, value=10.0, step=0.5)
                niveau_attr = c2.selectbox("Niveau attribué", ["En cours d’acquisition", "Acquis", "Maîtrisé"])
                if st.button("Lier ce barème à cette compétence", type="primary", use_container_width=True):
                    conn = get_conn()
                    conn.execute("""
                        INSERT INTO bareme_competences(bareme_id,competence_id,seuil_note,niveau_attribue)
                        VALUES(?,?,?,?)
                        ON CONFLICT(bareme_id,competence_id)
                        DO UPDATE SET seuil_note=excluded.seuil_note,
                                      niveau_attribue=excluded.niveau_attribue
                    """, (bid, cid, seuil, niveau_attr))
                    conn.commit()
                    conn.close()
                    st.success("Liaison enregistrée.")
                    st.rerun()

                links = qdf("""
                    SELECT c.code, c.libelle, bc.seuil_note, bc.niveau_attribue
                    FROM bareme_competences bc
                    JOIN competences c ON c.id=bc.competence_id
                    WHERE bc.bareme_id=?
                    ORDER BY c.code
                """, (bid,))
                st.markdown("### Compétences liées")
                st.dataframe(links, use_container_width=True, hide_index=True)

elif menu == "Compétences":
    st.subheader("Validation des compétences")
    st.caption("Validation individuelle ou rapide par groupe, avec suivi de progression.")

    tab_i, tab_g = st.tabs(["Par étudiant", "Par groupe"])

    with tab_i:
        c1, c2 = st.columns([1, 2])
        activite = c1.selectbox("Activité", ACTIVITES)
        etuds = qdf("SELECT id, nom, prenom, groupe FROM etudiants WHERE actif=1 ORDER BY nom, prenom")
        comps = qdf("SELECT * FROM competences WHERE activite=? ORDER BY code", (activite,))

        with c2.expander("Ajouter une compétence"):
            with st.form("new_comp"):
                code = st.text_input("Code", placeholder="Ex. NAT5")
                lib = st.text_input("Libellé")
                ok = st.form_submit_button("Ajouter")
                if ok:
                    try:
                        exec_sql("INSERT INTO competences(activite,code,libelle) VALUES(?,?,?)", (activite, code.strip(), lib.strip()))
                        st.success("Compétence ajoutée.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

        if etuds.empty:
            st.info("Ajoute d’abord des étudiants.")
        elif comps.empty:
            st.info("Aucune compétence pour cette activité.")
        else:
            labels = {r["id"]: f'{r["nom"]} {r["prenom"]} ({r["groupe"] or "sans groupe"})' for _, r in etuds.iterrows()}
            eid = st.selectbox("Étudiant", list(labels.keys()), format_func=lambda x: labels[x])
            acq = qdf("""
                SELECT a.*, c.code, c.libelle
                FROM acquisitions a
                JOIN competences c ON c.id=a.competence_id
                WHERE a.etudiant_id=? AND c.activite=?
            """, (eid, activite))
            amap = {r["competence_id"]: r for _, r in acq.iterrows()}

            niveaux = ["Non évalué", "En cours d’acquisition", "Acquis", "Maîtrisé"]
            with st.form("competence_form"):
                values = []
                for _, comp in comps.iterrows():
                    old = amap.get(comp["id"])
                    current = old["niveau"] if old is not None else "Non évalué"
                    oldcom = old["commentaire"] if old is not None and old["commentaire"] else ""
                    st.markdown(f'**{comp["code"]} — {comp["libelle"]}**')
                    c1, c2 = st.columns([1.5, 3])
                    niv = c1.selectbox("Niveau", niveaux, index=niveaux.index(current), key=f"niv_{comp['id']}")
                    com = c2.text_input("Commentaire", value=oldcom, key=f"ccom_{comp['id']}")
                    values.append((comp["id"], niv, com))
                save = st.form_submit_button("Enregistrer les compétences", use_container_width=True)
                if save:
                    for cid, niv, com in values:
                        dval = str(date.today()) if niv in ["Acquis", "Maîtrisé"] else None
                        upsert_acquisition(eid, cid, niv, dval, com)
                    st.success("Compétences mises à jour.")
                    st.rerun()

    with tab_g:
        groupes_df = qdf("SELECT DISTINCT groupe FROM etudiants WHERE actif=1 AND groupe IS NOT NULL AND groupe<>'' ORDER BY groupe")
        groupes = groupes_df["groupe"].tolist() if not groupes_df.empty else []
        if not groupes:
            st.info("Aucun groupe défini.")
        else:
            c1, c2 = st.columns(2)
            groupe_g = c1.selectbox("Groupe", groupes, key="comp_group")
            activite_g = c2.selectbox("Activité", ACTIVITES, key="comp_activity_group")
            comps_g = qdf("SELECT * FROM competences WHERE activite=? ORDER BY code", (activite_g,))
            students_g = qdf("SELECT id, nom, prenom FROM etudiants WHERE actif=1 AND groupe=? ORDER BY nom, prenom", (groupe_g,))

            if comps_g.empty:
                st.info("Aucune compétence pour cette activité.")
            else:
                comp_labels = {r["id"]: f'{r["code"]} — {r["libelle"]}' for _, r in comps_g.iterrows()}
                cid = st.selectbox("Compétence à valider", list(comp_labels.keys()), format_func=lambda x: comp_labels[x])
                niveau_g = st.radio(
                    "Niveau à appliquer",
                    ["En cours d’acquisition", "Acquis", "Maîtrisé"],
                    horizontal=True
                )

                selected = st.multiselect(
                    "Étudiants concernés",
                    options=students_g["id"].tolist(),
                    format_func=lambda x: f'{students_g[students_g.id==x].iloc[0]["nom"]} {students_g[students_g.id==x].iloc[0]["prenom"]}'
                )
                if st.button("Appliquer aux étudiants sélectionnés", type="primary", use_container_width=True):
                    for eid in selected:
                        dval = str(date.today()) if niveau_g in ["Acquis", "Maîtrisé"] else None
                        upsert_acquisition(int(eid), int(cid), niveau_g, dval, "Validation groupe")
                    st.success(f"{len(selected)} étudiant(s) mis à jour.")
                    st.rerun()

                st.markdown("### Progression du groupe")
                progress = qdf("""
                    SELECT e.nom, e.prenom,
                           SUM(CASE WHEN a.niveau IN ('Acquis','Maîtrisé') THEN 1 ELSE 0 END) AS acquises,
                           COUNT(c.id) AS total
                    FROM etudiants e
                    CROSS JOIN competences c
                    LEFT JOIN acquisitions a ON a.etudiant_id=e.id AND a.competence_id=c.id
                    WHERE e.actif=1 AND e.groupe=? AND c.activite=?
                    GROUP BY e.id, e.nom, e.prenom
                    ORDER BY e.nom, e.prenom
                """, (groupe_g, activite_g))
                if not progress.empty:
                    progress["progression_%"] = (progress["acquises"] / progress["total"] * 100).round(0)
                    st.dataframe(progress, use_container_width=True, hide_index=True)

elif menu == "Fiche étudiant":
    st.subheader("Fiche individuelle étudiant")

    etuds = qdf("SELECT id, nom, prenom, numero_etudiant, email, groupe FROM etudiants WHERE actif=1 ORDER BY nom, prenom")
    if etuds.empty:
        st.info("Ajoute d’abord des étudiants.")
    else:
        labels = {
            r["id"]: f'{r["nom"]} {r["prenom"]} — {r["groupe"] or "sans groupe"}'
            for _, r in etuds.iterrows()
        }
        eid = st.selectbox("Étudiant", list(labels.keys()), format_func=lambda x: labels[x])
        e = etuds[etuds.id == eid].iloc[0]

        st.markdown(f"### {e['nom']} {e['prenom']}")
        st.caption(f"N° étudiant : {e['numero_etudiant'] or '—'} • Groupe : {e['groupe'] or '—'} • Email : {e['email'] or '—'}")

        pres = qdf("""
            SELECT s.activite, p.statut
            FROM presences p
            JOIN seances s ON s.id=p.seance_id
            WHERE p.etudiant_id=?
        """, (eid,))
        evals = qdf("""
            SELECT activite, note, bareme, coefficient
            FROM evaluations
            WHERE etudiant_id=?
        """, (eid,))
        acq = qdf("""
            SELECT c.activite, c.code, c.libelle,
                   COALESCE(a.niveau,'Non évalué') AS niveau
            FROM competences c
            LEFT JOIN acquisitions a
              ON a.competence_id=c.id AND a.etudiant_id=?
            ORDER BY c.activite, c.code
        """, (eid,))

        c1, c2, c3 = st.columns(3)
        if len(pres):
            presents = pres["statut"].eq("Présent").sum()
            taux = 100 * presents / len(pres)
            c1.metric("Présence globale", f"{taux:.1f}%")
        else:
            c1.metric("Présence globale", "—")

        if len(evals):
            ev = evals.copy()
            ev["n20"] = (ev["note"] / ev["bareme"]) * 20
            moyenne = (ev["n20"] * ev["coefficient"]).sum() / ev["coefficient"].sum()
            c2.metric("Moyenne globale", f"{moyenne:.2f}/20")
        else:
            c2.metric("Moyenne globale", "—")

        if len(acq):
            acquired = acq["niveau"].isin(["Acquis", "Maîtrisé"]).sum()
            c3.metric("Compétences acquises", f"{acquired}/{len(acq)}")
        else:
            c3.metric("Compétences acquises", "—")

        st.divider()
        activite = st.selectbox("Voir le bilan de l’activité", ACTIVITES)

        pa = pres[pres.activite == activite] if len(pres) else pd.DataFrame()
        ea = evals[evals.activite == activite] if len(evals) else pd.DataFrame()
        ca = acq[acq.activite == activite] if len(acq) else pd.DataFrame()

        b1, b2, b3 = st.columns(3)
        if len(pa):
            tauxa = 100 * pa["statut"].eq("Présent").sum() / len(pa)
            b1.metric("Présence", f"{tauxa:.1f}%")
        else:
            b1.metric("Présence", "—")

        if len(ea):
            ea = ea.copy()
            ea["n20"] = (ea["note"] / ea["bareme"]) * 20
            ma = (ea["n20"] * ea["coefficient"]).sum() / ea["coefficient"].sum()
            b2.metric("Moyenne", f"{ma:.2f}/20")
        else:
            b2.metric("Moyenne", "—")

        if len(ca):
            na = ca["niveau"].isin(["Acquis", "Maîtrisé"]).sum()
            b3.metric("Compétences", f"{na}/{len(ca)} acquises")
        else:
            b3.metric("Compétences", "—")

        st.markdown("#### Compétences")
        if len(ca):
            st.dataframe(ca[["code", "libelle", "niveau"]], use_container_width=True, hide_index=True)
        else:
            st.info("Aucune compétence définie pour cette activité.")

        st.markdown("#### Validation du semestre / activité")
        existing = qdf(
            "SELECT * FROM validations_semestre WHERE etudiant_id=? AND activite=?",
            (eid, activite)
        )
        if len(existing):
            old_status = existing.iloc[0]["statut"]
            old_comment = existing.iloc[0]["commentaire"] or ""
        else:
            old_status = "À valider"
            old_comment = ""

        statuts = ["À valider", "Validé", "Non validé"]
        with st.form("validation_semestre"):
            statut = st.radio(
                "Décision",
                statuts,
                horizontal=True,
                index=statuts.index(old_status) if old_status in statuts else 0
            )
            commentaire = st.text_area("Appréciation / commentaire", value=old_comment)
            save = st.form_submit_button("Enregistrer la validation")
            if save:
                dval = str(date.today()) if statut in ["Validé", "Non validé"] else None
                upsert_validation_semestre(eid, activite, statut, dval, commentaire.strip())
                st.success("Validation enregistrée.")
                st.rerun()

        st.markdown("#### Inscriptions SUAPS")
        regs = qdf("""
            SELECT o.activite, o.intitule, o.jour_horaire, o.lieu,
                   i.modalite, i.date_inscription, i.statut
            FROM inscriptions i
            JOIN offres_inscription o ON o.id=i.offre_id
            WHERE i.etudiant_id=?
            ORDER BY i.date_inscription DESC
        """, (eid,))
        if len(regs):
            st.dataframe(regs, use_container_width=True, hide_index=True)
        else:
            st.caption("Aucune inscription enregistrée.")

        st.markdown("#### Performances enregistrées")
        perfs = qdf("""
            SELECT activite, intitule, date_perf, valeur, unite, note_calculee, commentaire
            FROM performances
            WHERE etudiant_id=?
            ORDER BY date_perf DESC
        """, (eid,))
        if len(perfs):
            st.dataframe(perfs, use_container_width=True, hide_index=True)
        else:
            st.caption("Aucune performance enregistrée.")

        st.markdown("#### Synthèse des validations")
        vals = qdf(
            "SELECT activite, statut, date_validation, commentaire FROM validations_semestre WHERE etudiant_id=? ORDER BY activite",
            (eid,)
        )
        if len(vals):
            st.dataframe(vals, use_container_width=True, hide_index=True)
        else:
            st.caption("Aucune validation finale enregistrée.")

elif menu == "Exports":
    st.subheader("Exports CSV")

    exports = {
        "Étudiants": qdf("SELECT * FROM etudiants"),
        "Séances": qdf("SELECT * FROM seances"),
        "Présences": qdf("""
            SELECT s.date_seance, s.activite, s.groupe, s.theme,
                   e.nom, e.prenom, e.numero_etudiant,
                   p.statut, p.commentaire
            FROM presences p
            JOIN seances s ON s.id=p.seance_id
            JOIN etudiants e ON e.id=p.etudiant_id
            ORDER BY s.date_seance DESC, e.nom, e.prenom
        """),
        "Évaluations": qdf("""
            SELECT e.nom, e.prenom, e.numero_etudiant, e.groupe,
                   v.activite, v.intitule, v.date_eval, v.note, v.bareme, v.coefficient, v.commentaire
            FROM evaluations v
            JOIN etudiants e ON e.id=v.etudiant_id
            ORDER BY v.date_eval DESC, e.nom, e.prenom
        """),
        "Compétences": qdf("""
            SELECT e.nom, e.prenom, e.numero_etudiant, e.groupe,
                   c.activite, c.code, c.libelle,
                   COALESCE(a.niveau,'Non évalué') AS niveau,
                   a.date_validation, a.commentaire
            FROM etudiants e
            CROSS JOIN competences c
            LEFT JOIN acquisitions a
              ON a.etudiant_id=e.id AND a.competence_id=c.id
            WHERE e.actif=1
            ORDER BY e.nom, e.prenom, c.activite, c.code
        """),
        "Validations semestre": qdf("""
            SELECT e.nom, e.prenom, e.numero_etudiant, e.groupe,
                   v.activite, v.statut, v.date_validation, v.commentaire
            FROM validations_semestre v
            JOIN etudiants e ON e.id=v.etudiant_id
            ORDER BY e.nom, e.prenom, v.activite
        """),
        "Performances": qdf("""
            SELECT e.nom, e.prenom, e.numero_etudiant, e.groupe,
                   p.activite, p.intitule, p.date_perf, p.valeur, p.unite,
                   p.note_calculee, b.nom AS bareme, p.commentaire
            FROM performances p
            JOIN etudiants e ON e.id=p.etudiant_id
            LEFT JOIN baremes b ON b.id=p.bareme_id
            ORDER BY p.date_perf DESC, e.nom, e.prenom
        """),
        "Barèmes": qdf("""
            SELECT activite, niveau_groupe, nom, unite, sens, valeur_0, valeur_20, actif
            FROM baremes
            ORDER BY activite, niveau_groupe, nom
        """),
        "Inscriptions": qdf("""
            SELECT o.activite, o.intitule, o.groupe AS groupe_offre, o.jour_horaire, o.lieu,
                   e.nom, e.prenom, e.numero_etudiant, e.email, e.groupe AS groupe_etudiant,
                   i.modalite, i.date_inscription, i.statut
            FROM inscriptions i
            JOIN offres_inscription o ON o.id=i.offre_id
            JOIN etudiants e ON e.id=i.etudiant_id
            ORDER BY o.activite, o.intitule, e.nom, e.prenom
        """),
    }

    for name, df in exports.items():
        st.markdown(f"### {name}")
        st.dataframe(df, use_container_width=True, hide_index=True)
        st.download_button(
            f"Télécharger {name}.csv",
            data=df.to_csv(index=False).encode("utf-8-sig"),
            file_name=f"{name.lower().replace('é','e').replace(' ','_')}.csv",
            mime="text/csv"
        )

st.sidebar.divider()
st.sidebar.caption("Version MVP — données stockées localement dans SQLite.")
