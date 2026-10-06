import unittest
from competition_access import allowed_swim_tabs, navigation_for_role


class CompetitionAccessTest(unittest.TestCase):
    def test_chrono_role_only_gets_timer(self):
        self.assertEqual(allowed_swim_tabs("Chronométreur étudiant"), ["⏱️ Chronométrage"])
        self.assertEqual(navigation_for_role("Chronométreur étudiant"), ["Accueil", "Compétition"])

    def test_manager_gets_full_swim_management(self):
        self.assertEqual(
            allowed_swim_tabs("Gestion compétition"),
            ["⏱️ Chronométrage", "👥 Équipes", "📊 Résultats", "🏅 Classements"],
        )
        self.assertEqual(navigation_for_role("Gestion compétition"), ["Accueil", "Compétition"])

    def test_teacher_keeps_full_competition(self):
        self.assertEqual(
            allowed_swim_tabs("Enseignant"),
            ["⏱️ Chronométrage", "👥 Équipes", "📊 Résultats", "🏅 Classements"],
        )


if __name__ == "__main__":
    unittest.main()
