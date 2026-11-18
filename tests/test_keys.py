import unittest

from helpers import ANON, PUBLISHABLE, REF, SECRET, SERVICE, USER_SESSION, make_jwt
from patet.keys import classify, jwt_claims, mask


class Keys(unittest.TestCase):
    def test_anon_jwt_is_a_browser_key(self):
        k = classify(ANON, "app.js")
        self.assertEqual((k.kind, k.project, k.is_server_key), ("anon", REF, False))

    def test_service_role_jwt_is_a_server_key(self):
        k = classify(SERVICE, "app.js")
        self.assertEqual(k.kind, "service_role")
        self.assertTrue(k.is_server_key)

    def test_new_style_keys(self):
        self.assertEqual(classify(PUBLISHABLE, "x").kind, "publishable")
        self.assertTrue(classify(SECRET, "x").is_server_key)

    def test_user_session_token_is_not_a_project_key(self):
        self.assertIsNone(classify(USER_SESSION, "x"))

    def test_unrelated_jwt_is_ignored(self):
        self.assertIsNone(classify(make_jwt({"iss": "auth0", "role": "anon"}), "x"))

    def test_garbage_is_ignored(self):
        self.assertIsNone(classify("eyJnot.eyJvalid.at-all", "x"))
        self.assertIsNone(jwt_claims("a.b"))

    def test_mask_hides_the_middle(self):
        m = mask(SERVICE)
        self.assertNotIn(SERVICE[12:-6], m)
        self.assertTrue(m.startswith(SERVICE[:10]))
        self.assertEqual(mask("short"), "…")


if __name__ == "__main__":
    unittest.main()
