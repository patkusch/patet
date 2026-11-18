"""Shared test helpers. Every key here is fake and built at run time."""

from __future__ import annotations

import base64
import json

REF = "abcdefghijklmnopqrst"


def make_jwt(claims: dict) -> str:
    def enc(d: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()

    return f"{enc({'alg': 'HS256', 'typ': 'JWT'})}.{enc(claims)}.{'s' * 43}"


ANON = make_jwt({"iss": "supabase", "ref": REF, "role": "anon"})
SERVICE = make_jwt({"iss": "supabase", "ref": REF, "role": "service_role"})
USER_SESSION = make_jwt({"iss": f"https://{REF}.supabase.co/auth/v1", "role": "authenticated", "sub": "u1"})
PUBLISHABLE = "sb_publishable_" + "A1b2C3d4E5f6G7h8I9j0"
SECRET = "sb_secret_" + "Z9y8X7w6V5u4T3s2R1q0"


# --- a fake Supabase project and website, served from one local port ---------------------------

import threading  # noqa: E402
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer  # noqa: E402
from urllib.parse import urlparse  # noqa: E402

PROFILE = {"id": 1, "email": "a@example.com", "passport_number": "X0000000", "full_name": "A", "user_id": "u1"}
# table -> (status for an anonymous read, total rows visible, one row)
TABLES = {
    "profiles": (206, 57, PROFILE),
    "notes": (200, 0, None),
    "payroll": (401, None, None),
}

APP_JS = f"""
const s=createClient("https://{REF}.supabase.co","{ANON}");
s.from("profiles").select("id, email");
s.from("notes").select("*");
s.from("payroll").select("amount");
s.storage.from("avatars").list(); s.storage.from("invoices").list();
s.rpc("get_stats");
import("./chunk.js");
"""
CHUNK_JS = 's.from("orders").select("total")'
PAGE = '<html><head><script type="module" src="/assets/index.js"></script></head><body></body></html>'
LEAKY_PAGE = f'<html><script>window.k="{SERVICE}"</script><script src="/assets/index.js"></script></html>'


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body=b"", headers=None):
        self.send_response(code)
        for k, v in (headers or {}).items():
            self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def _record(self):
        self.server.log.append((self.command, self.path, {k.lower(): v for k, v in self.headers.items()}))

    def _authorised(self):
        return self.headers.get("apikey") in (ANON, PUBLISHABLE)

    def do_HEAD(self):
        self._record()
        self._rest()

    def do_GET(self):
        self._record()
        path = urlparse(self.path).path
        site = {"/": PAGE, "/leaky": LEAKY_PAGE, "/assets/index.js": APP_JS, "/assets/chunk.js": CHUNK_JS}
        if path in site:
            return self._send(200, site[path].encode())
        if path == "/auth/v1/settings":
            if not self._authorised():
                return self._send(401)
            return self._send(200, json.dumps(self.server.auth).encode())
        if path.startswith("/rest/v1/"):
            return self._rest()
        self._send(404)

    def do_POST(self):
        self._record()
        path = urlparse(self.path).path
        if path.startswith("/storage/v1/object/list/"):
            if not self._authorised():
                return self._send(401)
            bucket = path.rsplit("/", 1)[1]
            files = {"avatars": [{"name": "a.png"}], "invoices": []}
            if bucket not in files:
                return self._send(400, b'{"error":"Bucket not found"}')
            return self._send(200, json.dumps(files[bucket]).encode())
        self._send(404)

    def _rest(self):
        if not self._authorised():
            return self._send(401)
        table = urlparse(self.path).path.rsplit("/", 1)[1]
        if table not in TABLES:
            return self._send(404, b'{"code":"PGRST205"}')
        status, total, row = TABLES[table]
        if status >= 400:
            return self._send(status, b'{"code":"42501"}')
        rng = "*/0" if not total else f"0-0/{total}"
        body = json.dumps([row] if row else []).encode()
        self._send(status, body, {"Content-Range": rng, "Content-Type": "application/json"})


class FakeSupabase:
    """`with FakeSupabase() as fake:` gives `fake.url` and `fake.log` of (method, path, headers)."""

    def __init__(self, auth: dict | None = None):
        self.auth = auth if auth is not None else {
            "disable_signup": False, "mailer_autoconfirm": True,
            "external": {"email": True, "google": False, "anonymous_users": False}}

    def __enter__(self):
        self.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.srv.log = []
        self.srv.auth = self.auth
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.srv.server_address[1]}"
        self.log = self.srv.log
        return self

    def __exit__(self, *exc):
        self.srv.shutdown()
        self.srv.server_close()
