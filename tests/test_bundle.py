import tempfile
import unittest
from pathlib import Path

from helpers import ANON, PUBLISHABLE, REF, SERVICE, USER_SESSION
from patet.bundle import Found, scan_paths, scan_text

APP = f"""
const s=createClient("https://{REF}.supabase.co","{ANON}");
await s.from("profiles").select("id, email, full_name");
await s.from( 'notes' ).insert({{a:1}});
const b = s.storage.from("avatars").list();
s.rpc("get_stats");
const xs = Array.from("abc");
const tok = "{USER_SESSION}";
"""


class Bundle(unittest.TestCase):
    def scan(self, text):
        f = Found()
        scan_text(text, "app.js", f)
        return f

    def test_finds_project_key_tables_buckets_functions(self):
        f = self.scan(APP)
        self.assertEqual(f.projects, {REF})
        self.assertEqual([k.kind for k in f.keys.values()], ["anon"])
        self.assertEqual(set(f.tables), {"profiles", "notes"})
        self.assertEqual(f.tables["profiles"], {"id", "email", "full_name"})
        self.assertEqual(f.buckets, {"avatars"})
        self.assertEqual(f.functions, {"get_stats"})

    def test_array_from_is_not_a_table(self):
        self.assertNotIn("abc", self.scan(APP).tables)

    def test_user_session_token_is_not_kept(self):
        self.assertEqual(len(self.scan(APP).keys), 1)

    def test_server_key_and_new_style_key(self):
        f = self.scan(f'x="{SERVICE}";y="{PUBLISHABLE}"')
        self.assertEqual([k.kind for k in f.server_keys], ["service_role"])
        self.assertEqual([k.kind for k in f.browser_keys], ["publishable"])
        self.assertEqual(f.projects, {REF})  # from the JWT's ref claim

    def test_minified_from(self):
        f = self.scan('e.from("orders").select("total,card_number")')
        self.assertEqual(f.tables["orders"], {"total", "card_number"})

    def test_scan_paths_reads_build_folder_and_skips_node_modules(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "assets").mkdir()
            (Path(d) / "assets" / "index.js").write_text(APP)
            (Path(d) / "node_modules").mkdir()
            (Path(d) / "node_modules" / "x.js").write_text(f'"{SERVICE}"')
            (Path(d) / "readme.txt").write_text(f'"{SERVICE}"')
            f = scan_paths([d])
        self.assertEqual(f.server_keys, [])
        self.assertIn("profiles", f.tables)


if __name__ == "__main__":
    unittest.main()
