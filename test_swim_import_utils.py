import unittest
from swim_import_utils import assign_series_lines

class SwimImportUtilsTest(unittest.TestCase):
    def test_higher_series_number_means_stronger_level(self):
        rows = [
            {"team":"Faible A","level":1},
            {"team":"Faible B","level":1},
            {"team":"Moyen A","level":2},
            {"team":"Fort A","level":3},
            {"team":"Fort B","level":3},
            {"team":"Fort C","level":3},
        ]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}
        self.assertEqual(by_team["Faible A"]["series"], 1)
        self.assertEqual(by_team["Fort C"]["series"], 2)
        self.assertLess(by_team["Faible A"]["series"], by_team["Fort C"]["series"])
        self.assertTrue(all(1 <= r["line"] <= 5 for r in out))

    def test_preserves_manual_series_and_line(self):
        rows = [
            {"team":"Equipe A","level":2,"series":4,"line":3},
            {"team":"Equipe B","level":1},
        ]
        out = assign_series_lines(rows, max_lines=5)
        by_team = {r["team"]: r for r in out}
        self.assertEqual((by_team["Equipe A"]["series"], by_team["Equipe A"]["line"]), (4,3))

if __name__ == "__main__":
    unittest.main()
