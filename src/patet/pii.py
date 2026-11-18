"""Guess what kind of personal data a column holds, from its name alone.

patet never reads values, so this is a guess from names like `email` or `passport_number`.
A column called `notes` that holds passport numbers will be missed. Grades run worst first.
"""

from __future__ import annotations

import re

RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}

RULES: list[tuple[str, str, re.Pattern]] = [(sev, label, re.compile(rx, re.I)) for sev, label, rx in [
    ("critical", "passwords or password hashes", r"^(pass(word)?|pwd|passwd)(_?hash)?$|password"),
    ("critical", "secrets, tokens or keys", r"secret|api_?key|private_?key|access_?key|refresh_?token|auth_?token|^token$"),
    ("critical", "card or bank numbers", r"card_?number|^pan$|cvv|cvc|iban|account_?number|routing_?number|sort_?code"),
    ("high", "government ID numbers", r"passport|ssn|social_?security|national_?id|tax_?id|driver_?licen[cs]e|^nin$|aadhaar"),
    ("high", "dates of birth", r"^dob$|birth_?date|date_?of_?birth|birthday"),
    ("high", "health details", r"diagnos|medical|medication|allerg|health_"),
    ("medium", "email addresses", r"e_?mail"),
    ("medium", "phone numbers", r"phone|mobile|telephone|whatsapp"),
    ("medium", "home addresses", r"address|street|post_?code|zip_?code|^zip$"),
    ("medium", "precise locations", r"^lat$|latitude|^lng$|^lon$|longitude"),
    ("medium", "IP addresses", r"ip_?addr|^ip$"),
    ("low", "people's names", r"first_?name|last_?name|full_?name|surname|display_?name|^name$"),
    ("low", "private messages or notes", r"message|^body$|^content$|^notes?$|chat"),
]]


def classify(column: str) -> tuple[str, str] | None:
    """(grade, label) for the worst rule the name matches, or None."""
    for sev, label, rx in RULES:
        if rx.search(column):
            return sev, label
    return None


def classify_columns(columns) -> list[tuple[str, str, str]]:
    """[(column, grade, label)] worst first."""
    hits = [(c, *hit) for c in columns if (hit := classify(c))]
    return sorted(hits, key=lambda h: (RANK[h[1]], h[0]))


def worst(columns) -> str | None:
    hits = classify_columns(columns)
    return hits[0][1] if hits else None
