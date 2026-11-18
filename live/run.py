"""Run patet against real Postgres and PostgREST, and check it reports each planted table correctly.

Needs PostgREST on PGRST_URL (default http://127.0.0.1:3000), set up with live/setup.sql and
PGRST_JWT_SECRET. CI starts both from their official container images (see .github/workflows).

In front of PostgREST this script runs a small stand-in for Supabase's gateway: it serves the
data API under /rest/v1, refuses requests without a known apikey, and answers 404 for auth and
storage, which are not part of this test. It also serves a tiny website whose code names the tables.
Exit 0 when every expectation holds, 1 otherwise.
"""

from __future__ import annotations

import base64
import contextlib
import hashlib
import hmac
import io
import json
import os
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from functools import partial
from http.server import BaseHTTPRequestHandler, SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from patet.cli import main  # noqa: E402

PGRST = os.environ.get("PGRST_URL", "http://127.0.0.1:3000").rstrip("/")
SECRET = os.environ.get("PGRST_JWT_SECRET", "patet-live-test-secret-at-least-32-chars")
REF = "patetlivetestproject"
PUBLISHABLE = "sb_publishable_patetLiveTest0000"

EXPECTED = {  # table -> (state, rows)
    "profiles": ("exposed", 57),
    "notes": ("hidden", 0),
    "payroll": ("blocked", None),
    "posts": ("exposed", 5),
    "messages": ("hidden", 0),
    "waitlist": ("hidden", 0),
    "orders": ("missing", None),
}
EXPECTED_GRADES = {"profiles": "critical", "posts": "medium"}


def b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def sign(claims: dict) -> str:
    head = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    body = b64(json.dumps(claims).encode())
    sig = hmac.new(SECRET.encode(), f"{head}.{body}".encode(), hashlib.sha256).digest()
    return f"{head}.{body}.{b64(sig)}"


ANON = sign({"iss": "supabase", "ref": REF, "role": "anon", "exp": 4102444800})


class Gateway(BaseHTTPRequestHandler):
    log: list = []

    def log_message(self, *a):
        pass

    def _forward(self):
        Gateway.log.append((self.command, self.path))
        if self.headers.get("apikey") not in (ANON, PUBLISHABLE):
            return self._reply(401, {}, b'{"message":"Invalid API key"}')
        if not self.path.startswith("/rest/v1/"):
            return self._reply(404, {}, b"")
        headers = {k: v for k, v in self.headers.items() if k.lower() not in ("host", "apikey", "content-length")}
        n = int(self.headers.get("Content-Length") or 0)
        req = urllib.request.Request(PGRST + self.path[len("/rest/v1"):], method=self.command, headers=headers,
                                     data=self.rfile.read(n) if n else None)
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                self._reply(r.status, dict(r.headers), b"" if self.command == "HEAD" else r.read())
        except urllib.error.HTTPError as e:
            with e:
                self._reply(e.code, dict(e.headers), b"" if self.command == "HEAD" else e.read())

    def _reply(self, code, headers, body):
        self.send_response(code)
        for k, v in headers.items():
            if k.lower() in ("content-range", "content-type", "preference-applied"):
                self.send_header(k, v)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    do_GET = do_HEAD = do_POST = _forward


def serve(handler) -> tuple[ThreadingHTTPServer, str]:
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}"


def write_site(folder: Path) -> None:
    (folder / "assets").mkdir()
    (folder / "index.html").write_text('<html><script type="module" src="/assets/index.js"></script></html>')
    calls = "".join(f's.from("{t}").select("*");\n' for t in EXPECTED)
    (folder / "assets" / "index.js").write_text(
        f'const s = createClient("https://{REF}.supabase.co", "{ANON}");\n{calls}')


def patet(argv: list[str]) -> tuple[int, dict]:
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = main(argv)
    return code, json.loads(out.getvalue())


def check(label: str, d: dict, failures: list[str], grades: bool) -> None:
    got = {t["name"]: (t["state"], t["rows"]) for t in d["tables"]}
    print(f"\n{label}")
    for name, want in EXPECTED.items():
        ok = got.get(name) == want
        print(f"  {'ok  ' if ok else 'FAIL'} {name:<9} expected {want[0]:<8} {want[1]!s:<5} got {got.get(name)}")
        if not ok:
            failures.append(f"{label}: {name} expected {want}, got {got.get(name)}")
    if grades:
        found = {f["where"]: f["grade"] for f in d["findings"]}
        for name, grade in EXPECTED_GRADES.items():
            ok = found.get(name) == grade
            print(f"  {'ok  ' if ok else 'FAIL'} {name:<9} graded {found.get(name)}, expected {grade}")
            if not ok:
                failures.append(f"{label}: {name} graded {found.get(name)}, expected {grade}")


def run() -> int:
    failures: list[str] = []
    gw, gw_url = serve(Gateway)
    with tempfile.TemporaryDirectory() as d:
        write_site(Path(d))
        site, site_url = serve(partial(SimpleHTTPRequestHandler, directory=d))
        base = ["check", site_url + "/", "--supabase-url", gw_url, "--i-own-this", "--json", "--delay", "0"]

        Gateway.log.clear()
        code, d1 = patet(base)
        check("Counting only, with the anon key from the page", d1, failures, grades=False)
        rows_fetched = [p for m, p in Gateway.log if m != "HEAD"]
        print(f"  {'ok  ' if not rows_fetched else 'FAIL'} only HEAD requests reached the data API")
        if rows_fetched:
            failures.append(f"counting fetched rows: {rows_fetched}")
        if code != 1:
            failures.append(f"exit code {code}, expected 1 (an open table with email-like columns)")

        Gateway.log.clear()
        _, d2 = patet(base + ["--columns"])
        check("With --columns", d2, failures, grades=True)
        gets = sorted(p for m, p in Gateway.log if m == "GET")
        want = ["/rest/v1/posts?select=*&limit=1", "/rest/v1/profiles?select=*&limit=1"]
        print(f"  {'ok  ' if gets == want else 'FAIL'} one row read per open table, nothing else")
        if gets != want:
            failures.append(f"--columns made {gets}")
        if "X0000001" in json.dumps(d2) or "@example.com" in json.dumps(d2):
            failures.append("a row value reached the output")

        _, d3 = patet(base + ["--key", PUBLISHABLE])
        check("With a publishable key (apikey header only)", d3, failures, grades=False)

        site.shutdown()
    gw.shutdown()
    print("\nAll live checks passed." if not failures else "\n" + "\n".join(failures))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(run())
