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
