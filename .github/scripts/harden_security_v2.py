from pathlib import Path


def replace_once(text, old, new, label):
    if new in text:
        print(f"{label}: déjà appliqué")
        return text
    if old not in text:
        raise SystemExit(f"Ancre introuvable: {label}")
    print(f"{label}: appliqué")
    return text.replace(old, new, 1)


security_path = Path("security_bootstrap/sitecustomize.py")
text = security_path.read_text(encoding="utf-8")

# 1) time dans le code généré pour expiration de session / temporisation.
text = replace_once(
    text,
    'import re\\nimport secrets\\ntry:',
    'import re\\nimport secrets\\nimport time\\ntry:',
    "import time",
)

# 2) Helpers de sécurité et filtrage des groupes dans le bloc runtime.
old_staff_tail = '''st.session_state.setdefault("teacher_avatar",None)
def go(p): st.session_state.page=p; st.rerun()'''
new_staff_tail = '''st.session_state.setdefault("teacher_avatar",None)
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
    _sql="SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id"
    if st.session_state.get("teacher_role")=="Admin":
        return rows(_sql+" ORDER BY i.id DESC LIMIT 30")
    _name=(st.session_state.get("teacher_name") or "").strip()
    if not _name: return []
    return rows(_sql+" JOIN offre_responsables r ON r.offre_id=o.id WHERE r.responsable=? OR r.coresponsable=? ORDER BY i.id DESC LIMIT 30",(_name,_name))

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
text = replace_once(text, old_staff_tail, new_staff_tail, "helpers sécurité")

# 3) Expiration de session étudiant via user().
marker = '''    # L'entrée Enseignant/Admin ne doit jamais ouvrir directement l'administration.'''
student_session_patch = '''    # Expiration automatique des sessions étudiant et filtrage des données enseignants.
    source = source.replace(
        'def user(): return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,)) if st.session_state.user_id else None',
        '''def user():
    if not st.session_state.user_id: return None
    _now=time.time(); _last=float(st.session_state.get("user_last_activity") or _now)
    if _now-_last>STUDENT_SESSION_TIMEOUT:
        _clear_student_auth(); return None
    st.session_state.user_last_activity=_now
    return one("SELECT * FROM utilisateurs WHERE id=? AND actif=1",(st.session_state.user_id,))''',
        1,
    )
    source = source.replace('offs=rows("SELECT * FROM offres ORDER BY activite,intitule")','offs=_staff_offers()')
    source = source.replace('_offs=rows("SELECT * FROM offres ORDER BY activite,intitule")','_offs=_staff_offers()')
    source = source.replace('us=rows("SELECT * FROM utilisateurs WHERE profil=\'Étudiant\' AND actif=1 ORDER BY nom,prenom")','us=_staff_students()')
    source = source.replace(
        's=one("SELECT (SELECT COUNT(*) FROM utilisateurs WHERE actif=1) u,(SELECT COUNT(*) FROM inscriptions WHERE statut=\'Inscrit\') i,(SELECT COUNT(*) FROM seances) s,(SELECT COUNT(*) FROM presences WHERE statut=\'Présent\') p")',
        's=_staff_dashboard_counts()',
        1,
    )
    source = source.replace(
        'd=rows("SELECT u.prenom,u.nom,o.activite,i.modalite,i.date_inscription FROM inscriptions i JOIN utilisateurs u ON u.id=i.utilisateur_id JOIN offres o ON o.id=i.offre_id ORDER BY i.id DESC LIMIT 30")',
        'd=_staff_recent_regs()',
        1,
    )

    # L'import administratif doit toujours contenir un numéro étudiant.
    source = source.replace('required=["nom","prenom","email","activite","creneau"]','required=["nom","prenom","email","identifiant","activite","creneau"]',1)
    source = source.replace('Colonnes obligatoires : nom, prenom, email, activite, creneau.','Colonnes obligatoires : nom, prenom, email, identifiant, activite, creneau.',1)
    source = source.replace('Facultatives : identifiant, composante, profil, responsable, co_responsable.','Facultatives : composante, profil, responsable, co_responsable.',1)
    source = source.replace('{"colonne":"identifiant","statut":"Facultatif"','{"colonne":"identifiant","statut":"Obligatoire"',1)
    source = source.replace(
        'nom=clean("nom"); prenom=clean("prenom"); email=clean("email").lower(); activite=clean("activite"); creneau=clean("creneau"); horaire=clean("jour_horaire")',
        'nom=clean("nom"); prenom=clean("prenom"); email=clean("email").lower(); identifiant=clean("identifiant"); activite=clean("activite"); creneau=clean("creneau"); horaire=clean("jour_horaire")',
        1,
    )
    source = source.replace(
        'if not nom or not prenom or not email or not activite or not creneau:',
        'if not nom or not prenom or not email or not identifiant or not activite or not creneau:',
        1,
    )

'''
if student_session_patch not in text:
    if marker not in text:
        raise SystemExit("Ancre introuvable: patch session étudiant")
    text = text.replace(marker, student_session_patch + marker, 1)
    print("session étudiant / groupes / import: appliqué")
else:
    print("session étudiant / groupes / import: déjà appliqué")

# 4) Connexion enseignant : temporisation + expiration.
old_admin_start = '''def admin_login():
    topbar(); hero("Accès enseignant","Un code commun, puis un profil nominatif pour savoir qui utilise l'application.","ESPACE SÉCURISÉ")
    if st.session_state.get("admin_auth") and st.session_state.get("teacher_name"):
        go("Administration")'''
new_admin_start = '''def admin_login():
    topbar(); hero("Accès enseignant","Un code commun, puis un profil nominatif pour savoir qui utilise l'application.","ESPACE SÉCURISÉ")
    if st.session_state.get("admin_auth") and st.session_state.get("teacher_name"):
        _now=time.time(); _last=float(st.session_state.get("teacher_last_activity") or _now)
        if _now-_last<=TEACHER_SESSION_TIMEOUT:
            st.session_state.teacher_last_activity=_now; go("Administration")
        _clear_teacher_auth()'''
text = replace_once(text, old_admin_start, new_admin_start, "expiration session enseignant login")

old_admin_ok = '''    if _ok:
        if secrets.compare_digest(_entered.strip(),_teacher_code):
            st.session_state.admin_auth=True
            st.session_state.teacher_name=_person["nom"]
            st.session_state.teacher_role=_person["role"]
            st.session_state.teacher_avatar=_person["avatar"]
            go("Administration")
        else:
            st.error("Code enseignant incorrect.")'''
new_admin_ok = '''    if _ok:
        _remaining=_auth_remaining("teacher_login")
        if _remaining>0:
            st.error(f"Trop de tentatives. Réessaie dans {_remaining} seconde(s).")
        elif secrets.compare_digest(_entered.strip(),_teacher_code):
            _auth_ok("teacher_login")
            st.session_state.admin_auth=True
            st.session_state.teacher_name=_person["nom"]
            st.session_state.teacher_role=_person["role"]
            st.session_state.teacher_avatar=_person["avatar"]
            st.session_state.teacher_last_activity=time.time()
            go("Administration")
        else:
            _auth_fail("teacher_login")
            st.error("Code enseignant incorrect.")'''
text = replace_once(text, old_admin_ok, new_admin_ok, "anti-bruteforce enseignant")

old_admin_guard = '''def admin():\n    if not st.session_state.get("admin_auth") or not st.session_state.get("teacher_name"):\n        go("Connexion Admin")\n    topbar(); hero("Enseignant / Administration"'''
new_admin_guard = '''def admin():\n    if not st.session_state.get("admin_auth") or not st.session_state.get("teacher_name"):\n        go("Connexion Admin")\n    _now=time.time(); _last=float(st.session_state.get("teacher_last_activity") or _now)\n    if _now-_last>TEACHER_SESSION_TIMEOUT:\n        _clear_teacher_auth(); go("Connexion Admin")\n    st.session_state.teacher_last_activity=_now\n    topbar(); hero("Enseignant / Administration"'''
text = replace_once(text, old_admin_guard, new_admin_guard, "expiration session enseignant admin")

text = text.replace(
    'st.session_state.admin_auth=False; st.session_state.teacher_name=None; st.session_state.teacher_role=None; st.session_state.teacher_avatar=None; st.session_state.profil=None; go("Accueil")',
    '_clear_teacher_auth(); st.session_state.profil=None; go("Accueil")',
    1,
)

# 5) Connexion étudiant : identifiant requis + anti-bruteforce + timestamp de session.
old_login_block = '''    new_login = '''        with st.form("login"):
            email=st.text_input("Adresse e-mail")
            ident_login=st.text_input("Numéro étudiant / identifiant",type="password",help="Demandé si un identifiant est enregistré sur votre profil.")
            ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
            if not r:
                st.error("Profil introuvable.")
            elif str(r.get("identifiant") or "").strip() and not secrets.compare_digest(ident_login.strip(),str(r.get("identifiant") or "").strip()):
                st.error("Identifiant incorrect.")
            else:
                st.session_state.user_id=r["id"]; go("Mon espace")''''''
new_login_block = '''    new_login = '''        with st.form("login"):
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
                    go("Mon espace")''''''
text = replace_once(text, old_login_block, new_login_block, "anti-bruteforce étudiant")

security_path.write_text(text, encoding="utf-8")

# 6) La page multipage Pédagogie doit utiliser la même authentification enseignant.
ped_path = Path("pages/02_📚_Pédagogie.py")
ped = ped_path.read_text(encoding="utf-8")
if "import time\n" not in ped:
    ped = ped.replace("import sqlite3\n", "import sqlite3\nimport time\n", 1)
old_guard = '''if st.session_state.get("role") != "Enseignant":
    st.warning("🔒 La partie Pédagogie est réservée au mode Enseignant. Passe d'abord l'application en mode Enseignant.")
    st.stop()'''
new_guard = '''_teacher_timeout=max(300,int(os.getenv("TEACHER_SESSION_TIMEOUT","1800") or 1800))
_now=time.time(); _last=float(st.session_state.get("teacher_last_activity") or _now)
if (not st.session_state.get("admin_auth") or not st.session_state.get("teacher_name") or _now-_last>_teacher_timeout):
    st.session_state.admin_auth=False
    st.session_state.teacher_name=None
    st.session_state.teacher_role=None
    st.session_state.teacher_avatar=None
    st.session_state.teacher_last_activity=0.0
    st.warning("🔒 La partie Pédagogie est réservée aux enseignants authentifiés depuis l'application SUAPS.")
    st.stop()
st.session_state.teacher_last_activity=_now'''
ped = replace_once(ped, old_guard, new_guard, "garde Pédagogie")
ped_path.write_text(ped, encoding="utf-8")

print("Renforcement sécurité V2 prêt.")
