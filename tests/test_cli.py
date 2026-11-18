import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from helpers import ANON, SERVICE, FakeSupabase
from patet.cli import main


def run(argv):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


class Check(unittest.TestCase):
    def test_end_to_end(self):
        with FakeSupabase() as fake:
            code, out, _ = run(["check", fake.url + "/", "--supabase-url", fake.url,
                                "--i-own-this", "--json", "--delay", "0"])
        d = json.loads(out)
        states = {t["name"]: t["state"] for t in d["tables"]}
        self.assertEqual(states, {"profiles": "exposed", "notes": "hidden", "payroll": "blocked",
                                  "orders": "missing"})  # orders comes from the lazily loaded chunk
        self.assertEqual({b["name"]: b["state"] for b in d["buckets"]},
                         {"avatars": "listable", "invoices": "closed"})
        self.assertEqual(d["summary"]["high"], 2)  # profiles (email) and the listable bucket
        self.assertEqual(code, 1)

    def test_without_ownership_nothing_is_asked_of_supabase(self):
        with FakeSupabase() as fake:
            code, out, err = run(["check", fake.url + "/", "--supabase-url", fake.url, "--delay", "0"])
            paths = [p for _, p, _ in fake.log]
        self.assertFalse([p for p in paths if p.startswith(("/rest", "/auth", "/storage"))], paths)
        self.assertIn("--i-own-this", err)
        self.assertIn("profiles", out)
        self.assertEqual(code, 0)

    def test_columns_makes_passport_table_critical_and_fix_prints_sql(self):
        with FakeSupabase() as fake:
            code, out, _ = run(["check", fake.url + "/", "--supabase-url", fake.url, "--i-own-this",
                                "--columns", "--fix", "--delay", "0"])
        self.assertIn("[CRITICAL] Anyone can read 57 rows of `profiles`", out)
        self.assertIn("alter table public.profiles enable row level security;", out)
        self.assertNotIn("X0000000", out)
        self.assertNotIn(ANON, out)

    def test_server_key_in_page_fails_even_without_ownership(self):
        with FakeSupabase() as fake:
            code, out, _ = run(["check", fake.url + "/leaky", "--delay", "0"])
        self.assertIn("A server key is in your website's code", out)
        self.assertNotIn(SERVICE, out)
        self.assertEqual(code, 1)

    def test_url_or_project_and_key_required(self):
        self.assertEqual(run(["check"])[0], 2)

    def test_bad_key(self):
        self.assertEqual(run(["check", "--supabase-url", "http://x", "--key", "nope"])[0], 2)

    def test_unreachable_site(self):
        self.assertEqual(run(["check", "http://127.0.0.1:9/", "--delay", "0"])[0], 2)


class Scan(unittest.TestCase):
    def test_build_folder(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "index.js").write_text(f'createClient("https://abcdefghijklmnopqrst.supabase.co","{ANON}")')
            self.assertEqual(run(["scan", d])[0], 0)
            (Path(d) / "admin.js").write_text(f'"{SERVICE}"')
            code, out, _ = run(["scan", d, "--json"])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)["summary"]["critical"], 1)


if __name__ == "__main__":
    unittest.main()
