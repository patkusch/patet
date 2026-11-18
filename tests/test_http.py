import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from patet.http import NetworkError, Transport


class _H(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_GET(self):
        code = 404 if self.path == "/missing" else 200
        body = b'{"ok": true}'
        self.send_response(code)
        self.send_header("Content-Range", "0-0/3")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    do_HEAD = do_GET


class HttpClient(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _H)
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()
        cls.url = f"http://127.0.0.1:{cls.srv.server_address[1]}"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_get_returns_body_and_lowercase_headers(self):
        r = Transport(delay=0).request("GET", self.url + "/x")
        self.assertEqual((r.status, r.json(), r.headers["content-range"]), (200, {"ok": True}, "0-0/3"))

    def test_error_status_is_returned_not_raised(self):
        self.assertEqual(Transport(delay=0).request("GET", self.url + "/missing").status, 404)

    def test_head_has_no_body(self):
        self.assertEqual(Transport(delay=0).request("HEAD", self.url + "/x").body, b"")

    def test_waits_between_requests(self):
        t = Transport(delay=0.2)
        start = time.monotonic()
        t.request("GET", self.url + "/a")
        t.request("GET", self.url + "/b")
        self.assertGreaterEqual(time.monotonic() - start, 0.19)
        self.assertEqual(len(t.sent), 2)

    def test_unreachable_host_raises_network_error(self):
        with self.assertRaises(NetworkError):
            Transport(delay=0, timeout=2).request("GET", "http://127.0.0.1:9/")


if __name__ == "__main__":
    unittest.main()
