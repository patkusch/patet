"""Tell a Supabase browser key from a server key.

A browser key (the old `anon` JWT, or the newer `sb_publishable_...`) is meant to sit in a web page.
Row rules decide what it can read. A server key (`service_role` JWT, or `sb_secret_...`) skips
every row rule, so finding one in a page means anyone can read, change and delete everything.
"""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

BROWSER_KINDS = ("anon", "publishable")
SERVER_KINDS = ("service_role", "secret")


@dataclass(frozen=True)
class Key:
    value: str
    kind: str  # anon, publishable, service_role, secret
    project: str | None
    where: str

    @property
    def is_server_key(self) -> bool:
        return self.kind in SERVER_KINDS

    @property
    def masked(self) -> str:
        return mask(self.value)


def mask(value: str) -> str:
    """Enough to recognise a key, not enough to use it."""
    if len(value) <= 20:
        return "…"
    return f"{value[:10]}…{value[-4:]}"


def jwt_claims(token: str) -> dict | None:
    parts = token.split(".")
    if len(parts) != 3:
        return None
    body = parts[1] + "=" * (-len(parts[1]) % 4)
    try:
        claims = json.loads(base64.urlsafe_b64decode(body))
    except (ValueError, UnicodeDecodeError):
        return None
    return claims if isinstance(claims, dict) else None


def classify(value: str, where: str) -> Key | None:
    """A Key if `value` is a Supabase project key, else None (other JWTs, user session tokens)."""
    if value.startswith("sb_publishable_"):
        return Key(value, "publishable", None, where)
    if value.startswith("sb_secret_"):
        return Key(value, "secret", None, where)
    claims = jwt_claims(value)
    if not claims:
        return None
    if claims.get("iss") not in ("supabase", "supabase-demo") and "ref" not in claims:
        return None
    role = claims.get("role")
    if role not in ("anon", "service_role"):
        return None  # a signed-in user's token, not a project key
    ref = claims.get("ref") if isinstance(claims.get("ref"), str) else None
    return Key(value, role, ref, where)
