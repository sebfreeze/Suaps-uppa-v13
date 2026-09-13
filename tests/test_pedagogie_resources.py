import sqlite3
from pathlib import Path

import pytest

from pedagogie_resources import (
    can_edit_resource,
    create_resource,
    create_seance_from_resource,
    delete_resource,
    duplicate_payload,
    ensure_seance_resource_column,
    get_resource,
    get_resource_file,
    hash_edit_code,
    init_pedagogy_schema,
    list_resources,
    resource_card_summary,
    update_resource,
    validate_external_url,
    validate_upload,
    verify_edit_code,
)


def sqlite_factory(tmp_path):
    db_path = tmp_path / "pedagogie.sqlite"

    def get_conn():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        return conn

    return get_conn


def test_edit_code_is_salted_and_verifiable():
    a = hash_edit_code("mon-code-123")
    b = hash_edit_code("mon-code-123")
    assert a != b
    assert verify_edit_code("mon-code-123", a)
    assert not verify_edit_code("mauvais", a)


def test_edit_code_requires_six_characters():
    with pytest.raises(ValueError, match="6 caractères"):
        hash_edit_code("123")


def test_external_url_only_accepts_http_https():
    assert validate_external_url("") == ""
    assert validate_external_url("https://youtu.be/abc") == "https://youtu.be/abc"
    with pytest.raises(ValueError):
        validate_external_url("javascript:alert(1)")
    with pytest.raises(ValueError):
        validate_external_url("https:///sans-hote")


@pytest.mark.parametrize(
    ("name", "mime"),
    [
        ("fiche.pdf", "application/pdf"),
        ("fiche.docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
        ("slides.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation"),
        ("notes.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("schema.png", "image/png"),
        ("photo.jpg", "image/jpeg"),
        ("photo.jpeg", "image/jpeg"),
    ],
)
def test_upload_accepts_whitelist(name, mime):
    safe_name, safe_mime, size = validate_upload(name, mime, b"demo")
    assert safe_name == Path(name).name
    assert safe_mime == mime
    assert size == 4


def test_upload_rejects_more_than_5mb():
    with pytest.raises(ValueError, match="5 Mo"):
        validate_upload("fiche.pdf", "application/pdf", b"x" * (5 * 1024 * 1024 + 1))


def test_upload_rejects_bad_extension_even_with_good_mime():
    with pytest.raises(ValueError, match="non autorisé"):
        validate_upload("payload.exe", "application/pdf", b"demo")


def test_upload_rejects_mime_mismatch():
    with pytest.raises(ValueError, match="MIME"):
        validate_upload("fiche.pdf", "image/png", b"demo")


def test_schema_crud_filters_and_blob_roundtrip(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    init_pedagogy_schema(get_conn, False)
    blob = b"%PDF-1.4\nSUAPS\n"
    assert create_resource(
        get_conn,
        activity="Natation",
        resource_type="Document",
        title="Fiche crawl",
        description="Progression crawl",
        author="Sébastien",
        author_code="secret1",
        visible_students=True,
        external_url="https://example.org/video",
        filename="crawl.pdf",
        mime_type="application/pdf",
        file_data=blob,
    )
    resources = list_resources(get_conn)
    assert len(resources) == 1
    assert "fichier_data" not in resources[0]
    assert resources[0]["titre"] == "Fiche crawl"
    resource_id = resources[0]["id"]
    assert get_resource_file(get_conn, resource_id) == ("crawl.pdf", "application/pdf", blob)

    assert len(list_resources(get_conn, student_only=True)) == 1
    assert len(list_resources(get_conn, activity="Rugby")) == 0
    assert len(list_resources(get_conn, activity="Natation", resource_type="Document", author="Sébastien", query="crawl")) == 1

    update_resource(
        get_conn,
        resource_id,
        activity="Natation",
        resource_type="Document",
        title="Fiche crawl V2",
        description="Mise à jour",
        content={"niveau": "tous"},
        visible_students=False,
        external_url="https://example.org/v2",
    )
    updated = get_resource(get_conn, resource_id)
    assert updated["titre"] == "Fiche crawl V2"
    assert updated["contenu"] == {"niveau": "tous"}
    assert updated["visible_etudiants"] == 0
    assert get_resource_file(get_conn, resource_id)[2] == blob
    assert list_resources(get_conn, student_only=True) == []

    delete_resource(get_conn, resource_id)
    assert get_resource(get_conn, resource_id) is None


def test_resource_authorization_rules():
    stored = hash_edit_code("auteur1")
    teacher_resource = {"auteur": "Hervé", "auteur_code_hash": stored, "officiel_suaps": 0}
    official_resource = {"auteur": "SUAPS UPPA", "auteur_code_hash": None, "officiel_suaps": 1}

    assert can_edit_resource(teacher_resource, "hervé", "auteur1", "", "")
    assert not can_edit_resource(teacher_resource, "Hervé", "mauvais", "", "")
    assert not can_edit_resource(teacher_resource, "Raphaël", "auteur1", "", "")
    assert not can_edit_resource(official_resource, "SUAPS UPPA", "", "", "")
    assert can_edit_resource(official_resource, "", "", "admin-secret", "admin-secret")
    assert not can_edit_resource(official_resource, "", "", "admin-secret", "")


def test_ensure_seance_resource_column_is_idempotent(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    conn = get_conn()
    conn.execute("CREATE TABLE seances(id INTEGER PRIMARY KEY, activite TEXT, date_seance TEXT, groupe TEXT, theme TEXT)")
    conn.commit()
    conn.close()
    ensure_seance_resource_column(get_conn, False)
    ensure_seance_resource_column(get_conn, False)
    conn = get_conn()
    columns = {row[1] for row in conn.execute("PRAGMA table_info(seances)").fetchall()}
    conn.close()
    assert "ressource_id" in columns


def test_create_seance_from_resource_links_source(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    conn = get_conn()
    conn.execute(
        "CREATE TABLE seances(id INTEGER PRIMARY KEY AUTOINCREMENT, activite TEXT, date_seance TEXT, groupe TEXT, theme TEXT, checkin_open INTEGER DEFAULT 0, ressource_id INTEGER)"
    )
    conn.commit()
    conn.close()

    def exec_sql(sql, params=()):
        conn = get_conn()
        conn.execute(sql, params)
        conn.commit()
        conn.close()

    create_seance_from_resource(
        exec_sql,
        {"id": 7, "activite": "Natation", "titre": "Crawl : coordination complète"},
        "2026-09-21",
        "Groupe A",
    )
    conn = get_conn()
    row = conn.execute("SELECT * FROM seances").fetchone()
    conn.close()
    assert row["activite"] == "Natation"
    assert row["date_seance"] == "2026-09-21"
    assert row["groupe"] == "Groupe A"
    assert row["theme"] == "Crawl : coordination complète"
    assert row["ressource_id"] == 7
    assert row["checkin_open"] == 0


def test_duplicate_payload_never_keeps_official_or_binary_flags():
    resource = {
        "id": 9,
        "seed_key": "suaps:natation:01",
        "activite": "Natation",
        "type_ressource": "Séance",
        "titre": "Diagnostic",
        "description": "Test",
        "contenu": {"objectif": "Observer"},
        "auteur": "SUAPS UPPA",
        "officiel_suaps": 1,
        "visible_etudiants": 1,
        "nom_fichier": "officiel.pdf",
    }
    payload = duplicate_payload(resource, "Hervé")
    assert payload["titre"] == "Copie — Diagnostic"
    assert payload["auteur"] == "Hervé"
    assert payload["officiel_suaps"] == 0
    assert payload["visible_etudiants"] == 0
    assert "seed_key" not in payload
    assert "fichier_data" not in payload
    assert "nom_fichier" not in payload


def test_resource_card_summary():
    summary = resource_card_summary(
        {
            "titre": "Séance 1",
            "activite": "Surf",
            "type_ressource": "Séance",
            "auteur": "SUAPS UPPA",
            "officiel_suaps": 1,
            "visible_etudiants": 0,
        }
    )
    assert summary == {
        "title": "Séance 1",
        "subtitle": "Surf • Séance",
        "author": "SUAPS UPPA",
        "official": True,
        "student_visible": False,
    }


def test_combined_filters_and_student_visibility(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    init_pedagogy_schema(get_conn, False)
    fixtures = [
        ("Natation", "Document", "Respiration crawl", "Hervé", True, "code-h1"),
        ("Natation", "Séance", "Virages", "Hervé", False, "code-h2"),
        ("Rugby", "Document", "Défense collective", "Raphaël", True, "code-r1"),
        ("Surf", "Vidéo / lien", "Take-off", "Ludovic", True, "code-l1"),
    ]
    for act, typ, title, author, visible, code in fixtures:
        create_resource(
            get_conn,
            activity=act,
            resource_type=typ,
            title=title,
            author=author,
            author_code=code,
            visible_students=visible,
            external_url="https://example.org" if typ == "Vidéo / lien" else "",
        )
    rows = list_resources(
        get_conn,
        student_only=True,
        activity="Natation",
        resource_type="Document",
        author="Hervé",
        query="respiration",
    )
    assert [r["titre"] for r in rows] == ["Respiration crawl"]


def test_binary_list_never_exposes_blob(tmp_path):
    get_conn = sqlite_factory(tmp_path)
    init_pedagogy_schema(get_conn, False)
    blob = b"%PDF" + b"x" * 4096
    create_resource(
        get_conn,
        activity="Rugby",
        resource_type="Document",
        title="Fiche",
        author="Hervé",
        author_code="secret2",
        filename="fiche.pdf",
        mime_type="application/pdf",
        file_data=blob,
    )
    row = list_resources(get_conn)[0]
    assert "fichier_data" not in row
    assert get_resource_file(get_conn, row["id"])[2] == blob
