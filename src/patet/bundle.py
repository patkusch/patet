"""Find the Supabase project, its keys and the tables an app names, in the app's own HTML and JavaScript.

Nothing here talks to Supabase. It reads the same files a visitor's browser downloads,
or a build folder on disk. Since April 2026 Supabase no longer hands the table list to
the browser key, so the names the app's own code asks for are the starting point.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse

from .http import Transport
from .keys import Key, classify

PROJECT_URL = re.compile(r"https://([a-z0-9]{20})\.supabase\.(?:co|in)\b")
JWT = re.compile(r"\beyJ[A-Za-z0-9_-]{8,}\.eyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}")
NEW_KEY = re.compile(r"\bsb_(?:publishable|secret)_[A-Za-z0-9_-]{16,}")
_NAME = r"[\"'`]([A-Za-z_][A-Za-z0-9_]{0,62})[\"'`]"
FROM = re.compile(r"(storage\s*)?\.from\(\s*" + _NAME + r"\s*\)")
SELECT = re.compile(r"\s*\.select\(\s*[\"'`]([^\"'`]{0,500})[\"'`]")
RPC = re.compile(r"\.rpc\(\s*" + _NAME)
CHUNK = re.compile(r"[\"'`]((?:\.{1,2}/|/)?[A-Za-z0-9_][A-Za-z0-9_./-]*\.m?js)[\"'`]")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")

MAX_SCRIPTS = 60
MAX_FILE_BYTES = 10_000_000
FILE_SUFFIXES = (".js", ".mjs", ".cjs", ".html", ".htm")


class FetchError(Exception):
    pass


@dataclass
class Found:
    projects: set[str] = field(default_factory=set)
    keys: dict[str, Key] = field(default_factory=dict)
    tables: dict[str, set[str]] = field(default_factory=dict)  # table -> columns the code selects
    buckets: set[str] = field(default_factory=set)
    functions: set[str] = field(default_factory=set)
    files: list[str] = field(default_factory=list)

    @property
    def browser_keys(self) -> list[Key]:
        return [k for k in self.keys.values() if not k.is_server_key]

    @property
    def server_keys(self) -> list[Key]:
        return [k for k in self.keys.values() if k.is_server_key]


def _columns(select: str) -> set[str]:
    return {w for w in WORD.findall(select) if w not in ("count", "head", "exact")}


def scan_text(text: str, where: str, found: Found) -> None:
    found.files.append(where)
    for m in PROJECT_URL.finditer(text):
        found.projects.add(m.group(1))
    for m in list(JWT.finditer(text)) + list(NEW_KEY.finditer(text)):
        k = classify(m.group(0), where)
        if k:
            found.keys.setdefault(k.value, k)
            if k.project:
                found.projects.add(k.project)
    for m in FROM.finditer(text):
        if text[max(0, m.start() - 5):m.start()].endswith("Array"):
            continue
        name = m.group(2)
        if m.group(1):
            found.buckets.add(name)
            continue
        cols = found.tables.setdefault(name, set())
        s = SELECT.match(text, m.end())
        if s:
            cols.update(_columns(s.group(1)))
    for m in RPC.finditer(text):
        found.functions.add(m.group(1))


class _Scripts(HTMLParser):
    def __init__(self):
        super().__init__()
        self.srcs: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = {k: v or "" for k, v in attrs}
        if tag == "script" and a.get("src"):
            self.srcs.append(a["src"])
        elif tag == "link" and a.get("rel") in ("modulepreload", "preload") \
                and a.get("href", "").split("?")[0].endswith((".js", ".mjs")):
            self.srcs.append(a["href"])


def read_site(transport: Transport, page_url: str) -> Found:
    """Fetch the page and every same-site script it loads, following JavaScript chunk imports."""
    found = Found()
    r = transport.request("GET", page_url)
    if r.status >= 400:
        raise FetchError(f"{page_url} answered {r.status}")
    html = r.text()
    scan_text(html, page_url, found)
    parser = _Scripts()
    parser.feed(html)
    site = urlparse(page_url).netloc
    queue = [urljoin(page_url, s) for s in parser.srcs]
    seen: set[str] = set()
    while queue and len(seen) < MAX_SCRIPTS:
        url = queue.pop(0).split("#")[0]
        if url in seen or urlparse(url).netloc != site:
            continue
        seen.add(url)
        r = transport.request("GET", url)
        if r.status >= 400:
            continue
        js = r.text()
        scan_text(js, url, found)
        for m in CHUNK.finditer(js):
            queue.append(urljoin(url, m.group(1)))
            queue.append(urljoin(page_url, m.group(1)))
    return found


def scan_paths(paths: list[str | Path]) -> Found:
    """Read a build folder (or single files) on disk. No network."""
    found = Found()
    for p in map(Path, paths):
        files = [p] if p.is_file() else sorted(f for f in p.rglob("*") if f.suffix in FILE_SUFFIXES)
        for f in files:
            if not f.is_file() or f.stat().st_size > MAX_FILE_BYTES or "node_modules" in f.parts:
                continue
            scan_text(f.read_text("utf-8", "replace"), str(f), found)
    return found
