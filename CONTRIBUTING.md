# Contributing

Thank you for helping. The most useful things to add are a column name patet grades wrongly, and a way apps name their tables that patet does not yet read.

## Add a column name

Everything patet guesses about personal data is in `src/patet/pii.py`. Each rule has a grade, a plain-English label and a pattern for column names. Add a case to `tests/test_pii.py` for the name you want caught, and one for a harmless name that looks like it, such as `email_verified` beside `email`.

Write labels the way a person would say them: "dates of birth", not "DOB_FIELD". They appear in every report.

## Add a way of naming tables

patet finds tables in an app's code by reading calls such as `supabase.from("profiles")`. The patterns are at the top of `src/patet/bundle.py`. Add the minified or bundled form you have seen to `tests/test_bundle.py` first, then teach the pattern.

## Check your work

```bash
make test
```

Every test must pass. The live test against real Postgres and PostgREST runs in CI; see [live/README.md](live/README.md) to run it yourself.

## Anything else

- Keep patet free of extra packages. It runs on the Python standard library alone.
- patet never downloads rows when counting, never prints a row value or a full key, and never asks Supabase anything without `--i-own-this`. Changes that would break any of these will not be merged.
- Build fake keys at run time in tests, as `tests/helpers.py` does. Never commit a real key.
- Report a security problem privately, as described in [SECURITY.md](SECURITY.md), not in a public issue.
