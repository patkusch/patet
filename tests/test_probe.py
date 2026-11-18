import unittest

from helpers import ANON, FakeSupabase
from patet.http import Transport
from patet.keys import classify
from patet.probe import parse_total, probe_tables


class Probe(unittest.TestCase):
    def run_probe(self, columns=False):
        with FakeSupabase() as fake:
            res = probe_tables(Transport(delay=0), fake.url, classify(ANON, "x"),
                               ["profiles", "notes", "payroll", "orders"], columns)
            return {r.name: r for r in res}, list(fake.log)

    def test_states_and_counts(self):
        res, _ = self.run_probe()
        self.assertEqual((res["profiles"].state, res["profiles"].rows), ("exposed", 57))
        self.assertEqual(res["notes"].state, "hidden")
        self.assertEqual(res["payroll"].state, "blocked")
        self.assertEqual(res["orders"].state, "missing")

    def test_counting_never_downloads_rows(self):
        _, log = self.run_probe()
        self.assertTrue(all(m == "HEAD" for m, _, _ in log), log)
        self.assertTrue(all(h.get("Prefer") == "count=exact" for _, _, h in log))

    def test_sends_browser_key_both_ways(self):
        _, log = self.run_probe()
        self.assertEqual(log[0][2]["apikey"], ANON)
        self.assertEqual(log[0][2]["Authorization"], f"Bearer {ANON}")

    def test_columns_reads_one_row_and_keeps_only_names(self):
        res, log = self.run_probe(columns=True)
        self.assertIn("passport_number", res["profiles"].columns)
        gets = [p for m, p, _ in log if m == "GET"]
        self.assertEqual(gets, ["/rest/v1/profiles?select=*&limit=1"])  # only for the exposed table
        self.assertNotIn("X0000000", repr(res))

    def test_parse_total(self):
        self.assertEqual(parse_total("0-0/57"), 57)
        self.assertEqual(parse_total("*/0"), 0)
        self.assertIsNone(parse_total("0-0/*"))
        self.assertIsNone(parse_total(None))


if __name__ == "__main__":
    unittest.main()
