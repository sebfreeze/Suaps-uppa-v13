import importlib
import sqlite3


def _load_service():
    try:
        return importlib.import_module("presence_note_service")
    except ModuleNotFoundError:
        return None


def _schema(conn):
    conn.executescript("""
        CREATE TABLE presences(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            seance_id INTEGER NOT NULL,
            etudiant_id INTEGER NOT NULL,
            statut TEXT NOT NULL DEFAULT 'Présent',
            commentaire TEXT,
            UNIQUE(seance_id, etudiant_id)
        );
        CREATE TABLE evaluations(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            etudiant_id INTEGER NOT NULL,
            activite TEXT NOT NULL,
            intitule TEXT NOT NULL,
            date_eval TEXT NOT NULL,
            note REAL,
            bareme REAL DEFAULT 20,
            coefficient REAL DEFAULT 1,
            commentaire TEXT
        );
    """)


def test_service_module_exists():
    service = _load_service()
    assert service is not None, "presence_note_service.py doit exister"


def test_evaluation_title_uses_theme_or_date():
    service = _load_service()
    assert service is not None, "service manquant"
    assert service.evaluation_title("  100 m nage libre  ", "2026-09-15") == "100 m nage libre"
    assert service.evaluation_title("", "2026-09-15") == "Évaluation du 2026-09-15"


def test_inject_combined_navigation_only_for_teacher_menu():
    service = _load_service()
    assert service is not None, "service manquant"
    teacher = ["Accueil", "Présences", "Cahier de notes", "Exports"]
    student = ["Accueil", "Portail étudiant"]
    assert service.inject_combined_navigation(teacher) == [
        "Accueil", "✅ Présence / Note évaluation", "Présences", "Cahier de notes", "Exports"
    ]
    assert service.inject_combined_navigation(student) == student


def test_save_rows_upserts_presence_and_creates_note():
    service = _load_service()
    assert service is not None, "service manquant"
    conn = sqlite3.connect(":memory:")
    _schema(conn)

    service.save_rows(
        conn,
        session_id=7,
        activity="Natation",
        date_eval="2026-09-15",
        title="100 m nage libre",
        bareme=20,
        coefficient=1,
        rows=[{
            "student_id": 3,
            "status": "Présent",
            "note": 14.5,
            "observation": "Bonne gestion de course",
        }],
    )

    presence = conn.execute(
        "SELECT statut, commentaire FROM presences WHERE seance_id=7 AND etudiant_id=3"
    ).fetchone()
    assert presence == ("Présent", "Bonne gestion de course")

    evaluation = conn.execute(
        "SELECT note, bareme, coefficient, commentaire FROM evaluations WHERE etudiant_id=3"
    ).fetchone()
    assert evaluation == (14.5, 20.0, 1.0, "Bonne gestion de course")


def test_resave_updates_same_evaluation_instead_of_duplicating():
    service = _load_service()
    assert service is not None, "service manquant"
    conn = sqlite3.connect(":memory:")
    _schema(conn)

    common = dict(
        conn=conn,
        session_id=7,
        activity="Rugby",
        date_eval="2026-09-15",
        title="Jeu collectif",
        bareme=20,
        coefficient=1,
    )
    service.save_rows(rows=[{
        "student_id": 11,
        "status": "Présent",
        "note": 12.0,
        "observation": "Premier passage",
    }], **common)
    service.save_rows(rows=[{
        "student_id": 11,
        "status": "Justifié",
        "note": 15.0,
        "observation": "Note corrigée",
    }], **common)

    count = conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0]
    assert count == 1
    note, comment = conn.execute(
        "SELECT note, commentaire FROM evaluations WHERE etudiant_id=11"
    ).fetchone()
    assert (note, comment) == (15.0, "Note corrigée")
    status = conn.execute(
        "SELECT statut FROM presences WHERE seance_id=7 AND etudiant_id=11"
    ).fetchone()[0]
    assert status == "Justifié"


def test_blank_note_saves_presence_without_creating_evaluation():
    service = _load_service()
    assert service is not None, "service manquant"
    conn = sqlite3.connect(":memory:")
    _schema(conn)

    service.save_rows(
        conn,
        session_id=5,
        activity="Surf",
        date_eval="2026-09-15",
        title="Take-off",
        bareme=20,
        coefficient=1,
        rows=[{
            "student_id": 8,
            "status": "Absent",
            "note": None,
            "observation": "Absent ce jour",
        }],
    )

    assert conn.execute("SELECT COUNT(*) FROM presences").fetchone()[0] == 1
    assert conn.execute("SELECT COUNT(*) FROM evaluations").fetchone()[0] == 0
