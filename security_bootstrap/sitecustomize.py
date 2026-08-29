"""Couche de sécurité chargée avant Streamlit sur Render.
Charge d'abord les correctifs historiques du projet, puis applique les garde-fous
sur le code généré de l'application live.
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

    # Dépendances nécessaires à l'authentification enseignant.
    if "import os\nimport secrets" not in source:
        source = source.replace(
            "import streamlit as st",
            "import streamlit as st\nimport os\nimport secrets",
            1,
        )

    # Etat de session dédié à l'espace enseignant.
    source = source.replace(
        'def go(p): st.session_state.page=p; st.rerun()',
        'st.session_state.setdefault("admin_auth",False)\ndef go(p): st.session_state.page=p; st.rerun()',
        1,
    )

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

    # Connexion enseignant protégée par une variable secrète Render.
    admin_login = '''def admin_login():
    topbar(); hero("Accès enseignant","Authentification requise pour accéder aux données et aux outils de gestion.","ESPACE SÉCURISÉ")
    if st.session_state.get("admin_auth"):
        go("Administration")
    _teacher_code=os.getenv("TEACHER_ACCESS_CODE","").strip()
    if not _teacher_code:
        st.error("Accès enseignant temporairement indisponible : code de sécurité non configuré.")
        if st.button("← Accueil",key="admin_login_back"): go("Accueil")
        return
    with st.form("teacher_login_form"):
        _entered=st.text_input("Code enseignant",type="password",autocomplete="off")
        _ok=st.form_submit_button("Accéder à l'espace enseignant",type="primary",use_container_width=True)
    if _ok:
        if secrets.compare_digest(_entered.strip(),_teacher_code):
            st.session_state.admin_auth=True
            go("Administration")
        else:
            st.error("Code enseignant incorrect.")
    if st.button("← Accueil",key="admin_login_home"): go("Accueil")

'''
    if "def admin_login():" not in source:
        source = source.replace("def admin():", admin_login + "def admin():", 1)

    # Garde systématique, même si une navigation directe tente d'ouvrir Administration.
    source = source.replace(
        'def admin():\n    topbar(); hero("Enseignant / Administration"',
        'def admin():\n    if not st.session_state.get("admin_auth"):\n        go("Connexion Admin")\n    topbar(); hero("Enseignant / Administration"',
        1,
    )

    # Bouton de déconnexion explicite dans l'administration.
    source = source.replace(
        '    sec=st.radio("Rubrique",',
        '    if st.button("🔒 Se déconnecter enseignant",key="teacher_logout"):\n        st.session_state.admin_auth=False; st.session_state.profil=None; go("Accueil")\n    sec=st.radio("Rubrique",',
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
            ident_login=st.text_input("Numéro étudiant / identifiant",type="password",help="Demandé si un identifiant est enregistré sur votre profil.")
            ok=st.form_submit_button("Me connecter",type="primary")
        if ok:
            r=one("SELECT * FROM utilisateurs WHERE lower(email)=lower(?) AND profil=? AND actif=1",(email.strip(),prof))
            if not r:
                st.error("Profil introuvable.")
            elif str(r.get("identifiant") or "").strip() and not secrets.compare_digest(ident_login.strip(),str(r.get("identifiant") or "").strip()):
                st.error("Identifiant incorrect.")
            else:
                st.session_state.user_id=r["id"]; go("Mon espace")'''
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
