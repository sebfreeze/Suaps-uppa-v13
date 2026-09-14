import json
import sqlite3
from pathlib import Path

import startup_bulk_enrollment


def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def seed(path):
    conn = open_db(path)
    conn.executescript(
        '''
        CREATE TABLE utilisateurs(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profil TEXT NOT NULL,
            nom TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            identifiant TEXT,
            actif INTEGER DEFAULT 1
        );
        CREATE TABLE offres(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            activite TEXT NOT NULL,
            intitule TEXT NOT NULL,
            jour_horaire TEXT,
            capacite INTEGER DEFAULT 20
        );
        CREATE TABLE offre_semestres(
            offre_id INTEGER NOT NULL,
            semestre TEXT NOT NULL,
            PRIMARY KEY(offre_id, semestre)
        );
        CREATE TABLE inscriptions(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            utilisateur_id INTEGER NOT NULL,
            offre_id INTEGER NOT NULL,
            modalite TEXT NOT NULL,
            statut TEXT DEFAULT 'Inscrit',
            date_inscription TEXT NOT NULL,
            UNIQUE(utilisateur_id, offre_id)
        );
        '''
    )
    conn.execute(
        "INSERT INTO offres(activite,intitule,jour_horaire,capacite) VALUES(?,?,?,?)",
        ("Course à pied", "Course à pied", "Lundi 19h15 à 20h45", 30),
    )
    offer_id = conn.execute("SELECT id FROM offres").fetchone()["id"]
    conn.execute(
        "INSERT INTO offre_semestres(offre_id,semestre) VALUES(?,?)",
        (offer_id, "Semestre 1 — 2026/2027"),
    )
    for ident, nom, prenom in [
        ("100001", "ALPHA", "Alice"),
        ("100002", "BETA", "Bastien"),
    ]:
        conn.execute(
            "INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Étudiant',?,?,?,?,1)",
            (nom, prenom, f"{ident}@example.invalid", ident),
        )
    conn.commit()
    conn.close()


def payload():
    return {
        "activity": "Course à pied",
        "semester": "Semestre 1 — 2026/2027",
        "schedule_terms": ["lundi", "19h15", "20h45"],
        "students": [
            {"identifiant": "100001", "modalite": "UECF"},
            {"identifiant": "100002", "modalite": "UET"},
        ],
    }


def test_startup_runner_executes_private_payload_without_streamlit_session(tmp_path):
    path = tmp_path / "startup.sqlite"
    seed(path)
    logs = []

    result = startup_bulk_enrollment.run_startup_bulk_enrollment(
        raw_payload=json.dumps(payload()),
        db_factory=lambda: open_db(path),
        use_postgres=False,
        logger=logs.append,
    )

    assert result["status"] == "ok"
    assert any("status=ok" in line and "enrolled=2" in line for line in logs)
    conn = open_db(path)
    assert conn.execute("SELECT COUNT(*) n FROM inscriptions WHERE statut='Inscrit'").fetchone()["n"] == 2
    conn.close()


def test_startup_runner_noops_when_private_payload_is_absent():
    logs = []
    result = startup_bulk_enrollment.run_startup_bulk_enrollment(
        raw_payload="",
        db_factory=lambda: None,
        use_postgres=False,
        logger=logs.append,
    )
    assert result is None
    assert logs == []


def test_startup_bootstrap_invokes_runner_and_preserves_security_bootstrap():
    source = Path("startup_bootstrap/sitecustomize.py").read_text(encoding="utf-8")
    assert "security_bootstrap" in source
    assert "startup_bulk_enrollment" in source
    assert "run_from_environment" in source
    assert "SUAPS_BULK_ENROLL_JSON" not in source
