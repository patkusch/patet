import unittest

from helpers import ANON, FakeSupabase
from patet.http import Transport
from patet.keys import classify
from patet.surface import probe_bucket, read_auth

KEY = classify(ANON, "x")


class Surface(unittest.TestCase):
    def test_auth_settings(self):
        with FakeSupabase() as fake:
            a = read_auth(Transport(delay=0), fake.url, KEY)
        self.assertEqual((a.signup_open, a.autoconfirm, a.anonymous, a.providers), (True, True, False, ["email"]))

    def test_auth_settings_missing_fields_are_unknown(self):
        with FakeSupabase(auth={"external": {}}) as fake:
            a = read_auth(Transport(delay=0), fake.url, KEY)
        self.assertEqual((a.signup_open, a.autoconfirm, a.anonymous), (None, None, None))

    def test_buckets(self):
        with FakeSupabase() as fake:
            t = Transport(delay=0)
            states = {b: probe_bucket(t, fake.url, KEY, b).state for b in ("avatars", "invoices", "nope")}
            bodies = [h for m, _, h in fake.log if m == "POST"]
        self.assertEqual(states, {"avatars": "listable", "invoices": "closed", "nope": "missing"})
        self.assertEqual(len(bodies), 3)


if __name__ == "__main__":
    unittest.main()
