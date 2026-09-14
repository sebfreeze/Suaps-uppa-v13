import importlib
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def load_feature():
    try:
        return importlib.import_module('qr_registration')
    except ModuleNotFoundError:
        pytest.fail("Le module qr_registration manque : la fonctionnalité QR n'est pas encore implémentée.")


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
    conn.execute("INSERT INTO offres(activite,intitule,capacite,public,ouverte,inscription_token) VALUES('Natation','Lundi 18h',2,'Étudiants',1,'tok-abc')")
    conn.commit()
    conn.close()


def test_qr_registration_records_student_when_credentials_and_capacity_are_valid(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'qr.sqlite'
    seed_db(db_path)

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '12345678', 'UET')

    assert result == 'ok'
    conn = open_db(db_path)
    row = conn.execute("SELECT modalite,statut FROM inscriptions").fetchone()
    conn.close()
    assert dict(row) == {'modalite': 'UET', 'statut': 'Inscrit'}


def test_qr_registration_refuses_when_course_is_full(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'full.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    conn.execute("UPDATE offres SET capacite=1 WHERE inscription_token='tok-abc'")
    conn.execute("INSERT INTO utilisateurs(profil,nom,prenom,email,identifiant,actif) VALUES('Étudiant','MARTIN','Léa','lea@etu.univ-pau.fr','87654321',1)")
    other_id = conn.execute("SELECT id FROM utilisateurs WHERE email='lea@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres WHERE inscription_token='tok-abc'").fetchone()['id']
    conn.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit','2026-09-14T10:00:00')", (other_id, offer_id, 'UECF'))
    conn.commit(); conn.close()

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '12345678', 'UET')

    assert result == 'full'
    conn = open_db(db_path)
    count = conn.execute("SELECT COUNT(*) AS n FROM inscriptions WHERE offre_id=? AND statut='Inscrit'", (offer_id,)).fetchone()['n']
    conn.close()
    assert count == 1


def test_qr_registration_returns_duplicate_without_creating_second_registration(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'duplicate.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    student_id = conn.execute("SELECT id FROM utilisateurs WHERE email='paul@etu.univ-pau.fr'").fetchone()['id']
    offer_id = conn.execute("SELECT id FROM offres WHERE inscription_token='tok-abc'").fetchone()['id']
    conn.execute("INSERT INTO inscriptions(utilisateur_id,offre_id,modalite,statut,date_inscription) VALUES(?,?,?,'Inscrit','2026-09-14T10:00:00')", (student_id, offer_id, 'UECF'))
    conn.commit(); conn.close()

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '12345678', 'UET')

    assert result == 'duplicate'
    conn = open_db(db_path)
    rows = conn.execute("SELECT modalite,statut FROM inscriptions WHERE utilisateur_id=? AND offre_id=?", (student_id, offer_id)).fetchall()
    conn.close()
    assert len(rows) == 1
    assert rows[0]['modalite'] == 'UECF'


def test_qr_registration_rejects_wrong_student_identifier(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'bad-ident.sqlite'
    seed_db(db_path)

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '00000000', 'UET')

    assert result == 'bad_credentials'
    conn = open_db(db_path)
    count = conn.execute("SELECT COUNT(*) AS n FROM inscriptions").fetchone()['n']
    conn.close()
    assert count == 0


def test_qr_registration_refuses_closed_course(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'closed.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    conn.execute("UPDATE offres SET ouverte=0 WHERE inscription_token='tok-abc'")
    conn.commit(); conn.close()

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '12345678', 'UET')

    assert result == 'closed'
    conn = open_db(db_path)
    count = conn.execute("SELECT COUNT(*) AS n FROM inscriptions").fetchone()['n']
    conn.close()
    assert count == 0


def test_registration_url_is_safe_and_uses_inscription_query_parameter():
    qr = load_feature()
    assert qr.registration_url('https://suaps.example/', 'abc def') == 'https://suaps.example/?inscription=abc%20def'


def test_new_registration_token_is_opaque_and_unique():
    qr = load_feature()
    first = qr.new_registration_token()
    second = qr.new_registration_token()
    assert first != second
    assert len(first) >= 24
    assert len(second) >= 24


def test_make_qr_png_returns_png_bytes():
    qr = load_feature()
    data = qr.make_qr_png('https://suaps.example/?inscription=abc')
    assert data.startswith(b'\x89PNG\r\n\x1a\n')
    assert len(data) > 100


def test_qr_registration_refuses_personnel_only_course(tmp_path):
    qr = load_feature()
    db_path = tmp_path / 'personnel.sqlite'
    seed_db(db_path)
    conn = open_db(db_path)
    conn.execute("UPDATE offres SET public='Personnel' WHERE inscription_token='tok-abc'")
    conn.commit(); conn.close()

    result = qr.register_student_from_qr(lambda: open_db(db_path), 'tok-abc', 'paul@etu.univ-pau.fr', '12345678', 'UET')

    assert result == 'forbidden'
    conn = open_db(db_path)
    count = conn.execute("SELECT COUNT(*) AS n FROM inscriptions").fetchone()['n']
    conn.close()
    assert count == 0
