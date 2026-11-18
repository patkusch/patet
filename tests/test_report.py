import json
import unittest

from helpers import ANON, SERVICE
from patet.bundle import Found, scan_text
from patet.fixes import sql_fix
from patet.probe import TableResult
from patet.report import Report, analyse, to_json, to_text
from patet.surface import AuthSettings, BucketResult


def report(**kw):
    f = Found()
    scan_text(f'"{ANON}" x.from("profiles").select("id, email") x.rpc("get_stats")', "app.js", f)
    rep = Report("https://app.example", "ref", f, probed=True, **kw)
    rep.findings = analyse(rep)
    return rep


class Findings(unittest.TestCase):
    def test_open_table_with_email_is_high(self):
        rep = report(tables=[TableResult("profiles", "exposed", 57)])
        f = rep.findings[0]
        self.assertEqual((f.grade, f.title), ("high", "Anyone can read 57 rows of `profiles`"))
        self.assertIn("email addresses", f.why)
        self.assertTrue(rep.failed)

    def test_passport_column_makes_it_critical(self):
        rep = report(tables=[TableResult("profiles", "exposed", 3, ["id", "passport_number"])])
        self.assertEqual(rep.findings[0].grade, "critical")

    def test_open_table_without_personal_columns_is_medium(self):
        rep = report(tables=[TableResult("posts", "exposed", 9)])
        self.assertEqual(rep.findings[0].grade, "medium")
        self.assertFalse(rep.failed)

    def test_unknown_columns_point_to_the_columns_option(self):
        rep = report(tables=[TableResult("orders", "exposed", 4)])
        self.assertIn("--columns", rep.findings[0].why)

    def test_closed_tables_make_no_findings(self):
        rep = report(tables=[TableResult("a", "hidden", 0), TableResult("b", "blocked")])
        self.assertEqual([f.grade for f in rep.findings], ["info"])  # just the function note

    def test_server_key_auth_and_bucket(self):
        f = Found()
        scan_text(f'"{SERVICE}"', "app.js", f)
        rep = Report(None, "ref", f, buckets=[BucketResult("avatars", "listable")],
                     auth=AuthSettings(True, True, True))
        grades = [x.grade for x in analyse(rep)]
        self.assertEqual(grades, ["critical", "high", "medium", "medium"])

    def test_json_never_holds_a_full_key(self):
        rep = report(tables=[TableResult("profiles", "exposed", 57)])
        out = to_json(rep)
        self.assertNotIn(ANON, out)
        self.assertEqual(json.loads(out)["summary"]["high"], 1)

    def test_text_with_fix(self):
        rep = report(tables=[TableResult("profiles", "exposed", 57, ["id", "user_id"])])
        out = to_text(rep, fix=True)
        self.assertIn("profiles  OPEN", out)
        self.assertIn("enable row level security", out)
        self.assertIn("= user_id", out)


class Fixes(unittest.TestCase):
    def test_owner_column_gets_a_policy(self):
        self.assertIn("create policy", sql_fix("notes", ["owner_id"]).splitlines()[2])

    def test_no_owner_column_gets_commented_example(self):
        self.assertTrue(sql_fix("notes").splitlines()[3].startswith("--"))

    def test_odd_names_get_no_sql(self):
        self.assertIn("no SQL", sql_fix('x"; drop table y; --'))


if __name__ == "__main__":
    unittest.main()
