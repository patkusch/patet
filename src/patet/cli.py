"""patet check <your app's URL>   look at your live app as a visitor would
patet scan <build folder>       read a build folder on disk, no network
"""

from __future__ import annotations

import argparse
import re
import sys

from . import __version__
from .bundle import FetchError, Found, read_site, scan_paths
from .http import NetworkError, Transport
from .keys import classify
from .probe import COMMON_TABLES, probe_tables
from .report import Report, analyse, to_json, to_text
from .surface import probe_bucket, read_auth

MAX_TABLES = 200
_TABLE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")

GATE = """patet stopped before asking Supabase anything.
It only checks a project when you confirm it is yours: add --i-own-this.
Checking someone else's project without permission may be illegal where you live."""


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="patet", description="See what an anonymous visitor can read from "
                                "your own Supabase-backed app, without reading a single row.")
    p.add_argument("--version", action="version", version=f"patet {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="look at your live app as a visitor would")
    c.add_argument("url", nargs="?", help="your app's address, e.g. https://myapp.example")
    c.add_argument("--i-own-this", dest="owner", action="store_true",
                   help="confirm the app and its Supabase project are yours; nothing is asked of Supabase without it")
    c.add_argument("--supabase-url", help="the project address, if the page does not show it")
    c.add_argument("--key", help="the browser key (anon or publishable), if the page does not show it")
    c.add_argument("--tables", help="more table names to check, comma-separated")
    c.add_argument("--guess", action="store_true", help=f"also try {len(COMMON_TABLES)} common table names")
    c.add_argument("--columns", action="store_true",
                   help="for open tables, read one row to learn the column names; values are dropped")
    c.add_argument("--fix", action="store_true", help="print SQL to close each open table, for you to review")
    c.add_argument("--json", action="store_true", help="print JSON")
    c.add_argument("--delay", type=float, default=0.25, help="seconds between requests (default 0.25)")

    s = sub.add_parser("scan", help="read a build folder on disk for server keys and table names")
    s.add_argument("paths", nargs="+")
    s.add_argument("--json", action="store_true", help="print JSON")
    return p


def _emit(rep: Report, as_json: bool, fix: bool = False) -> int:
    print(to_json(rep) if as_json else to_text(rep, fix), end="" if not as_json else "\n")
    return 1 if rep.failed else 0


def _scan(args) -> int:
    found = scan_paths(args.paths)
    rep = Report(None, ", ".join(sorted(found.projects)) or None, found)
    rep.findings = analyse(rep)
    return _emit(rep, args.json)


def _check(args) -> int:
    if not args.url and not (args.supabase_url and args.key):
        print("patet: give your app's URL, or both --supabase-url and --key", file=sys.stderr)
        return 2
    t = Transport(delay=args.delay)
    found = read_site(t, args.url) if args.url else Found()
    if args.key:
        k = classify(args.key, "--key")
        if not k:
            print("patet: --key is not a Supabase anon or publishable key", file=sys.stderr)
            return 2
        found.keys.setdefault(k.value, k)

    if args.supabase_url:
        base = args.supabase_url.rstrip("/")
        project = base
    elif len(found.projects) == 1:
        project = next(iter(found.projects))
        base = f"https://{project}.supabase.co"
    else:
        project, base = (", ".join(sorted(found.projects)) or None), None

    rep = Report(args.url, project, found)
    browser = [k for k in found.browser_keys if not args.key or k.value == args.key]
    if not args.owner or not base or not browser:
        rep.findings = analyse(rep)
        code = _emit(rep, args.json)
        if not args.owner:
            print(GATE, file=sys.stderr)
        elif not base:
            print("patet: found no single Supabase project in the page; pass --supabase-url", file=sys.stderr)
        else:
            print("patet: found no browser key in the page; pass --key", file=sys.stderr)
        return code or (0 if not args.owner else 2)

    names = list(found.tables)
    if args.tables:
        names += [n.strip() for n in args.tables.split(",") if n.strip()]
    if args.guess:
        names += list(COMMON_TABLES)
    names = list(dict.fromkeys(n for n in names if _TABLE.match(n)))[:MAX_TABLES]

    key = browser[0]
    rep.tables = probe_tables(t, base, key, names, columns=args.columns)
    rep.buckets = [probe_bucket(t, base, key, b) for b in sorted(found.buckets)]
    rep.auth = read_auth(t, base, key)
    rep.probed = True
    rep.findings = analyse(rep)
    return _emit(rep, args.json, args.fix)


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        return _scan(args) if args.cmd == "scan" else _check(args)
    except (NetworkError, FetchError) as e:
        print(f"patet: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
