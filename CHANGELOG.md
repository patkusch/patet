# Changelog

## 0.1.0 (2026-11-18)

First release.

- `patet check URL --i-own-this` reads your site's HTML and JavaScript, finds the Supabase project, the browser key and the tables your code uses, then counts what a stranger can read from each table without downloading rows.
- Open tables are graded by the personal data their column names suggest. `--columns` learns the names from one row and drops the values.
- Checks storage bucket listings and sign-up settings.
- Flags a service role or secret key in your site's code as critical.
- `patet scan FOLDER` does the key and table checks on a build folder, offline. A GitHub Action wraps it.
- `--fix` prints SQL to close each open table, for review.
