"""Couche de sécurité et de persistance chargée avant Streamlit sur Render.
Charge d'abord les correctifs historiques du projet, puis applique les garde-fous
sur le code généré de l'application live. PostgreSQL est utilisé dès qu'un
DATABASE_URL est configuré; SQLite reste disponible comme repli réversible.
"""
from __future__ import annotations

import builtins
import importlib.util
from pathlib import Path

# Conserver les correctifs historiques (semestres/CSV, design, etc.).
_root = Path(__file__).resolve().parents[1]
_legacy = _root / "sitecustomize.py"
if _legacy.exists():
    try:
        _spec = importlib.util.spec_from_file_location("suaps_legacy_sitecustomize", _legacy)
        if _spec and _spec.loader:
            _mod = importlib.util.module_from_spec(_spec)
            _spec.loader.exec_module(_mod)
    except Exception:
        pass

_previous_compile = builtins.compile


def _secure_generated_app(source):
    if not isinstance(source, str):
        return source
    if "def admin():" not in source or "Enseignant / Admin" not in source:
        return source

    # Dépendances nécessaires à la sécurité et au backend PostgreSQL.
    if "from psycopg_pool import ConnectionPool" not in source:
        source = source.replace(
            "import streamlit as st",
            "import streamlit as st\nimport os\nimport re\nimport secrets\nimport hashlib\nimport time\ntry:\n    import psycopg\n    from psycopg.rows import dict_row\n    try:\n        from psycopg_pool import ConnectionPool\n    except Exception:\n        ConnectionPool=None\nexcept Exception:\n    psycopg=None\n    dict_row=None\n    ConnectionPool=None",
            1,
        )

    # Backend compatible SQLite/PostgreSQL. La bascule ne se fait que si
    # DATABASE_URL est réellement présent sur Render. En production, les
    # connexions PostgreSQL sont réutilisées par un pool partagé entre les
    # sessions Streamlit du processus.
    old_db = '''def db():
    c=sqlite3.connect(DB,check_same_thread=False,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=NORMAL")
    return c'''
    new_db = '''DATABASE_URL=os.getenv("DATABASE_URL","").strip()
USE_POSTGRES=bool(DATABASE_URL)
DBIntegrityError=(sqlite3.IntegrityError, psycopg.IntegrityError) if psycopg else sqlite3.IntegrityError


def _env_int(name,default):
    try: return int(os.getenv(name,str(default)))
    except Exception: return int(default)


def _env_float(name,default):
    try: return float(os.getenv(name,str(default)))
    except Exception: return float(default)


DB_POOL_MIN=max(1,_env_int("DB_POOL_MIN",1))
DB_POOL_MAX=max(DB_POOL_MIN,_env_int("DB_POOL_MAX",12))
DB_POOL_TIMEOUT=max(1.0,_env_float("DB_POOL_TIMEOUT",15.0))


@st.cache_resource(show_spinner=False)
def _get_pg_pool():
    if not USE_POSTGRES:
        return None
    if psycopg is None or ConnectionPool is None:
        raise RuntimeError("DATABASE_URL configuré mais psycopg_pool indisponible")
    return ConnectionPool(
        conninfo=DATABASE_URL,
        min_size=DB_POOL_MIN,
        max_size=DB_POOL_MAX,
        timeout=DB_POOL_TIMEOUT,
        max_idle=300,
        max_lifetime=1800,
        kwargs={"row_factory":dict_row},
        open=True,
        name="suaps-app",
    )


def _pg_sql(sql):
    s=str(sql).strip()
    # SQLite accepte les alias entre apostrophes, PostgreSQL non.
    s=re.sub(r"(?i)AS[ ]+'([^']+)'",lambda m:'AS "'+m.group(1).replace('"','""')+'"',s)
    ignore=bool(re.match(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO",s))
    if ignore:
        s=re.sub(r"(?is)^INSERT\s+OR\s+IGNORE\s+INTO","INSERT INTO",s,count=1)
    s=s.replace("INTEGER PRIMARY KEY AUTOINCREMENT","BIGSERIAL PRIMARY KEY")
    s=re.sub(r"\bBLOB\b","BYTEA",s,flags=re.I)
    s=s.replace("?","%s")
    if ignore and "ON CONFLICT" not in s.upper():
        m=re.search(r"(?is)\s+RETURNING\s+",s)
        if m:
            s=s[:m.start()]+" ON CONFLICT DO NOTHING"+s[m.start():]
        else:
            s=s.rstrip().rstrip(";")+" ON CONFLICT DO NOTHING"
    return s


class _PGCursor:
    def __init__(self,conn):
        self.conn=conn
        self.cur=conn.raw.cursor(row_factory=dict_row)
        self.lastrowid=None
    def execute(self,sql,p=()):
        self.cur.execute(_pg_sql(sql),tuple(p or ()))
        return self
    def executemany(self,sql,seq):
        self.cur.executemany(_pg_sql(sql),seq)
        return self
    def executescript(self,script):
        for stmt in str(script).split(";"):
            if stmt.strip(): self.execute(stmt)
        return self
    def fetchone(self): return self.cur.fetchone()
    def fetchall(self): return self.cur.fetchall()


class _PGConnection:
    def __init__(self):
        self.pool=_get_pg_pool()
        self.raw=self.pool.getconn(timeout=DB_POOL_TIMEOUT)
    def cursor(self): return _PGCursor(self)
    def execute(self,sql,p=()): return self.cursor().execute(sql,p)
    def commit(self): self.raw.commit()
    def rollback(self): self.raw.rollback()
    def close(self):
        raw=self.raw
        if raw is None: return
        self.raw=None
        try:
            if not raw.closed:
                try: raw.rollback()
                except Exception: pass
        finally:
            self.pool.putconn(raw)


def db():
    if USE_POSTGRES:
        if psycopg is None or ConnectionPool is None:
            raise RuntimeError("DATABASE_URL configuré mais le pool PostgreSQL est indisponible")
        return _PGConnection()
    c=sqlite3.connect(DB,check_same_thread=False,timeout=10)
    c.row_factory=sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL"); c.execute("PRAGMA synchronous=NORMAL")
    return c'''
    if old_db in source and "class _PGConnection" not in source:
        source = source.replace(old_db, new_db, 1)

    # rows() doit toujours rendre la connexion au pool, même en cas d'erreur SQL.
    safe_rows = '''def rows(sql,p=()):
    c=db()
    try:
        r=c.execute(sql,p).fetchall()
        return [dict(x) for x in r]
    finally:
        c.close()'''
    for old_rows in (
        '''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return r''',
        '''def rows(sql,p=()):
    c=db(); r=c.execute(sql,p).fetchall(); c.close(); return [dict(x) for x in r]''',
    ):
        if old_rows in source:
            source = source.replace(old_rows, safe_rows, 1)
            break

    # exe() retourne l'id créé sous PostgreSQL et rend systématiquement la
    # connexion au pool, y compris lorsqu'une requête échoue.
    old_exe = '''def exe(sql,p=()):
    c=db(); q=c.cursor(); q.execute(sql,p); c.commit(); x=q.lastrowid; c.close(); return x'''
    new_exe = '''def exe(sql,p=()):
    c=db()
    try:
        q=c.cursor()
        if USE_POSTGRES and re.match(r"(?is)^\s*INSERT\s+",str(sql)) and "OR IGNORE" not in str(sql).upper() and "RETURNING" not in str(sql).upper():
            m=re.match(r"(?is)^\s*INSERT\s+INTO\s+([A-Za-z_][A-Za-z0-9_]*)",str(sql))
            table=m.group(1).lower() if m else ""
            if table and table not in {"offre_semestres"}:
                q.execute(str(sql).rstrip().rstrip(";")+" RETURNING id",p)
                row=q.fetchone(); x=row.get("id") if row else None
            else:
                q.execute(sql,p); x=None
        else:
            q.execute(sql,p); x=None if USE_POSTGRES else q.lastrowid
        c.commit()
        return x
    except Exception:
        try: c.rollback()
        except Exception: pass
        raise
    finally:
        c.close()'''
    if old_exe in source:
        source = source.replace(old_exe,new_exe,1)

    # Les deux moteurs exposent désormais la même exception fonctionnelle.
    source = source.replace("except sqlite3.IntegrityError","except DBIntegrityError")

    # Profils définitifs : source unique afin d'éviter les régressions entre
    # correctifs successifs. Les profils doubles conservent role=Admin pour les
    # fonctions réservées tout en étant affichés Enseignant + Administrateur.
    staff_block = '''STAFF_PROFILES=[
    {"nom":"Hervé","role":"Enseignant","avatar":"🏉😎"},
    {"nom":"Luhpo","role":"Enseignant","avatar":"🏊‍♂️🤿"},
    {"nom":"Raphaël","role":"Enseignant","avatar":"🏄‍♂️🌊"},
    {"nom":"Dudu","role":"Enseignant","avatar":"🏀😄"},
    {"nom":"Geoffrey","role":"Admin","avatar":"🏸⚡"},
    {"nom":"Bernard","role":"Admin","avatar":"🚴‍♂️😜"},
    {"nom":"Mathieu","role":"Admin","avatar":"🏋️‍♂️💪"},
    {"nom":"Michel","role":"Admin","avatar":"⛷️😎"},
    {"nom":"Stéphanie","role":"Admin","avatar":"💃✨"},
    {"nom":"Yan-Erick","role":"Admin","avatar":"🧗‍♂️⚽"},
    {"nom":"Patrick","role":"Admin","avatar":"🛶🌊"},
    {"nom":"Sébastien","role":"Admin","avatar":"🏉🧢"},
]
st.session_state.setdefault("admin_auth",False)
st.session_state.setdefault("teacher_name",None)
st.session_state.setdefault("teacher_role",None)
st.session_state.setdefault("teacher_avatar",None)
st.session_state.setdefault("teacher_last_activity",0.0)
st.session_state.setdefault("user_last_activity",0.0)
st.session_state.setdefault("student_login_failures",0)
st.session_state.setdefault("student_login_lock_until",0.0)
st.session_state.setdefault("teacher_login_failures",0)
st.session_state.setdefault("teacher_login_lock_until",0.0)

def _auth_env_int(name,default):
    try: return int(os.getenv(name,str(default)))
    except Exception: return int(default)

AUTH_MAX_ATTEMPTS=max(3,_auth_env_int("AUTH_MAX_ATTEMPTS",5))
AUTH_LOCK_SECONDS=max(60,_auth_env_int("AUTH_LOCK_SECONDS",300))
STUDENT_SESSION_TIMEOUT=max(300,_auth_env_int("STUDENT_SESSION_TIMEOUT",3600))
TEACHER_SESSION_TIMEOUT=max(300,_auth_env_int("TEACHER_SESSION_TIMEOUT",1800))

STAFF_PASSWORD_ENV={
    "Hervé":"STAFF_PASSWORD_HASH_HERVE",
    "Luhpo":"STAFF_PASSWORD_HASH_LUHPO",
    "Raphaël":"STAFF_PASSWORD_HASH_RAPHAEL",
    "Dudu":"STAFF_PASSWORD_HASH_DUDU",
    "Geoffrey":"STAFF_PASSWORD_HASH_GEOFFREY",
    "Bernard":"STAFF_PASSWORD_HASH_BERNARD",
    "Mathieu":"STAFF_PASSWORD_HASH_MATHIEU",
    "Michel":"STAFF_PASSWORD_HASH_MICHEL",
    "Stéphanie":"STAFF_PASSWORD_HASH_STEPHANIE",
    "Yan-Erick":"STAFF_PASSWORD_HASH_YAN_ERICK",
    "Patrick":"STAFF_PASSWORD_HASH_PATRICK",
    "Sébastien":"STAFF_PASSWORD_HASH_SEBASTIEN",
}

def _staff_password_ok(name,entered):
    _key=STAFF_PASSWORD_ENV.get(str(name or ""))
    _stored=os.getenv(_key,"").strip() if _key else ""
    if not _stored: return False
    try:
        _scheme,_iterations,_salt_hex,_digest_hex=_stored.split("$",3)
        if _scheme!="pbkdf2_sha256": return False
        _iterations=int(_iterations)
        if _iterations<200000 or _iterations>1000000: return False
        _derived=hashlib.pbkdf2_hmac("sha256",str(entered or "").encode("utf-8"),bytes.fromhex(_salt_hex),_iterations)
        return secrets.compare_digest(_derived.hex(),_digest_hex)
    except Exception:
        return False

def _auth_remaining(prefix):
    return max(0,int(float(st.session_state.get(prefix+"_lock_until") or 0)-time.time()))

def _auth_fail(prefix):
    n=int(st.session_state.get(prefix+"_failures") or 0)+1
    if n>=AUTH_MAX_ATTEMPTS:
        st.session_state[prefix+"_failures"]=0
        st.session_state[prefix+"_lock_until"]=time.time()+AUTH_LOCK_SECONDS
    else:
        st.session_state[prefix+"_failures"]=n

def _auth_ok(prefix):
    st.session_state[prefix+"_failures"]=0
    st.session_state[prefix+"_lock_until"]=0.0

def _clear_student_auth():
    st.session_state.user_id=None
    st.session_state.user_last_activity=0.0

def _clear_teacher_auth():
    st.session_state.admin_auth=False
    st.session_state.teacher_name=None
    st.session_state.teacher_role=None
    st.session_state.teacher_avatar=None
    st.session_state.teacher_last_activity=0.0

def _staff_offers():
    if st.session_state.get("teacher_role")=="Admin":
        return rows("SELECT * FROM offres ORDER BY activite,intitule")
    _name=(st.session_state.get("teacher_name") or "").strip()
    if not _name: return []
    return rows("SELECT DISTINCT o.* FROM offres o JOIN offre_responsables r ON r.offre_id=o.id WHERE r.responsable=? OR r.coresponsable=? ORDER BY o.activite,o.intitule",(_name,_name))

def _staff_students():
    if st.session_state.get("teacher_role")=="Admin":
        return rows("SELECT * FROM utilisateurs WHERE profil='Étudiant' AND actif=1 ORDER BY nom,prenom")
    _name=(st.session_state.get("teacher_name") or "").strip()
    if not _name: return []
    return rows("SELECT DISTINCT u.* FROM utilisateurs u JOIN inscriptions i ON i.utilisateur_id=u.id AND i.statut='Inscrit' JOIN offre_responsables r ON r.offre_id=i.offre_id WHERE u.profil='Étudiant' AND u.actif=1 AND (r.responsable=? OR r.coresponsable=?) ORDER BY u.nom,u.prenom",(_name,_name))

def _staff_recent_regs():
    _base="SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id"
    if st.session_state.get("teacher_role")=="Admin":
        return rows(_base+" ORDER BY i.id DESC LIMIT 30")
    _name=(st.session_state.get("teacher_name") or "").strip()
    if not _name: return []
    return rows(_base+" JOIN offre_responsables r ON r.offre_id=o.id WHERE r.responsable=? OR r.coresponsable=? ORDER BY i.id DESC LIMIT 30",(_name,_name))

def _staff_dashboard_counts():
    if st.session_state.get("teacher_role")=="Admin":
        return one("SELECT (SELECT COUNT(*) FROM utilisateurs WHERE actif=1) u,(SELECT COUNT(*) FROM inscriptions WHERE statut='Inscrit') i,(SELECT COUNT(*) FROM seances) s,(SELECT COUNT(*) FROM presences WHERE statut='Présent') p")
    _ids=[int(o["id"]) for o in _staff_offers()]
    if not _ids: return {"u":0,"i":0,"s":0,"p":0}
    _ph=",".join("?" for _ in _ids); _p=tuple(_ids)
    _u=one(f"SELECT COUNT(DISTINCT utilisateur_id) n FROM inscriptions WHERE statut='Inscrit' AND offre_id IN ({_ph})",_p)
    _i=one(f"SELECT COUNT(*) n FROM inscriptions WHERE statut='Inscrit' AND offre_id IN ({_ph})",_p)
    _s=one(f"SELECT COUNT(*) n FROM seances WHERE offre_id IN ({_ph})",_p)
    _pr=one(f"SELECT COUNT(*) n FROM presences p JOIN seances s ON s.id=p.seance_id WHERE p.statut='Présent' AND s.offre_id IN ({_ph})",_p)
    return {"u":int(_u["n"] if _u else 0),"i":int(_i["n"] if _i else 0),"s":int(_s["n"] if _s else 0),"p":int(_pr["n"] if _pr else 0)}

def go(p): st.session_state.page=p; st.rerun()'''
    source = source.replace(
        'def go(p): st.session_state.page=p; st.rerun()',
        staff_block,
        1,
    )

    # Expiration automatique des sessions étudiant + cloisonnement enseignants.
    source = source.replace(
        'def user(): return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,)) if st.session_state.user_id else None',
        'def user():\n    if not st.session_state.user_id: return None\n    _now=time.time(); _last=float(st.session_state.get("user_last_activity") or _now)\n    if _now-_last>STUDENT_SESSION_TIMEOUT:\n        _clear_student_auth(); return None\n    st.session_state.user_last_activity=_now\n    return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,))',
        1,
    )
    source = source.replace('offs=rows("SELECT * FROM offres ORDER BY activite,intitule")','offs=_staff_offers()')
    source = source.replace('_offs=rows("SELECT * FROM offres ORDER BY activite,intitule")','_offs=_staff_offers()')
    source = source.replace('us=rows("SELECT * FROM utilisateurs WHERE profil=\'Étudiant\' AND actif=1 ORDER BY nom,prenom")','us=_staff_students()')
    source = source.replace(
        's=one("SELECT (SELECT COUNT(*) FROM utilisateurs WHERE actif=1) u,(SELECT COUNT(*) FROM inscriptions WHERE statut=\'Inscrit\') i,(SELECT COUNT(*) FROM seances) s,(SELECT COUNT(*) FROM presences WHERE statut=\'Présent\') p")',
        's=_staff_dashboard_counts()',1)
    source = source.replace(
        'd=rows("SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id ORDER BY i.id DESC LIMIT 30")',
        'd=_staff_recent_regs()',1)

    # L'entrée Enseignant/Admin ne doit jamais ouvrir directement l'administration.
    source = source.replace(
        'st.session_state.profil=prof; go("Administration" if prof=="Enseignant/Admin" else "Connexion")',
        'st.session_state.profil=prof; go("Connexion Admin" if prof=="Enseignant/Admin" else "Connexion")',
        1,
    )

    # Logo officiel présent à la racine du projet sur toutes les pages principales.
    source = source.replace(
        "def topbar():\n    st.markdown(",
        "def topbar():\n    _logo=Path(__file__).with_name('logo_uppa.png')\n    if _logo.exists(): st.image(str(_logo),width=235)\n    st.markdown(",
        1,
    )

    # Connexion enseignant : profil nominatif + mot de passe individuel.
    admin_login = '''def admin_login():
    topbar(); hero("Accès enseignant","Choisissez votre profil puis saisissez votre mot de passe individuel.","ESPACE SÉCURISÉ")
    if st.session_state.get("admin_auth") and st.session_state.get("teacher_name"):
        _now=time.time(); _last=float(st.session_state.get("teacher_last_activity") or _now)
        if _now-_last<=TEACHER_SESSION_TIMEOUT:
            st.session_state.teacher_last_activity=_now; go("Administration")
        _clear_teacher_auth()
    if st.session_state.get("admin_auth") and not st.session_state.get("teacher_name"):
        st.session_state.admin_auth=False
    _teacher_code=os.getenv("TEACHER_ACCESS_CODE","").strip()
    if not _teacher_code:
        st.error("Accès enseignant temporairement indisponible : code de sécurité non configuré.")
        if st.button("← Accueil",key="admin_login_back"): go("Accueil")
        return
    with st.form("teacher_login_form"):
        _person=st.selectbox(
            "Qui êtes-vous ?",
            STAFF_PROFILES,
            format_func=lambda p:f"{p['avatar']}  {p['nom']} — {'Enseignant + Administrateur' if p['nom'] in ('Sébastien','Geoffrey','Bernard') else ('Administrateur' if p['role']=='Admin' else 'Enseignant')}",
            key="teacher_identity_pick",
        )
        _entered=st.text_input("Mot de passe individuel",type="password",autocomplete="current-password")
        _ok=st.form_submit_button("Accéder à l'espace enseignant",type="primary",use_container_width=True)
    if _ok:
        _remaining=_auth_remaining("teacher_login")
        if _remaining>0:
            st.error(f"Trop de tentatives. Réessaie dans {_remaining} seconde(s).")
        elif _staff_password_ok(_person["nom"],_entered):
            _auth_ok("teacher_login")
            st.session_state.admin_auth=True
            st.session_state.teacher_name=_person["nom"]
            st.session_state.teacher_role=_person["role"]
            st.session_state.teacher_avatar=_person["avatar"]
            st.session_state.teacher_last_activity=time.time()
            go("Administration")
        else:
            _auth_fail("teacher_login")
            st.error("Mot de passe incorrect.")
    if st.button("← Accueil",key="admin_login_home"): go("Accueil")

'''
    if "def admin_login():" not in source:
        source = source.replace("def admin():", admin_login + "def admin():", 1)

    # Garde systématique, même si une navigation directe tente d'ouvrir Administration.
    source = source.replace(
        'def admin():\n    topbar(); hero("Enseignant / Administration"',
        'def admin():\n    if not st.session_state.get("admin_auth") or not st.session_state.get("teacher_name"):\n        go("Connexion Admin")\n    _now=time.time(); _last=float(st.session_state.get("teacher_last_activity") or _now)\n    if _now-_last>TEACHER_SESSION_TIMEOUT:\n        _clear_teacher_auth(); go("Connexion Admin")\n    st.session_state.teacher_last_activity=_now\n    topbar(); hero("Enseignant / Administration"',
        1,
    )

    # Afficher clairement l'identité active et permettre la déconnexion.
    source = source.replace(
        '    sec=st.radio("Rubrique",',
        '    _role_label="Enseignant + Administrateur" if st.session_state.get("teacher_name") in ("Sébastien","Geoffrey","Bernard") else ("Administrateur" if st.session_state.get("teacher_role")=="Admin" else "Enseignant")\n    st.success(f"{st.session_state.get(\'teacher_avatar\') or \'🏅\'}  Connecté : {st.session_state.get(\'teacher_name\')} • {_role_label}")\n    if st.button("🔒 Se déconnecter enseignant",key="teacher_logout"):\n        _clear_teacher_auth(); st.session_state.profil=None; go("Accueil")\n    sec=st.radio("Rubrique",',
        1,
    )

    # Sauvegardes et imports globaux restent réservés aux profils Admin.
    source = source.replace(
        'horizontal=True,key="admin_section")',
        'horizontal=True,key="admin_section")\n    if st.session_state.get("teacher_role")!="Admin" and sec in ("Sauvegardes","Semestres & CSV"):\n        st.warning("Cette rubrique est réservée aux administrateurs.")\n        if st.button("← Tableau de bord",key="teacher_admin_only_back"):\n            st.session_state.admin_section="Tableau de bord"; st.rerun()\n        return',
        1,
    )

    # Connexion utilisateur : lorsqu'un identifiant existe, il devient obligatoire.
    old_login = '''        with st.form("login"):
            email=st.text_input("Adresse e-mail")
            ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
            if r: st.session_state.user_id=r["id"]; go("Mon espace")
            else: st.error("Profil introuvable.")'''
    new_login = '''        with st.form("login"):
            email=st.text_input("Adresse e-mail")
            ident_login=st.text_input("Numéro étudiant / identifiant",type="password",help="Obligatoire pour un étudiant.")
            ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            _remaining=_auth_remaining("student_login")
            if _remaining>0:
                st.error(f"Trop de tentatives. Réessaie dans {_remaining} seconde(s).")
            else:
                r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
                _stored_ident=str(r.get("identifiant") or "").strip() if r else ""
                if not r:
                    _auth_fail("student_login"); st.error("Profil introuvable.")
                elif prof=="Étudiant" and not _stored_ident:
                    _auth_fail("student_login"); st.error("Profil étudiant incomplet : numéro étudiant absent. Contacte le SUAPS.")
                elif _stored_ident and not secrets.compare_digest(ident_login.strip(),_stored_ident):
                    _auth_fail("student_login"); st.error("Identifiant incorrect.")
                else:
                    _auth_ok("student_login")
                    st.session_state.user_id=r["id"]
                    st.session_state.user_last_activity=time.time()
                    go("Mon espace")'''
    source = source.replace(old_login, new_login, 1)

    # Pour un nouveau profil étudiant, le numéro étudiant devient obligatoire.
    source = source.replace(
        'if not nom or not pre or not mail: st.warning("Nom, prénom et e-mail sont obligatoires.")',
        'if not nom or not pre or not mail or (prof=="Étudiant" and not ident.strip()): st.warning("Nom, prénom, e-mail et numéro étudiant sont obligatoires pour un étudiant.")',
        1,
    )

    # Ajouter la page de connexion enseignant au routeur, quel que soit le patch V17 actif.
    source = source.replace(
        '"Administration":admin}',
        '"Connexion Admin":admin_login,"Administration":admin}',
        1,
    )

    return source


def _secure_compile(source, filename, mode, *args, **kwargs):
    return _previous_compile(_secure_generated_app(source), filename, mode, *args, **kwargs)


builtins.compile = _secure_compile

# Charger explicitement les correctifs complémentaires de migration. Dans les
# environnements virtuels Render, l'import automatique de usercustomize peut être
# désactivé, donc on le force ici après l'installation de la couche de sécurité.
try:
    import usercustomize as _suaps_usercustomize
except Exception as exc:
    print(f"[SUAPS_BOOTSTRAP] usercustomize_error={type(exc).__name__}:{exc}")

# Couche de montée en charge : inscriptions atomiques et index dédiés aux pics de
# rentrée. Elle est chargée en dernier afin de rester indépendante des correctifs
# historiques et des modules pédagogiques/compétition.
try:
    import scaling as _suaps_scaling
except Exception as exc:
    print(f"[SUAPS_BOOTSTRAP] scaling_error={type(exc).__name__}:{exc}")
