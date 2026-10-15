"""Tests d'intégrité du lien tournoi/inscrits (sans Streamlit installé)."""
import sqlite3
import sys
import types
import unittest

sys.modules.setdefault("streamlit", types.ModuleType("streamlit"))
from tournoi_etudiant import _hash, _offers, _players, init_access


class TournamentAccessTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE offres_inscription(id INTEGER PRIMARY KEY, activite TEXT, intitule TEXT, groupe TEXT, jour_horaire TEXT);
            CREATE TABLE etudiants(id INTEGER PRIMARY KEY, nom TEXT, prenom TEXT, numero_etudiant TEXT, actif INTEGER);
            CREATE TABLE inscriptions(offre_id INTEGER, etudiant_id INTEGER, statut TEXT);
            INSERT INTO offres_inscription VALUES(1,'Rugby','Rugby jeudi','A','Jeudi');
            INSERT INTO offres_inscription VALUES(2,'Football','Foot jeudi','A','Jeudi');
            INSERT INTO etudiants VALUES(1,'Martin','Léa','100',1);
            INSERT INTO etudiants VALUES(2,'Durand','Hugo','101',1);
            INSERT INTO etudiants VALUES(3,'Ancien','Test','102',0);
            INSERT INTO inscriptions VALUES(1,1,'Inscrit');
            INSERT INTO inscriptions VALUES(1,2,'Annulé');
            INSERT INTO inscriptions VALUES(1,3,'Inscrit');
            INSERT INTO inscriptions VALUES(2,2,'Inscrit');
        """)

    def rows(self, sql, params=()):
        return [dict(r) for r in self.db.execute(sql, params).fetchall()]

    def exe(self, sql, params=()):
        self.db.execute(sql, params)
        self.db.commit()

    def test_liaison_creneau_activite(self):
        self.assertEqual([r["id"] for r in _offers(self.rows, "Rugby")], [1])

    def test_uniquement_inscrits_actifs_au_creneau(self):
        self.assertEqual([r["id"] for r in _players(self.rows, 1)], [1])

    def test_codes_uniques_non_stockes_en_clair(self):
        self.assertEqual(_hash(" abC "), _hash("ABC"))
        self.assertNotEqual(_hash("ABC"), "ABC")

    def test_table_configuration_unique_par_tournoi(self):
        init_access(self.exe)
        self.exe("INSERT INTO tournoi_acces_etudiant VALUES(?,?,?)", (7,1,_hash("CODE")))
        with self.assertRaises(sqlite3.IntegrityError):
            self.exe("INSERT INTO tournoi_acces_etudiant VALUES(?,?,?)", (7,2,_hash("CODE2")))


if __name__ == "__main__":
    unittest.main()
