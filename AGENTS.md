# Working in patet

See what an anonymous visitor can read from your own Supabase-backed app, without reading a single row.

## Run the tests

You need Python 3.11 or newer.

```bash
PYTHONPATH=src:tests python -m unittest discover -s tests
```

Every check should pass before you start and after you finish.

## Where things are

- `src/`: the code
- `live/`: checks that run against a real database server
- `tests/`: the tests
- `examples/`: worked examples
- `docs/`: written documentation

## Before you commit

- Make sure the checks pass.
- Put changes people will notice in `CHANGELOG.md`.
- Do not put real passwords, keys or private data in test files or examples. Use made-up ones.
