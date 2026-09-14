import sqlite3

import bulk_enrollment


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
        ("100001", "DUPONT", "Lola"),
        ("100002", "ARBIN", "Ismael"),
        ("100003", "MAILLE", "Matthis"),
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
            {"identifiant": "100003", "modalite": "UET"},
        ],
    }


def test_bulk_enrollment_is_all_or_nothing_and_sets_modalities(tmp_path):
    path = tmp_path / "bulk.sqlite"
    seed(path)
    factory = lambda: open_db(path)

    result = bulk_enrollment.apply_bulk_enrollment(factory, payload())

    assert result["status"] == "ok"
    conn = open_db(path)
    rows = conn.execute(
        "SELECT u.identifiant,i.modalite,i.statut FROM inscriptions i "
        "JOIN utilisateurs u ON u.id=i.utilisateur_id ORDER BY u.identifiant"
    ).fetchall()
    conn.close()
    assert [(r["identifiant"], r["modalite"], r["statut"]) for r in rows] == [
        ("100001", "UECF", "Inscrit"),
        ("100002", "UET", "Inscrit"),
        ("100003", "UET", "Inscrit"),
    ]

    broken = payload()
    broken["students"].append({"identifiant": "999999", "modalite": "UECF"})
    result = bulk_enrollment.apply_bulk_enrollment(factory, broken)
    assert result["status"] == "missing_students"

    conn = open_db(path)
    assert conn.execute("SELECT COUNT(*) n FROM inscriptions").fetchone()["n"] == 3
    conn.close()
