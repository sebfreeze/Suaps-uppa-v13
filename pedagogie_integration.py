"""Injection ciblée du module pédagogique dans la source Streamlit historique."""
from __future__ import annotations

SENTINEL = "# --- pédagogie resources integration ---"


def patch_app_source(source: str) -> str:
    if SENTINEL in source:
        return source

    import_marker = "from io import BytesIO\n"
    import_block = '''from io import BytesIO\nfrom pedagogie_resources import (\n    init_pedagogy_schema, ensure_seance_resource_column,\n    render_teacher_resources, render_student_resources,\n)\nfrom pedagogie_seed import seed_official_resources\n'''
    if import_marker not in source:
        raise RuntimeError("Point d'injection imports pédagogie introuvable.")
    source = source.replace(import_marker, import_block, 1)

    init_marker = "\ninit_db()\n"
    init_block = '''\ninit_db()\n# --- pédagogie resources integration ---\ninit_pedagogy_schema(get_conn, USE_POSTGRES)\nensure_seance_resource_column(get_conn, USE_POSTGRES)\nseed_official_resources(get_conn, USE_POSTGRES)\n'''
    if init_marker not in source:
        raise RuntimeError("Point d'initialisation pédagogie introuvable.")
    source = source.replace(init_marker, init_block, 1)

    student_old = 'menu = st.sidebar.radio("Navigation", ["Accueil", "Portail étudiant"])'
    student_new = 'menu = st.sidebar.radio("Navigation", ["Accueil", "Portail étudiant", "Ressources pédagogiques"])'
    if student_old not in source:
        raise RuntimeError("Navigation étudiant introuvable.")
    source = source.replace(student_old, student_new, 1)

    teacher_old = '''["Accueil", "Tableau de bord", "Portail étudiant", "Étudiants", "Inscriptions en ligne",\n         "Présences", "Émargement QR / NFC", "Cahier de notes", "Performances", "Barèmes",\n         "Compétences", "Fiche étudiant", "Exports"]'''
    teacher_new = '''["Accueil", "Tableau de bord", "Ressources pédagogiques", "Portail étudiant", "Étudiants", "Inscriptions en ligne",\n         "Présences", "Émargement QR / NFC", "Cahier de notes", "Performances", "Barèmes",\n         "Compétences", "Fiche étudiant", "Exports"]'''
    if teacher_old not in source:
        raise RuntimeError("Navigation enseignant introuvable.")
    source = source.replace(teacher_old, teacher_new, 1)

    dispatch_marker = 'if menu == "Accueil":\n'
    dispatch = '''if menu == "Ressources pédagogiques":\n    if st.session_state.role == "Étudiant":\n        render_student_resources(st, get_conn=get_conn)\n    else:\n        render_teacher_resources(\n            st,\n            get_conn=get_conn,\n            use_postgres=USE_POSTGRES,\n            exec_sql=exec_sql,\n            activities=ACTIVITES,\n            admin_code_value=secret_value("PEDAGOGY_ADMIN_CODE", "").strip(),\n        )\nelif menu == "Accueil":\n'''
    if dispatch_marker not in source:
        raise RuntimeError("Dispatch principal introuvable.")
    source = source.replace(dispatch_marker, dispatch, 1)
    return source
