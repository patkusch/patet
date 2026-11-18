"""Turn what patet saw into graded findings, in plain words, as text or JSON."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field

from .bundle import Found
from .fixes import sql_fix
from .pii import classify_columns
from .probe import TableResult
from .surface import AuthSettings, BucketResult

GRADES = ("critical", "high", "medium", "low", "info")
# A table anyone can read is graded by the worst personal data its column names suggest.
_TABLE_GRADE = {"critical": "critical", "high": "critical", "medium": "high", "low": "medium", None: "medium"}


@dataclass
class Finding:
    grade: str
    title: str
    why: str
    fix: str
    where: str = ""


@dataclass
class Report:
    page: str | None
    project: str | None
    found: Found
    tables: list[TableResult] = field(default_factory=list)
    buckets: list[BucketResult] = field(default_factory=list)
    auth: AuthSettings | None = None
    probed: bool = False
    findings: list[Finding] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        return any(f.grade in ("critical", "high") for f in self.findings)


def _rows(n: int | None) -> str:
    if n is None:
        return "its rows"
    return f"{n:,} row" + ("" if n == 1 else "s")


def analyse(rep: Report) -> list[Finding]:
    out: list[Finding] = []
    for k in rep.found.server_keys:
        out.append(Finding(
            "critical", "A server key is in your website's code",
            f"The {k.kind} key ({k.masked}) skips every row rule. Anyone who opens the page can read, "
            "change and delete everything in the project.",
            "Rotate it in the Supabase dashboard now, then use only the anon or publishable key in the browser.",
            k.where))
    for t in rep.tables:
        if t.state != "exposed":
            continue
        cols = t.columns or sorted(rep.found.tables.get(t.name, ()))
        hits = classify_columns(cols)
        grade = _TABLE_GRADE[hits[0][1] if hits else None]
        labels = sorted({h[2] for h in hits}, key=lambda l: [h[2] for h in hits].index(l))
        source = "Its columns" if t.columns else "The columns your code asks for"
        if hits:
            why = f"{source} hold {', '.join(labels)} ({', '.join(h[0] for h in hits)}). "
        elif not cols:
            why = ("patet could not see its columns, because your code asks for all of them (`*`). "
                   "Run with --columns to grade what it holds. ")
        else:
            why = "Fine only if every row is meant to be public. "
        why += "A visitor needs only the key in your page, no login."
        out.append(Finding(grade, f"Anyone can read {_rows(t.rows)} of `{t.name}`", why,
                           "Turn on row level security for this table and add a rule for who may read "
                           "which rows. `patet check --fix` prints the SQL.", t.name))
    for b in rep.buckets:
        if b.state == "listable":
            out.append(Finding("high", f"Anyone can list the files in the `{b.name}` bucket",
                               "File names often hold names or dates, and a listed file can be downloaded "
                               "if the bucket is public.",
                               "Add a storage rule so only the owner can list their own folder.", b.name))
    a = rep.auth
    if a and a.signup_open and a.autoconfirm:
        out.append(Finding("medium", "Anyone can sign up and is let in straight away",
                           "Email confirmation is off, so a rule that lets any signed-in user read is as "
                           "open as no rule at all.",
                           "Turn on email confirmation, and write rules that check whose row it is.", "auth"))
    if a and a.anonymous:
        out.append(Finding("medium", "Anonymous sign-ins are on",
                           "Every visitor can become a signed-in user, so rules for signed-in users "
                           "cover everyone.", "Check each rule that says `to authenticated`.", "auth"))
    if rep.found.functions:
        names = ", ".join(sorted(rep.found.functions))
        out.append(Finding("info", f"Your site calls {len(rep.found.functions)} database function(s): {names}",
                           "patet does not call them. A function marked SECURITY DEFINER skips row rules.",
                           "Check each one runs as SECURITY INVOKER, or checks the caller itself.", "rpc"))
    return sorted(out, key=lambda f: GRADES.index(f.grade))


def to_json(rep: Report) -> str:
    d = {
        "page": rep.page,
        "project": rep.project,
        "probed": rep.probed,
        "keys": [{"kind": k.kind, "key": k.masked, "where": k.where} for k in rep.found.keys.values()],
        "tables": [asdict(t) for t in rep.tables],
        "buckets": [asdict(b) for b in rep.buckets],
        "auth": asdict(rep.auth) if rep.auth else None,
        "functions": sorted(rep.found.functions),
        "findings": [asdict(f) for f in rep.findings],
        "summary": {g: sum(f.grade == g for f in rep.findings) for g in GRADES},
    }
    return json.dumps(d, indent=2)


def to_text(rep: Report, fix: bool = False) -> str:
    L: list[str] = []
    if rep.page:
        L.append(f"Page:     {rep.page}")
    L.append(f"Project:  {rep.project or 'not found'}")
    keys = ", ".join(f"{k.kind} {k.masked}" for k in rep.found.keys.values()) or "none found"
    L.append(f"Keys:     {keys}")
    if rep.tables:
        L += ["", "What a visitor can read, table by table:", ""]
        w = max(len(t.name) for t in rep.tables)
        for t in rep.tables:
            rows = f"{t.rows:,} rows" if t.state == "exposed" and t.rows is not None else ""
            word = {"exposed": "OPEN", "hidden": "no rows", "blocked": "closed", "missing": "missing",
                    "error": "error"}[t.state]
            L.append(f"  {t.name:<{w}}  {word:<8} {rows}")
    elif rep.found.tables:
        L += ["", "Tables your code names: " + ", ".join(sorted(rep.found.tables))]
    if rep.findings:
        L += [""]
        for f in rep.findings:
            L += [f"[{f.grade.upper()}] {f.title}", f"  Why: {f.why}", f"  Fix: {f.fix}", ""]
    else:
        L += ["", "Nothing open found." if rep.probed else ""]
    if fix:
        opened = [t for t in rep.tables if t.state == "exposed"]
        if opened:
            L += ["SQL to review before you run it (Supabase SQL editor):", ""]
            for t in opened:
                L += [sql_fix(t.name, t.columns or rep.found.tables.get(t.name, ())), ""]
    return "\n".join(L).rstrip() + "\n"
