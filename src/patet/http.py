"""A small, slow HTTP client: one request at a time, a pause between them, nothing kept on disk."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass, field

from . import __version__

USER_AGENT = f"patet/{__version__} (+https://github.com/patkusch/patet)"


class NetworkError(Exception):
    pass


@dataclass
class Response:
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    body: bytes = b""

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")

    def json(self):
        return json.loads(self.body or b"null")


def _lower(headers) -> dict[str, str]:
    return {k.lower(): v for k, v in headers.items()} if headers else {}


class Transport:
    """Waits `delay` seconds between requests so a check never hammers anyone's project."""

    def __init__(self, delay: float = 0.25, timeout: float = 15.0, max_bytes: int = 10_000_000):
        self.delay = delay
        self.timeout = timeout
        self.max_bytes = max_bytes
        self.sent: list[tuple[str, str]] = []
        self._last = 0.0

    def request(self, method: str, url: str, headers: dict | None = None, data: bytes | None = None) -> Response:
        wait = self._last + self.delay - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"User-Agent": USER_AGENT, **(headers or {})})
        self.sent.append((method, url))
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                body = b"" if method == "HEAD" else r.read(self.max_bytes)
                return Response(r.status, _lower(r.headers), body)
        except urllib.error.HTTPError as e:
            body = b"" if method == "HEAD" else e.read(self.max_bytes)
            return Response(e.code, _lower(e.headers), body)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise NetworkError(f"could not reach {url}: {getattr(e, 'reason', e)}") from None
        finally:
            self._last = time.monotonic()
