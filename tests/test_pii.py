import unittest

from patet.pii import classify, classify_columns, worst


class Pii(unittest.TestCase):
    def test_grades(self):
        cases = {
            "password_hash": "critical", "stripe_secret": "critical", "card_number": "critical",
            "passport_number": "high", "date_of_birth": "high", "medical_notes": "high",
            "email": "medium", "contact_email": "medium", "phone": "medium", "street_address": "medium",
            "latitude": "medium", "ip_address": "medium",
            "full_name": "low", "message": "low", "body": "low",
        }
        for col, sev in cases.items():
            with self.subTest(col=col):
                self.assertEqual(classify(col)[0], sev)

    def test_harmless_names(self):
        for col in ("id", "created_at", "title", "price", "status", "slug", "updated_at", "is_public"):
            with self.subTest(col=col):
                self.assertIsNone(classify(col))

    def test_worst_first(self):
        hits = classify_columns(["email", "id", "passport_number", "full_name"])
        self.assertEqual([h[0] for h in hits], ["passport_number", "email", "full_name"])
        self.assertEqual(worst(["id", "email"]), "medium")
        self.assertIsNone(worst(["id"]))


if __name__ == "__main__":
    unittest.main()
