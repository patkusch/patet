"""Ask Supabase, as an anonymous visitor would, how many rows of each table it would hand over.

Each table gets one HEAD request with `Prefer: count=exact`. Supabase answers with a row count
in the Content-Range header and no rows. Column names are read only when asked (--columns):
one row is fetched, its column names kept and its values dropped straight away.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from urllib.parse import quote

from .http import Transport
from .keys import Key

# Tried only with --guess, for tables the app's code does not name.
COMMON_TABLES = (
    "users", "profiles", "accounts", "customers", "clients", "members", "contacts", "leads",
    "messages", "conversations", "chats", "comments", "posts", "notes", "documents", "files",
    "orders", "payments", "invoices", "subscriptions", "transactions", "bookings", "appointments",
    "applications", "submissions", "responses", "feedback", "waitlist", "signups", "emails",
)

STATES = ("exposed", "hidden", "blocked", "missing", "error")


@dataclass
class TableResult:
    name: str
    state: str  # one of STATES
    rows: int | None = None
    columns: list[str] = field(default_factory=list)
    detail: str = ""


def auth_headers(key: Key) -> dict[str, str]:
    h = {"apikey": key.value}
    if key.value.startswith("eyJ"):
        h["Authorization"] = f"Bearer {key.value}"
    return h


def rest_url(base: str, table: str) -> str:
    return f"{base.rstrip('/')}/rest/v1/{quote(table, safe='')}"


def parse_total(content_range: str | None) -> int | None:
    if not content_range or "/" not in content_range:
        return None
    tail = content_range.rsplit("/", 1)[1].strip()
    return int(tail) if tail.isdigit() else None


def probe_table(t: Transport, base: str, key: Key, table: str, columns: bool = False) -> TableResult:
    url = rest_url(base, table) + "?select=*"
    r = t.request("HEAD", url, {**auth_headers(key), "Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"})
    if r.status in (200, 206):
        total = parse_total(r.headers.get("content-range"))
        if total == 0:
            return TableResult(table, "hidden", 0, detail="no rows visible to a visitor")
        result = TableResult(table, "exposed", total)
        if columns:
            result.columns = _column_names(t, url, key)
        return result
    if r.status == 416:
        return TableResult(table, "hidden", 0, detail="no rows visible to a visitor")
    if r.status in (401, 403):
        return TableResult(table, "blocked", detail=f"refused ({r.status})")
    if r.status == 404:
        return TableResult(table, "missing", detail="not found, or not offered through the API")
    return TableResult(table, "error", detail=f"unexpected answer {r.status}")


def _column_names(t: Transport, url: str, key: Key) -> list[str]:
    r = t.request("GET", url + "&limit=1", auth_headers(key))
    if r.status not in (200, 206):
        return []
    try:
        rows = r.json()
    except ValueError:
        return []
    names = sorted(rows[0]) if isinstance(rows, list) and rows and isinstance(rows[0], dict) else []
    del rows  # values are never kept, printed or written
    return names


def probe_tables(t: Transport, base: str, key: Key, tables: list[str], columns: bool = False) -> list[TableResult]:
    return [probe_table(t, base, key, name, columns) for name in tables]
