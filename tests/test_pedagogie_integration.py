from pathlib import Path

from pedagogie_integration import SENTINEL, patch_app_source


SAMPLE = '''from io import BytesIO


def init_db():
    pass


def get_conn():
    pass


def exec_sql(sql, params=()):
    pass


def secret_value(name, default=""):
    return default

USE_POSTGRES = False
ACTIVITES = ["Natation"]
init_db()

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
    pass
elif menu == "Tableau de bord":
    pass
'''


def test_patch_adds_import_initialization_and_navigation():
    patched = patch_app_source(SAMPLE)
    assert SENTINEL in patched
    assert "from pedagogie_resources import (" in patched
    assert "from pedagogie_seed import seed_official_resources" in patched
    assert "init_pedagogy_schema(get_conn, USE_POSTGRES)" in patched
    assert "ensure_seance_resource_column(get_conn, USE_POSTGRES)" in patched
    assert "seed_official_resources(get_conn, USE_POSTGRES)" in patched
    assert '["Accueil", "Portail étudiant", "Ressources pédagogiques"]' in patched
    assert '["Accueil", "Tableau de bord", "Ressources pédagogiques", "Portail étudiant"' in patched
    assert 'if menu == "Ressources pédagogiques":' in patched
    assert 'elif menu == "Accueil":' in patched
    assert "render_teacher_resources(" in patched
    assert "render_student_resources(st, get_conn=get_conn)" in patched


def test_patch_is_idempotent():
    patched = patch_app_source(SAMPLE)
    assert patch_app_source(patched) == patched


def test_render_entrypoint_applies_pedagogy_patch():
    entry = Path("v14_complete.py").read_text(encoding="utf-8")
    assert "from pedagogie_integration import patch_app_source as _patch_pedagogy_source" in entry
    assert "source = _patch_pedagogy_source(source)" in entry
