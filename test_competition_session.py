import unittest
from competition_session import issue_role_token, validate_role_token


class CompetitionSessionTest(unittest.TestCase):
    def test_valid_token_restores_role_for_four_hours(self):
        token = issue_role_token("Enseignant", "secret", now=1000)
        self.assertEqual(
            validate_role_token(token, {"Enseignant": "secret"}, now=1000 + 3 * 60 * 60),
            "Enseignant",
        )

    def test_expired_token_is_rejected(self):
        token = issue_role_token("Enseignant", "secret", now=1000)
        self.assertIsNone(
            validate_role_token(token, {"Enseignant": "secret"}, now=1000 + 4 * 60 * 60),
        )

    def test_wrong_secret_is_rejected(self):
        token = issue_role_token("Gestion compétition", "secret", now=1000)
        self.assertIsNone(
            validate_role_token(token, {"Gestion compétition": "other"}, now=1100),
        )


if __name__ == "__main__":
    unittest.main()
