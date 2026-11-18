# patet

*Latin: "it lies open."*

[![tests](https://github.com/patkusch/patet/actions/workflows/tests.yml/badge.svg)](https://github.com/patkusch/patet/actions/workflows/tests.yml)

See what a stranger can read from your own Supabase-backed app, without reading a single row.

Apps built with Lovable, Bolt, Cursor or Claude Code often talk to Supabase straight from the browser. That is safe only when every table has row rules. When one does not, anyone who opens the site can read the whole table. patet looks at your app the way a stranger would and tells you which tables are open, how many rows they hold, and what kind of personal data the column names suggest.

## Why now

In November 2026 researchers found that 24,664 of 34,545 Lovable apps on Supabase handed over database records to visitors who had not logged in. Some held passport details and private messages ([Crissy Field research](https://www.crissyfield.de/research/lovable-en/); [Hacker News discussion](https://news.ycombinator.com/item?id=50499017)). The cause in nearly every case was a table with no row rules. The researchers published no tool, so builders had nothing to run on their own app.

## What it does

- **Finds your project and key** in the HTML and JavaScript your site sends to every visitor.
- **Finds the tables your code uses**, by reading its `.from("...")` calls, including code split into lazily loaded files.
- **Counts what a stranger can read** from each table. It asks Supabase for a row count only, so no rows are downloaded.
- **Grades each open table** by the personal data its column names suggest: passwords and card numbers worst, then ID numbers, then emails and phone numbers.
- **Checks storage buckets** for file listings a stranger can see, and **sign-up settings** that make "signed-in users only" rules open to everyone.
- **Catches a server key in your site's code**, which skips every rule. This works offline on a build folder too, so CI can stop it before it ships.
- **Prints the SQL to close each open table**, for you to read before you run it.

## Install and run

```bash
pip install git+https://github.com/patkusch/patet
```

Look at your live app:

```bash
patet check https://myapp.example --i-own-this
```

Read a build folder before you deploy (no network):

```bash
patet scan dist
```

Without `--i-own-this`, patet reads only your public web page and stops before asking Supabase anything.

| Option | What it does |
|---|---|
| `--i-own-this` | Confirms the app is yours. Nothing is asked of Supabase without it. |
| `--columns` | For each open table, reads one row to learn the column names. The values are dropped at once and never printed. |
| `--fix` | Prints SQL to close each open table. |
| `--tables a,b` | Checks tables your code does not name. |
| `--guess` | Also tries 30 common table names such as `users`, `messages` and `orders`. |
| `--supabase-url`, `--key` | Use these when the page does not show the project address or key. |
| `--json` | Prints JSON instead of text. |
| `--delay` | Seconds between requests. Default 0.25. |

patet exits with 1 when it finds anything graded high or critical, 2 when it could not run, and 0 otherwise.

## What the output looks like

This run is against the fake project in the tests.

```text
Page:     https://myapp.example/
Project:  abcdefghijklmnopqrst
Keys:     anon eyJhbGciOi…ssss

What a visitor can read, table by table:

  profiles  OPEN     57 rows
  notes     no rows
  payroll   closed
  orders    missing

[CRITICAL] Anyone can read 57 rows of `profiles`
  Why: Its columns hold government ID numbers, email addresses, people's names (passport_number, email, full_name). A visitor needs only the key in your page, no login.
  Fix: Turn on row level security for this table and add a rule for who may read which rows. `patet check --fix` prints the SQL.

[HIGH] Anyone can list the files in the `avatars` bucket
  Why: File names often hold names or dates, and a listed file can be downloaded if the bucket is public.
  Fix: Add a storage rule so only the owner can list their own folder.

[MEDIUM] Anyone can sign up and is let in straight away
  Why: Email confirmation is off, so a rule that lets any signed-in user read is as open as no rule at all.
  Fix: Turn on email confirmation, and write rules that check whose row it is.

SQL to review before you run it (Supabase SQL editor):

-- profiles: stop anonymous visitors reading every row
alter table public.profiles enable row level security;
create policy "profiles: people read their own rows" on public.profiles
  for select to authenticated using ((select auth.uid()) = user_id);
-- If visitors never need this table at all: revoke select on public.profiles from anon;
```

## In GitHub Actions

Fail the build when a server key ends up in your built site:

```yaml
- run: npm run build
- uses: patkusch/patet@v0.1.0
  with:
    path: dist
```

## What it can and can't tell you

| patet says | It shows | It does not show |
|---|---|---|
| a table is open | a stranger with your page's key can read that many rows | what is in them. patet never looks |
| no rows | Supabase handed back zero rows | whether the table is empty or a rule hides every row. Both are fine for strangers |
| a column holds emails | the column's name looks like it | what it really holds. A column called `notes` full of passport numbers is missed |
| nothing open | none of the tables it tried were open | tables your code never names. Add `--tables` or `--guess` |
| a server key is in your code | something shaped like a service role or secret key was found | whether it still works. Rotate it anyway |

patet checks reading only. It never writes, so it cannot tell you whether a stranger can add, change or delete rows. It does not call your database functions. It does not read your database's settings from the inside. The Supabase dashboard's Security Advisor does that, and the two together give the fuller picture.

Since April 2026 Supabase no longer gives the list of tables to the browser key ([changelog](https://supabase.com/changelog/42949-breaking-change-removing-access-to-openapi-spec-via-the-anon-key)). That is why patet starts from the table names in your own code.

## Use it only on your own apps

patet is for checking apps you own or have written permission to test. It sends one request per table, waits between requests, downloads no rows by default, and keeps nothing on disk. Checking someone else's project without permission may be illegal where you live.

## Tests

```bash
make test
```

The tests run against a fake Supabase project and website on your own machine. They check that counting never downloads rows, that nothing reaches Supabase without `--i-own-this`, and that no full key or row value ever appears in the output. CI runs them on Python 3.11 to 3.14 and runs the GitHub Action against a clean and a leaky build folder.

## Licence

MIT
