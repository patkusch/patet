"""SQL to close a table that anonymous visitors can read. Printed for you to review, never run."""

from __future__ import annotations

import re

OWNER_COLUMNS = ("user_id", "owner_id", "profile_id", "created_by", "author_id", "account_id")
_SAFE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,62}$")


def sql_fix(table: str, columns=()) -> str:
    if not _SAFE.match(table):
        return f"-- {table!r}: not a plain table name, so no SQL is suggested"
    t = f"public.{table}"
    owner = next((c for c in OWNER_COLUMNS if c in set(columns)), None)
    lines = [
        f"-- {table}: stop anonymous visitors reading every row",
        f"alter table {t} enable row level security;",
    ]
    if owner:
        lines += [
            f'create policy "{table}: people read their own rows" on {t}',
            f"  for select to authenticated using ((select auth.uid()) = {owner});",
        ]
    else:
        lines += [
            "-- Then add a rule for who may read which rows. If each row belongs to a user:",
            f'-- create policy "{table}: people read their own rows" on {t}',
            "--   for select to authenticated using ((select auth.uid()) = user_id);",
        ]
    lines.append(f"-- If visitors never need this table at all: revoke select on {t} from anon;")
    return "\n".join(lines)
