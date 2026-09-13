"""Injection ciblée du module pédagogique dans les sources Streamlit SUAPS."""
from __future__ import annotations

SENTINEL = "# --- pédagogie resources integration ---"


def _patch_v14_source(source: str) -> str:
    import_marker = "import streamlit as st\n"
    import_block = (
        "import streamlit as st\n"
        "from pedagogie_v14 import init_v14_pedagogy, render_v14_teacher_resources, render_v14_student_resources\n"
    )
    if import_marker not in source:
        raise RuntimeError("Point d'injection imports V14 pédagogie introuvable.")
    source = source.replace(import_marker, import_block, 1)

    init_marker = "init_db()\n\ndef rows(sql,p=()):"
    init_block = (
        "init_db()\n"
        f"{SENTINEL}\n"
        "init_v14_pedagogy(db)\n\n"
        "def rows(sql,p=()):"
    )
    if init_marker not in source:
        raise RuntimeError("Point d'initialisation V14 pédagogie introuvable.")
    source = source.replace(init_marker, init_block, 1)

    home_marker = '    if st.button(label_live,key="home_infos_live",type="primary"): go("Infos Live")\n'
    home_block = (
        home_marker
        + '    if st.button("📚 Ressources pédagogiques",key="home_ped_resources",use_container_width=True): go("Ressources pédagogiques")\n'
    )
    if home_marker not in source:
        raise RuntimeError("Bouton Infos Live V14 introuvable.")
    source = source.replace(home_marker, home_block, 1)

    family_marker = "\ndef famille():"
    student_page = '''
def ressources_pedagogiques_etudiant():
    topbar(); hero("Ressources pédagogiques","Documents et séances partagés par l'équipe SUAPS.","SUAPS • PÉDAGOGIE")
    render_v14_student_resources(st, db)
    if st.button("← Accueil",key="ped_resources_student_back"): go("Accueil")
    nav()

def famille():'''
    if family_marker not in source:
        raise RuntimeError("Point d'insertion page étudiant V14 introuvable.")
    source = source.replace(family_marker, student_page, 1)

    admin_marker = (
        'def admin():\n'
        '    topbar(); hero("Enseignant / Administration","Pilotage rapide des créneaux, présences et évaluations.","ESPACE ENSEIGNANT")\n'
    )
    admin_block = admin_marker + '''    if st.session_state.get("ped_resources_open",False):
        if st.button("← Retour à l’administration",key="close_ped_resources",use_container_width=True):
            st.session_state.ped_resources_open=False; st.rerun()
        render_v14_teacher_resources(st, db, rows, one, exe, ACTIVITES)
        return
    if st.button("📚 Ressources pédagogiques",key="open_ped_resources",type="primary",use_container_width=True):
        st.session_state.ped_resources_open=True; st.rerun()
'''
    if admin_marker not in source:
        raise RuntimeError("Point d'insertion espace enseignant V14 introuvable.")
    source = source.replace(admin_marker, admin_block, 1)

    pages_marker = '"Infos Live":infos_live,'
    pages_block = '"Infos Live":infos_live,"Ressources pédagogiques":ressources_pedagogiques_etudiant,'
    if pages_marker not in source:
        raise RuntimeError("Navigation pages V14 introuvable.")
    source = source.replace(pages_marker, pages_block, 1)
    return source


def _patch_sidebar_source(source: str) -> str:
    import_marker = "from io import BytesIO\n"
    import_block = '''from io import BytesIO
from pedagogie_resources import (
    init_pedagogy_schema, ensure_seance_resource_column,
    render_teacher_resources, render_student_resources,
)
from pedagogie_seed import seed_official_resources
'''
    if import_marker not in source:
        raise RuntimeError("Point d'injection imports pédagogie introuvable.")
    source = source.replace(import_marker, import_block, 1)

    init_marker = "\ninit_db()\n"
    init_block = '''
init_db()
# --- pédagogie resources integration ---
init_pedagogy_schema(get_conn, USE_POSTGRES)
ensure_seance_resource_column(get_conn, USE_POSTGRES)
seed_official_resources(get_conn, USE_POSTGRES)
'''
    if init_marker not in source:
        raise RuntimeError("Point d'initialisation pédagogie introuvable.")
    source = source.replace(init_marker, init_block, 1)

    student_old = 'menu = st.sidebar.radio("Navigation", ["Accueil", "Portail étudiant"])'
    student_new = 'menu = st.sidebar.radio("Navigation", ["Accueil", "Portail étudiant", "Ressources pédagogiques"])'
    if student_old not in source:
        raise RuntimeError("Navigation étudiant introuvable.")
    source = source.replace(student_old, student_new, 1)

    teacher_old = '''["Accueil", "Tableau de bord", "Portail étudiant", "Étudiants", "Inscriptions en ligne",
         "Présences", "Émargement QR / NFC", "Cahier de notes", "Performances", "Barèmes",
         "Compétences", "Fiche étudiant", "Exports"]'''
    teacher_new = '''["Accueil", "Tableau de bord", "Ressources pédagogiques", "Portail étudiant", "Étudiants", "Inscriptions en ligne",
         "Présences", "Émargement QR / NFC", "Cahier de notes", "Performances", "Barèmes",
         "Compétences", "Fiche étudiant", "Exports"]'''
    if teacher_old not in source:
        raise RuntimeError("Navigation enseignant introuvable.")
    source = source.replace(teacher_old, teacher_new, 1)

    dispatch_marker = 'if menu == "Accueil":\n'
    dispatch = '''if menu == "Ressources pédagogiques":
    if st.session_state.role == "Étudiant":
        render_student_resources(st, get_conn=get_conn)
    else:
        render_teacher_resources(
            st,
            get_conn=get_conn,
            use_postgres=USE_POSTGRES,
            exec_sql=exec_sql,
            activities=ACTIVITES,
            admin_code_value=secret_value("PEDAGOGY_ADMIN_CODE", "").strip(),
        )
elif menu == "Accueil":
'''
    if dispatch_marker not in source:
        raise RuntimeError("Dispatch principal introuvable.")
    source = source.replace(dispatch_marker, dispatch, 1)
    return source


def patch_app_source(source: str) -> str:
    if SENTINEL in source:
        return source
    if "def db():" in source and "def admin():" in source and 'key="admin_section"' in source:
        return _patch_v14_source(source)
    return _patch_sidebar_source(source)
