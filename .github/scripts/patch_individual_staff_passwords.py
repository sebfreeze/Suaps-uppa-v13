from pathlib import Path

p = Path("security_bootstrap/sitecustomize.py")
s = p.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global s
    if new in s:
        print(f"{label}: déjà appliqué")
        return
    if old not in s:
        raise SystemExit(f"Ancre introuvable: {label}")
    s = s.replace(old, new, 1)
    print(f"{label}: appliqué")


# hashlib est nécessaire pour PBKDF2-SHA256 dans le code généré.
replace_once(
    'import secrets\\nimport time\\ntry:',
    'import secrets\\nimport hashlib\\nimport time\\ntry:',
    "import hashlib",
)

# Table de correspondance profil -> secret Render et vérification PBKDF2.
old_auth = '''TEACHER_SESSION_TIMEOUT=max(300,_auth_env_int("TEACHER_SESSION_TIMEOUT",1800))

def _auth_remaining(prefix):'''
new_auth = '''TEACHER_SESSION_TIMEOUT=max(300,_auth_env_int("TEACHER_SESSION_TIMEOUT",1800))

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

def _auth_remaining(prefix):'''
replace_once(old_auth, new_auth, "PBKDF2 individuel")

# Interface et logique de connexion : suppression du code commun.
replace_once(
    '# Connexion enseignant : code partagé + choix nominatif du profil.',
    '# Connexion enseignant : profil nominatif + mot de passe individuel.',
    "commentaire connexion",
)
replace_once(
    'topbar(); hero("Accès enseignant","Un code commun, puis un profil nominatif pour savoir qui utilise l\'application.","ESPACE SÉCURISÉ")',
    'topbar(); hero("Accès enseignant","Choisissez votre profil puis saisissez votre mot de passe individuel.","ESPACE SÉCURISÉ")',
    "texte connexion",
)

old_shared = '''    _teacher_code=os.getenv("TEACHER_ACCESS_CODE","").strip()
    if not _teacher_code:
        st.error("Accès enseignant temporairement indisponible : code de sécurité non configuré.")
        if st.button("← Accueil",key="admin_login_back"): go("Accueil")
        return
'''
replace_once(old_shared, '', "suppression code commun")
replace_once(
    '_entered=st.text_input("Code enseignant commun",type="password",autocomplete="off")',
    '_entered=st.text_input("Mot de passe individuel",type="password",autocomplete="current-password")',
    "champ mot de passe",
)
replace_once(
    'elif secrets.compare_digest(_entered.strip(),_teacher_code):',
    'elif _staff_password_ok(_person["nom"],_entered):',
    "vérification individuelle",
)
replace_once(
    'st.error("Code enseignant incorrect.")',
    'st.error("Mot de passe incorrect.")',
    "message erreur",
)

p.write_text(s, encoding="utf-8")
print("Authentification individuelle prête")
