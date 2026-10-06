import unittest
from swim_import_utils import assign_series_lines, normalize_swim_status, validate_swimmer_entries

class SwimImportUtilsTest(unittest.TestCase):
    def test_last_series_gets_strongest_and_partial_first_series_is_centered(self):
        rows = [
            {"team":"T1","level":1},
            {"team":"T2","level":2},
            {"team":"T3","level":3},
            {"team":"T4","level":4},
            {"team":"T5","level":5},
            {"team":"T6","level":6},
            {"team":"T7","level":7},
        ]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}

        # Série 1 incomplète : les deux plus faibles, centrés lignes 3 puis 2.
        self.assertEqual((by_team["T2"]["series"], by_team["T2"]["line"]), (1, 3))
        self.assertEqual((by_team["T1"]["series"], by_team["T1"]["line"]), (1, 2))

        # Série 2 complète : les cinq plus forts, meilleur en ligne 3.
        self.assertEqual((by_team["T7"]["series"], by_team["T7"]["line"]), (2, 3))
        self.assertEqual((by_team["T6"]["series"], by_team["T6"]["line"]), (2, 2))
        self.assertEqual((by_team["T5"]["series"], by_team["T5"]["line"]), (2, 4))
        self.assertEqual((by_team["T4"]["series"], by_team["T4"]["line"]), (2, 1))
        self.assertEqual((by_team["T3"]["series"], by_team["T3"]["line"]), (2, 5))

    def test_twelve_teams_leave_two_weakest_in_series_one(self):
        rows = [{"team": f"T{i}", "level": i} for i in range(1, 13)]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}
        self.assertEqual((by_team["T12"]["series"], by_team["T12"]["line"]), (3, 3))
        self.assertEqual((by_team["T8"]["series"], by_team["T8"]["line"]), (3, 5))
        self.assertEqual((by_team["T7"]["series"], by_team["T7"]["line"]), (2, 3))
        self.assertEqual((by_team["T3"]["series"], by_team["T3"]["line"]), (2, 5))
        self.assertEqual((by_team["T2"]["series"], by_team["T2"]["line"]), (1, 3))
        self.assertEqual((by_team["T1"]["series"], by_team["T1"]["line"]), (1, 2))

    def test_preserves_manual_series_and_line(self):
        rows = [
            {"team":"Equipe A","level":2,"series":4,"line":3},
            {"team":"Equipe B","level":1},
        ]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}
        self.assertEqual((by_team["Equipe A"]["series"], by_team["Equipe A"]["line"]), (4,3))

    def test_preferred_lanes_are_applied_within_series(self):
        rows = [
            {"team":"UPPA 1","level":2,"preferred_line":3},
            {"team":"Toulouse 1","level":2,"preferred_line":2},
            {"team":"Bordeaux 1","level":2,"preferred_line":4},
            {"team":"Autre A","level":1},
            {"team":"Autre B","level":1},
        ]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}
        self.assertEqual(by_team["UPPA 1"]["line"], 3)
        self.assertEqual(by_team["Toulouse 1"]["line"], 2)
        self.assertEqual(by_team["Bordeaux 1"]["line"], 4)

    def test_swimmer_status_aliases(self):
        self.assertEqual(normalize_swim_status("titulaire"), "Titulaire")
        self.assertEqual(normalize_swim_status("R"), "Remplaçant")
        self.assertEqual(normalize_swim_status("x", bonus=True), "Engagé")
        self.assertIsNone(normalize_swim_status(""))

    def test_swimmer_limits_allow_incomplete_team(self):
        entries = [
            {"swimmer": f"N{i}", "code": "C1", "status": "Titulaire"}
            for i in range(8)
        ]
        entries.append({"swimmer": "R1", "code": "C1", "status": "Remplaçant"})
        self.assertEqual(validate_swimmer_entries(entries), [])

    def test_swimmer_limits_reject_ninth_holder(self):
        entries = [
            {"swimmer": f"N{i}", "code": "C3", "status": "Titulaire"}
            for i in range(9)
        ]
        self.assertTrue(validate_swimmer_entries(entries))

    def test_bonus_accepts_twelve_swimmers(self):
        entries = [
            {"swimmer": f"N{i}", "code": "BONUS", "status": "Engagé"}
            for i in range(12)
        ]
        self.assertEqual(validate_swimmer_entries(entries), [])

    def test_c2_stroke_limits_two_holders(self):
        ok = [
            {"swimmer": "A", "code": "C2-PAP", "status": "Titulaire"},
            {"swimmer": "B", "code": "C2-PAP", "status": "Titulaire"},
        ]
        self.assertEqual(validate_swimmer_entries(ok), [])
        too_many = ok + [{"swimmer": "C", "code": "C2-PAP", "status": "Titulaire"}]
        self.assertIn("C2 Papillon : maximum 2 titulaires", validate_swimmer_entries(too_many))


    unittest.main()