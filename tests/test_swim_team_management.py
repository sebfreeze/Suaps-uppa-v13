"""Tests métier des opérations d'édition/suppression d'équipe de natation."""
import sqlite3
import unittest

from swim_team_management import save_team_changes, delete_swim_team


class SwimTeamManagementTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE natation_equipes (
                id INTEGER PRIMARY KEY, competition_id INTEGER, nom TEXT, universite TEXT,
                categorie TEXT, niveau TEXT, serie INTEGER, ligne INTEGER,
                placement_verrouille INTEGER,
                UNIQUE(competition_id,nom,categorie)
            );
            CREATE TABLE natation_nageurs (
                id INTEGER PRIMARY KEY, equipe_id INTEGER, nom TEXT, prenom TEXT
            );
            CREATE TABLE natation_engagements (
                id INTEGER PRIMARY KEY, nageur_id INTEGER, code_epreuve TEXT, statut TEXT
            );
            CREATE TABLE natation_resultats (
                id INTEGER PRIMARY KEY, competition_id INTEGER, equipe_id INTEGER,
                epreuve_id INTEGER, temps_final REAL
            );
            CREATE TABLE natation_splits (
                id INTEGER PRIMARY KEY, resultat_id INTEGER, numero INTEGER,
                temps_cumule REAL, temps_split REAL
            );
            INSERT INTO natation_equipes VALUES
                (1,1,'UPPA A','UPPA','Mixte','1',1,3,1),
                (2,1,'UPPA B','UPPA','Mixte','2',1,2,1),
                (3,2,'Autre','Lyon','Mixte','1',1,3,1);
            INSERT INTO natation_nageurs VALUES (21,1,'Martin','Léa'),(22,2,'Dupont','Paul');
            INSERT INTO natation_engagements VALUES (31,21,'C1','Titulaire'),(32,22,'C1','Titulaire');
            INSERT INTO natation_resultats VALUES (41,1,1,2,153.8),(42,1,2,2,155.4);
            INSERT INTO natation_splits VALUES (51,41,1,20.1,20.1),(52,42,1,21.0,21.0);
        """)
        self.reflows = []

    def tearDown(self):
        self.db.close()

    def rows(self, sql, params=()):
        return [dict(r) for r in self.db.execute(sql, params).fetchall()]

    def exe(self, sql, params=()):
        self.db.execute(sql, params)
        self.db.commit()

    def reflow(self, rows, exe, comp_id, category, max_lines, unlock_all=False):
        self.reflows.append((comp_id, category, max_lines, unlock_all))

    def team(self):
        return self.rows("SELECT * FROM natation_equipes WHERE id=1")[0]

    def changes(self, **overrides):
        data = dict(nom="UPPA A+", universite="UPPA", categorie="Mixte",
                    niveau=2, manual=True, serie=2, ligne=3)
        data.update(overrides)
        return save_team_changes(
            self.rows, self.exe, 1, self.team(), reflow=self.reflow, **data
        )

    def test_edit_preserves_swimmers_engagements_and_times(self):
        self.assertIsNone(self.changes())
        self.assertEqual(self.team()["nom"], "UPPA A+")
        self.assertEqual(self.team()["ligne"], 3)
        self.assertEqual(self.rows("SELECT id FROM natation_nageurs WHERE equipe_id=1"), [{"id": 21}])
        self.assertEqual(self.rows("SELECT temps_final FROM natation_resultats WHERE equipe_id=1"), [{"temps_final": 153.8}])
        self.assertEqual(self.rows("SELECT temps_split FROM natation_splits WHERE resultat_id=41"), [{"temps_split": 20.1}])

    def test_duplicate_and_occupied_slot_rejected(self):
        self.assertIn("déjà ce nom", self.changes(nom="uppa b"))
        self.assertEqual(self.team()["nom"], "UPPA A")
        self.assertIn("déjà occupée", self.changes(serie=1, ligne=2))
        self.assertEqual(self.team()["nom"], "UPPA A")

    def test_auto_reflow_on_category_change(self):
        self.assertIsNone(self.changes(categorie="Féminin", manual=False))
        self.assertIsNone(self.team()["ligne"])
        self.assertEqual(
            self.reflows,
            [(1, "Mixte", 5, False), (1, "Féminin", 5, False)]
        )

    def test_delete_cascades_only_selected_team(self):
        delete_swim_team(self.rows, self.exe, 1, self.team(), self.reflow)
        self.assertEqual(self.rows("SELECT * FROM natation_equipes WHERE id=1"), [])
        self.assertEqual(self.rows("SELECT * FROM natation_nageurs WHERE id=21"), [])
        self.assertEqual(self.rows("SELECT * FROM natation_engagements WHERE id=31"), [])
        self.assertEqual(self.rows("SELECT * FROM natation_resultats WHERE id=41"), [])
        self.assertEqual(self.rows("SELECT * FROM natation_splits WHERE id=51"), [])
        self.assertEqual(len(self.rows("SELECT * FROM natation_equipes WHERE id IN (2,3)")), 2)
        self.assertEqual(self.rows("SELECT id FROM natation_resultats WHERE id=42"), [{"id": 42}])
        self.assertEqual(self.reflows, [(1, "Mixte", 5, False)])


if __name__ == "__main__":
    unittest.main()
