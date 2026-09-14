import sqlite3

import qr_registration as registration


def open_db(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def seed_db(path):
    conn = open_db(path)
    conn.executescript('''
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
            capacite INTEGER DEFAULT 20,
            public TEXT DEFAULT 'Tous',
            ouverte INTEGER DEFAULT 1,
            inscription_token TEXT UNIQUE
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
    ''')
    conn.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Étudiant','DUPONT','Paul','paul@etu.univ-pau.fr','12345678',1)")
    conn.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Étudiant','MARTIN','Léa','lea@etu.univ-pau.fr','87654321',1)")
    conn.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Étudiant','DURAND','Marie','marie@etu.univ-pau.fr','11223344',0)")
    conn.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Personnel','ADMIN','Pierre','pierre@univ-pau.fr','P001',1)")
    conn.execute("INSERT INTO offres(activite,intitule,capacite,public,ouverte,inscription_token) VALUES('Natation','Lundi 18h',2,'Étudiants',1,'tok-abc')")
    conn.commit()
    conn.close()


def test_search_students_matches_name_email_or_student_number_and_only_active_students(tmp_path):
    db_path = tmp_path / 'search.sqlite'
    seed_db(db_path)
    factory = lambda: open_db(db_path)

    by_name = registration.search_students(factory, 'dup')
    by_email = registration.search_students(factory, 'lea@etu')
    by_number = registration.search_students(factory, '12345678')
    inactive = registration.search_students(factory, 'durand')
    personnel = registration.search_students(factory, 'pierre')

    assert [(r['nom'], r['prenom']) for r in by_name] == [('DUPONT', 'Paul')]
    assert [(r['nom'], r['prenom']) for r in by_email] == [('MARTIN', 'Léa')]
    assert [(r['nom'], r['prenom']) for r in by_number] == [('DUPONT', 'Paul')]
    assert inactive == []
    assert personnel == []


def test_manual_registration_adds_selected_student(tmp_path):
    db_path = tmp_path / 'manual.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    student_id = conn.execute("SELECT id FROM utilisateurs WHERE email='paul@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres").fetchone()['id']
    conn.close()

    result = registration.register_student_manually(lambda: open_db(db_path), offer_id, student_id, 'UET')

    assert result == 'ok'
    conn = open_db(db_path)
    row = conn.execute("SELECT utilisateur_id, offre_id, modalite, statut FROM inscriptions").fetchone()
    conn.close()
    assert dict(row) == {'utilisateur_id': student_id, 'offre_id': offer_id, 'modalite': 'UET', 'statut': 'Inscrit'}


def test_manual_registration_blocks_duplicate(tmp_path):
    db_path = tmp_path / 'duplicate.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    student_id = conn.execute("SELECT id FROM utilisateurs WHERE email='paul@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres").fetchone()['id']
    conn.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit','2026-09-14T10:00:00')", (student_id, offer_id, 'UECF'))
    conn.commit(); conn.close()

    result = registration.register_student_manually(lambda: open_db(db_path), offer_id, student_id, 'UET')

    assert result == 'duplicate'
    conn = open_db(db_path)
    rows = conn.execute("SELECT modalite FROM inscriptions WHERE utilisateur_id=? AND offre_id=?", (student_id, offer_id)).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]['modalite'] == 'UECF'


def test_manual_registration_respects_capacity(tmp_path):
    db_path = tmp_path / 'full.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    conn.execute("UPDATE offres SET capacite=1")
    paul_id = conn.execute("SELECT id FROM utilisateurs WHERE email='paul@etu.univ-pau.fr'").fetchone()['id']
    lea_id = conn.execute("SELECT id FROM utilisateurs WHERE email='lea@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres").fetchone()['id']
    conn.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit','2026-09-14T10:00:00')", (lea_id, offer_id, 'UET'))
    conn.commit(); conn.close()

    result = registration.register_student_manually(lambda: open_db(db_path), offer_id, paul_id, 'UET')

    assert result == 'full'


def test_manual_registration_rejects_invalid_modality_and_unknown_student(tmp_path):
    db_path = tmp_path / 'invalid.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    student_id = conn.execute("SELECT id FROM utilisateurs WHERE email='paul@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres").fetchone()['id']
    conn.close()

    assert registration.register_student_manually(lambda: open_db(db_path), offer_id, student_id, 'ADMIN') == 'invalid_modality'
    assert registration.register_student_manually(lambda: open_db(db_path), offer_id, 999999, 'UET') == 'unknown_student'
