"""Two more things a visitor can reach with the browser key: sign-up settings and storage buckets.

Sign-up settings matter because a rule that lets "any signed-in user" read is only as closed as
sign-up is. If anyone can make an account and is let in without confirming an email, such a rule
is open to everyone. Storage listing is checked with a limit of one, and file names are not kept.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from urllib.parse import quote

from .http import Transport
from .keys import Key
from .probe import auth_headers


@dataclass
class AuthSettings:
    signup_open: bool | None
    autoconfirm: bool | None
    anonymous: bool | None
    providers: list[str] = field(default_factory=list)


@dataclass
class BucketResult:
    name: str
    state: str  # listable, closed, missing, error
    detail: str = ""


def read_auth(t: Transport, base: str, key: Key) -> AuthSettings | None:
    r = t.request("GET", f"{base.rstrip('/')}/auth/v1/settings", auth_headers(key))
    if r.status != 200:
        return None
    try:
        d = r.json()
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    ext = d.get("external") if isinstance(d.get("external"), dict) else {}
    return AuthSettings(
        signup_open=(not d["disable_signup"]) if isinstance(d.get("disable_signup"), bool) else None,
        autoconfirm=d.get("mailer_autoconfirm") if isinstance(d.get("mailer_autoconfirm"), bool) else None,
        anonymous=ext.get("anonymous_users") if isinstance(ext.get("anonymous_users"), bool) else None,
        providers=sorted(k for k, v in ext.items() if v is True and k != "anonymous_users"),
    )


def probe_bucket(t: Transport, base: str, key: Key, bucket: str) -> BucketResult:
    url = f"{base.rstrip('/')}/storage/v1/object/list/{quote(bucket, safe='')}"
    body = json.dumps({"prefix": "", "limit": 1, "offset": 0}).encode()
    r = t.request("POST", url, {**auth_headers(key), "Content-Type": "application/json"}, body)
    if r.status == 200:
        try:
            listed = r.json()
        except ValueError:
            listed = None
        if isinstance(listed, list) and listed:
            return BucketResult(bucket, "listable", "a visitor can list its files")
        return BucketResult(bucket, "closed", "no files listed to a visitor")
    if r.status in (401, 403):
        return BucketResult(bucket, "closed", f"refused ({r.status})")
    if r.status in (400, 404):
        return BucketResult(bucket, "missing", "no bucket by that name")
    return BucketResult(bucket, "error", f"unexpected answer {r.status}")
